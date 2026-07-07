from __future__ import annotations

import mimetypes
import random
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from src.config import settings
from src.db.mongo_client import get_database
from src.db.mongo_client import get_games_collection
from src.db.rustfs_client import ensure_bucket, get_rustfs_client
from src.services.cache import clear_cache_namespace


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


def _first_trailer(details: dict[str, Any]) -> dict[str, Any] | None:
    movies = details.get("movies") or []
    if not movies:
        return None

    for movie in movies:
        if movie.get("highlight"):
            return movie

    return movies[0]


def _select_trailer_source(movie: dict[str, Any]) -> str | None:
    for field_name in ("mp4_max", "mp4", "webm", "hls_h264", "dash_h264", "dash_av1"):
        source_url = movie.get(field_name)
        if source_url:
            return source_url
    return None


def _database_catalog_candidates(limit: int) -> list[dict[str, Any]]:
    collection = get_games_collection()
    cursor = collection.find(
        {"raw.movies.0": {"$exists": True}},
        {"appid": 1, "name": 1, "raw.movies": 1},
    ).limit(limit * 20)

    return list(cursor)


def _guess_extension(url: str, content_type: str | None = None) -> str:
    parsed_path = urlparse(url).path
    suffix = Path(parsed_path).suffix.lower()
    if suffix:
        if suffix in {".m3u8", ".mpd"}:
            return ".mp4"
        return suffix

    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            return guessed

    return ".mp4"


def _download_trailer_to_tempfile(source_url: str, output_extension: str) -> tuple[Path, str, int]:
    output_file = tempfile.NamedTemporaryFile(delete=False, suffix=output_extension)
    output_path = Path(output_file.name)
    output_file.close()

    headers = (
        "Referer: https://store.steampowered.com/\r\n"
        "Origin: https://store.steampowered.com\r\n"
        "User-Agent: Mozilla/5.0\r\n"
    )

    command = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-protocol_whitelist",
        "file,http,https,tcp,tls,crypto",
        "-headers",
        headers,
        "-i",
        source_url,
        "-c",
        "copy",
        str(output_path),
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        try:
            output_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise RuntimeError(result.stderr.strip() or "ffmpeg failed to download the trailer")

    size = output_path.stat().st_size
    content_type = "video/mp4" if output_extension == ".mp4" else "video/webm"
    return output_path, content_type, size


def _build_catalog_key(appid: int, name: str, movie_id: int | str, extension: str) -> str:
    safe_name = "".join(character if character.isalnum() or character in {"-", "_"} else "-" for character in name.lower())
    safe_name = "-".join(part for part in safe_name.split("-") if part)
    if not safe_name:
        safe_name = f"app-{appid}"

    return f"catalog/{appid}/{safe_name}/{movie_id}{extension}"


def ingest_steam_catalog_trailers(limit: int = 50, seed: int = 42) -> dict[str, int]:
    catalog_collection = get_database()["catalog_media"]
    catalog_collection.create_index([("appid", 1), ("movie_id", 1)], unique=True)
    catalog_collection.create_index("appid")
    catalog_collection.create_index("name")
    ensure_bucket(settings.rustfs_catalog_bucket)

    database_candidates = _database_catalog_candidates(limit)
    random.Random(seed).shuffle(database_candidates)

    live_candidates: list[dict[str, Any]] = []
    if len(database_candidates) < limit:
        apps = _fetch_app_list()
        live_candidates = [app for app in apps if app.get("name")]
        random.Random(seed).shuffle(live_candidates)

    uploaded = 0
    skipped_games = 0
    skipped_trailers = 0

    for app in database_candidates + live_candidates:
        if uploaded >= limit:
            break

        appid = app.get("appid")
        if not appid:
            skipped_games += 1
            continue

        if app.get("raw") and app.get("raw", {}).get("movies"):
            details = app.get("raw") or {}
            trailer = _first_trailer(details)
        else:
            try:
                details = _fetch_app_details(appid)
            except requests.RequestException:
                skipped_games += 1
                continue

            if not details or details.get("type") != "game":
                skipped_games += 1
                continue

            trailer = _first_trailer(details)

        if not trailer:
            skipped_trailers += 1
            continue

        trailer_url = _select_trailer_source(trailer)
        if not trailer_url:
            skipped_trailers += 1
            continue

        movie_id = trailer.get("id") or f"movie-{appid}"
        extension = _guess_extension(trailer_url, trailer.get("thumbnail"))
        object_key = _build_catalog_key(int(appid), details.get("name") or app.get("name", "game"), movie_id, extension)

        temp_path: Path | None = None
        try:
            temp_path, content_type, size = _download_trailer_to_tempfile(trailer_url, extension)
            rustfs_client = get_rustfs_client()
            extra_args: dict[str, str] = {}
            if content_type:
                extra_args["ContentType"] = content_type

            upload_kwargs = {
                "Bucket": settings.rustfs_catalog_bucket,
                "Key": object_key,
            }
            if extra_args:
                upload_kwargs["ExtraArgs"] = extra_args

            rustfs_client.upload_file(str(temp_path), **upload_kwargs)

            catalog_collection.update_one(
                {"appid": int(appid), "movie_id": str(movie_id)},
                {
                    "$set": {
                        "appid": int(appid),
                        "name": details.get("name") or app.get("name"),
                        "movie_id": str(movie_id),
                        "bucket": settings.rustfs_catalog_bucket,
                        "object_key": object_key,
                        "filename": trailer.get("name") or f"{details.get('name') or app.get('name')} trailer",
                        "content_type": content_type,
                        "size": size,
                        "source_url": trailer_url,
                        "thumbnail_url": trailer.get("thumbnail"),
                        "steam_url": f"https://store.steampowered.com/app/{appid}",
                        "created_at": datetime.utcnow(),
                    }
                },
                upsert=True,
            )

            uploaded += 1
        except requests.RequestException:
            skipped_trailers += 1
        except Exception:
            skipped_trailers += 1
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except Exception:
                    pass

        time.sleep(0.08)

    clear_cache_namespace("search:games")
    return {
        "requested_games": limit,
        "uploaded": uploaded,
        "skipped_games": skipped_games,
        "skipped_trailers": skipped_trailers,
    }


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

    clear_cache_namespace("search:games")
    return {"requested": limit, "inserted": inserted, "skipped": skipped}
