import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class HarvestRound(Base):
    __tablename__ = "harvest_rounds"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fields.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pluckable_ratio: Mapped[float | None] = mapped_column(
        Numeric(5, 4)
    )
    total_captured_area_sqm: Mapped[float] = mapped_column(
        Numeric(8, 2), nullable=False, default=0, server_default="0"
    )
    plucking_status: Mapped[str] = mapped_column(
        String(30), default="awaiting_analysis"
    )
    predicted_yield: Mapped[float | None] = mapped_column(Numeric(8, 2))
    actual_yield: Mapped[float | None] = mapped_column(Numeric(8, 2))
    is_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
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
