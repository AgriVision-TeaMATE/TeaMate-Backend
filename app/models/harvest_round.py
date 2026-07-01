import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, Numeric, Integer, DateTime, ForeignKey, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class RoundStatus(str, PyEnum):
    draft = "draft"
    analyzing = "analyzing"
    analyzed = "analyzed"
    completed = "completed"


class HarvestRound(Base):
    __tablename__ = "harvest_rounds"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fields.id", ondelete="CASCADE"), nullable=False, index=True
    )
    round_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    field_area_hectares: Mapped[float | None] = mapped_column(Numeric(6, 2))
    predicted_yield_kg: Mapped[float | None] = mapped_column(Numeric(8, 2))
    actual_yield_kg: Mapped[float | None] = mapped_column(Numeric(8, 2))
    avg_pluckable_ratio: Mapped[float | None] = mapped_column(Numeric(5, 4))
    total_arimbu_count: Mapped[int] = mapped_column(Integer, default=0)
    total_pluckable_count: Mapped[int] = mapped_column(Integer, default=0)
    total_captured_area_sqm: Mapped[float] = mapped_column(
        Numeric(8, 2), default=0
    )
    labor_priority: Mapped[str | None] = mapped_column(String(30))
    readiness_status: Mapped[str] = mapped_column(
        String(30), default="awaiting_analysis"
    )
    status: Mapped[RoundStatus] = mapped_column(
        Enum(RoundStatus, name="round_status_enum", create_constraint=True),
        nullable=False,
        default=RoundStatus.draft,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    field = relationship("Field", back_populates="harvest_rounds")
    analysis_images = relationship(
        "AnalysisImage",
        back_populates="harvest_round",
        cascade="all, delete-orphan",
    )
    weather_log = relationship(
        "WeatherLog",
        back_populates="harvest_round",
        uselist=False,
        cascade="all, delete-orphan",
    )
    notifications = relationship(
        "Notification", back_populates="harvest_round"
    )
