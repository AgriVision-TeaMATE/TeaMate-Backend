import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class AlertSeverity(str, PyEnum):
    info = "info"
    warning = "warning"
    critical = "critical"


class NotificationCategory(str, PyEnum):
    weather = "weather"
    labor = "labor"
    quality = "quality"
    schedule = "schedule"
    reminder = "reminder"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    field_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("fields.id", ondelete="SET NULL"), index=True
    )
    harvest_round_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("harvest_rounds.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[NotificationCategory] = mapped_column(
        Enum(
            NotificationCategory,
            name="notification_category_enum",
            create_constraint=True,
        ),
        nullable=False,
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(
            AlertSeverity,
            name="alert_severity_enum",
            create_constraint=True,
        ),
        nullable=False,
        default=AlertSeverity.info,
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    field = relationship("Field", back_populates="notifications")
    harvest_round = relationship(
        "HarvestRound", back_populates="notifications"
    )
