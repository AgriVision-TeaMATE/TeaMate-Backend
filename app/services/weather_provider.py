from datetime import datetime, timezone

import httpx

from ..config import get_settings

settings = get_settings()


async def fetch_weather_snapshot() -> dict:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={settings.DEFAULT_WEATHER_LAT}"
        f"&longitude={settings.DEFAULT_WEATHER_LON}"
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
    storm_risk = rain_chance >= 70 or float(current.get("wind_speed_10m") or 0) >= 35
    summary = _weather_summary(weather_code, rain_chance)

    return {
        "summary": summary,
        "rain_chance_pct": rain_chance,
        "humidity_pct": int(current.get("relative_humidity_2m") or 0),
        "temperature_c": float(current.get("temperature_2m") or 0),
        "wind_speed_kmh": float(current.get("wind_speed_10m") or 0),
        "storm_risk": storm_risk,
        "weather_code": weather_code,
        "recorded_at": datetime.now(timezone.utc),
    }


def _weather_summary(weather_code: int | None, rain_chance: int) -> str:
    if rain_chance >= 70:
        return "Heavy rain risk"
    if rain_chance >= 40:
        return "Possible rain"
    if weather_code in {0, 1}:
        return "Clear to partly cloudy"
    if weather_code in {2, 3, 45, 48}:
        return "Cloudy"
    return "Field weather update"
