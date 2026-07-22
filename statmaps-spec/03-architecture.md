# 03 — Architecture & Technical Stack

Opinionated choices with rationale. Alternatives were considered; where the call is close, the runner-up and the tripwire for switching are noted.

## 1. System overview

```
                    ┌───────────────────────── Cloudflare ─────────────────────────┐
 Users ──────────▶  │  CDN  │ WAF │ edge cache │ image resizing │ R2 (tiles/assets) │
                    └──────┬──────────────┬───────────────┬───────────────────────┘
                           │              │               │
                    Next.js (SSR/ISR)   PMTiles         Static assets
                    Vercel or ECS       (range reads     
                           │             from R2)        
                           ▼                             
                    ┌────────────────── API tier (AWS, ECS Fargate) ──────────────┐
                    │ Fastify API (Node/TS)   FastAPI stats svc (Py)   Martin      │
                    │  - REST + GraphQL        - correlation engine    (dyn tiles) │
                    │  - auth, layers, search  - stats/aggregation                 │
                    └───────┬──────────┬───────────┬──────────┬───────────────────┘
                            │          │           │          │
                       PostgreSQL   Redis      Typesense   ClickHouse
                       17 + PostGIS (cache +   (search)    (analytics/
                       + Timescale   BullMQ)               correlation)
                       + pgvector      │
                            │          ▼
                            │      Workers (BullMQ consumers: exports, thumbnails,
                            │      AI generation, tile builds)
                            ▼
                       S3/R2 data lake (raw/staging/published GeoParquet, COG, PMTiles)
                            ▲
                       Dagster (data platform, separate deployment)
                            ▲
                       Claude API (AI features)
```

## 2. Frontend

| Choice | Why |
|---|---|
| **Next.js 15 (React, TypeScript)** | SSR/ISR is mandatory for the SEO strategy (thousands of layer landing pages, 01-product §2.11). App Router + RSC keeps the heavy map bundle client-side while metadata/data tables render on the server. Largest hiring pool. |
| **MapLibre GL JS** (base map) | See GIS decision, §5. |
| **deck.gl** (overlay analytics layers) | Interleaved with MapLibre via `@deck.gl/mapbox`; used only for the visual types MapLibre handles poorly (see §5). |
| **Zustand** (map/layer state) + **TanStack Query** (server state) | Map state is a hot, frequently-mutated local store — Redux ceremony hurts here; URL-serialisable state (01-product §2.8) is a thin layer over Zustand. |
| **Tailwind CSS + Radix UI** | Speed + accessibility primitives; tokens shared with React Native via a design-token package. |
| **Workbox** | PWA/service-worker toolkit for the offline spec. |
| **Turborepo monorepo** | `apps/web`, `apps/mobile`, `apps/api`, `packages/{ui,api-client,map-core,tokens}` — API client generated from OpenAPI so web/mobile/public SDK never drift. |

**Mobile:** React Native + Expo with `maplibre-react-native` (Phase 3). Runner-up: Flutter — rejected because we'd lose TS code sharing for state/API/URL-state logic, which is where our complexity lives.

## 3. Backend

| Choice | Why |
|---|---|
| **Fastify (Node 22, TypeScript)** for the main API | Same language as frontend (shared types, one hiring profile), excellent throughput for I/O-bound work (our API is 95% cache/DB lookups), first-class OpenAPI generation. Runner-up NestJS: rejected as ceremony without payoff at this team size. |
| **FastAPI (Python 3.12)** for the stats/data service | The correlation engine, spatial statistics, and ingestion transforms live in Python because the ecosystem (pandas/polars, scipy, statsmodels, GDAL, rasterio) is unmatched. Two services, clear boundary: Node owns users/layers/API surface; Python owns numbers. |
| **BullMQ on Redis** for queues | Exports, thumbnail rendering, AI generation, tile builds, webhooks. Redis is already in the stack; SQS is the fallback if queue volume outgrows it (tripwire: sustained >5k jobs/min). |
| **Auth: better-auth (self-hosted) + OAuth providers** | Auth is core user data; avoid per-MAU pricing of Auth0/Clerk at "millions of users" scale. Magic link + Google + Apple. Sessions as httpOnly cookies (web) / secure tokens (native). API keys separate (05-api §2). Runner-up: Clerk for speed in Phase 1 — acceptable if we accept a migration later; recommendation is to self-host from day one since auth scope is modest. |

## 4. Data stores (polyglot, each with one job)

| Store | Job | Why |
|---|---|---|
| **PostgreSQL 17 + PostGIS 3.5** | System of record: geometries, regions, datasets, users, saved maps, licences | PostGIS is the industry-standard spatial engine; nothing else is close for versioned boundary storage + spatial queries. |
| **TimescaleDB** (Postgres extension) | Observations time-series (`observations` hypertable) | Compression (10–20×) and time-bucket queries on billions of rows without leaving Postgres. Keeps the transactional join story simple. |
| **pgvector** (Postgres extension) | Dataset/layer embeddings for semantic search + "similar layers" | Small corpus (10⁴–10⁵ vectors) — a dedicated vector DB is overkill. |
| **ClickHouse** | Correlation engine + usage analytics | Correlation Mode needs "scan 3,000 indicators × 200 countries × 60 years, compute pairwise stats" interactively. Columnar scans at this shape are 50–200× faster than Postgres. Also stores product analytics events. |
| **Redis** | Cache (API responses, tiles-in-flight, sessions), BullMQ, rate-limit counters | Standard. |
| **Typesense** | Instant search | Sub-50 ms typo-tolerant search with tiny ops burden. Runner-up OpenSearch: heavier ops, worse latency at our corpus size; switch only if we need complex log-style querying. |
| **S3 / Cloudflare R2** | Data lake (GeoParquet), PMTiles, COGs, exports, thumbnails | R2 for anything CDN-served (zero egress fees — significant for tiles); S3 for the Dagster lake. |

## 5. GIS decisions (explicit answers to the options list)

| Technology | Verdict | Rationale |
|---|---|---|
| **MapLibre GL JS** | ✅ **Core renderer** | Open-source (BSD), no per-load pricing, vector-native, style-spec compatible, globe projection landed, huge community. The Mapbox-pricing risk is exactly what it removes. |
| **Mapbox GL** | ❌ | Per-load pricing is ruinous at "millions of users"; proprietary lock-in. MapLibre is the fork that exists for this reason. |
| **deck.gl** | ✅ **Overlay engine** | For 100k+ points (earthquakes, POIs), animated arcs/flows (trade, migration), H3 hex layers, and GPU-filtered time scrubbing (`DataFilterExtension` makes timeline animation free on the GPU). Interleaves with MapLibre's WebGL context. |
| **Cesium** | ❌ (revisit for AR/3D stretch) | Full 3D globe engine; heavy bundle, different mental model. MapLibre's globe view covers the "spinning globe" need. |
| **Leaflet** | ❌ | Raster-era; no vector styling, no GPU. |
| **OpenLayers** | ❌ | Capable but heavier DX; MapLibre+deck.gl covers everything we need with better performance. |
| **PostGIS** | ✅ | See §4. |
| **Vector tiles** | ✅ **Primary distribution format** | Client-side styling (instant recolour without re-fetch — critical for the layer style controls), small payloads, one tileset serves all styles. |
| **Raster tiles** | ✅ For genuinely raster data only | Solar/wind resource, population density grids, land cover — served as **Cloud-Optimised GeoTIFF → tiled via TiTiler** (or pre-tiled PNG in PMTiles for fixed styles). Never for statistical choropleths. |
| **PMTiles** | ✅ **Distribution format** | Single-file tile archives on R2, HTTP range reads via CDN — no tile server in the hot path for static tilesets. Enormous ops simplification. |
| **Martin** | ✅ For dynamic tiles | Rust tile server generating MVT from PostGIS for anything too dynamic to pre-build (user filters producing custom geometries, live event layers). |
| **3D terrain** | ✅ Phase 3 | MapLibre terrain with Terrarium/MapZen DEM tiles (public) — cheap win for the terrain basemap style. |
| **Clustering** | ✅ | supercluster (points at low zoom, e.g. castles, museums). |
| **Heatmaps** | ✅ | MapLibre heatmap layer for density (UFO sightings); deck.gl `HeatmapLayer` for large sets. |
| **Hex grids** | ✅ | **H3** is our canonical spatial aggregation index (sensor data like OpenAQ, POI density). Precomputed at resolutions 2–7 at ingest. |
| **Choropleths** | ✅ Core | Boundary tiles carry only `region_id`; statistical values arrive as JSON keyed by region and joined client-side via MapLibre `feature-state`. **This is the key rendering decision:** changing year/filter/classification re-paints without re-fetching tiles — timeline scrubbing costs one small JSON fetch per step, pre-fetched. |
| **Animated flows** | ✅ | deck.gl `ArcLayer`/`TripsLayer` for trade, migration, shipping. |

**Choropleth data-flow (normative):**
1. Client loads boundary PMTiles (geometry + `region_id`, built once per boundary-set version).
2. Client fetches `/layers/{id}/values?t=2019` → `{"USA": 314.2, "DEU": 122.9, …}` (small, CDN-cached, immutable per dataset version).
3. Values applied via `feature-state`; style expression maps value → colour ramp client-side.

## 6. AI platform

- **Claude API**: `claude-sonnet-5` for interactive chat/query-to-layers; `claude-haiku-4-5` for bulk generation (layer summaries, quiz items, facts) at ingest time.
- Tool-use pattern: the model gets typed tools (`search_layers`, `set_layers`, `run_correlation`, `filter_regions`) — the model manipulates the map through the same API the UI uses; it never fabricates data values. Full spec in 06-ai.
- Embeddings for semantic layer search: computed at ingest, stored in pgvector.

## 7. Hosting, delivery, observability

| Concern | Choice | Why |
|---|---|---|
| Cloud | **AWS** (ECS Fargate, RDS, ElastiCache, S3) | Managed Postgres/Redis, boring and hireable. GCP equivalent acceptable; pick one, don't abstract. |
| Edge/CDN | **Cloudflare** (CDN, R2, WAF, Workers for OG-image + short-link redirects) | R2 zero-egress is decisive for tile serving economics. |
| Frontend hosting | **Vercel** (Phase 1–2) → ECS if costs bite | ISR/preview DX now; portability later since it's just Next.js. |
| IaC | **OpenTofu (Terraform) + Terragrunt** | Standard; state in S3. Env parity dev/staging/prod. |
| CI/CD | **GitHub Actions** | Monorepo-aware pipelines (Turborepo remote cache): lint → typecheck → unit → integration (Testcontainers Postgres/Redis) → Playwright E2E → deploy. Trunk-based, preview deploys per PR. |
| Monitoring | **Grafana Cloud stack** (Prometheus metrics, Loki logs, Tempo traces via OpenTelemetry) + **Sentry** (FE+BE errors) | OTel from day one; one trace ID from browser → API → Python svc → DB. |
| Product analytics | **PostHog** (self-hosted on ClickHouse we already run) | Funnels/retention for WELAU metric without shipping user data to third parties. |
| Testing | Vitest (unit), Testcontainers (integration), Playwright (E2E + visual regression on map screenshots), pgTAP (DB), Locust (load), Great Expectations/Pandera (data quality) | Map visual-regression testing matters: style changes break maps silently. |

## 8. Cost estimates (monthly, rough)

| Stage | Assumptions | Infra | Notable lines |
|---|---|---|---|
| **Phase 1 (beta)** ~5k MAU | 1× API task, db.r6g.large RDS, small CH, Vercel Pro | **$1.2k–2k** | RDS $350, ClickHouse Cloud dev $200, Vercel $150, Cloudflare $50, Dagster/worker EC2 $200, AI $100–300 |
| **Phase 2–3** ~200k MAU | 3–6 API tasks, db.r6g.2xlarge + replica, CH prod | **$6k–12k** | RDS $1.5k, CH $1k, compute $1.5k, AI $1–3k (caching-dependent), Vercel $500 |
| **Scale** ~2M MAU | Autoscaled API, Aurora or sharded PG, CH cluster | **$30k–60k** | Tiles stay cheap (R2+CDN ≈ $500 — this is the PMTiles payoff); AI is the swing line ($5–15k, controlled by pre-generation + caching); people cost >> infra cost throughout |

Biggest cost risks: AI inference (mitigate: pre-generate + cache summaries, prompt caching, haiku-class models for bulk) and managed-DB growth (mitigate: Timescale compression, ClickHouse offload). Tile serving — usually the scary line in map products — is structurally cheap here by design.
