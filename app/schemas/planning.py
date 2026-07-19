from datetime import date, time, datetime
from uuid import UUID

from pydantic import BaseModel


class RoundPlanRequest(BaseModel):
    kg_per_worker_per_day: float = 30.0
    scheduled_date: date | None = None
    shift_start: time | None = None
    shift_end: time | None = None


class RoundPlanResponse(BaseModel):
    round_id: UUID
    field_id: UUID
    plucking_status: str
    predicted_yield: float | None
    recommended_workers: int
    kg_per_worker_per_day: float
    weather_summary: str | None = None
    rain_chance_pct: int | None = None
    humidity_pct: int | None = None
    temperature_c: float | None = None
    wind_speed_kmh: float | None = None
    storm_risk: bool = False
    weather_warning: str | None = None
    weather_action: str | None = None
    can_schedule: bool
    scheduled_date: date
    shift_start: time
    shift_end: time
    created_notification_ids: list[UUID] = []


class SmsDispatchResponse(BaseModel):
    schedule_id: UUID
    sent_count: int
    provider: str
    message: str
    sent_at: datetime
