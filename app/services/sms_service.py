from datetime import datetime, timezone

from ..config import get_settings
from ..models import PluckingSchedule, Worker
from .round_planning import weather_action_for_sms

settings = get_settings()


def send_schedule_sms(
    schedule: PluckingSchedule,
    workers: list[Worker],
    field_name: str,
) -> dict:
    weather_log = (
        schedule.harvest_round.weather_log if schedule.harvest_round else None
    )
    if weather_log:
        weather_action = weather_action_for_sms(
            {
                "storm_risk": weather_log.storm_risk,
                "rain_chance_pct": weather_log.rain_chance_pct or 0,
            }
        )
    else:
        weather_action = "Follow supervisor instructions."

    message = (
        f"TeaMate: You are assigned to Field {field_name} today.\n"
        f"Weather: {weather_action}\n"
        "Please report to the field supervisor."
    )

    if settings.SMS_PROVIDER == "mock":
        for worker in workers:
            print(f"[SMS MOCK] -> {worker.phone}: {message}")

    return {
        "provider": settings.SMS_PROVIDER,
        "message": message,
        "sent_count": len(workers),
        "sent_at": datetime.now(timezone.utc),
    }
