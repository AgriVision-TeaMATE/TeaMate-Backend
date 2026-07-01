import base64
import io
import os
import random
from urllib.parse import urlparse

import httpx

from ..config import get_settings

settings = get_settings()


async def fetch_image_bytes(image_url_or_path: str) -> bytes:
    """Fetches image bytes from either a network URL (Firebase), data URI, or local filesystem."""
    if image_url_or_path.startswith("data:"):
        if "," in image_url_or_path:
            encoded_str = image_url_or_path.split(",", 1)[1]
        else:
            encoded_str = image_url_or_path
        return base64.b64decode(encoded_str)

    if image_url_or_path.startswith(("http://", "https://")):
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url_or_path, timeout=15.0)
            response.raise_for_status()
            return response.content

    # Handle local path fallback for testing
    parsed = urlparse(image_url_or_path)
    local_path = parsed.path if parsed.scheme == "file" else image_url_or_path
    if os.path.exists(local_path):
        with open(local_path, "rb") as f:
            return f.read()

    raise ValueError(f"Could not retrieve image from {image_url_or_path}")


async def analyze_image_with_ml(image_url_or_path: str) -> dict:
    """Sends image to E:\\TeaMATE YOLOv8 API (port 8000) and returns bud counts + mask."""
    try:
        img_bytes = await fetch_image_bytes(image_url_or_path)
    except Exception as e:
        print(f"[ML_CLIENT ERROR] Failed to fetch image bytes for payload (starts with '{str(image_url_or_path)[:60]}...'): {e}")
        # Fallback ONLY for development mock URLs
        if settings.DEBUG and "mock" in str(image_url_or_path).lower():
            arimbu = random.randint(10, 25)
            pluckable = random.randint(15, 35)
            return {
                "arimbu_count": arimbu,
                "pluckable_count": pluckable,
                "image": "",
            }
        raise e

    url = f"{settings.ML_MODEL_URL}/predict"
    files = {"file": ("image.jpg", io.BytesIO(img_bytes), "image/jpeg")}

    try:
        async with httpx.AsyncClient() as client:
            print(f"[ML_CLIENT] Sending {len(img_bytes)} bytes to AI model at {url}...")
            response = await client.post(url, files=files, timeout=60.0)
            response.raise_for_status()
            res_json = response.json()
            print(f"[ML_CLIENT] AI model returned arimbu={res_json.get('arimbu_count')}, pluckable={res_json.get('pluckable_count')}")
            return res_json
    except Exception as e:
        print(f"[ML_CLIENT ERROR] Request to AI model ({url}) failed: {e}")
        raise e
