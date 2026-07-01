import uuid
from datetime import datetime

from sqlalchemy import String, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class BudMarker(Base):
    __tablename__ = "bud_markers"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    analysis_image_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analysis_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    x_position: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False)
    y_position: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False)
    marker_type: Mapped[str] = mapped_column(String(20), default="bud")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    analysis_image = relationship(
        "AnalysisImage", back_populates="bud_markers"
    )
