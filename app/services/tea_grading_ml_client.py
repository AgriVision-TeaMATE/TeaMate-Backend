"""Tea-grade composition prediction client.

Calls the real classify-then-count grading model service over HTTP and
returns its raw prediction data. This module does not interpret the
predictions further (no descriptions, recommendations, etc.) — the router
is responsible for persisting and shaping the API response.
"""

from dataclasses import dataclass

import httpx

from ..config import get_settings

settings = get_settings()


@dataclass
class RawGradePrediction:
    grade: str
    percentage: float


@dataclass
class ParticlePrediction:
    label: str
    bbox: list[int]
    area_mm2: float | None = None
    area_px: float | None = None


@dataclass
class RawGradingResult:
    method: str
    weighting: str
    px_per_mm_used: float
    num_particles_detected: int
    num_particles_classified: int
    composition: list[RawGradePrediction]
    particles: list[ParticlePrediction]
    segmented_image_base64: str | None = None


class MLPredictionError(Exception):
    """Raised when the grading ML backend fails or returns malformed data."""


async def predict_tea_grade_composition(
    image_bytes: bytes,
    method: str = "traditional",
    scale_level: int | None = None,
) -> RawGradingResult:
    """POSTs the sample image to the grading model's /predict endpoint and
    returns its full raw response (composition, particles, segmented image).
    """
    if not image_bytes:
        raise MLPredictionError("No image bytes provided")

    if not settings.TEA_GRADING_ML_URL:
        raise MLPredictionError("TEA_GRADING_ML_URL is not configured")

    url = f"{settings.TEA_GRADING_ML_URL.rstrip('/')}/predict"

    data = {
        "method": method,
        "model_name": "random_forest",
        "backbone": "resnet18",
        "include_image": True,
    }
    if scale_level is not None:
        data["scale_level"] = scale_level

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                files={"file": ("image.jpg", image_bytes)},
                data=data,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as e:
        raise MLPredictionError(f"Grading ML backend timed out: {e}") from e
    except httpx.HTTPStatusError as e:
        raise MLPredictionError(
            f"Grading ML backend returned {e.response.status_code}: {e.response.text}"
        ) from e
    except httpx.RequestError as e:
        raise MLPredictionError(f"Could not reach grading ML backend at {url}: {e}") from e

    predicted_proportions = data.get("predicted_proportions")
    if not predicted_proportions:
        raise MLPredictionError("Grading ML backend response missing 'predicted_proportions'")

    try:
        composition = [
            RawGradePrediction(grade=grade, percentage=float(pct) * 100)
            for grade, pct in predicted_proportions.items()
        ]
        composition.sort(key=lambda p: p.percentage, reverse=True)

        particles = [
            ParticlePrediction(
                label=p["label"],
                bbox=list(p["bbox"]),
                area_mm2=p.get("area_mm2"),
                area_px=p.get("area_px"),
            )
            for p in data.get("particles", [])
        ]

        result = RawGradingResult(
            method=data["method"],
            weighting=data["weighting"],
            px_per_mm_used=float(data["px_per_mm_used"]),
            num_particles_detected=int(data["num_particles_detected"]),
            num_particles_classified=int(data["num_particles_classified"]),
            composition=composition,
            particles=particles,
            segmented_image_base64=data.get("segmented_image_base64"),
        )
    except (KeyError, TypeError, ValueError) as e:
        raise MLPredictionError(f"Malformed grading response: {e}") from e

    return result
