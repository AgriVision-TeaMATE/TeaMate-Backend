from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorkerCreate(BaseModel):
    name: str
    phone: str


class WorkerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None


class WorkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    phone: str
    status: str
    created_at: datetime
    updated_at: datetime


class WorkerDetailResponse(WorkerResponse):
    assigned_field_id: UUID | None = None
    assigned_field_name: str | None = None


class AssignWorkerRequest(BaseModel):
    field_id: UUID


class WorkerStatusUpdate(BaseModel):
    status: str  # "available" | "on_leave"
