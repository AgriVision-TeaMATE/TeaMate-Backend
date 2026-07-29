from datetime import date, time, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WeatherSummary(BaseModel):
    """Rolling 7-day weather aggregates, matching /weather/weekly-summary
    and the fields the ML backend expects."""

    # rainy_days_last_7: int | None = Field(default=None, ge=0, le=7)
    # rainy_hours_last_7: int | None = Field(default=None, ge=0)
    total_rainfall_last_7: float | None = Field(default=None, ge=0)
    avg_temperature_last_7: float | None = None
    avg_humidity_last_7: float | None = Field(default=None, ge=0, le=100)
    # max_humidity_last_7: float | None = Field(default=None, ge=0, le=100)
    avg_wind_speed_last_7: float | None = Field(default=None, ge=0)
    # max_wind_speed_last_7: float | None = Field(default=None, ge=0)
    avg_sunshine_hours_last_7: float | None = None
    # estimated_leaf_wetness_hours_last_7: int | None = Field(default=None, ge=0)


class DiseaseScanCreate(BaseModel):
    field_id: UUID | None = None
    latitude: float | None = None
    longitude: float | None = None
    weather_summary: WeatherSummary | None = None
    environmental_data: dict | None = None


class DiseaseScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scan_id: str
    field_id: UUID | None = None
    latitude: float | None = None
    longitude: float | None = None
    scan_datetime: datetime
    image_url: str
    detected_disease: str
    severity: str
    confidence: float
    description: str | None = None
    weather_summary: dict | None = None
    environmental_data: dict | None = None
    risk_level: str | None = None
    risk_reason: str | None = None
    treatment_suggestions: list | None = None
    all_predictions: list | None = None
    model_version: str | None = None
    inference_time_ms: float | None = None
    created_at: datetime
    updated_at: datetime


class MostProbableDisease(BaseModel):
    disease_name: str
    confidence: float
    severity: str
    description: str
    causes: list[str] = []


class ConfidenceItem(BaseModel):
    disease: str
    probability: float
    confidence_label: str
    category: str


class Classification(BaseModel):
    level: str
    label: str
    confidence: float
    category: str | None = None
    message: str

class AIExplanation(BaseModel):
    disease: str
    explanation: str
    recommended_actions: list[str]


class RiskLevel(BaseModel):
    level: str
    reason: str


class ScanSummary(BaseModel):
    field_id: UUID | None = None
    field_name: str | None = None
    date: date
    time: time
    weather_details: WeatherSummary | None = None
    image_url: str
    latitude: float | None = None
    longitude: float | None = None
    scan_datetime: datetime


class Meta(BaseModel):
    model_version: str | None = None
    inference_time_ms: float | None = None
    timestamp: datetime


class DiseaseScanAPIResponse(BaseModel):
    scan_id: str
    status: str
    scan_summary: ScanSummary
    most_probable_disease: MostProbableDisease
    confidence_analysis: list[ConfidenceItem]
    # risk_level: RiskLevel
    # ai_explanation: list[AIExplanation]
    recommendations: list[str]
    meta: Meta
    classification: Classification
