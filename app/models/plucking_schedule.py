import uuid
from datetime import datetime, date, time
from enum import Enum as PyEnum

from sqlalchemy import (
    String,
    Integer,
    Text,
    Date,
    Time,
    DateTime,
    ForeignKey,
    Enum,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class ScheduleStatus(str, PyEnum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class PluckingSchedule(Base):
    __tablename__ = "plucking_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fields.id", ondelete="CASCADE"), nullable=False
    )
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift_start: Mapped[time] = mapped_column(Time, nullable=False)
    shift_end: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[ScheduleStatus] = mapped_column(
        Enum(
            ScheduleStatus,
            name="schedule_status_enum",
            create_constraint=True,
        ),
        nullable=False,
        default=ScheduleStatus.scheduled,
    )
    recommended_workers: Mapped[int] = mapped_column(Integer, default=5)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    field = relationship("Field", back_populates="plucking_schedules")
    schedule_workers = relationship(
        "ScheduleWorker",
        back_populates="schedule",
        cascade="all, delete-orphan",
    )

    @property
    def assigned_worker_ids(self) -> list[uuid.UUID]:
        return [sw.worker_id for sw in self.schedule_workers]


class ScheduleWorker(Base):
    __tablename__ = "schedule_workers"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    schedule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plucking_schedules.id", ondelete="CASCADE"), nullable=False
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workers.id", ondelete="CASCADE"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "schedule_id", "worker_id", name="uq_schedule_worker"
        ),
    )

    # Relationships
    schedule = relationship(
        "PluckingSchedule", back_populates="schedule_workers"
    )
    worker = relationship("Worker", back_populates="schedule_assignments")
