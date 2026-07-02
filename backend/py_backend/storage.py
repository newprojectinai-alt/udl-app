import mimetypes
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

import boto3
from botocore.config import Config

from . import config


MEDIA_DIRECTORIES = {
    "uploads": config.UPLOADS_DIR,
    "renders": config.RENDERS_DIR,
    "audio": config.AUDIO_DIR,
}


def uses_s3():
    return bool(config.AWS_S3_BUCKET)


def validate_media_path(category: str, filename: str):
    if category not in MEDIA_DIRECTORIES:
        raise ValueError("Unsupported media category")
    safe_filename = Path(filename).name
    if not safe_filename or safe_filename != filename:
        raise ValueError("Invalid media filename")
    return safe_filename


def media_url(category: str, filename: str):
    safe_filename = validate_media_path(category, filename)
    if uses_s3():
        return f"/api/media/{category}/{quote(safe_filename)}"
    return f"/{category}/{quote(safe_filename)}"


def local_media_path(category: str, filename: str):
    safe_filename = validate_media_path(category, filename)
    return MEDIA_DIRECTORIES[category] / safe_filename


def object_key(category: str, filename: str):
    safe_filename = validate_media_path(category, filename)
    parts = [part for part in (config.AWS_S3_PREFIX, category, safe_filename) if part]
    return "/".join(parts)


@lru_cache(maxsize=1)
def s3_client():
    kwargs = {
        "config": Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
    }
    if config.AWS_REGION:
        kwargs["region_name"] = config.AWS_REGION
    return boto3.client("s3", **kwargs)


def upload_media(local_path: Path, category: str, filename: str | None = None, content_type: str | None = None):
    local_path = Path(local_path)
    safe_filename = validate_media_path(category, filename or local_path.name)
    if not uses_s3():
        return media_url(category, safe_filename)

    resolved_content_type = content_type or mimetypes.guess_type(safe_filename)[0] or "application/octet-stream"
    s3_client().upload_file(
        str(local_path),
        config.AWS_S3_BUCKET,
        object_key(category, safe_filename),
        ExtraArgs={"ContentType": resolved_content_type},
    )
    return media_url(category, safe_filename)


def presigned_media_url(category: str, filename: str):
    if not uses_s3():
        raise RuntimeError("S3 storage is not configured")
    return s3_client().generate_presigned_url(
        "get_object",
        Params={
            "Bucket": config.AWS_S3_BUCKET,
            "Key": object_key(category, filename),
        },
        ExpiresIn=config.AWS_S3_PRESIGNED_TTL_SECONDS,
    )
