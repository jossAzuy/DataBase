from fastapi import FastAPI, File, HTTPException, Query, UploadFile

from src.db.rustfs_client import ensure_default_buckets
from src.models import CatalogMediaIngestResponse, CatalogTrailerListResponse, IngestResponse, MediaUploadResponse, SearchFilters, SearchResponse, StorageBucketResponse
from src.services.catalog_media import list_catalog_trailers
from src.services.chroma_sync import semantic_search, sync_mongo_to_chroma
from src.services.media_storage import store_media_file
from src.services.search import search_games
from src.services.steam_ingest import ingest_steam_catalog_trailers, ingest_steam_games


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


@app.post("/ingest/steam/catalog-trailers", response_model=CatalogMediaIngestResponse)
def ingest_catalog_trailers(limit: int = Query(default=50, ge=1, le=500)) -> dict[str, int]:
    try:
        return ingest_steam_catalog_trailers(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Catalog trailer ingestion failed: {exc}") from exc


@app.get("/catalog/trailers", response_model=CatalogTrailerListResponse)
def catalog_trailers(limit: int = Query(default=20, ge=1, le=100), skip: int = Query(default=0, ge=0)) -> dict:
    try:
        return list_catalog_trailers(limit=limit, skip=skip)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Catalog listing failed: {exc}") from exc


@app.post("/sync/chroma")
def sync_chroma() -> dict[str, int]:
    try:
        return sync_mongo_to_chroma()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Sync failed: {exc}") from exc


@app.post("/storage/buckets/ensure", response_model=dict[str, StorageBucketResponse])
def ensure_storage_buckets() -> dict[str, StorageBucketResponse]:
    try:
        return ensure_default_buckets()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Bucket provisioning failed: {exc}") from exc


@app.post("/media/upload/{target}", response_model=MediaUploadResponse)
async def upload_media(target: str, file: UploadFile = File(...)) -> dict:
    if target not in {"gameplay", "catalog"}:
        raise HTTPException(status_code=400, detail="target must be 'gameplay' or 'catalog'")

    try:
        return await store_media_file(target=target, file=file)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Media upload failed: {exc}") from exc


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
