"""
Disease Insights aggregation service.

Computes estate-level and field-level insights from existing DiseaseScan,
Field, and Disease reference data. No ML inference — pure reporting logic.

All functions accept a SQLAlchemy Session and a user_id, filtering results
to only the requesting user's fields (multi-tenant isolation).
"""
from collections import defaultdict
from datetime import date
from uuid import UUID

from sqlalchemy import select

from ..models import DiseaseScan, Field
from ..services.risk_engine import assess_risk


# ---------------------------------------------------------------------------
# Thresholds / constants
# ---------------------------------------------------------------------------

CONFIDENCE_BUCKETS = [
    ("0-50", 0.0, 0.50),
    ("50-70", 0.50, 0.70),
    ("70-85", 0.70, 0.85),
    ("85-100", 0.85, 1.01),
]

SEVERITY_WEIGHTS = {
    "high": 3.0,
    "medium": 2.0,
    "low": 1.0,
    "none": 0.5,
}

RESCAN_THRESHOLD_DAYS = 30
LOW_CONFIDENCE_THRESHOLD = 0.75
HIGH_RISK_THRESHOLD = 0.6
MEDIUM_RISK_THRESHOLD = 0.3

HEALTHY_KEYS = {"healthy", "Healthy", "HEALTHY"}


def _is_healthy(disease_name: str | None) -> bool:
    """Check whether a detected-disease value represents 'healthy'."""
    if disease_name is None:
        return True  # no disease detected == healthy
    return disease_name.lower() in {"healthy", "healthy_leaf", "none"}


def _max_disease_probability(all_predictions: list | None) -> float:
    """Highest probability among non-healthy predictions.

    Returns 0.0 when there are no non-healthy predictions (i.e. the scan
    was clean or all_predictions is missing).
    """
    if not all_predictions:
        return 0.0

    best = 0.0
    for p in all_predictions:
        cls_key = p.get("class_key", "")
        if not cls_key.lower().startswith("healthy"):
            best = max(best, float(p.get("probability", 0)))
    return best


def _compute_weather_risk(weather_summary: dict | None) -> str:
    """Compute risk level from stored weather_summary JSON.

    Falls back to "LOW" when weather data is absent or incomplete.
    """
    if not weather_summary:
        return "LOW"
    try:
        result = assess_risk(weather_summary)
        return result.level
    except Exception:
        return "LOW"


def _disease_name_from_scan(scan: DiseaseScan) -> str:
    """Get the detected disease name, normalised for display."""
    return scan.detected_disease or "Unknown"


# ---------------------------------------------------------------------------
# Estate-level insights
# ---------------------------------------------------------------------------

def get_estate_insights(db, user_id: UUID):
    """Aggregate insights across all of a user's fields."""

    # --- Load fields + scans -------------------------------------------
    fields_stmt = select(Field).where(Field.user_id == user_id)
    fields_list = db.execute(fields_stmt).scalars().unique().all()

    field_ids = [f.id for f in fields_list]
    total_fields = len(fields_list)

    # Load all scans for these fields in one query
    if field_ids:
        scans_stmt = (
            select(DiseaseScan)
            .where(DiseaseScan.field_id.in_(field_ids))
            .order_by(DiseaseScan.scan_datetime.desc())
        )
    else:
        scans_stmt = select(DiseaseScan).where(DiseaseScan.id == None)  # empty

    all_scans = db.execute(scans_stmt).scalars().all()

    # Index scans by field_id for quick lookup
    scans_by_field: dict[UUID, list[DiseaseScan]] = defaultdict(list)
    for scan in all_scans:
        scans_by_field[scan.field_id].append(scan)

    # --- KPI cards ----------------------------------------------------
    high_risk_field_count = 0
    fields_with_scans = 0
    action_due_count = 0
    affected_area = 0.0

    for field in fields_list:
        field_scans = scans_by_field.get(field.id, [])
        if field_scans:
            fields_with_scans += 1

            latest = field_scans[0]  # sorted desc by scan_datetime

            # Compute risk from the latest scan's weather
            risk = _compute_weather_risk(latest.weather_summary)
            if risk == "HIGH":
                high_risk_field_count += 1

            # Health assessment
            max_disease_prob = _max_disease_probability(latest.all_predictions)
            is_healthy = _is_healthy(latest.detected_disease)

            if not is_healthy and max_disease_prob > HIGH_RISK_THRESHOLD:
                high_risk_field_count += 1
                affected_area += float(field.area_hectares)

            # Action due: low confidence or disease detected
            needs_action = (
                (latest.confidence is not None and latest.confidence < LOW_CONFIDENCE_THRESHOLD)
                or (not is_healthy and max_disease_prob > 0.3)
            )
            if needs_action:
                action_due_count += 1

    scan_coverage_pct = round((fields_with_scans / total_fields * 100), 1) if total_fields else 0.0

    # --- Risk map -----------------------------------------------------
    risk_map = []
    for field in fields_list:
        field_scans = scans_by_field.get(field.id, [])
        if not field_scans:
            health_pct = 100.0
            risk = "LOW"
        else:
            latest = field_scans[0]
            risk = _compute_weather_risk(latest.weather_summary)
            max_prob = _max_disease_probability(latest.all_predictions)
            health_pct = round((1.0 - max_prob) * 100, 1) if max_prob > 0 else 100.0
            health_pct = max(0.0, min(100.0, health_pct))

            # If risk_level column is populated, prefer stored value
            if latest.risk_level:
                risk = latest.risk_level.upper()

        risk_map.append({
            "field_id": str(field.id),
            "field_name": field.name,
            "risk_level": risk,
            "health_percentage": health_pct,
        })

    # Sort by risk level descending (HIGH first)
    risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    risk_map.sort(key=lambda x: risk_order.get(x["risk_level"], 3))

    # --- Disease trend (daily, last 30 days) --------------------------
    today = date.today()
    trend_map: dict[date, dict] = defaultdict(lambda: {"total_scans": 0, "disease_distribution": defaultdict(int)})

    for scan in all_scans:
        scan_date = scan.scan_datetime.date()
        if (today - scan_date).days > 30:
            continue
        d = trend_map[scan_date]
        d["total_scans"] += 1
        d["disease_distribution"][_disease_name_from_scan(scan)] += 1

    disease_trend = []
    for d in sorted(trend_map.keys()):
        data = trend_map[d]
        disease_trend.append({
            "date": d.isoformat(),
            "total_scans": data["total_scans"],
            "disease_distribution": dict(data["disease_distribution"]),
        })

    # --- Field priority (ranked) --------------------------------------
    field_priority = []
    for field in fields_list:
        field_scans = scans_by_field.get(field.id, [])
        if not field_scans:
            continue

        latest = field_scans[0]
        max_prob = _max_disease_probability(latest.all_predictions)
        is_healthy = _is_healthy(latest.detected_disease)

        if is_healthy and max_prob == 0:
            score = 0.0
        else:
            # Base score from probability
            score = max_prob * 100
            # Boost by frequency of disease scans
            disease_scans = sum(
                1 for s in field_scans
                if not _is_healthy(s.detected_disease)
            )
            detection_rate = disease_scans / len(field_scans)
            score *= (1 + detection_rate)
            # Weight by field size
            score = min(100.0, score * (1 + min(float(field.area_hectares) / 10, 1.0)))

        if score >= HIGH_RISK_THRESHOLD * 100:
            level = "high"
        elif score >= MEDIUM_RISK_THRESHOLD * 100:
            level = "medium"
        else:
            level = "low"

        field_priority.append({
            "field_id": str(field.id),
            "field_name": field.name,
            "priority_score": round(score, 1),
            "priority_level": level,
            "detected_disease": latest.detected_disease,
            "confidence": float(latest.confidence) if latest.confidence is not None else None,
            "severity": latest.severity,
        })

    # Sort by priority score descending
    field_priority.sort(key=lambda x: x["priority_score"], reverse=True)

    # --- Disease composition ------------------------------------------
    composition_map: dict[str, int] = defaultdict(int)
    total_predictions = 0

    for scan in all_scans:
        if scan.all_predictions:
            for p in scan.all_predictions:
                comp_name = p.get("disease") or _disease_name_from_scan(scan)
                composition_map[comp_name] += 1
                total_predictions += 1

    disease_composition = {}
    if total_predictions > 0:
        for name, count in composition_map.items():
            disease_composition[name] = round(count / total_predictions * 100, 1)
    else:
        # Fallback: use detected_disease from scans
        for scan in all_scans:
            comp_name = _disease_name_from_scan(scan)
            if not _is_healthy(comp_name):
                composition_map[comp_name] += 1
                total_predictions += 1
        if total_predictions > 0:
            for name, count in composition_map.items():
                disease_composition[name] = round(count / total_predictions * 100, 1)

    # --- Action queue --------------------------------------------------
    action_queue = []

    for field in fields_list:
        field_scans = scans_by_field.get(field.id, [])
        if not field_scans:
            action_queue.append({
                "field_id": str(field.id),
                "field_name": field.name,
                "action_type": "inspection",
                "reason": "Field has no scans — initial inspection recommended",
                "severity": "medium",
                "last_scan_date": None,
                "confidence": None,
            })
            continue

        latest = field_scans[0]
        days_since = (date.today() - latest.scan_datetime.date()).days

        # Rescan if not scanned in threshold days
        if days_since > RESCAN_THRESHOLD_DAYS:
            action_queue.append({
                "field_id": str(field.id),
                "field_name": field.name,
                "action_type": "rescan",
                "reason": f"No scan in {days_since} days — rescan recommended",
                "severity": "medium",
                "last_scan_date": latest.scan_datetime.isoformat(),
                "confidence": float(latest.confidence) if latest.confidence is not None else None,
            })
            continue

        # Inspection for low confidence
        if latest.confidence is not None and latest.confidence < LOW_CONFIDENCE_THRESHOLD:
            action_queue.append({
                "field_id": str(field.id),
                "field_name": field.name,
                "action_type": "inspection",
                "reason": f"Low prediction confidence ({latest.confidence:.2f}) — manual inspection recommended",
                "severity": "high" if latest.confidence < 0.5 else "medium",
                "last_scan_date": latest.scan_datetime.isoformat(),
                "confidence": float(latest.confidence),
            })
            continue

        # Follow-up for active disease
        max_prob = _max_disease_probability(latest.all_predictions)
        if not _is_healthy(latest.detected_disease) and max_prob > 0.3:
            action_queue.append({
                "field_id": str(field.id),
                "field_name": field.name,
                "action_type": "follow_up",
                "reason": f"Disease detected: {_disease_name_from_scan(latest)} — treatment recommended",
                "severity": "high",
                "last_scan_date": latest.scan_datetime.isoformat(),
                "confidence": float(latest.confidence) if latest.confidence is not None else None,
            })

    return {
        "kpi_cards": {
            "high_risk_field_count": high_risk_field_count,
            "scan_coverage_pct": scan_coverage_pct,
            "action_due_count": action_due_count,
            "affected_area_hectares": round(affected_area, 2),
        },
        "risk_map": risk_map,
        "disease_trend": disease_trend,
        "field_priority": field_priority,
        "disease_composition": disease_composition,
        "action_queue": action_queue,
    }


# ---------------------------------------------------------------------------
# Field-level insights
# ---------------------------------------------------------------------------

def get_field_insights(db, user_id: UUID, field_id: UUID):
    """Aggregate insights for a single field owned by the user."""

    # Validate ownership
    field = db.get(Field, field_id)
    if not field or field.user_id != user_id:
        return None  # caller raises 404

    # Load all scans for this field
    scans_stmt = (
        select(DiseaseScan)
        .where(DiseaseScan.field_id == field_id)
        .order_by(DiseaseScan.scan_datetime.desc())
    )
    scans = db.execute(scans_stmt).scalars().all()

    total_scans = len(scans)

    # --- Disease pressure score ---------------------------------------
    disease_pressure_score = None
    if scans:
        probs = []
        for s in scans:
            p = _max_disease_probability(s.all_predictions)
            probs.append(p)
        avg_prob = sum(probs) / len(probs) if probs else 0.0
        disease_pressure_score = round(avg_prob * 100, 1)

    # --- Health timeline ----------------------------------------------
    timeline = []
    for scan in scans:
        max_prob = _max_disease_probability(scan.all_predictions)
        health_pct = round((1.0 - max_prob) * 100, 1) if max_prob > 0 else 100.0
        health_pct = max(0.0, min(100.0, health_pct))
        timeline.append({
            "date": scan.scan_datetime.date().isoformat(),
            "health_percentage": health_pct,
            "detected_disease": scan.detected_disease,
            "confidence": float(scan.confidence) if scan.confidence is not None else None,
        })

    # --- Confidence distribution ------------------------------------
    buckets = [{"bucket": b, "count": 0} for b, _, _ in CONFIDENCE_BUCKETS]
    for scan in scans:
        if scan.confidence is None:
            continue
        for i, (label, lo, hi) in enumerate(CONFIDENCE_BUCKETS):
            if lo <= scan.confidence < hi:
                buckets[i]["count"] += 1
                break

    # --- Weather vs disease relationship ------------------------------
    weather_relationship = None
    disease_weather_values = {"humidity": [], "rainfall": [], "temperature": []}
    healthy_weather_values = {"humidity": [], "rainfall": [], "temperature": []}

    for scan in scans:
        ws = scan.weather_summary
        if not ws:
            continue
        humidity = ws.get("avg_humidity_last_7")
        rainfall = ws.get("total_rainfall_last_7")
        temperature = ws.get("avg_temperature_last_7")

        target = disease_weather_values if not _is_healthy(scan.detected_disease) else healthy_weather_values
        if humidity is not None:
            target["humidity"].append(float(humidity))
        if rainfall is not None:
            target["rainfall"].append(float(rainfall))
        if temperature is not None:
            target["temperature"].append(float(temperature))

    if disease_weather_values["humidity"] or healthy_weather_values["humidity"]:
        def _avg(vals):
            return round(sum(vals) / len(vals), 1) if vals else None

        d_avg_humidity = _avg(disease_weather_values["humidity"])
        h_avg_humidity = _avg(healthy_weather_values["humidity"])
        d_avg_rainfall = _avg(disease_weather_values["rainfall"])
        h_avg_rainfall = _avg(healthy_weather_values["rainfall"])
        d_avg_temp = _avg(disease_weather_values["temperature"])
        h_avg_temp = _avg(healthy_weather_values["temperature"])

        insights = []
        if d_avg_humidity is not None and h_avg_humidity is not None:
            if d_avg_humidity > h_avg_humidity:
                insights.append(
                    f"Disease scans occurred with higher humidity ({d_avg_humidity}% vs {h_avg_humidity}% healthy)"
                )
            else:
                insights.append(
                    f"Disease scans occurred with lower humidity ({d_avg_humidity}% vs {h_avg_humidity}% healthy)"
                )
        if d_avg_rainfall is not None and h_avg_rainfall is not None:
            if d_avg_rainfall > h_avg_rainfall:
                insights.append(
                    f"Higher rainfall associated with disease ({d_avg_rainfall}mm vs {h_avg_rainfall}mm)"
                )
            else:
                insights.append(
                    f"Lower rainfall during disease scans ({d_avg_rainfall}mm vs {h_avg_rainfall}mm)"
                )

        weather_relationship = {
            "healthy_avg_humidity": h_avg_humidity,
            "disease_avg_humidity": d_avg_humidity,
            "healthy_avg_rainfall": h_avg_rainfall,
            "disease_avg_rainfall": d_avg_rainfall,
            "healthy_avg_temperature": h_avg_temp,
            "disease_avg_temperature": d_avg_temp,
            "insight": " ".join(insights) if insights else None,
        }

    # --- Treatment response trend (not available) ---------------------
    treatment_response_trend = {
        "available": False,
        "message": (
            "Treatment response tracking requires a treatment_history table. "
            "No treatment tracking data is currently available."
        ),
    }

    return {
        "field_id": str(field.id),
        "field_name": field.name,
        "area_hectares": float(field.area_hectares),
        "total_scans": total_scans,
        "disease_pressure_score": disease_pressure_score,
        "field_health_timeline": timeline,
        "confidence_distribution": buckets,
        "weather_vs_disease_relationship": weather_relationship,
        "treatment_response_trend": treatment_response_trend,
    }
