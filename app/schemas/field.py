from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FieldCreate(BaseModel):
    name: str
    area_hectares: float


class FieldUpdate(BaseModel):
    name: str | None = None
    area_hectares: float | None = None


class FieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    area_hectares: float
    created_at: datetime
    updated_at: datetime


class FieldDetailResponse(FieldResponse):
    assigned_worker_count: int = 0
    latest_round: "HarvestRoundResponse | None" = None


# Avoid circular imports
from .harvest_round import HarvestRoundResponse  # noqa: E402

FieldDetailResponse.model_rebuild()
