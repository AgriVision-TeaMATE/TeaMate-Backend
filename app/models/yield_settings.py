import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class YieldSettings(Base):
    __tablename__ = "yield_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    tea_variant: Mapped[str] = mapped_column(
        String(100), nullable=False, default="TRI 2025", server_default="TRI 2025"
    )
    pluckable_100_bud_weight_g: Mapped[float | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    arimbu_100_bud_weight_g: Mapped[float | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="yield_settings")
