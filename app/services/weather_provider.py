from datetime import date, datetime, timedelta, timezone

import httpx

from ..config import get_settings

settings = get_settings()


async def fetch_weather_snapshot(
    latitude: float,
    longitude: float,
) -> dict:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
        "&hourly=precipitation_probability"
        "&forecast_days=1"
        "&timezone=auto"
    )

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=20.0)
        response.raise_for_status()
        payload = response.json()

    current = payload.get("current", {})
    hourly = payload.get("hourly", {})

    rain_chance = 0
    if hourly.get("precipitation_probability"):
        rain_chance = int(hourly["precipitation_probability"][0] or 0)

    weather_code = current.get("weather_code")

    storm_risk = (
        rain_chance >= 70
        or float(current.get("wind_speed_10m") or 0) >= 35
    )

    summary = _weather_summary(
        weather_code,
        rain_chance,
    )

    return {
        "summary": summary,
        "rain_chance_pct": rain_chance,
        "humidity_pct": int(
            current.get("relative_humidity_2m") or 0
        ),
        "temperature_c": float(
            current.get("temperature_2m") or 0
        ),
        "wind_speed_kmh": float(
            current.get("wind_speed_10m") or 0
        ),
        "storm_risk": storm_risk,
        "weather_code": weather_code,
        "recorded_at": datetime.now(timezone.utc),
    }


async def fetch_last_week_summary(
    latitude: float,
    longitude: float,
) -> dict:
    end_date = date.today()
    start_date = end_date - timedelta(days=6)

    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        f"&start_date={start_date}"
        f"&end_date={end_date}"
        "&daily="
        "temperature_2m_mean,"
        "relative_humidity_2m_mean,"
        "precipitation_sum,"
        "wind_speed_10m_max"
        "&timezone=auto"
    )

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=20.0)
        response.raise_for_status()
        payload = response.json()

    daily = payload.get("daily", {})

    temperatures = daily.get(
        "temperature_2m_mean",
        []
    )

    humidities = daily.get(
        "relative_humidity_2m_mean",
        []
    )

    rainfall = daily.get(
        "precipitation_sum",
        []
    )

    wind_speeds = daily.get(
        "wind_speed_10m_max",
        []
    )

    rainy_days = sum(
        1 for rain in rainfall if rain > 0
    )

    avg_temperature = (
        round(sum(temperatures) / len(temperatures), 1)
        if temperatures
        else 0
    )

    avg_humidity = (
        round(sum(humidities) / len(humidities))
        if humidities
        else 0
    )

    max_wind_speed = (
        round(max(wind_speeds), 1)
        if wind_speeds
        else 0
    )

    total_rainfall = round(
        sum(rainfall),
        1
    )

    return {
        "rainy_days_last_7": rainy_days,
        "avg_temperature_last_7": avg_temperature,
        "avg_humidity_last_7": avg_humidity,
        "max_wind_speed_last_7": max_wind_speed,
        "total_rainfall_last_7": total_rainfall,
    }


def _weather_summary(
    weather_code: int | None,
    rain_chance: int,
) -> str:
    if rain_chance >= 70:
        return "Heavy rain risk"

    if rain_chance >= 40:
        return "Possible rain"

    if weather_code in {0, 1}:
        return "Clear to partly cloudy"

    if weather_code in {2, 3, 45, 48}:
        return "Cloudy"

    return "Field weather update"