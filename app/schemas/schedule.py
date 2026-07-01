from datetime import date, time, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ScheduleCreate(BaseModel):
    field_id: UUID
    scheduled_date: date
    shift_start: time
    shift_end: time
    recommended_workers: int = 5
    notes: str | None = None
    assigned_worker_ids: list[UUID] = []


class ScheduleUpdate(BaseModel):
    status: str | None = None
    recommended_workers: int | None = None
    notes: str | None = None


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    field_id: UUID
    scheduled_date: date
    shift_start: time
    shift_end: time
    status: str
    recommended_workers: int
    notes: str | None
    created_at: datetime
    updated_at: datetime
    assigned_worker_ids: list[UUID] = []
