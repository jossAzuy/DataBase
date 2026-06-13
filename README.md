# Steam Games Search with MongoDB + ChromaDB

Proyecto con Docker Compose que levanta:

- `mongodb` (MongoDB)
- `app` (API FastAPI con `pymongo` y `chromadb`)

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

## Endpoints

- `GET /health`
- `POST /ingest/steam?limit=100`
- `POST /sync/chroma`
- `POST /search`
- `GET /search/semantic?query=...&top_k=...`

## Notas

- La ingesta intenta recolectar juegos validos (`type=game`) y normaliza campos clave.
- En MongoDB se guarda el JSON completo de Steam en `raw` mas campos indexables.
- `release_date` se normaliza a `YYYY-MM-DD` cuando es posible.
