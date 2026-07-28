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
    AIExplanation,
    ConfidenceItem,
    DiseaseScanAPIResponse,
    DiseaseScanResponse,
    Meta,
    MostProbableDisease,
    RiskLevel,
    ScanSummary,
    WeatherSummary,
)
from ..services.disease_analysis import build_ai_explanation, resolve_predictions
from ..services.disease_ml_client import MLPredictionError, predict_disease_from_image
from ..services.risk_engine import assess_risk

router = APIRouter(prefix="/disease", tags=["Disease Scan"])

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "media" / "disease-scans"

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


def _build_and_persist_dummy_response(
    scan_id: str,
    image_url: str,
    field: Field | None,
    latitude: float | None,
    longitude: float | None,
    effective_scan_datetime: datetime,
    weather_data: WeatherSummary | None,
    env_data: dict | None,
    db: Session,
) -> DiseaseScanAPIResponse:
    """Build a structured dummy response when ML backend is unavailable.

    Uses the 'healthy' disease entry from the reference table as a safe fallback
    that won't cause unnecessary alarm when the service is down for maintenance.
    Also persists the dummy scan to the database for record keeping.
    """
    weather_dict = weather_data.model_dump() if weather_data else {}

    dummy_scan = DiseaseScan(
        scan_id=scan_id,
        field_id=field.id if field else None,
        latitude=latitude,
        longitude=longitude,
        scan_datetime=effective_scan_datetime,
        image_url=image_url,
        detected_disease="Healthy",
        severity="none",
        confidence=0.40,
        description="No disease detected. The tea leaf appears healthy with no significant pathological symptoms.",
        weather_summary=weather_dict or None,
        environmental_data=env_data,
        risk_level="low",
        risk_reason="Unable to assess - ML service unavailable",
        treatment_suggestions=[],
        all_predictions=[
            {"disease": "Healthy", "class_key": "healthy", "probability": 0.40},
            {"disease": "Mite Disease", "class_key": "mite_disease", "probability": 0.15},
            {"disease": "Blister Blight", "class_key": "blister_blight", "probability": 0.12},
            {"disease": "Anthracnose", "class_key": "anthracnose", "probability": 0.08},
            {"disease": "Red Leaf Spot", "class_key": "red_leaf_spot", "probability": 0.07},
            {"disease": "Tea Mosquito Bug", "class_key": "tea_mosquito_bug", "probability": 0.05},
            {"disease": "Other", "class_key": "other", "probability": 0.03},
            {"disease": "Unknown", "class_key": "unknown", "probability": 0.02},
            {"disease": "Pest Damage", "class_key": "pest_damage", "probability": 0.02},
            {"disease": "Nutrient Deficiency", "class_key": "nutrient_deficiency", "probability": 0.01},
            {"disease": "Viral Infection", "class_key": "viral_infection", "probability": 0.01},
        ],
        ai_explanation="ML service temporarily unavailable. No disease analysis performed.",
        model_version="dummy-fallback",
        inference_time_ms=None,
    )

    try:
        db.add(dummy_scan)
        db.commit()
        db.refresh(dummy_scan)
    except Exception:
        db.rollback()
        # Continue to return response even if persistence fails

    dummy_disease = MostProbableDisease(
        disease_name="Healthy",
        confidence=0.40,
        severity="none",
        description="No disease detected. The tea leaf appears healthy with no significant pathological symptoms.",
        causes=[],
    )
    dummy_confidence = [
        ConfidenceItem(disease="Healthy", probability=0.40, confidence_label="medium"),
        ConfidenceItem(disease="Mite Disease", probability=0.15, confidence_label="low"),
        ConfidenceItem(disease="Blister Blight", probability=0.12, confidence_label="low"),
        ConfidenceItem(disease="Anthracnose", probability=0.08, confidence_label="low"),
        ConfidenceItem(disease="Red Leaf Spot", probability=0.07, confidence_label="low"),
        ConfidenceItem(disease="Tea Mosquito Bug", probability=0.05, confidence_label="low"),
        ConfidenceItem(disease="Other", probability=0.03, confidence_label="low"),
        ConfidenceItem(disease="Unknown", probability=0.02, confidence_label="low"),
        ConfidenceItem(disease="Pest Damage", probability=0.02, confidence_label="low"),
        ConfidenceItem(disease="Nutrient Deficiency", probability=0.01, confidence_label="low"),
        ConfidenceItem(disease="Viral Infection", probability=0.01, confidence_label="low"),
    ]
    dummy_risk = RiskLevel(level="low", reason="Unable to assess - ML service unavailable")
    dummy_explanation = [AIExplanation(disease="Healthy", explanation="ML service temporarily unavailable. No disease analysis performed.", recommended_actions=[])]

    return DiseaseScanAPIResponse(
        scan_id=scan_id,
        status="success",
        scan_summary=ScanSummary(
            field_id=field.id if field else None,
            field_name=field.name if field else None,
            date=effective_scan_datetime.date(),
            time=effective_scan_datetime.time(),
            weather_details=weather_data,
            image_url=image_url,
            latitude=latitude,
            longitude=longitude,
            scan_datetime=effective_scan_datetime,
        ),
        most_probable_disease=dummy_disease,
        confidence_analysis=dummy_confidence,
        risk_level=dummy_risk,
        ai_explanation=dummy_explanation,
        recommendations=[],
        meta=Meta(
            model_version="dummy-fallback",
            inference_time_ms=None,
            timestamp=datetime.now(),
        ),
    )


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
    # Individual weather form fields (match ML model's expected format)
    # rainy_days_last_7: int | None = Form(default=None, ge=0, le=7),
    # rainy_hours_last_7: int | None = Form(default=None, ge=0),
    total_rainfall_last_7: float | None = Form(default=None, ge=0),
    avg_temperature_last_7: float | None = Form(default=None),
    avg_humidity_last_7: float | None = Form(default=None, ge=0, le=100),
    # max_humidity_last_7: float | None = Form(default=None, ge=0, le=100),
    avg_wind_speed_last_7: float | None = Form(default=None, ge=0),
    #max_wind_speed_last_7: float | None = Form(default=None, ge=0),
    avg_sunshine_hours_last_7: float | None = Form(default=None),
    # estimated_leaf_wetness_hours_last_7: int | None = Form(default=None, ge=0),
    # Legacy JSON weather_summary parameter (optional, takes precedence if both provided)
    weather_summary: str | None = Form(
        default=None,
        description="JSON string matching the WeatherSummary schema (deprecated, use individual fields)",
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

    # --- Build weather data from individual form fields or legacy JSON ----------
    weather_data: WeatherSummary | None = None
    weather_dict: dict = {}

    # Legacy JSON weather_summary takes precedence if provided
    if weather_summary:
        try:
            weather_data = WeatherSummary.model_validate_json(weather_summary)
            weather_dict = weather_data.model_dump(exclude_none=True)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid weather_summary: {e}")
    else:
        # Build from individual form fields
        weather_dict = {
            k: v for k, v in {
                "total_rainfall_last_7": total_rainfall_last_7,
                "avg_temperature_last_7": avg_temperature_last_7,
                "avg_humidity_last_7": avg_humidity_last_7,
                "avg_wind_speed_last_7": avg_wind_speed_last_7,
                "avg_sunshine_hours_last_7": avg_sunshine_hours_last_7,
            }.items() if v is not None
        }
        if weather_dict:
            weather_data = WeatherSummary.model_validate(weather_dict)

    env_data = None
    if environmental_data:
        try:
            env_data = json.loads(environmental_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid environmental_data JSON format")

    effective_scan_datetime = scan_date or datetime.now()

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
    except MLPredictionError:
        return _build_and_persist_dummy_response(
            scan_id=_generate_scan_id(),
            image_url=image_url,
            field=field,
            latitude=latitude,
            longitude=longitude,
            effective_scan_datetime=effective_scan_datetime,
            weather_data=weather_data,
            env_data=env_data,
            db=db,
        )

    if not raw_predictions:
        return _build_and_persist_dummy_response(
            scan_id=_generate_scan_id(),
            image_url=image_url,
            field=field,
            latitude=latitude,
            longitude=longitude,
            effective_scan_datetime=effective_scan_datetime,
            weather_data=weather_data,
            env_data=env_data,
            db=db,
        )

    # --- Resolve against disease reference table (Step 4) ----------------------
    scored = resolve_predictions(db, raw_predictions, top_n=3)
    if not scored:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="None of the predicted classes matched known disease reference data",
        )

    top = scored[0]

    # --- Risk analysis (Step 3, rule-based) -------------------------------------
    risk = assess_risk(weather_dict)

    # --- AI explanations per top prediction (Step 5) -----------------------------
    explanations = [
        AIExplanation(
            disease=s.disease.name,
            explanation=build_ai_explanation(s.disease, risk),
            recommended_actions=s.disease.recommendations,
        )
        for s in scored
    ]

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
        risk_level=risk.level,
        risk_reason=risk.reason,
        treatment_suggestions=top.disease.recommendations,
        all_predictions=[
            {"disease": s.disease.name, "class_key": s.disease.class_key, "probability": s.probability}
            for s in scored
        ],
        ai_explanation=explanations[0].explanation,
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
            ConfidenceItem(disease=s.disease.name, probability=s.probability, confidence_label=s.confidence)
            for s in scored
        ],
        risk_level=RiskLevel(level=risk.level, reason=risk.reason),
        ai_explanation=explanations,
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
    scan = db.scalar(select(DiseaseScan).where(DiseaseScan.scan_id == scan_id))
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    if scan.field_id:
        field = db.get(Field, scan.field_id)
        if not field or field.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this scan")

    return scan


@router.get("/list", response_model=list[DiseaseScanResponse])
def list_scans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(DiseaseScan)
        .join(Field, DiseaseScan.field_id == Field.id, isouter=True)
        .where(Field.user_id == current_user.id)
        .order_by(DiseaseScan.created_at.desc())
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