from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WeatherLogCreate(BaseModel):
    summary: str
    rain_chance_pct: int
    humidity_pct: int
    temperature_c: float
    wind_speed_kmh: float
    storm_risk: bool
    weather_code: int
    recorded_at: datetime


class WeatherLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    harvest_round_id: UUID
    summary: str | None
    rain_chance_pct: int | None
    humidity_pct: int | None
    temperature_c: float | None
    wind_speed_kmh: float | None
    storm_risk: bool
    weather_code: int | None
    recorded_at: datetime
