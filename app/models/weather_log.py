import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Numeric, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class WeatherLog(Base):
    __tablename__ = "weather_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    harvest_round_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("harvest_rounds.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    summary: Mapped[str | None] = mapped_column(String(100))
    rain_chance_pct: Mapped[int | None] = mapped_column(Integer)
    humidity_pct: Mapped[int | None] = mapped_column(Integer)
    temperature_c: Mapped[float | None] = mapped_column(Numeric(5, 2))
    wind_speed_kmh: Mapped[float | None] = mapped_column(Numeric(5, 2))
    storm_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    weather_code: Mapped[int | None] = mapped_column(Integer)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    harvest_round = relationship(
        "HarvestRound", back_populates="weather_log"
    )
