from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import UploadFile

from src.config import settings
from src.db.rustfs_client import ensure_bucket, put_object


MediaTarget = Literal["gameplay", "catalog"]


def _bucket_for_target(target: MediaTarget) -> str:
    if target == "gameplay":
        return settings.rustfs_gameplay_bucket
    return settings.rustfs_catalog_bucket


def _object_key(target: MediaTarget, filename: str | None) -> str:
    suffix = Path(filename or "media").suffix.lower()
    if suffix and len(suffix) > 16:
        suffix = suffix[:16]

    date_prefix = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    return f"{target}/{date_prefix}/{uuid4().hex}{suffix}"


async def store_media_file(target: MediaTarget, file: UploadFile) -> dict[str, Any]:
    bucket_name = _bucket_for_target(target)
    ensure_bucket(bucket_name)

    content = await file.read()
    object_key = _object_key(target, file.filename)
    upload_result = put_object(bucket_name, object_key, content, file.content_type)

    return {
        "bucket": bucket_name,
        "object_key": object_key,
        "filename": file.filename or object_key,
        "content_type": file.content_type,
        "size": len(content),
        "etag": upload_result.get("etag"),
    }