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
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        "&hourly="
        "temperature_2m,"
        "relative_humidity_2m,"
        "precipitation,"
        "wind_speed_10m,"
        "sunshine_duration"
        "&past_days=7"
        "&forecast_days=1"
        "&timezone=auto"
    )

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=20.0)
        response.raise_for_status()
        payload = response.json()

    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    temperatures = hourly.get("temperature_2m", [])
    humidities = hourly.get("relative_humidity_2m", [])
    precipitation = hourly.get("precipitation", [])
    wind_speeds = hourly.get("wind_speed_10m", [])
    sunshine_seconds = hourly.get("sunshine_duration", [])

    # timezone=auto returns naive local timestamps for the queried
    # location. Attach that location's actual UTC offset (returned by
    # the API) to make every datetime timezone-aware and comparable,
    # instead of guessing based on the server's own local time.
    utc_offset_seconds = payload.get("utc_offset_seconds", 0)
    local_tz = timezone(timedelta(seconds=utc_offset_seconds))

    now = datetime.now(local_tz)
    cutoff_date = (now - timedelta(days=7)).date()

    rows = []
    for i, ts in enumerate(times):
        dt = datetime.fromisoformat(ts).replace(tzinfo=local_tz)
        if dt.date() < cutoff_date or dt > now:
            continue
        rows.append(
            {
                "date": dt.date(),
                "temperature": temperatures[i] if i < len(temperatures) else None,
                "humidity": humidities[i] if i < len(humidities) else None,
                "rain": precipitation[i] if i < len(precipitation) else 0,
                "wind": wind_speeds[i] if i < len(wind_speeds) else None,
                "sunshine": sunshine_seconds[i] if i < len(sunshine_seconds) else 0,
            }
        )

    if not rows:
        return {
            "rainy_days_last_7": 0,
            "rainy_hours_last_7": 0,
            "total_rainfall_last_7": 0,
            "avg_temperature_last_7": 0,
            "avg_humidity_last_7": 0,
            "max_humidity_last_7": 0,
            "avg_wind_speed_last_7": 0,
            "max_wind_speed_last_7": 0,
            "avg_sunshine_hours_last_7": 0,
            "estimated_leaf_wetness_hours_last_7": 0,
        }

    temperatures_clean = [r["temperature"] for r in rows if r["temperature"] is not None]
    humidities_clean = [r["humidity"] for r in rows if r["humidity"] is not None]
    winds_clean = [r["wind"] for r in rows if r["wind"] is not None]

    rainy_hours = sum(1 for r in rows if (r["rain"] or 0) > 0)
    total_rainfall = round(sum(r["rain"] or 0 for r in rows), 1)

    days_seen = {r["date"] for r in rows}
    rainy_days = sum(
        1
        for d in days_seen
        if sum(r["rain"] or 0 for r in rows if r["date"] == d) > 0
    )

    total_sunshine_hours = sum(r["sunshine"] or 0 for r in rows) / 3600
    num_days = len(days_seen) or 1

    leaf_wetness_hours = sum(
        1
        for r in rows
        if (r["rain"] or 0) > 0 or (r["humidity"] is not None and r["humidity"] >= 90)
    )

    return {
        "rainy_days_last_7": rainy_days,
        "rainy_hours_last_7": rainy_hours,
        "total_rainfall_last_7": total_rainfall,
        "avg_temperature_last_7": (
            round(sum(temperatures_clean) / len(temperatures_clean), 1)
            if temperatures_clean
            else 0
        ),
        "avg_humidity_last_7": (
            round(sum(humidities_clean) / len(humidities_clean))
            if humidities_clean
            else 0
        ),
        "max_humidity_last_7": (
            round(max(humidities_clean)) if humidities_clean else 0
        ),
        "avg_wind_speed_last_7": (
            round(sum(winds_clean) / len(winds_clean), 1) if winds_clean else 0
        ),
        "max_wind_speed_last_7": (
            round(max(winds_clean), 1) if winds_clean else 0
        ),
        "avg_sunshine_hours_last_7": round(total_sunshine_hours / num_days, 1),
        "estimated_leaf_wetness_hours_last_7": leaf_wetness_hours,
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