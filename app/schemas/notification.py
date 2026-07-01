from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationCreate(BaseModel):
    field_id: UUID | None = None
    harvest_round_id: UUID | None = None
    title: str
    message: str
    category: str
    severity: str = "info"


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    field_id: UUID | None
    harvest_round_id: UUID | None
    title: str
    message: str
    category: str
    severity: str
    is_read: bool
    created_at: datetime
    read_at: datetime | None
