from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from ..services.weather_provider import (
    fetch_weather_snapshot,
    fetch_last_week_summary,
)

router = APIRouter(prefix="/weather", tags=["Weather"])


class LocationRequest(BaseModel):
    latitude: float
    longitude: float


class CurrentWeatherResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    summary: str
    rain_chance_pct: int
    humidity_pct: int
    temperature_c: float
    wind_speed_kmh: float
    storm_risk: bool
    weather_code: int | None
    recorded_at: datetime


class WeeklyWeatherSummaryResponse(BaseModel):
    rainy_days_last_7: int
    avg_temperature_last_7: float
    avg_humidity_last_7: int
    max_wind_speed_last_7: float
    total_rainfall_last_7: float


@router.post("/current", response_model=CurrentWeatherResponse)
async def get_current_weather(
    location: LocationRequest,
):
    """
    Get current weather based on user location.
    """

    weather_data = await fetch_weather_snapshot(
        latitude=location.latitude,
        longitude=location.longitude,
    )

    return CurrentWeatherResponse(
        summary=weather_data["summary"],
        rain_chance_pct=weather_data["rain_chance_pct"],
        humidity_pct=weather_data["humidity_pct"],
        temperature_c=weather_data["temperature_c"],
        wind_speed_kmh=weather_data["wind_speed_kmh"],
        storm_risk=weather_data["storm_risk"],
        weather_code=weather_data["weather_code"],
        recorded_at=weather_data["recorded_at"],
    )


@router.post(
    "/weekly-summary",
    response_model=WeeklyWeatherSummaryResponse,
)
async def get_weekly_weather_summary(
    location: LocationRequest,
):
    """
    Get last 7 days weather summary based on user location.
    """

    summary = await fetch_last_week_summary(
        latitude=location.latitude,
        longitude=location.longitude,
    )

    return WeeklyWeatherSummaryResponse(
        rainy_days_last_7=summary["rainy_days_last_7"],
        avg_temperature_last_7=summary["avg_temperature_last_7"],
        avg_humidity_last_7=summary["avg_humidity_last_7"],
        max_wind_speed_last_7=summary["max_wind_speed_last_7"],
        total_rainfall_last_7=summary["total_rainfall_last_7"],
    )