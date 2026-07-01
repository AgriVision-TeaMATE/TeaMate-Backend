from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .analysis_image import AnalysisImageResponse
from .weather import WeatherLogResponse


class HarvestRoundCreate(BaseModel):
    round_date: datetime | None = None


class HarvestRoundUpdate(BaseModel):
    actual_yield_kg: float | None = None
    field_area_hectares: float | None = None


class HarvestRoundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    field_id: UUID
    round_date: datetime
    field_area_hectares: float | None
    predicted_yield_kg: float | None
    actual_yield_kg: float | None
    avg_pluckable_ratio: float | None
    total_arimbu_count: int
    total_pluckable_count: int
    total_captured_area_sqm: float
    labor_priority: str | None
    readiness_status: str
    status: str
    created_at: datetime
    updated_at: datetime
    analysis_images: list[AnalysisImageResponse] = []
    weather_log: WeatherLogResponse | None = None
