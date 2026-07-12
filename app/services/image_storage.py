import base64
from pathlib import Path
from urllib.parse import urlparse

from ..models import Field, HarvestRound

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "media" / "analysis-images"


def delete_analysis_file_for_url(image_url: str | None) -> None:
    if not image_url:
        return

    parsed = urlparse(image_url)
    file_name = Path(parsed.path).name
    if not file_name:
        return

    target = UPLOAD_DIR / file_name
    if target.exists():
        target.unlink()


def local_path_for_image_url(image_url: str | None) -> Path | None:
    if not image_url:
        return None

    parsed = urlparse(image_url)
    file_name = Path(parsed.path).name
    if not file_name:
        return None

    target = UPLOAD_DIR / file_name
    return target if target.exists() else None


def replace_analysis_file_with_base64(image_url: str | None, encoded_image: str) -> None:
    if not encoded_image:
        return

    target = local_path_for_image_url(image_url)
    if target is None:
        return

    target.write_bytes(base64.b64decode(encoded_image))


def delete_round_analysis_files(round_obj: HarvestRound) -> None:
    for image in round_obj.analysis_images:
        delete_analysis_file_for_url(image.image_url)


def delete_field_analysis_files(field: Field) -> None:
    for round_obj in field.harvest_rounds:
        delete_round_analysis_files(round_obj)
