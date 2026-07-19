from datetime import datetime, timezone

from ..config import get_settings
from ..models import PluckingSchedule, Worker

settings = get_settings()


def send_schedule_sms(schedule: PluckingSchedule, workers: list[Worker], field_name: str) -> dict:
    message = (
        f"TeaMate: You are assigned to plucking at {field_name} "
        f"(Field ID: {str(schedule.field_id)[:8]}) "
        f"on {schedule.scheduled_date.isoformat()}."
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
