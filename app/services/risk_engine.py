"""
Rule-based agronomic risk scoring — explicitly NOT from the ML model.
Implements Step 3 of the architecture: weather-driven disease risk.
"""
from dataclasses import dataclass

HUMIDITY_THRESHOLD = 90
LEAF_WETNESS_THRESHOLD = 60
RAINFALL_THRESHOLD = 15


@dataclass
class RiskAssessment:
    level: str  # "HIGH" | "MEDIUM" | "LOW"
    reason: str
    triggered_factors: list[str]


def assess_risk(weather: dict) -> RiskAssessment:
    """
    weather may contain (any may be missing/None):
      avg_humidity_last_7, estimated_leaf_wetness_hours_last_7, total_rainfall_last_7
    """
    triggered: list[str] = []

    humidity = weather.get("avg_humidity_last_7")
    leaf_wetness = weather.get("estimated_leaf_wetness_hours_last_7")
    rainfall = weather.get("total_rainfall_last_7")

    if humidity is not None and humidity > HUMIDITY_THRESHOLD:
        triggered.append(f"humidity {humidity}% > {HUMIDITY_THRESHOLD}%")

    if leaf_wetness is not None and leaf_wetness > LEAF_WETNESS_THRESHOLD:
        triggered.append(f"leaf wetness {leaf_wetness}h > {LEAF_WETNESS_THRESHOLD}h")

    if rainfall is not None and rainfall > RAINFALL_THRESHOLD:
        triggered.append(f"rainfall {rainfall}mm > {RAINFALL_THRESHOLD}mm")

    if len(triggered) >= 2:
        level = "HIGH"
    elif len(triggered) == 1:
        level = "MEDIUM"
    else:
        level = "LOW"

    reason = (
        "Elevated risk due to " + ", ".join(triggered) + "."
        if triggered
        else "Weather conditions during the last 7 days do not indicate elevated disease risk."
    )

    return RiskAssessment(level=level, reason=reason, triggered_factors=triggered)