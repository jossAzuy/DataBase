from __future__ import annotations

from typing import Any

from src.db.mongo_client import get_database


def list_catalog_trailers(limit: int = 20, skip: int = 0) -> dict[str, Any]:
    collection = get_database()["catalog_media"]

    total = collection.count_documents({})
    cursor = (
        collection.find(
            {},
            {
                "_id": 0,
                "appid": 1,
                "name": 1,
                "movie_id": 1,
                "bucket": 1,
                "object_key": 1,
                "filename": 1,
                "content_type": 1,
                "size": 1,
                "thumbnail_url": 1,
                "steam_url": 1,
                "created_at": 1,
            },
        )
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )

    results = list(cursor)
    return {"total": total, "results": results}