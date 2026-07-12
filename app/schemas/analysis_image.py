from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnalysisImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    harvest_round_id: UUID
    image_url: str
    captured_area_sqm: float
    arimbu_count: int
    pluckable_count: int
