from __future__ import annotations

from datetime import datetime
from typing import Any

from src.db.mongo_client import get_games_collection
from src.models import SearchFilters
from src.services.cache import build_cache_key, get_cached_json, set_cached_json


def _valid_date(value: str | None) -> str | None:
    if not value:
        return None
    datetime.strptime(value, "%Y-%m-%d")
    return value


def build_query(filters: SearchFilters) -> dict[str, Any]:
    query: dict[str, Any] = {}

    if filters.game_name:
        query["name"] = {"$regex": filters.game_name, "$options": "i"}

    if filters.genre:
        query["genres"] = {"$elemMatch": {"$regex": filters.genre, "$options": "i"}}

    if filters.developer:
        query["developers"] = {"$elemMatch": {"$regex": filters.developer, "$options": "i"}}

    date_from = _valid_date(filters.release_date_from)
    date_to = _valid_date(filters.release_date_to)

    if date_from or date_to:
        date_filter: dict[str, Any] = {}
        if date_from:
            date_filter["$gte"] = date_from
        if date_to:
            date_filter["$lte"] = date_to
        query["release_date"] = date_filter

    return query


def search_games(filters: SearchFilters, limit: int = 20, skip: int = 0) -> list[dict[str, Any]]:
    collection = get_games_collection()
    cache_key = build_cache_key(
        "search:games",
        {
            "filters": filters.model_dump(mode="json"),
            "limit": limit,
            "skip": skip,
        },
    )

    cached_results = get_cached_json(cache_key)
    if cached_results is not None:
        return cached_results

    mongo_query = build_query(filters)

    projection = {
        "_id": 0,
        "appid": 1,
        "name": 1,
        "genres": 1,
        "developers": 1,
        "publishers": 1,
        "release_date": 1,
        "steam_url": 1,
        "short_description": 1,
        "long_description": 1,
    }

    cursor = collection.find(mongo_query, projection).skip(skip).limit(limit)
    results = list(cursor)
    set_cached_json(cache_key, results)
    return results
