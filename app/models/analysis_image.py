import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Numeric, Boolean, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class AnalysisImage(Base):
    __tablename__ = "analysis_images"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    harvest_round_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("harvest_rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    firebase_url: Mapped[str] = mapped_column(Text, nullable=False)
    firebase_path: Mapped[str] = mapped_column(String(500), nullable=False)
    source_label: Mapped[str] = mapped_column(String(50), nullable=False)
    arimbu_count: Mapped[int] = mapped_column(Integer, default=0)
    pluckable_count: Mapped[int] = mapped_column(Integer, default=0)
    captured_area_sqm: Mapped[float] = mapped_column(
        Numeric(8, 2), default=0
    )
    pluckable_ratio: Mapped[float | None] = mapped_column(Numeric(5, 4))
    is_analyzed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    harvest_round = relationship(
        "HarvestRound", back_populates="analysis_images"
    )
    bud_markers = relationship(
        "BudMarker",
        back_populates="analysis_image",
        cascade="all, delete-orphan",
    )
