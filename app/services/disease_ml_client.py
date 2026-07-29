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


@dataclass
class BatchPredictionResult:
    predictions: list[RawPrediction]
    explanation: dict
    processed_images: int
    failed_images: list[str]


class MLPredictionError(Exception):
    """Raised when the ML backend call fails or returns an unusable response."""


async def predict_disease_from_images(
    images: list[tuple[str, bytes]],
    weather: dict,
) -> BatchPredictionResult:
    """
    POSTs multiple leaf images + weather aggregates to ML backend.

    Calls:
        POST {ML_MODEL_URL}/predict/batch

    Returns:
        Raw predictions + explanations returned by ML backend.
    """

    url = f"{settings.ML_MODEL_URL.rstrip('/')}/predict/batch"

    files = []

    for filename, image_bytes in images:
        files.append(
            (
                "images",
                (
                    filename,
                    image_bytes,
                    "image/jpeg",
                ),
            )
        )


    form_data = {
        "total_rainfall_last_7": str(weather.get("total_rainfall_last_7", 0)),
        "avg_temperature_last_7": str(weather.get("avg_temperature_last_7", 0)),
        "avg_humidity_last_7": str(weather.get("avg_humidity_last_7", 0)),
        "avg_wind_speed_last_7": str(weather.get("avg_wind_speed_last_7", 0)),
        "avg_sunshine_hours_last_7": str(weather.get("avg_sunshine_hours_last_7", 0)),
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                files=files,
                data=form_data,
                timeout=60.0,
            )

            response.raise_for_status()
            data = response.json()

    except httpx.TimeoutException as e:
        raise MLPredictionError(
            f"ML backend timed out: {e}"
        ) from e

    except httpx.HTTPStatusError as e:
        raise MLPredictionError(
            f"ML backend returned {e.response.status_code}: {e.response.text}"
        ) from e

    except httpx.RequestError as e:
        raise MLPredictionError(
            f"Could not reach ML backend at {url}: {e}"
        ) from e


    raw_predictions = data.get("predictions")

    if not raw_predictions:
        raise MLPredictionError(
            "ML backend response missing 'predictions'"
        )


    try:
        predictions = [
            RawPrediction(
                class_key=p["class"],
                probability=float(p["probability"]),
            )
            for p in raw_predictions
        ]

    except (KeyError, TypeError, ValueError) as e:
        raise MLPredictionError(
            f"Malformed prediction entry: {e}"
        ) from e


    predictions.sort(
        key=lambda p: p.probability,
        reverse=True
    )


    return BatchPredictionResult(
        predictions=predictions,
        explanation=data.get("explanation", {}),
        processed_images=data.get("processed_images", 0),
        failed_images=data.get("failed_images", []),
    )