from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .analysis_image import AnalysisImageResponse
from .weather import WeatherLogResponse


class HarvestRoundCreate(BaseModel):
    pass


class HarvestRoundUpdate(BaseModel):
    plucking_status: str | None = None
    predicted_yield: float | None = None
    actual_yield: float | None = None
    is_completed: bool | None = None


class HarvestRoundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    field_id: UUID
    pluckable_ratio: float | None
    total_captured_area_sqm: float
    plucking_status: str
    predicted_yield: float | None
    actual_yield: float | None
    is_completed: bool
    created_at: datetime
    updated_at: datetime
    analysis_images: list[AnalysisImageResponse] = []
    weather_log: WeatherLogResponse | None = None
