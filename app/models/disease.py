import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Disease(Base):
    """Reference/lookup table for disease metadata."""

    __tablename__ = "diseases"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    class_key: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unknown"
    )

    description: Mapped[str] = mapped_column(
        String(1000),
        nullable=False
    )

    causes: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list
    )

    recommendations: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list
    )

    severity_default: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="low"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )