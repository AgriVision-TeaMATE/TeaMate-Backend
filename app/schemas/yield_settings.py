from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class YieldSettingsResponse(BaseModel):
    id: UUID | None = None
    tea_variant: str
    pluckable_100_bud_weight_g: float | None
    arimbu_100_bud_weight_g: float | None
    is_configured: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class YieldSettingsUpdate(BaseModel):
    tea_variant: str
    pluckable_100_bud_weight_g: float
    arimbu_100_bud_weight_g: float

    @field_validator("tea_variant")
    @classmethod
    def validate_variant(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Tea variant is required.")
        return cleaned

    @field_validator("pluckable_100_bud_weight_g", "arimbu_100_bud_weight_g")
    @classmethod
    def validate_weight(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Weight must be greater than zero.")
        return value
