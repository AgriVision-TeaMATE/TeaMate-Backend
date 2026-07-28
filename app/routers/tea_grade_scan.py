import random
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models import Field, TeaGradeScan, User
from ..schemas.tea_grade_scan import TeaGradeScanResponse
from ..services.tea_grading_ml_client import MLPredictionError, predict_tea_grade_composition

router = APIRouter(prefix="/tea-quality", tags=["Tea Quality"])

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "media" / "tea-quality-scans"

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def _validate_image_type(content_type: str | None) -> None:
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Invalid image type: {content_type}. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )


def _generate_scan_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = "".join(str(random.randint(0, 9)) for _ in range(4))
    return f"tea_{timestamp}_{random_suffix}"


def _persist_image_bytes(content: bytes, original_filename: str | None) -> str:
    """Writes already-read image bytes to disk. Returns the public-facing URL."""
    suffix = Path(original_filename or "image.jpg").suffix or ".jpg"
    file_name = f"{UUID(int=random.getrandbits(128))}{suffix}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    destination = UPLOAD_DIR / file_name

    with destination.open("wb") as buffer:
        buffer.write(content)

    return f"/media/tea-quality-scans/{file_name}"


@router.post(
    "/scan",
    response_model=TeaGradeScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a tea sample image for grade composition prediction",
    description=(
        "Accepts a tea sample image plus an optional field id as "
        "multipart/form-data. Sends the image to the grading ML backend "
        "(currently mocked) and persists the resulting per-grade "
        "composition breakdown."
    ),
)
async def scan_tea_grade(
    image: UploadFile = File(..., description="Tea sample image (jpeg/png/webp)"),
    field_id: UUID | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # --- Field ownership check --------------------------------------------
    field = None
    if field_id:
        field = db.scalar(select(Field).where(Field.id == field_id, Field.user_id == current_user.id))
        if not field:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found or not owned by user")

    # --- Validation ----------------------------------------------------------
    _validate_image_type(image.content_type)

    content = await image.read()
    if len(content) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds max size of {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)}MB",
        )

    try:
        image_url = _persist_image_bytes(content, image.filename)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to store image: {e}")

    # --- Call grading ML backend (mocked for now) -----------------------------
    try:
        raw_predictions = await predict_tea_grade_composition(content)
    except MLPredictionError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Tea grading analysis failed: {e}")

    if not raw_predictions:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="ML backend returned no predictions")

    top = raw_predictions[0]
    grade_composition = {p.grade: p.percentage for p in raw_predictions}
    scan_datetime = datetime.now()
    scan_id = _generate_scan_id()

    # --- Persist ---------------------------------------------------------------
    tea_grade_scan = TeaGradeScan(
        scan_id=scan_id,
        user_id=current_user.id,
        field_id=field_id,
        image_url=image_url,
        scan_datetime=scan_datetime,
        grade_composition=grade_composition,
        dominant_grade=top.grade,
        dominant_grade_percentage=top.percentage,
        total_particles_detected=None,  # populate once the real model reports counts
        model_version="mock-v0",  # replace once a real grading model is wired in
        inference_time_ms=None,
    )

    try:
        db.add(tea_grade_scan)
        db.commit()
        db.refresh(tea_grade_scan)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save scan record")

    # --- Build response ----------------------------------------------------------
    return TeaGradeScanResponse.from_model(tea_grade_scan, field_name=field.name if field else None)


@router.get("/scan/{scan_id}", response_model=TeaGradeScanResponse)
def get_scan(
    scan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = db.scalar(select(TeaGradeScan).where(TeaGradeScan.scan_id == scan_id))
    if not scan or scan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    field_name = None
    if scan.field_id:
        field_name = db.scalar(select(Field.name).where(Field.id == scan.field_id))

    return TeaGradeScanResponse.from_model(scan, field_name=field_name)


@router.get("/scans", response_model=list[TeaGradeScanResponse])
def list_scans(
    field_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(TeaGradeScan, Field.name)
        .outerjoin(Field, TeaGradeScan.field_id == Field.id)
        .where(TeaGradeScan.user_id == current_user.id)
    )
    if field_id:
        stmt = stmt.where(TeaGradeScan.field_id == field_id)
    stmt = stmt.order_by(TeaGradeScan.created_at.desc())

    rows = db.execute(stmt).all()
    return [TeaGradeScanResponse.from_model(scan, field_name=field_name) for scan, field_name in rows]
