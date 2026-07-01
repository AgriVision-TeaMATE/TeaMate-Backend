from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FieldCreate(BaseModel):
    name: str
    region: str
    area_hectares: float
    latitude: float = 6.927100
    longitude: float = 80.600500
    elevation_meters: float = 1200.00


class FieldUpdate(BaseModel):
    name: str | None = None
    region: str | None = None
    area_hectares: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    elevation_meters: float | None = None


class FieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    region: str
    area_hectares: float
    latitude: float
    longitude: float
    elevation_meters: float
    created_at: datetime
    updated_at: datetime


class FieldDetailResponse(FieldResponse):
    assigned_worker_count: int = 0
    latest_round: "HarvestRoundResponse | None" = None


# Avoid circular imports
from .harvest_round import HarvestRoundResponse  # noqa: E402

FieldDetailResponse.model_rebuild()
