# StatMaps — Phase 1 Walking Skeleton

The first slice of the real architecture from [statmaps-spec](../statmaps-spec/README.md): a PostGIS-backed catalogue with the hot-path read API. This replaces the prototype's "bake everything into one HTML file" data plane with the spec's server-side model — the catalogue can now grow to thousands of datasets without clients downloading all of them.

```
countries.geo.json ─┐
wb_*.json / owid_* ─┤  etl/load.py  ─▶  PostGIS  ─▶  api (Fastify)  ─▶ clients
usgs / wri / wikidata┘   (reuses prototype/build.py dataset definitions)
```

## Run it

```bash
# 1. Database (docker) — or point DATABASE_URL at any PostGIS 16
docker compose up -d db

# 2. Schema
psql postgres://statmaps@127.0.0.1:5544/statmaps -f db/schema.sql

# 3. Load data (same source directory the prototype build uses)
DATABASE_URL=postgres://statmaps@127.0.0.1:5544/statmaps \
  python3 etl/load.py /path/to/data_dir

# 4. API
cd api && npm install && npm run dev   # http://127.0.0.1:8787
```

## Endpoints (subset of spec 05-api)

| Endpoint | Purpose |
|---|---|
| `GET /v1/health` | liveness + dataset count |
| `GET /v1/search?q=coffee` | layer search (ILIKE-ranked; Typesense in production) |
| `GET /v1/layers?category=Energy` | catalogue browse |
| `GET /v1/layers/{id}` | metadata, source, licence gates |
| `GET /v1/layers/{id}/values?t=2023` | **hot path** — choropleth values keyed by ISO3, CDN-cacheable |
| `GET /v1/layers/{id}/series?region=BRA` | one region's time series |
| `GET /v1/layers/{id}/timeline` | available years + coverage per year |
| `GET /v1/regions/{iso}/profile?t=2023` | nearest-year values across the whole catalogue |
| `GET /v1/features/{id}?bbox=&year=` | point layers as GeoJSON (earthquakes, power plants, UNESCO) |

The `values` response shape is exactly what the prototype consumes for feature-state painting, so pointing a client at this API instead of the embedded blob is a data-source swap, not a rewrite.

## Deliberately deferred (specced, not yet wired)

TimescaleDB compression on `observations`, pgvector embeddings + semantic search, dataset versioning/publish workflow, vector tile generation (PMTiles/tippecanoe) and CDN layer, auth/rate limiting, users & saved maps. Each is specified in [statmaps-spec/04-database.md](../statmaps-spec/04-database.md) and [05-api.md](../statmaps-spec/05-api.md).
