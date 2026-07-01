from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BudMarkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    x_position: float
    y_position: float
    marker_type: str


class AnalysisImageCreate(BaseModel):
    firebase_url: str
    firebase_path: str
    source_label: str
    captured_at: datetime


class AnalysisImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    harvest_round_id: UUID
    firebase_url: str
    firebase_path: str
    source_label: str
    arimbu_count: int
    pluckable_count: int
    captured_area_sqm: float
    pluckable_ratio: float | None
    is_analyzed: bool
    captured_at: datetime
    analyzed_at: datetime | None
    bud_markers: list[BudMarkerResponse] = []
