import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, JSON, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class DiseaseScan(Base):
    __tablename__ = "disease_scans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    field_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fields.id", ondelete="CASCADE"), nullable=True, index=True)
    image_urls: Mapped[list] = mapped_column(JSON, nullable=False)
    detected_disease: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    scan_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    weather_summary: Mapped[dict | None] = mapped_column(JSON)
    environmental_data: Mapped[dict | None] = mapped_column(JSON)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    risk_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    treatment_suggestions: Mapped[list | None] = mapped_column(JSON)
    all_predictions: Mapped[list | None] = mapped_column(JSON)
    ai_explanation: Mapped[str | None] = mapped_column(String, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(50))
    inference_time_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    field = relationship("Field", back_populates="disease_scans")
    explanation_data: Mapped[dict | None] = mapped_column(JSON)
    environmental_summary: Mapped[str | None] = mapped_column(String(1000),nullable=True)
    environmental_insights: Mapped[list | None] = mapped_column(JSON)
    environmental_technical_summary: Mapped[dict | None] = mapped_column(JSON)