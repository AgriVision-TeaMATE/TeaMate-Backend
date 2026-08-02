"""
Pydantic response schemas for Disease Insights APIs.
These aggregate data from DiseaseScan, Field, and Disease reference tables.
No ML inference — pure data aggregation/reporting.
"""
from pydantic import ConfigDict
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Shared component schemas
# ---------------------------------------------------------------------------

class KPISummary(BaseModel):
    """Four KPI cards shown on the Estate Insights screen."""
    high_risk_field_count: int = 0
    scan_coverage_pct: float = 0.0
    action_due_count: int = 0
    affected_area_hectares: float = 0.0


class RiskMapEntry(BaseModel):
    """One row in the risk-map list."""
    field_id: UUID
    field_name: str
    risk_level: str  # "HIGH" | "MEDIUM" | "LOW"
    health_percentage: float  # 0–100, higher = healthier


class DiseaseTrendEntry(BaseModel):
    """One data point in the disease-trend chart."""
    date: date
    total_scans: int
    disease_distribution: dict[str, int]  # {disease_name: count}


class FieldPriorityEntry(BaseModel):
    """One ranked field in the priority list."""
    field_id: UUID
    field_name: str
    priority_score: float  # 0–100
    priority_level: str  # "high" | "medium" | "low"
    detected_disease: str | None = None
    confidence: float | None = None
    severity: str | None = None


class ActionQueueEntry(BaseModel):
    """One suggested action in the action queue."""
    field_id: UUID
    field_name: str
    action_type: str  # "inspection" | "rescan" | "follow_up"
    reason: str
    severity: str  # "high" | "medium" | "low"
    last_scan_date: datetime | None = None
    confidence: float | None = None


# ---------------------------------------------------------------------------
# Estate Insights
# ---------------------------------------------------------------------------

class EstateInsightsResponse(BaseModel):
    """GET /api/v1/disease/estate-insights"""
    model_config = ConfigDict(from_attributes=False)

    kpi_cards: KPISummary
    risk_map: list[RiskMapEntry]
    disease_trend: list[DiseaseTrendEntry]
    field_priority: list[FieldPriorityEntry]
    disease_composition: dict[str, float]  # {disease_name: percentage}
    action_queue: list[ActionQueueEntry]


# ---------------------------------------------------------------------------
# Field Insights
# ---------------------------------------------------------------------------

class HealthTimelineEntry(BaseModel):
    """One point on the health timeline."""
    date: date
    health_percentage: float
    detected_disease: str | None = None
    confidence: float | None = None


class ConfidenceDistributionItem(BaseModel):
    bucket: str
    count: int


class WeatherDiseaseRelationship(BaseModel):
    """Comparison of weather conditions during healthy vs disease scans."""
    healthy_avg_humidity: float | None = None
    disease_avg_humidity: float | None = None
    healthy_avg_rainfall: float | None = None
    disease_avg_rainfall: float | None = None
    healthy_avg_temperature: float | None = None
    disease_avg_temperature: float | None = None
    insight: str | None = None


class TreatmentResponseTrend(BaseModel):
    """Treatment tracking is not yet implemented in the database."""
    available: bool = False
    message: str = (
        "Treatment response tracking requires a treatment_history table. "
        "No treatment tracking data is currently available."
    )


class FieldInsightsResponse(BaseModel):
    """GET /api/v1/disease/field-insights/{field_id}"""
    model_config = ConfigDict(from_attributes=False)

    field_id: UUID
    field_name: str
    area_hectares: float
    total_scans: int

    disease_pressure_score: float | None = None

    field_health_timeline: list[HealthTimelineEntry]
    confidence_distribution: list[ConfidenceDistributionItem]
    weather_vs_disease_relationship: WeatherDiseaseRelationship | None = None
    treatment_response_trend: TreatmentResponseTrend | None = None
