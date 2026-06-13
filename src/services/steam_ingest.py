from __future__ import annotations

import random
import time
from datetime import datetime
from typing import Any

import requests

from src.config import settings
from src.db.mongo_client import get_games_collection


def _safe_release_date(raw_date: dict[str, Any] | None) -> str | None:
    if not raw_date:
        return None

    date_str = raw_date.get("date")
    if not date_str:
        return None

    formats = ["%d %b, %Y", "%b %d, %Y", "%Y-%m-%d"]
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _normalize_game(appid: int, details: dict[str, Any]) -> dict[str, Any]:
    genres = [genre.get("description") for genre in details.get("genres", []) if genre.get("description")]
    developers = details.get("developers") or []
    publishers = details.get("publishers") or []
    short_description = details.get("short_description", "")
    long_description = details.get("about_the_game") or details.get("detailed_description") or ""

    return {
        "appid": appid,
        "name": details.get("name"),
        "type": details.get("type"),
        "genres": genres,
        "developers": developers,
        "publishers": publishers,
        "release_date": _safe_release_date(details.get("release_date")),
        "steam_url": f"https://store.steampowered.com/app/{appid}",
        "short_description": short_description,
        "long_description": long_description,
        "raw": details,
    }


def _fetch_app_list() -> list[dict[str, Any]]:
    terms = list("abcdefghijklmnopqrstuvwxyz0123456789") + [
        "rpg",
        "action",
        "strategy",
        "indie",
        "sim",
        "horror",
        "racing",
        "sports",
    ]

    unique_apps: dict[int, dict[str, Any]] = {}

    for term in terms:
        params = {"term": term, "l": "english", "cc": "us"}
        response = requests.get(settings.steam_app_list_url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()

        for item in payload.get("items", []):
            if item.get("type") != "app":
                continue

            appid = item.get("id")
            name = item.get("name")
            if not appid or not name:
                continue

            unique_apps[int(appid)] = {"appid": int(appid), "name": name}

    return list(unique_apps.values())


def _fetch_app_details(appid: int) -> dict[str, Any] | None:
    params = {"appids": appid, "l": "english", "cc": "us"}
    response = requests.get(settings.steam_app_details_url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json().get(str(appid), {})

    if not data.get("success"):
        return None
    return data.get("data")


def ingest_steam_games(limit: int = 100, seed: int = 42) -> dict[str, int]:
    collection = get_games_collection()
    collection.create_index("appid", unique=True)
    collection.create_index("name")
    collection.create_index("genres")
    collection.create_index("developers")
    collection.create_index("release_date")

    apps = _fetch_app_list()
    apps = [app for app in apps if app.get("name")]

    random.Random(seed).shuffle(apps)

    inserted = 0
    skipped = 0

    for app in apps:
        if inserted >= limit:
            break

        appid = app.get("appid")
        if not appid:
            skipped += 1
            continue

        try:
            details = _fetch_app_details(appid)
        except requests.RequestException:
            skipped += 1
            continue

        if not details or details.get("type") != "game":
            skipped += 1
            continue

        normalized = _normalize_game(appid, details)
        if not normalized.get("name"):
            skipped += 1
            continue

        update_result = collection.update_one(
            {"appid": appid},
            {"$set": normalized},
            upsert=True,
        )

        if update_result.upserted_id is not None:
            inserted += 1
        elif update_result.modified_count > 0:
            inserted += 1
        else:
            skipped += 1

        # Keep requests gentle with Steam endpoints.
        time.sleep(0.08)

    return {"requested": limit, "inserted": inserted, "skipped": skipped}
