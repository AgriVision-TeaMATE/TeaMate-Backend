"""
Real ML backend client.

Invokes the internal TensorFlow model (loaded from serve_api.py) directly
with the leaf image bytes and the last-7-days weather summary, and returns
raw {class, probability} predictions. This module does NOT interpret those
predictions — no descriptions, risk, or recommendations. Per the architecture
split: ML backend predicts, main backend decides everything else.
"""
import asyncio
from dataclasses import dataclass
from pathlib import Path
import sys


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

    environmental_summary: str | None = None
    environmental_insights: list | None = None
    environmental_technical_summary: dict | None = None


class MLPredictionError(Exception):
    """Raised when the ML backend call fails or returns an unusable response."""


# Lazily imported handle to the serve_api module (the ML backend).
# Populated on the first call to predict_disease_from_images.
_serve_api_module = None


def _get_serve_api():
    """Lazy-import the serve_api module that holds the loaded model.

    The project root (parent of the ``app`` package) is added to
    ``sys.path`` so that ``import serve_api`` resolves regardless of the
    current working directory.
    """
    global _serve_api_module
    if _serve_api_module is None:
        project_root = str(Path(__file__).resolve().parents[2])  # app/services -> root
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        import serve_api
        _serve_api_module = serve_api
    return _serve_api_module


async def predict_disease_from_images(
    images: list[tuple[str, bytes]],
    weather: dict,
) -> BatchPredictionResult:
    """
    Run disease inference directly using the internal ML model — no HTTP calls.

    Invokes the model loading, preprocessing, inference, and postprocessing
    code in serve_api.py directly via ``run_batch_inference``.

    Returns:
        Raw predictions + explanations returned by ML backend.
    """

    # Build the weather dict the model expects, defaulting missing / None
    # values to 0 (same semantics as the previous HTTP form encoding).
    weather_dict = {
        "total_rainfall_last_7": weather.get("total_rainfall_last_7") or 0,
        "avg_temperature_last_7": weather.get("avg_temperature_last_7") or 0,
        "avg_humidity_last_7": weather.get("avg_humidity_last_7") or 0,
        "avg_wind_speed_last_7": weather.get("avg_wind_speed_last_7") or 0,
        "avg_sunshine_hours_last_7": weather.get("avg_sunshine_hours_last_7") or 0,
    }

    try:
        serve_api = _get_serve_api()
        data = await asyncio.to_thread(
            serve_api.run_batch_inference, images, weather_dict
        )

    except ImportError as e:
        raise MLPredictionError(
            f"ML backend modules not available: {e}"
        ) from e

    except Exception as e:
        raise MLPredictionError(
            f"ML backend call failed: {e}"
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

    environmental_summary=data.get(
        "environmental_summary"
    ),

    environmental_insights=data.get(
        "environmental_insights"
    ),

    environmental_technical_summary=data.get(
        "environmental_technical_summary"
    ),
)
