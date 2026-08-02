"""
Disease Insights API endpoints.

Provides aggregated, reporting-level endpoints that combine data from
DiseaseScan, Field, and Disease reference tables. No ML inference —
pure data aggregation for the Flutter DiseaseInsightsScreen.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models import User
from ..schemas.disease_insights import (
    EstateInsightsResponse,
    FieldInsightsResponse,
)
from ..services.disease_insights_service import (
    get_estate_insights,
    get_field_insights,
)

router = APIRouter(
    prefix="/disease",
    tags=["Disease Insights"],
)


@router.get(
    "/estate-insights",
    response_model=EstateInsightsResponse,
    status_code=status.HTTP_200_OK,
    summary="Estate-level disease insights dashboard",
    description=(
        "Aggregates disease scan data across all of the authenticated user's "
        "fields. Returns KPI cards, a risk map, disease trend, field priority, "
        "disease composition, and an action queue."
    ),
)
def read_estate_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GET /api/v1/disease/estate-insights"""
    result = get_estate_insights(db, current_user.id)
    return result


@router.get(
    "/field-insights/{field_id}",
    response_model=FieldInsightsResponse,
    status_code=status.HTTP_200_OK,
    summary="Field-level disease insights",
    description=(
        "Detailed disease insights for a single field: disease pressure score, "
        "health timeline, confidence distribution, and weather-vs-disease "
        "relationship data."
    ),
)
def read_field_insights(
    field_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GET /api/v1/disease/field-insights/{field_id}"""
    result = get_field_insights(db, current_user.id, field_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field not found or not owned by user",
        )
    return result
