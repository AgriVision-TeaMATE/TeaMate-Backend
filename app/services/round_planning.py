from datetime import date, time
from math import ceil

from sqlalchemy.orm import Session

from ..models import HarvestRound, Notification, WeatherLog
from ..models.notification import AlertSeverity, NotificationCategory
from .weather_provider import fetch_weather_snapshot


async def build_round_plan(
    round_obj: HarvestRound,
    db: Session,
    kg_per_worker_per_day: float,
    scheduled_date: date,
    shift_start: time,
    shift_end: time,
) -> dict:
    predicted_yield = float(round_obj.predicted_yield or 0)
    recommended_workers = max(
        1, ceil(predicted_yield / max(kg_per_worker_per_day, 1))
    ) if predicted_yield > 0 else 1

    weather = await fetch_weather_snapshot()
    weather_log = round_obj.weather_log
    if not weather_log:
        weather_log = WeatherLog(harvest_round_id=round_obj.id, **weather)
        db.add(weather_log)
    else:
        for key, value in weather.items():
            setattr(weather_log, key, value)

    warning = None
    can_schedule = True
    if weather["storm_risk"]:
        warning = "Heavy rain or wind risk detected for plucking."
        can_schedule = False
    elif weather["rain_chance_pct"] >= 40:
        warning = "Rain chance is elevated. Review timing before dispatch."

    notification_ids: list = []
    if warning:
        notification = Notification(
            field_id=round_obj.field_id,
            harvest_round_id=round_obj.id,
            title="Weather warning",
            message=warning,
            category=NotificationCategory.weather,
            severity=AlertSeverity.warning if can_schedule else AlertSeverity.critical,
        )
        db.add(notification)
        db.flush()
        notification_ids.append(notification.id)

    db.commit()
    db.refresh(round_obj)

    return {
        "round_id": round_obj.id,
        "field_id": round_obj.field_id,
        "plucking_status": round_obj.plucking_status,
        "predicted_yield": float(round_obj.predicted_yield) if round_obj.predicted_yield is not None else None,
        "recommended_workers": recommended_workers,
        "kg_per_worker_per_day": kg_per_worker_per_day,
        "weather_summary": weather["summary"],
        "rain_chance_pct": weather["rain_chance_pct"],
        "humidity_pct": weather["humidity_pct"],
        "temperature_c": weather["temperature_c"],
        "wind_speed_kmh": weather["wind_speed_kmh"],
        "storm_risk": weather["storm_risk"],
        "weather_warning": warning,
        "can_schedule": can_schedule,
        "scheduled_date": scheduled_date,
        "shift_start": shift_start,
        "shift_end": shift_end,
        "created_notification_ids": notification_ids,
    }
