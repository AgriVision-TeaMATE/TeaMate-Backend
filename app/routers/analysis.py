import random
import shutil
from uuid import UUID
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models import HarvestRound, AnalysisImage, Field, User
from ..schemas.analysis_image import AnalysisImageResponse
from ..schemas.harvest_round import HarvestRoundResponse
from ..services.image_storage import (
    UPLOAD_DIR,
    delete_analysis_file_for_url,
    local_path_for_image_url,
    replace_analysis_file_with_base64,
)
from ..services.ml_client import analyze_image_with_ml
from ..services.yield_calculator import calculate_predicted_yield

router = APIRouter(tags=["Analysis & ML"])


def _recalculate_total_captured_area(round_obj: HarvestRound) -> None:
    round_obj.total_captured_area_sqm = round(
        sum(float(img.captured_area_sqm or 0) for img in round_obj.analysis_images),
        2,
    )


def _store_uploaded_image(upload: UploadFile) -> Path:
    suffix = Path(upload.filename or "image.jpg").suffix or ".jpg"
    file_name = f"{UUID(int=random.getrandbits(128))}{suffix}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    destination = UPLOAD_DIR / file_name
    with destination.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)
    return destination


@router.post(
    "/rounds/{round_id}/images",
    response_model=AnalysisImageResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_analysis_image(
    round_id: UUID,
    request: Request,
    image: UploadFile = File(...),
    captured_area_sqm: float = Form(8.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    round_obj = db.scalar(
        select(HarvestRound)
        .join(Field, HarvestRound.field_id == Field.id)
        .where(HarvestRound.id == round_id, Field.user_id == current_user.id)
    )
    if not round_obj:
        raise HTTPException(status_code=404, detail="Harvest round not found")
    if round_obj.is_completed:
        raise HTTPException(
            status_code=400,
            detail="Completed round is locked for new image uploads.",
        )

    stored_path = _store_uploaded_image(image)
    image_url = str(
        request.url_for("media", path=f"analysis-images/{stored_path.name}")
    )

    analysis_image = AnalysisImage(
        harvest_round_id=round_id,
        image_url=image_url,
        captured_area_sqm=captured_area_sqm,
        arimbu_count=0,
        pluckable_count=0,
    )
    db.add(analysis_image)
    round_obj.total_captured_area_sqm = round(
        float(round_obj.total_captured_area_sqm or 0) + captured_area_sqm,
        2,
    )
    db.commit()
    db.refresh(analysis_image)
    return analysis_image


@router.get("/images/{image_id}", response_model=AnalysisImageResponse)
def get_image(
    image_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(AnalysisImage)
        .join(HarvestRound, AnalysisImage.harvest_round_id == HarvestRound.id)
        .join(Field, HarvestRound.field_id == Field.id)
        .where(AnalysisImage.id == image_id, Field.user_id == current_user.id)
    )
    img = db.scalar(stmt)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    return img


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    image_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(AnalysisImage)
        .join(HarvestRound, AnalysisImage.harvest_round_id == HarvestRound.id)
        .join(Field, HarvestRound.field_id == Field.id)
        .where(AnalysisImage.id == image_id, Field.user_id == current_user.id)
        .options(selectinload(AnalysisImage.harvest_round))
    )
    img = db.scalar(stmt)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    if img.harvest_round.is_completed:
        raise HTTPException(
            status_code=400,
            detail="Completed round images cannot be deleted.",
        )
    if img.arimbu_count > 0 or img.pluckable_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Analyzed images cannot be deleted from this screen.",
        )

    round_obj = img.harvest_round
    delete_analysis_file_for_url(img.image_url)
    db.delete(img)
    db.flush()
    _recalculate_total_captured_area(round_obj)
    db.commit()


@router.post("/rounds/{round_id}/analyze", response_model=HarvestRoundResponse)
async def analyze_round_images(
    round_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(HarvestRound).join(Field, HarvestRound.field_id == Field.id).where(
        HarvestRound.id == round_id, Field.user_id == current_user.id
    ).options(
        selectinload(HarvestRound.analysis_images).selectinload(
            AnalysisImage.bud_markers
        ),
        selectinload(HarvestRound.weather_log),
    )
    round_obj = db.scalar(stmt)
    if not round_obj:
        raise HTTPException(status_code=404, detail="Harvest round not found")
    if round_obj.is_completed:
        raise HTTPException(
            status_code=400,
            detail="Completed round cannot be analyzed again.",
        )
    round_obj.plucking_status = "analyzing"
    db.commit()

    pending_images = [
        img
        for img in round_obj.analysis_images
        if img.arimbu_count == 0 and img.pluckable_count == 0
    ]

    for img in pending_images:
        try:
            image_input = local_path_for_image_url(img.image_url) or img.image_url
            res = await analyze_image_with_ml(str(image_input))
            img.arimbu_count = res.get("arimbu_count", 0)
            img.pluckable_count = res.get("pluckable_count", 0)
            replace_analysis_file_with_base64(img.image_url, res.get("image", ""))
        except Exception as e:
            round_obj.plucking_status = "awaiting_analysis"
            db.commit()
            raise HTTPException(
                status_code=502, detail=f"ML Analysis Failed: {str(e)}"
            )

    # Update round aggregated statistics
    all_images = round_obj.analysis_images
    if all_images:
        ratios = [
            (i.pluckable_count / (i.arimbu_count + i.pluckable_count))
            for i in all_images
            if (i.arimbu_count + i.pluckable_count) > 0
        ]
        avg_ratio = sum(ratios) / len(ratios) if ratios else 0.0
        round_obj.pluckable_ratio = round(avg_ratio, 4)

        if 0.60 <= avg_ratio <= 0.70:
            round_obj.plucking_status = "ready_to_pluck"
        elif avg_ratio > 0.70:
            round_obj.plucking_status = "overgrown"
        elif avg_ratio >= 0.50:
            round_obj.plucking_status = "maturing"
        else:
            round_obj.plucking_status = "needs_growth"
    else:
        round_obj.plucking_status = "awaiting_analysis"
    db.commit()
    db.refresh(round_obj)
    return round_obj


@router.post("/rounds/{round_id}/predict-yield", response_model=HarvestRoundResponse)
def predict_round_yield(
    round_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(HarvestRound).join(Field, HarvestRound.field_id == Field.id).where(
        HarvestRound.id == round_id, Field.user_id == current_user.id
    ).options(
        selectinload(HarvestRound.analysis_images),
        selectinload(HarvestRound.weather_log),
    )
    round_obj = db.scalar(stmt)
    if not round_obj:
        raise HTTPException(status_code=404, detail="Harvest round not found")
    if round_obj.is_completed:
        raise HTTPException(
            status_code=400,
            detail="Completed round prediction cannot be changed.",
        )

    area = float(round_obj.field.area_hectares) if round_obj.field else 1.0
    total_pluckable_count = sum(
        image.pluckable_count for image in round_obj.analysis_images
    )
    total_arimbu_count = sum(image.arimbu_count for image in round_obj.analysis_images)
    predicted = calculate_predicted_yield(
        field_area_hectares=area,
        total_captured_area_sqm=float(round_obj.total_captured_area_sqm or 0),
        total_pluckable_count=total_pluckable_count,
        total_arimbu_count=total_arimbu_count,
        avg_pluckable_ratio=float(round_obj.pluckable_ratio or 0.0),
    )
    round_obj.predicted_yield = predicted
    db.commit()
    db.refresh(round_obj)
    return round_obj
