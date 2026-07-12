import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, Text
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
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    captured_area_sqm: Mapped[float] = mapped_column(
        Numeric(8, 2), nullable=False, default=0, server_default="0"
    )
    arimbu_count: Mapped[int] = mapped_column(Integer, default=0)
    pluckable_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    harvest_round = relationship(
        "HarvestRound", back_populates="analysis_images"
    )
    bud_markers = relationship(
        "BudMarker",
        back_populates="analysis_image",
        cascade="all, delete-orphan",
    )
