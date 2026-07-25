import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class TeaGradeScan(Base):
    __tablename__ = "tea_grade_scans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("fields.id", ondelete="CASCADE"), nullable=True, index=True
    )

    image_url: Mapped[str] = mapped_column(String, nullable=False)
    scan_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    grade_composition: Mapped[dict] = mapped_column(JSON, nullable=False)
    dominant_grade: Mapped[str] = mapped_column(String(50), nullable=False)
    dominant_grade_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    total_particles_detected: Mapped[int | None] = mapped_column(Integer, nullable=True)

    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    inference_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
