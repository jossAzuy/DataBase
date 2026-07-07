from __future__ import annotations

from typing import Any

from src.db.chroma_client import get_chroma_collection
from src.db.mongo_client import get_games_collection
from src.config import settings
from src.services.cache import build_cache_key, clear_cache_namespace, get_cached_json, set_cached_json


def _to_chroma_doc(doc: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    appid = str(doc["appid"])
    name = doc.get("name", "")
    genres = ", ".join(doc.get("genres", []))
    developers = ", ".join(doc.get("developers", []))
    release_date = doc.get("release_date") or ""
    short_description = doc.get("short_description", "")
    long_description = doc.get("long_description", "")

    text = (
        f"Name: {name}\n"
        f"Genres: {genres}\n"
        f"Developers: {developers}\n"
        f"Release Date: {release_date}\n"
        f"Short Description: {short_description}\n"
        f"Long Description: {long_description}"
    )

    metadata = {
        "appid": appid,
        "name": name,
        "release_date": release_date,
        "genre_count": len(doc.get("genres", [])),
        "developer_count": len(doc.get("developers", [])),
        "steam_url": doc.get("steam_url", ""),
    }
    return appid, text, metadata


def sync_mongo_to_chroma(batch_size: int = 100) -> dict[str, int]:
    mongo_collection = get_games_collection()
    chroma_collection = get_chroma_collection()

    cursor = mongo_collection.find({}, {"_id": 0})

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []

    synced = 0

    for doc in cursor:
        if "appid" not in doc:
            continue

        appid, text, metadata = _to_chroma_doc(doc)
        ids.append(appid)
        documents.append(text)
        metadatas.append(metadata)

        if len(ids) >= batch_size:
            chroma_collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
            synced += len(ids)
            ids, documents, metadatas = [], [], []

    if ids:
        chroma_collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        synced += len(ids)

    clear_cache_namespace("search:semantic")
    return {"synced": synced}


def semantic_search(query: str, top_k: int = 5) -> dict[str, Any]:
    chroma_collection = get_chroma_collection()
    cache_key = build_cache_key("search:semantic", {"query": query, "top_k": top_k})

    cached_results = get_cached_json(cache_key)
    if cached_results is not None:
        return cached_results

    results = chroma_collection.query(query_texts=[query], n_results=top_k)
    set_cached_json(cache_key, results, ttl_seconds=settings.cache_ttl_seconds)
    return results
