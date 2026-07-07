from __future__ import annotations

import hashlib
import json
from typing import Any

from src.config import settings
from src.db.redis_client import get_cache_client


def build_cache_key(namespace: str, payload: dict[str, Any]) -> str:
    normalized_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(normalized_payload.encode("utf-8")).hexdigest()
    return f"{namespace}:{digest}"


def get_cached_json(cache_key: str) -> Any | None:
    try:
        cached_value = get_cache_client().get(cache_key)
    except Exception:
        return None

    if cached_value is None:
        return None

    return json.loads(cached_value)


def set_cached_json(cache_key: str, payload: Any, ttl_seconds: int | None = None) -> None:
    ttl = ttl_seconds if ttl_seconds is not None else settings.cache_ttl_seconds

    try:
        get_cache_client().setex(cache_key, ttl, json.dumps(payload, default=str))
    except Exception:
        return


def clear_cache_namespace(namespace: str) -> None:
    try:
        cache_client = get_cache_client()
        for cache_key in cache_client.scan_iter(f"{namespace}:*"):
            cache_client.delete(cache_key)
    except Exception:
        return