import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, func, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class WorkerStatus(str, PyEnum):
    available = "available"
    assigned = "assigned"
    on_leave = "on_leave"


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    status: Mapped[WorkerStatus] = mapped_column(
        Enum(WorkerStatus, name="worker_status_enum", create_constraint=True),
        nullable=False,
        default=WorkerStatus.available,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    field_assignments = relationship(
        "WorkerFieldAssignment", back_populates="worker"
    )
    schedule_assignments = relationship(
        "ScheduleWorker", back_populates="worker"
    )
