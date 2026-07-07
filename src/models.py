from typing import Any, Optional

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    game_name: Optional[str] = Field(default=None)
    genre: Optional[str] = Field(default=None)
    developer: Optional[str] = Field(default=None)
    release_date_from: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    release_date_to: Optional[str] = Field(default=None, description="YYYY-MM-DD")


class IngestResponse(BaseModel):
    requested: int
    inserted: int
    skipped: int


class CatalogMediaIngestResponse(BaseModel):
    requested_games: int
    uploaded: int
    skipped_games: int
    skipped_trailers: int


class CatalogTrailerItem(BaseModel):
    appid: int
    name: str
    movie_id: str
    bucket: str
    object_key: str
    filename: str
    content_type: Optional[str] = None
    size: int
    thumbnail_url: Optional[str] = None
    steam_url: Optional[str] = None
    created_at: Any | None = None


class CatalogTrailerListResponse(BaseModel):
    total: int
    results: list[CatalogTrailerItem]


class StorageBucketResponse(BaseModel):
    bucket: str
    created: bool


class MediaUploadResponse(BaseModel):
    bucket: str
    object_key: str
    filename: str
    content_type: Optional[str] = None
    size: int
    etag: Optional[str] = None


class SearchResponse(BaseModel):
    total: int
    results: list[dict[str, Any]]
