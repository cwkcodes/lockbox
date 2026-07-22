# 05 — API Specification

Two surfaces over one service layer: **REST** (public, versioned, CDN-friendly, powers our own clients) and **GraphQL** (flexible reads for power users/partners). REST is primary — map data is highly cacheable and REST caches; GraphQL is a read-only companion, added Phase 2.

Base URL: `https://api.statmaps.app/v1`. OpenAPI 3.1 spec is the contract; client SDKs (`@statmaps/sdk` TS, `statmaps` Python) are generated from it.

## 1. Conventions

- JSON; errors follow RFC 9457 (`application/problem+json`).
- Cursor pagination (`?cursor=…&limit=…`, max 100).
- Immutable data responses carry `Cache-Control: public, max-age=86400, stale-while-revalidate` + strong ETags; anything keyed by `version_id` is cacheable forever.
- Standard rate-limit headers: `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset`.

## 2. Authentication

| Client | Mechanism |
|---|---|
| Web/mobile apps | Session cookie (httpOnly, SameSite=Lax) / refresh-token flow on native |
| Third-party API | `Authorization: Bearer sm_live_…` API keys (hashed at rest, scoped: `read:layers`, `read:data`, `write:usercontent`, `ai:query`) |
| Embeds | Public read endpoints, no auth; domain-locked embed tokens for Business tier |

Anonymous access is allowed on read endpoints at the lowest rate tier — exploration must work logged-out.

## 3. Rate limiting

Token bucket in Redis, per key/session/IP:

| Tier | Reads/min | AI req/day | Bulk downloads/day |
|---|---|---|---|
| Anonymous | 60 | 5 | — |
| Free account | 300 | 25 | 3 |
| Plus | 600 | 200 | 20 |
| Pro / API tier | 3,000 | 2,000 | 200 |
| Business | Custom | Custom | Custom |

Tile and values requests served from CDN don't count (they never reach the API).

## 4. REST endpoints

### Search & catalogue
```
GET  /search?q=coffee&types=layer,place,question&limit=20
     → { layers: [{layer_id, title, category, thumbnail_url, score}], places: […], suggested_question: … }
GET  /categories                        # tree
GET  /layers?category=energy&sort=popular&cursor=…
GET  /layers/{layer_id}                 # full metadata: dataset, source, licence, confidence,
                                        # time extent, default style, related layers
GET  /layers/{layer_id}/similar        # pgvector neighbours
```

### Layer data (the hot path — CDN-cached, key design in 03-architecture §5)
```
GET  /layers/{layer_id}/values?t=2019&level=country&format=json
     → { version: 1842, t: "2019", unit: "tonnes", values: {"BRA": 3009402, …}, flags: {…} }
GET  /layers/{layer_id}/values?t=2019&format=csv|geojson       # licence-gated (licences.allow_export)
GET  /layers/{layer_id}/series?region=BRA&from=1961&to=2023    # time series for one region
GET  /layers/{layer_id}/features?bbox=…&t=…&limit=…            # point/event layers (GeoJSON)
GET  /layers/{layer_id}/histogram?t=2019                       # for classification UI
GET  /tiles/{tileset}/{z}/{x}/{y}.mvt                          # dynamic tiles (Martin) — static tilesets
                                                               # are PMTiles on CDN, not API
```

### Regions & time
```
GET  /regions?kind=country&at=1975-01-01      # region list valid at a date
GET  /regions/{region_id}                     # metadata + available datasets count
GET  /regions/{region_id}/profile?t=2019      # headline stats across marquee datasets (country page)
GET  /layers/{layer_id}/timeline              # available time steps + coverage per step
```

### User content
```
POST /maps                        # body: {title, description, state}
GET  /maps/{map_id}    PATCH /maps/{map_id}    DELETE /maps/{map_id}
POST /maps/{map_id}/fork
GET  /users/{handle}/maps?visibility=public
POST /collections … (same CRUD pattern)       PUT /collections/{id}/items
PUT  /bookmarks/{layer_id}        DELETE /bookmarks/{layer_id}
```

### Sharing & export (async where slow)
```
POST /maps/{map_id}/exports       # body: {format: "png"|"pdf"|"svg", scale: 2, width: 2400}
     → 202 { export_id, status_url }          # BullMQ job → rendered via headless MapLibre
GET  /exports/{export_id}         → { status, download_url }   # signed R2 URL, 24h expiry
POST /shortlinks                  # body: {state} → { url: "https://statmaps.app/s/Ab3xK" }
GET  /embed/{map_id}              # embed bootstrap config (used by iframe/SDK)
```

### AI (spec details in 06-ai)
```
POST /ai/query        # body: {q: "solar resource high but GDP low", session_id?}
                      # → SSE stream: tool events + final {map_state, narration, citations}
POST /ai/correlate    # body: {target: "life-expectancy", scope?: {region, year}, max_results: 20}
                      # → ranked correlations (cached, see 06-ai §4)
GET  /layers/{layer_id}/summary?locale=en     # pre-generated AI summary (cheap, cached)
GET  /discover?seed=daily                     # Discover feed (curated + AI-ranked)
POST /ai/quiz         # body: {topic?, region?, difficulty} → quiz items with map states
```

### Bulk & historical
```
GET  /datasets/{dataset_id}/download?version=latest&format=csv|parquet|geoparquet
     → 302 to signed URL (licence-gated; Parquet for analysts)
GET  /datasets/{dataset_id}/versions          # version history + diff summaries
GET  /changes?since=2026-07-01                # catalogue changelog (for API consumers to sync)
```

## 5. GraphQL (Phase 2, read-only)

Endpoint: `POST /graphql`. Schema mirrors the REST resource model; exists for partners who want shaped joins in one round-trip (e.g. a country profile: region + 12 indicators + series). Guardrails: depth ≤ 8, complexity budget per request, persisted queries only for anonymous callers (blocks abuse), no mutations (user content mutations stay REST-only — smaller attack surface).

```graphql
type Query {
  layer(id: ID!): Layer
  layers(filter: LayerFilter, first: Int, after: String): LayerConnection
  region(id: ID!): Region
  search(q: String!, types: [SearchType!]): SearchResults
  correlations(target: ID!, scope: ScopeInput): [CorrelationResult!]
}
type Layer {
  id: ID!  title: String!  unit: String  geometryKind: GeometryKind!
  dataset: Dataset!        # source, licence, confidence, methodology
  values(t: String!, level: SpatialLevel): ValueMap
  series(regionId: ID!, from: Int, to: Int): [Observation!]
  timeline: Timeline!      similar(first: Int): [Layer!]
}
type Region {
  id: ID!  name(locale: String): String!  kind: RegionKind!
  indicators(layerIds: [ID!]!, t: String!): [IndicatorValue!]
}
```

## 6. Webhooks (Business/API tier)

`dataset.updated`, `dataset.published`, `layer.created` — signed (HMAC) POSTs so API consumers can sync incrementally instead of polling `/changes`.

## 7. Versioning & deprecation

URL-versioned (`/v1`). Additive changes don't bump the version. Breaking changes: new version, 12-month deprecation window, `Deprecation` + `Sunset` headers, changelog + email to affected key owners.
