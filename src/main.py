from fastapi import FastAPI, HTTPException, Query

from src.models import IngestResponse, SearchFilters, SearchResponse
from src.services.chroma_sync import semantic_search, sync_mongo_to_chroma
from src.services.search import search_games
from src.services.steam_ingest import ingest_steam_games


app = FastAPI(title="Steam Games Search API", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest/steam", response_model=IngestResponse)
def ingest(limit: int = Query(default=100, ge=1, le=500)) -> dict[str, int]:
    try:
        return ingest_steam_games(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc


@app.post("/sync/chroma")
def sync_chroma() -> dict[str, int]:
    try:
        return sync_mongo_to_chroma()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Sync failed: {exc}") from exc


@app.post("/search", response_model=SearchResponse)
def search(filters: SearchFilters, limit: int = Query(default=20, ge=1, le=100), skip: int = Query(default=0, ge=0)) -> dict:
    try:
        results = search_games(filters=filters, limit=limit, skip=skip)
        return {"total": len(results), "results": results}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/search/semantic")
def search_semantic(query: str, top_k: int = Query(default=5, ge=1, le=20)) -> dict:
    try:
        return semantic_search(query=query, top_k=top_k)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {exc}") from exc
