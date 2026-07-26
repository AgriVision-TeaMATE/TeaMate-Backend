import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Field(Base):
    __tablename__ = "fields"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    area_hectares: Mapped[float] = mapped_column(
        Numeric(6, 2), nullable=False
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
    disease_scans = relationship(
        "DiseaseScan", back_populates="field"
    )
    user = relationship("User")
