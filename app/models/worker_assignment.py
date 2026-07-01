import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class WorkerFieldAssignment(Base):
    __tablename__ = "worker_field_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workers.id", ondelete="CASCADE"), nullable=False
    )
    field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fields.id", ondelete="CASCADE"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    unassigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    __table_args__ = (
        UniqueConstraint(
            "worker_id",
            "field_id",
            name="uq_worker_field_active",
        ),
    )

    # Relationships
    worker = relationship("Worker", back_populates="field_assignments")
    field = relationship("Field", back_populates="worker_assignments")
