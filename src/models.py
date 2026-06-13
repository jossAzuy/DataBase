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


class SearchResponse(BaseModel):
    total: int
    results: list[dict[str, Any]]
