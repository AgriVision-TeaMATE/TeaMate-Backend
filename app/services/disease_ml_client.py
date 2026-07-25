"""
Real ML backend client.

Sends the leaf image (base64) and the last-7-days weather summary to the
external ML inference service and returns raw {class, probability}
predictions. This module does NOT interpret those predictions — no
descriptions, risk, or recommendations. Per the architecture split: ML
backend predicts, main backend decides everything else.
"""
import base64
from dataclasses import dataclass

import httpx

from ..config import get_settings

settings = get_settings()


@dataclass
class RawPrediction:
    class_key: str
    probability: float


class MLPredictionError(Exception):
    """Raised when the ML backend call fails or returns an unusable response."""


async def predict_disease_from_image(
    image_bytes: bytes,
    weather: dict,
) -> list[RawPrediction]:
    """
    POSTs to {ML_MODEL_URL}/predict with the image + weather aggregates.
    Returns raw predictions sorted by probability descending.
    """
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "image": encoded_image,
        "weather": weather,
    }

    url = f"{settings.ML_MODEL_URL.rstrip('/')}/predict"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as e:
        raise MLPredictionError(f"ML backend timed out: {e}") from e
    except httpx.HTTPStatusError as e:
        raise MLPredictionError(
            f"ML backend returned {e.response.status_code}: {e.response.text}"
        ) from e
    except httpx.RequestError as e:
        raise MLPredictionError(f"Could not reach ML backend at {url}: {e}") from e

    raw_predictions = data.get("predictions")
    if not raw_predictions:
        raise MLPredictionError("ML backend response missing 'predictions'")

    try:
        predictions = [
            RawPrediction(class_key=p["class"], probability=float(p["probability"]))
            for p in raw_predictions
        ]
    except (KeyError, TypeError, ValueError) as e:
        raise MLPredictionError(f"Malformed prediction entry: {e}") from e

    predictions.sort(key=lambda p: p.probability, reverse=True)
    return predictions