import os

BASE_URL = os.getenv(
    "BASE_URL",
    "http://localhost:8001"
)


def to_public_url(local_path: str | None):
    if not local_path:
        return None

    local_path = local_path.replace("\\", "/")

    return f"{BASE_URL}/{local_path}"