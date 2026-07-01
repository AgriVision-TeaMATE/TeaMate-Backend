import uuid
from datetime import datetime

from sqlalchemy import String, Numeric, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Field(Base):
    __tablename__ = "fields"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    area_hectares: Mapped[float] = mapped_column(
        Numeric(6, 2), nullable=False
    )
    latitude: Mapped[float] = mapped_column(
        Numeric(9, 6), nullable=False, default=6.927100
    )
    longitude: Mapped[float] = mapped_column(
        Numeric(9, 6), nullable=False, default=80.600500
    )
    elevation_meters: Mapped[float] = mapped_column(
        Numeric(7, 2), default=1200.00
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    harvest_rounds = relationship(
        "HarvestRound", back_populates="field", cascade="all, delete-orphan"
    )
    worker_assignments = relationship(
        "WorkerFieldAssignment",
        back_populates="field",
        cascade="all, delete-orphan",
    )
    plucking_schedules = relationship(
        "PluckingSchedule",
        back_populates="field",
        cascade="all, delete-orphan",
    )
    notifications = relationship(
        "Notification", back_populates="field"
    )
