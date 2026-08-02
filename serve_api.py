from fastapi.openapi import models
import base64
import binascii
import io
import json
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List

import cv2
from dotenv import load_dotenv

load_dotenv()

import joblib
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from xai.explanation_service import generate_explanation
from xai.gradcam import generate_gradcam

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_PATH = Path("multimodal_efficientnet_20260731_025816/efficientnet_model.h5")
SCALER_PATH = Path("multimodal_efficientnet_20260731_025816/scaler.pkl")
CLASS_MAP_PATH = Path("models/class_indices.json")

BACKBONE = os.environ.get(
    "BACKBONE",
    "efficientnet"
)

IMG_SIZE = int(os.environ.get(
    "IMG_SIZE",
    "224"
))

MODEL_ENV_FEATURE_ORDER = [
    "total_rainfall_last_7",
    "avg_temperature_last_7",
    "avg_humidity_last_7",
    "avg_wind_speed_last_7",
    "avg_sunshine_hours_last_7",
]

CLASS_KEY_MAP = {
    "mite_damage_pest": "Spider_mite_disease",
    "anthracnose": "Anthracnose",
    "blister_blight": "Blister_blight",
    "healthy": "Healthy",
    "fungal":"Algae_or_Moss",
    "nutrient_deficiency_Mg": "Nutrient_deficiency_Mg",
}

# ---------------------------------------------------------------------------
# App + lazy-loaded model state
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Tea Disease Detection — ML Backend",
    version="1.1.0",
)

_state: Dict[str, object] = {}

_load_lock = threading.Lock()

def _preprocess_input_fn(backbone: str):
    if backbone == "efficientnet":
        from tensorflow.keras.applications.efficientnet import preprocess_input
    elif backbone == "resnet":
        from tensorflow.keras.applications.resnet import preprocess_input
    elif backbone == "mobilenet":
        from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
    else:
        raise ValueError(f"Unknown backbone: {backbone}")
    return preprocess_input

@app.on_event("startup")
def load_artifacts() -> None:
    """Load model artifacts. Idempotent — safe to call from threads;
    the model is loaded only once and subsequent calls are no-ops."""
    with _load_lock:
        if "model" in _state:
            print("Model already loaded, skipping artifact loading.")
            return

        if not MODEL_PATH.exists():
            raise RuntimeError(f"Model not found at {MODEL_PATH}")
        if not SCALER_PATH.exists():
            raise RuntimeError(f"Scaler not found at {SCALER_PATH}")
        if not CLASS_MAP_PATH.exists():
            raise RuntimeError(f"Class map not found at {CLASS_MAP_PATH}")

        import tensorflow as tf

        print(f"Loading model from {MODEL_PATH} ...")
        _state["model"] = tf.keras.models.load_model(
            MODEL_PATH,
            compile=False,
        )

        gradcam_path = MODEL_PATH.with_name(
            MODEL_PATH.stem + "_gradcam.h5"
        )

        print(f"Loading GradCAM model from {gradcam_path} ...")

        _state["gradcam_model"] = tf.keras.models.load_model(
            gradcam_path,
            compile=False,
        )

        # Debug: check model architecture
        print("Model output shape:")
        print(_state["model"].output_shape)

        print(f"Loading scaler from {SCALER_PATH} ...")
        _state["scaler"] = joblib.load(SCALER_PATH)

        class_indices = json.loads(CLASS_MAP_PATH.read_text(encoding="utf-8"))
        _state["index_to_class"] = {v: k for k, v in class_indices.items()}
        _state["preprocess_input"] = _preprocess_input_fn(BACKBONE)

        print(f"Loaded {len(class_indices)} classes: {list(class_indices)}")
        print("Model, scaler, and class map loaded. Ready to serve.")

        print("\nMODEL LAYERS")
        for i, layer in enumerate(_state["model"].layers):
            print(i, layer.name, type(layer))

        print("\nGradCAM model outputs:")
        print(_state["gradcam_model"].output_shape)
        _state["gradcam_model"].summary()
# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class WeatherInput(BaseModel):
    total_rainfall_last_7: float
    avg_temperature_last_7: float
    avg_humidity_last_7: float
    avg_wind_speed_last_7: float
    avg_sunshine_hours_last_7: float


class PredictRequest(BaseModel):
    image: str = Field(..., description="Base64-encoded image bytes")
    weather: WeatherInput

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def _run_prediction(image_bytes: bytes, weather_dict: Dict[str, float]) -> Dict[str, list]:
    """Shared inference logic used by both /predict and /predict/upload."""
    if "model" not in _state:
        raise HTTPException(status_code=503, detail="Model is not loaded yet.")

    from tensorflow.keras.preprocessing.image import img_to_array, load_img

    try:
        img = load_img(io.BytesIO(image_bytes), target_size=(IMG_SIZE, IMG_SIZE))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not decode image: {exc}")

    img_array = img_to_array(img).astype(np.float32)
    img_array = _state["preprocess_input"](img_array)
    img_batch = np.expand_dims(img_array, axis=0)

    try:
        env_values = np.array(
            [[weather_dict[key] for key in MODEL_ENV_FEATURE_ORDER]],
            dtype=np.float32,
        )
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"Missing weather field: {exc}")

    env_scaled = _state["scaler"].transform(env_values)

    try:
        preds = _state["model"].predict([img_batch, env_scaled], verbose=0)[0]
        print("RAW:", preds)
        print("SUM:", preds.sum())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}")

    index_to_class = _state["index_to_class"]

    predictions: List[Dict[str, float]] = []
    for i, prob in enumerate(preds):
        raw_key = index_to_class[i]
        mapped_key = CLASS_KEY_MAP.get(raw_key, raw_key)
        predictions.append({"class": mapped_key, "probability": float(prob)})

    predictions.sort(key=lambda p: p["probability"], reverse=True)

    return {"predictions": predictions}

def run_batch_inference(
    images: list[tuple[str, bytes]],
    weather_dict: dict,
) -> dict:
    """
    Run batch disease inference directly using the lazily-loaded internal
    model — no HTTP calls.

    This is the direct-callable equivalent of the ``/predict/batch``
    endpoint.  The model / scaler / class-map are loaded on the first call
    (``load_artifacts`` is idempotent and thread-safe).

    Parameters
    ----------
    images
        List of ``(filename, image_bytes)`` tuples — already read from
        ``UploadFile`` objects by the caller.
    weather_dict
        Dict with the five keys listed in ``MODEL_ENV_FEATURE_ORDER``
        mapping to float values.

    Returns
    -------
    dict with keys: ``predictions``, ``explanation``, ``processed_images``,
    ``failed_images`` — identical to what ``/predict/batch`` returned.
    """

    # Lazy-load model artifacts on first call
    load_artifacts()

    if len(images) == 0:
        raise ValueError("At least one image is required.")

    print(f"\n[predict/batch] Received {len(images)} image(s). Weather: {weather_dict}")

    from tensorflow.keras.preprocessing.image import img_to_array, load_img

    # -------------------------------
    # Prepare weather
    # -------------------------------
    env_values = np.array(
        [[weather_dict[key] for key in MODEL_ENV_FEATURE_ORDER]],
        dtype=np.float32,
    )
    env_scaled = _state["scaler"].transform(env_values)

    index_to_class = _state["index_to_class"]

    # -------------------------------
    # Storage
    # -------------------------------
    prob_vectors = []
    processed_images = []   # BUG FIX: this was never populated before,
    processed_names = []    # so GradCAM/SHAP silently never ran.
    failed_files = []

    # -------------------------------
    # Image predictions
    # -------------------------------
    for i, (filename, image_bytes) in enumerate(images, start=1):
        try:
            img = load_img(io.BytesIO(image_bytes), target_size=(IMG_SIZE, IMG_SIZE))
        except Exception as exc:
            failed_files.append(filename)
            print(f"[predict/batch] [{i}/{len(images)}] {filename} FAILED: {exc}")
            continue

        img_array = img_to_array(img).astype(np.float32)
        img_array = _state["preprocess_input"](img_array)
        img_batch = np.expand_dims(img_array, axis=0)

        # keep it this time - needed for per-image GradCAM + SHAP
        processed_images.append(img_batch)
        processed_names.append(filename)

        try:
            preds = _state["model"].predict([img_batch, env_scaled], verbose=0)[0]
        except Exception as exc:
            raise RuntimeError(f"Inference failed on {filename}: {exc}") from exc

        prob_vectors.append(preds)

        # -------------------------------
        # Logging
        # -------------------------------
        top_idx = int(np.argmax(preds))
        top_raw = index_to_class[top_idx]
        top_class = CLASS_KEY_MAP.get(top_raw, top_raw)
        top_prob = float(preds[top_idx])

        per_class_sorted = sorted(
            [
                (CLASS_KEY_MAP.get(index_to_class[j], index_to_class[j]), float(prob))
                for j, prob in enumerate(preds)
            ],
            key=lambda x: x[1],
            reverse=True,
        )
        breakdown = ", ".join(f"{cls}={prob:.4f}" for cls, prob in per_class_sorted)

        print(f"[predict/batch] [{i}/{len(images)}] {filename}")
        print(f"    top: {top_class} ({top_prob:.4f})")
        print(f"    all: {breakdown}")

    if len(prob_vectors) == 0:
        raise ValueError(f"No images processed. Failed: {failed_files}")

    # -------------------------------
    # Ensemble prediction
    # -------------------------------
    mean_probs = np.mean(np.stack(prob_vectors), axis=0)

    predictions = []
    for idx, prob in enumerate(mean_probs):
        raw_key = index_to_class[idx]
        mapped_key = CLASS_KEY_MAP.get(raw_key, raw_key)
        predictions.append({"class": mapped_key, "probability": float(prob)})

    predictions.sort(key=lambda x: x["probability"], reverse=True)

    top_class_index = int(np.argmax(mean_probs))

    # ==================================================
    # XAI (GradCAM + SHAP) - once per image, run concurrently
    # ==================================================
    # Both explainers are dominated by model.predict()/gradient calls,
    # which release the GIL while TensorFlow does the actual compute, so
    # a thread pool gives a real wall-clock speedup here instead of
    # running each image's XAI strictly one after another.
    #
    # If your TF/Keras version turns out not to be thread-safe for
    # concurrent predict/gradient calls on the same model object, wrap
    # the body of `_explain_one` in a shared `threading.Lock()` - it'll
    # still be correct, just back to sequential for the model calls.

    # Build the GradCAM wrapper model once, synchronously, on this
    # thread - BEFORE any worker threads try to use it. This is what
    # avoids the "Output with path `0` is not connected to `inputs`"
    # race when several images are explained concurrently.
    # warmup_gradcam(_state["model"])

    per_image_explanations = [None] * len(processed_images)

    def _explain_one(idx, img_batch):
        gradcam_path = f"explanations/generated/gradcam_{uuid.uuid4()}.jpg"
        result = generate_explanation(
            prediction_model=_state["model"],
            gradcam_model=_state["gradcam_model"],
            image_batch=img_batch,
            env_scaled=env_scaled,
            predicted_class=top_class_index,
            output_path=gradcam_path,
        )
        return idx, result

    max_workers = 1
    with ThreadPoolExecutor(max_workers=1) as pool:
        futures = [
            pool.submit(_explain_one, idx, img_batch)
            for idx, img_batch in enumerate(processed_images)
        ]
        for future in as_completed(futures):
            idx, result = future.result()
            per_image_explanations[idx] = result

    per_image_results = [
        {
            "filename": processed_names[idx],
            "gradcam_image": exp["gradcam_image"],
            "environment_factors": exp["environment_factors"],
        }
        for idx, exp in enumerate(per_image_explanations)
    ]

    # ==================================================
    # Aggregated GradCAM (mean heatmap across images)
    # ==================================================
    aggregated_path = None
    heatmaps = [exp["gradcam_heatmap"] for exp in per_image_explanations]

    if len(heatmaps) > 0:
        mean_heatmap = np.mean(np.stack(heatmaps), axis=0)
        mean_heatmap = np.uint8(mean_heatmap * 255)

        aggregated_path = f"explanations/generated/aggregate_{uuid.uuid4()}.jpg"
        Path(aggregated_path).parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(aggregated_path, mean_heatmap)

    # ==================================================
    # Final logs
    # ==================================================
    print(f"[predict/batch] Combined result from {len(prob_vectors)}/{len(images)} images")
    for p in predictions:
        print(f"{p['class']}: {p['probability']:.6f}")
    print(f"[predict/batch] FINAL: {predictions[0]['class']} {predictions[0]['probability']:.4f}")

    return {
        "predictions": predictions,

        "explanation": {
            "per_image": per_image_results,
            "aggregated_gradcam": aggregated_path,
        },

        "processed_images": len(prob_vectors),

        "failed_images": failed_files,
    }

@app.post("/predict/batch", tags=["Prediction"])
async def predict_batch(
    images: List[UploadFile] = File(
        ...,
        description="Multiple leaf photos (jpg/png) from one scan session"
    ),
    total_rainfall_last_7: float = Form(...),
    avg_temperature_last_7: float = Form(...),
    avg_humidity_last_7: float = Form(...),
    avg_wind_speed_last_7: float = Form(...),
    avg_sunshine_hours_last_7: float = Form(...),
):
    """Batch prediction — delegates to :func:`run_batch_inference`."""
    if len(images) == 0:
        raise HTTPException(status_code=422, detail="At least one image is required.")

    weather_dict = {
        "total_rainfall_last_7": total_rainfall_last_7,
        "avg_temperature_last_7": avg_temperature_last_7,
        "avg_humidity_last_7": avg_humidity_last_7,
        "avg_wind_speed_last_7": avg_wind_speed_last_7,
        "avg_sunshine_hours_last_7": avg_sunshine_hours_last_7,
    }

    # Read every UploadFile into (filename, bytes) tuples — the heavy
    # lifting (decode + inference + XAI) is done by run_batch_inference.
    image_tuples: list[tuple[str, bytes]] = []
    read_failed: list[str] = []
    for i, upload in enumerate(images, start=1):
        filename = upload.filename or f"<unnamed_{i}>"
        try:
            image_tuples.append((filename, await upload.read()))
        except Exception as exc:
            read_failed.append(filename)
            print(f"[predict/batch] [{i}/{len(images)}] {filename} FAILED to read: {exc}")

    try:
        result = run_batch_inference(image_tuples, weather_dict)
        # Merge read failures (endpoint-side) with decode failures
        # (function-side) so the response contains every failed file.
        result["failed_images"] = read_failed + result.get("failed_images", [])
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(status_code=503, detail="Model is not loaded: " + msg)
        raise HTTPException(status_code=500, detail=msg)
