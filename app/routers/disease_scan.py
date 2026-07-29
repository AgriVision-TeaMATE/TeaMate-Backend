import json
import random
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models import DiseaseScan, Field, User
from ..schemas.disease_scan import (
    ConfidenceItem,
    Classification,
    DiseaseScanAPIResponse,
    DiseaseScanResponse,
    Meta,
    MostProbableDisease,
    ScanSummary,
    WeatherSummary,
)
from ..services.disease_analysis import (
    classify_result,
    resolve_predictions,
    _classification_message,
)
from ..services.disease_ml_client import (
    MLPredictionError,
    predict_disease_from_image,
)

router = APIRouter(prefix="/disease", tags=["Disease Scan"])

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "media" / "disease-scans"

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/jpg",
}

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024

def _validate_image_type(content_type: str | None) -> None:
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Invalid image type: {content_type}. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )


def _generate_scan_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = "".join(str(random.randint(0, 9)) for _ in range(4))
    return f"scan_{timestamp}_{random_suffix}"


def _persist_image_bytes(content: bytes, original_filename: str | None) -> str:
    """Writes already-read image bytes to disk. Returns the public-facing URL."""
    suffix = Path(original_filename or "image.jpg").suffix or ".jpg"
    file_name = f"{UUID(int=random.getrandbits(128))}{suffix}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    destination = UPLOAD_DIR / file_name

    with destination.open("wb") as buffer:
        buffer.write(content)

    return f"/media/disease-scans/{file_name}"


@router.post(
    "/scan",
    response_model=DiseaseScanAPIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Analyze a tea leaf image for disease",
    description=(
        "Accepts a leaf image plus optional field, GPS, weather, and "
        "environmental metadata as multipart/form-data. Sends the image + "
        "weather to the ML backend for classification, applies weather-based "
        "risk rules, resolves disease reference info, and persists the scan."
    ),
)
async def scan_disease(
    image: UploadFile = File(..., description="Leaf image (jpeg/png/webp)"),
    field_id: UUID | None = Form(default=None),
    latitude: float | None = Form(default=None, description="GPS latitude"),
    longitude: float | None = Form(default=None, description="GPS longitude"),
    weather_summary: str | None = Form(
        default=None,
        description="JSON string matching the WeatherSummary schema",
    ),
    environmental_data: str | None = Form(
        default=None, description="Freeform JSON metadata (soil moisture, pH, etc.)"
    ),
    scan_date: datetime | None = Form(
        default=None, description="ISO datetime of the scan; defaults to server time if omitted"
    ),
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

    weather_data: WeatherSummary | None = None
    if weather_summary:
        try:
            weather_data = WeatherSummary.model_validate_json(weather_summary)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid weather_summary: {e}")

    env_data = None
    if environmental_data:
        try:
            env_data = json.loads(environmental_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid environmental_data JSON format")

    effective_scan_datetime = scan_date or datetime.now()
    weather_dict = weather_data.model_dump() if weather_data else {}

    # --- Read image once, use for both storage and ML call -------------------
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

    # --- Call ML backend -------------------------------------------------------
    try:
        raw_predictions = await predict_disease_from_image(content, weather_dict)
    except MLPredictionError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Disease analysis failed: {e}")

    if not raw_predictions:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="ML backend returned no predictions")

    # --- Resolve against disease reference table (Step 4) ----------------------
    scored = resolve_predictions(db, raw_predictions, top_n=3)
    classification = classify_result(scored)
    if not scored:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="None of the predicted classes matched known disease reference data",
        )

    top = scored[0]

    # --- Risk analysis (Step 3, rule-based) -------------------------------------
    # risk = assess_risk(weather_dict)

    # --- AI explanations per top prediction (Step 5) -----------------------------
    # explanations = [
    #     AIExplanation(
    #         disease=s.disease.name,
    #         explanation=build_ai_explanation(s.disease, risk),
    #         recommended_actions=s.disease.recommendations,
    #     )
    #     for s in scored
    # ]

    scan_id = _generate_scan_id()

    # --- Persist (Step 6) --------------------------------------------------------
    disease_scan = DiseaseScan(
        scan_id=scan_id,
        field_id=field_id,
        latitude=latitude,
        longitude=longitude,
        scan_datetime=effective_scan_datetime,
        image_url=image_url,
        detected_disease=top.disease.name,
        severity=top.disease.severity_default,
        confidence=top.probability,
        description=top.disease.description,
        weather_summary=weather_dict or None,
        environmental_data=env_data,
        # risk_level=risk.level,
        # risk_reason=risk.reason,
        treatment_suggestions=top.disease.recommendations,
        all_predictions=[
            {"disease": s.disease.name, "class_key": s.disease.class_key, "probability": s.probability}
            for s in scored
        ],
        # ai_explanation=explanations[0].explanation,
        model_version="ml-backend",  # replace once ML backend reports its own version
        inference_time_ms=None,  # populate once ML backend reports timing
    )

    try:
        db.add(disease_scan)
        db.commit()
        db.refresh(disease_scan)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save scan record")

    # --- Build response ------------------------------------------------------------
    return DiseaseScanAPIResponse(
    scan_id=scan_id,
    status="success",

    scan_summary=ScanSummary(
        field_id=field_id,
        field_name=field.name if field else None,
        date=effective_scan_datetime.date(),
        time=effective_scan_datetime.time(),
        weather_details=weather_data,
        image_url=image_url,
        latitude=latitude,
        longitude=longitude,
        scan_datetime=effective_scan_datetime,
    ),

    most_probable_disease=MostProbableDisease(
        disease_name=top.disease.name,
        confidence=top.probability,
        severity=top.disease.severity_default,
        description=top.disease.description,
        causes=top.disease.causes,
    ),

    confidence_analysis=[
        ConfidenceItem(
            disease=s.disease.name,
            probability=s.probability,
            confidence_label=s.confidence,
            category=s.disease.category,
        )
        for s in scored
    ],

    classification=Classification(
        level=classification.level,
        label=classification.label,
        confidence=classification.confidence,
        category=classification.category,
        message=_classification_message(classification),
    ),

    recommendations=top.disease.recommendations,

    meta=Meta(
        model_version=disease_scan.model_version,
        inference_time_ms=disease_scan.inference_time_ms,
        timestamp=datetime.now(),
    ),
)

@router.get("/{scan_id}", response_model=DiseaseScanResponse)
def get_scan(
    scan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = db.scalar(select(DiseaseScan).where(DiseaseScan.id == scan_id))
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    if scan.field_id:
        field = db.get(Field, scan.field_id)
        if not field or field.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this scan")

    return scan

# @router.get("/list", response_model=list[DiseaseScanResponse])
# def list_scans(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     stmt = (
#         select(DiseaseScan)
#         .join(Field, DiseaseScan.field_id == Field.id, isouter=True)
#         .where(Field.user_id == current_user.id)
#         .order_by(DiseaseScan.created_at.desc())
#     )
#     return db.scalars(stmt).all()

@router.get("/by-field/{field_id}", response_model=list[DiseaseScanResponse])
def list_scans_by_field(
    field_id: UUID,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    field = db.scalar(
        select(Field).where(Field.id == field_id, Field.user_id == current_user.id)
    )
    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field not found or not owned by user",
        )

    stmt = (
        select(DiseaseScan)
        .where(DiseaseScan.field_id == field_id)
        .order_by(DiseaseScan.scan_datetime.desc())
        .offset(offset)
        .limit(limit)
    )
    return db.scalars(stmt).all()

@router.get("/by-location/nearby", response_model=list[DiseaseScanResponse])
def list_scans_by_location(
    latitude: float,
    longitude: float,
    radius_degrees: float = 0.01,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(DiseaseScan).where(
        DiseaseScan.field_id.is_(None),
        DiseaseScan.latitude.between(latitude - radius_degrees, latitude + radius_degrees),
        DiseaseScan.longitude.between(longitude - radius_degrees, longitude + radius_degrees),
    ).order_by(DiseaseScan.created_at.desc())
    return db.scalars(stmt).all()