"""Tea-grade composition prediction client.

The real classify-then-count model (per docs/Plan_Final.md) doesn't exist
yet, so this module returns a deterministic mock composition derived from
the image bytes. The call signature matches what a real HTTP-based ML
service would expose, so swapping the mock body for an actual `httpx` call
later requires no changes to the router.
"""

import hashlib
from dataclasses import dataclass

# from ..config import get_settings
# import httpx

GRADES = ["OP", "OPA", "PEKOE", "BOP", "BOP1", "BOPF", "Dust No.1"]


@dataclass
class RawGradePrediction:
    grade: str
    percentage: float


class MLPredictionError(Exception):
    """Raised when the grading ML backend fails or returns malformed data."""


async def predict_tea_grade_composition(image_bytes: bytes) -> list[RawGradePrediction]:
    """Returns a mock per-grade composition breakdown summing to 100.

    Deterministic per-image (hash-seeded) so repeated calls with the same
    image return the same result, without needing a real model yet.
    """
    if not image_bytes:
        raise MLPredictionError("No image bytes provided")

    digest = hashlib.sha256(image_bytes).digest()
    weights = [digest[i] + 1 for i in range(len(GRADES))]  # avoid all-zero weights
    total_weight = sum(weights)

    percentages = [round(w / total_weight * 100, 2) for w in weights]
    # Correct rounding drift so the breakdown sums to exactly 100.
    percentages[-1] = round(100 - sum(percentages[:-1]), 2)

    predictions = [
        RawGradePrediction(grade=grade, percentage=pct)
        for grade, pct in zip(GRADES, percentages)
    ]
    return sorted(predictions, key=lambda p: p.percentage, reverse=True)

    # --- Future real integration sketch (once the model service exists) ---
    # settings = get_settings()
    # async with httpx.AsyncClient(timeout=30.0) as client:
    #     try:
    #         response = await client.post(
    #             f"{settings.TEA_GRADING_ML_URL.rstrip('/')}/predict",
    #             files={"image": image_bytes},
    #         )
    #         response.raise_for_status()
    #     except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as e:
    #         raise MLPredictionError(str(e)) from e
    #     data = response.json()
    #     return [RawGradePrediction(**item) for item in data["composition"]]
