# Steam Games Search with MongoDB + ChromaDB + Redis + RustFS

Proyecto con Docker Compose que levanta:

- `mongodb` (MongoDB)
- `redis` (caché para búsquedas)
- `app` (API FastAPI con `pymongo` y `chromadb`)

RustFS se usa como almacenamiento S3-compatible para dos buckets separados:

- `gameplay-videos` para videos de gameplay
- `catalog-media` para imágenes y videos del catalogo de juegos

## Requisitos

- Docker
- Docker Compose

## Levantar el proyecto

1. Construir y ejecutar:

```bash
docker compose up --build -d
```

2. Verificar estado:

```bash
docker compose ps
```

3. Probar salud:

```bash
curl http://localhost:8000/health
```

## Variables de entorno

Para que la app use Redis y RustFS, define estas variables en `.env`:

```env
REDIS_URL=redis://redis:6379/0
CACHE_TTL_SECONDS=300
RUSTFS_ENDPOINT=http://localhost:9000
RUSTFS_ACCESS_KEY=your-access-key
RUSTFS_SECRET_KEY=your-secret-key
RUSTFS_REGION=us-east-1
RUSTFS_SECURE=false
RUSTFS_GAMEPLAY_BUCKET=gameplay-videos
RUSTFS_CATALOG_BUCKET=catalog-media
```

## Flujo solicitado

1. Ingerir 100 juegos desde API de Steam hacia MongoDB:

```bash
curl -X POST "http://localhost:8000/ingest/steam?limit=100"
```

2. Sincronizar MongoDB con ChromaDB:

```bash
curl -X POST "http://localhost:8000/sync/chroma"
```

3. Buscar por filtros en MongoDB:

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "game_name": "counter",
    "genre": "Action",
    "developer": "Valve",
    "release_date_from": "2000-01-01",
    "release_date_to": "2025-12-31"
  }'
```

4. Busqueda semantica con ChromaDB:

```bash
curl "http://localhost:8000/search/semantic?query=multiplayer%20shooter&top_k=5"
```

5. Asegurar los buckets de RustFS:

```bash
curl -X POST http://localhost:8000/storage/buckets/ensure
```

## Carga de Videos

### Ingesta automatica de trailers de Steam

Si quieres poblar el bucket de catalogo con trailers directamente desde Steam:

```bash
curl -X POST "http://localhost:8000/ingest/steam/catalog-trailers?limit=50"
```

### Video de gameplay

Para subir un video de gameplay al bucket `gameplay-videos`, usa un archivo local existente en tu equipo:

```powershell
curl.exe -X POST "http://localhost:8000/media/upload/gameplay" `
  -F "file=@C:\Users\jossc\Downloads\video.mp4"
```

### Video o imagen del catalogo

Para subir un trailer, video o imagen del catalogo al bucket `catalog-media`:

```powershell
curl.exe -X POST "http://localhost:8000/media/upload/catalog" `
  -F "file=@C:\Users\jossc\Downloads\cover-image.jpg"
```

### Verificacion de trailers subidos

Si ejecutaste la ingesta automatica de trailers de Steam, puedes listar los objetos guardados con:

```bash
curl "http://localhost:8000/catalog/trailers?limit=20&skip=0"
```

Tambien puedes revisarlos directamente en la consola de RustFS:

```text
http://localhost:9001
```

Credenciales por defecto:

- usuario: `rustfsadmin`
- password: `rustfsadmin`

## Endpoints

- `GET /health`
- `POST /ingest/steam?limit=100`
- `POST /ingest/steam/catalog-trailers?limit=50`
- `POST /sync/chroma`
- `POST /storage/buckets/ensure`
- `POST /media/upload/gameplay`
- `POST /media/upload/catalog`
- `GET /catalog/trailers?limit=20&skip=0`
- `POST /search`
- `GET /search/semantic?query=...&top_k=...`

## Notas

- La ingesta intenta recolectar juegos validos (`type=game`) y normaliza campos clave.
- En MongoDB se guarda el JSON completo de Steam en `raw` mas campos indexables.
- `release_date` se normaliza a `YYYY-MM-DD` cuando es posible.
- `search` y `search/semantic` usan Redis como caché con TTL configurable.
- Los buckets de RustFS se crean bajo demanda con nombres separados por tipo de media.
