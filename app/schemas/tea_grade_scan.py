from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GradeCompositionEntry(BaseModel):
    grade: str
    percentage: float


class ParticlePredictionEntry(BaseModel):
    label: str
    bbox: list[int]
    area_mm2: float | None = None
    area_px: float | None = None


class TeaGradeScanResponse(BaseModel):
    id: UUID
    scan_id: str
    field_id: UUID | None = None
    field_name: str | None = None
    image_url: str
    scan_datetime: datetime
    grade_composition: list[GradeCompositionEntry]
    dominant_grade: str
    dominant_grade_percentage: float
    total_particles_detected: int | None = None
    num_particles_classified: int | None = None
    method: str | None = None
    weighting: str | None = None
    px_per_mm_used: float | None = None
    particles: list[ParticlePredictionEntry] = []
    segmented_image_base64: str | None = None
    model_version: str | None = None
    inference_time_ms: float | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, scan, field_name: str | None = None) -> "TeaGradeScanResponse":
        composition = sorted(
            (GradeCompositionEntry(grade=grade, percentage=pct) for grade, pct in scan.grade_composition.items()),
            key=lambda entry: entry.percentage,
            reverse=True,
        )
        return cls(
            id=scan.id,
            scan_id=scan.scan_id,
            field_id=scan.field_id,
            field_name=field_name,
            image_url=scan.image_url,
            scan_datetime=scan.scan_datetime,
            grade_composition=composition,
            dominant_grade=scan.dominant_grade,
            dominant_grade_percentage=scan.dominant_grade_percentage,
            total_particles_detected=scan.total_particles_detected,
            num_particles_classified=scan.num_particles_classified,
            method=scan.method,
            weighting=scan.weighting,
            px_per_mm_used=scan.px_per_mm_used,
            particles=[ParticlePredictionEntry(**p) for p in (scan.particles or [])],
            segmented_image_base64=scan.segmented_image_base64,
            model_version=scan.model_version,
            inference_time_ms=scan.inference_time_ms,
            created_at=scan.created_at,
            updated_at=scan.updated_at,
        )
