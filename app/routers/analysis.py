import random
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import HarvestRound, AnalysisImage, BudMarker
from ..models.harvest_round import RoundStatus
from ..schemas.analysis_image import AnalysisImageCreate, AnalysisImageResponse
from ..schemas.harvest_round import HarvestRoundResponse
from ..services.ml_client import analyze_image_with_ml
from ..services.yield_calculator import calculate_predicted_yield

router = APIRouter(tags=["Analysis & ML"])


@router.post(
    "/rounds/{round_id}/images",
    response_model=AnalysisImageResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_analysis_image(
    round_id: UUID, data: AnalysisImageCreate, db: Session = Depends(get_db)
):
    round_obj = db.get(HarvestRound, round_id)
    if not round_obj:
        raise HTTPException(status_code=404, detail="Harvest round not found")

    image = AnalysisImage(harvest_round_id=round_id, **data.model_dump())
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


@router.get("/images/{image_id}", response_model=AnalysisImageResponse)
def get_image(image_id: UUID, db: Session = Depends(get_db)):
    stmt = select(AnalysisImage).where(AnalysisImage.id == image_id).options(
        selectinload(AnalysisImage.bud_markers)
    )
    img = db.scalar(stmt)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    return img


@router.post("/rounds/{round_id}/analyze", response_model=HarvestRoundResponse)
async def analyze_round_images(round_id: UUID, db: Session = Depends(get_db)):
    stmt = select(HarvestRound).where(HarvestRound.id == round_id).options(
        selectinload(HarvestRound.analysis_images).selectinload(
            AnalysisImage.bud_markers
        ),
        selectinload(HarvestRound.weather_log),
    )
    round_obj = db.scalar(stmt)
    if not round_obj:
        raise HTTPException(status_code=404, detail="Harvest round not found")

    round_obj.status = RoundStatus.analyzing
    db.commit()

    pending = [img for img in round_obj.analysis_images if not img.is_analyzed]

    for img in pending:
        try:
            res = await analyze_image_with_ml(img.firebase_url)
            img.arimbu_count = res.get("arimbu_count", 0)
            img.pluckable_count = res.get("pluckable_count", 0)
            total = img.arimbu_count + img.pluckable_count
            img.pluckable_ratio = (
                round(img.pluckable_count / total, 4) if total > 0 else 0.0
            )
            img.captured_area_sqm = round(random.uniform(6.0, 10.0), 2)
            img.is_analyzed = True
            img.analyzed_at = datetime.now(timezone.utc)

            base64_img = res.get("image", "")
            if base64_img:
                img.firebase_url = f"data:image/jpeg;base64,{base64_img}"
        except Exception as e:
            # Revert status on failure
            round_obj.status = RoundStatus.draft
            db.commit()
            raise HTTPException(
                status_code=502, detail=f"ML Analysis Failed: {str(e)}"
            )

    # Update round aggregated statistics
    all_images = round_obj.analysis_images
    if all_images:
        round_obj.total_arimbu_count = sum(i.arimbu_count for i in all_images)
        round_obj.total_pluckable_count = sum(
            i.pluckable_count for i in all_images
        )
        round_obj.total_captured_area_sqm = sum(
            i.captured_area_sqm for i in all_images
        )
        ratios = [
            i.pluckable_ratio for i in all_images if i.pluckable_ratio is not None
        ]
        avg_ratio = sum(ratios) / len(ratios) if ratios else 0.0
        round_obj.avg_pluckable_ratio = round(avg_ratio, 4)

        # Set readiness and priority labels
        if 0.60 <= avg_ratio <= 0.70:
            round_obj.readiness_status = "ready_to_pluck"
            round_obj.labor_priority = "dispatch_now"
        elif avg_ratio > 0.70:
            round_obj.readiness_status = "overgrown"
            round_obj.labor_priority = "urgent_review"
        elif avg_ratio >= 0.50:
            round_obj.readiness_status = "maturing"
            round_obj.labor_priority = "prepare_crew"
        else:
            round_obj.readiness_status = "needs_growth"
            round_obj.labor_priority = "monitor_only"

    round_obj.status = RoundStatus.analyzed
    db.commit()
    db.refresh(round_obj)
    return round_obj


@router.post("/rounds/{round_id}/predict-yield", response_model=HarvestRoundResponse)
def predict_round_yield(round_id: UUID, db: Session = Depends(get_db)):
    stmt = select(HarvestRound).where(HarvestRound.id == round_id).options(
        selectinload(HarvestRound.analysis_images),
        selectinload(HarvestRound.weather_log),
    )
    round_obj = db.scalar(stmt)
    if not round_obj:
        raise HTTPException(status_code=404, detail="Harvest round not found")

    area = round_obj.field_area_hectares or 1.0
    predicted = calculate_predicted_yield(
        field_area_hectares=area,
        total_pluckable_count=round_obj.total_pluckable_count,
        total_arimbu_count=round_obj.total_arimbu_count,
        avg_pluckable_ratio=round_obj.avg_pluckable_ratio or 0.0,
    )
    round_obj.predicted_yield_kg = predicted
    db.commit()
    db.refresh(round_obj)
    return round_obj
