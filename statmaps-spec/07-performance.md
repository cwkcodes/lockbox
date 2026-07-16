# 07 — Performance & Scale

Target: millions of MAU, thousands of datasets, with realtime search/filter/overlay UX — on infrastructure a small team can run. The architecture (03) was chosen so that **scale problems are absorbed by the CDN, not the origin**; this doc sets the budgets and the mechanisms.

## 1. Performance budgets (enforced in CI via Lighthouse + custom Playwright timings)

| Metric | Budget |
|---|---|
| First map paint (cold load, 4G mid-range mobile) | < 2.5 s |
| LCP on layer landing pages (SEO pages) | < 2.0 s |
| Search results | < 150 ms end-to-end perceived (50 ms server) |
| Layer toggle → painted | < 500 ms (values fetch + feature-state paint) |
| Timeline scrub step | < 100 ms (pre-fetched values, GPU repaint) |
| Pan/zoom | 60 fps sustained; no frame > 33 ms with ≤ 5 active layers |
| JS bundle (initial, gz) | < 300 KB before map engine; MapLibre/deck.gl lazy-loaded |
| API p99 (cache miss) | < 300 ms |

## 2. Caching hierarchy (request path, top wins)

1. **Client:** Service Worker (tiles LRU, values by version — immutable), IndexedDB for offline saved maps, in-memory TanStack Query cache.
2. **CDN (Cloudflare):** PMTiles range reads, `values` JSON, layer metadata, thumbnails, SSR pages (ISR). Cache keys include `version_id` ⇒ infinite TTL, purge-on-publish (deterministic via `published_artifacts`, 04-database §8).
3. **Redis:** search results (short TTL), session, rate limits, hot API responses, live-events buffer.
4. **Postgres/ClickHouse:** cold path only.

Rule of thumb enforced in code review: **any endpoint on the map render path must be servable by CDN or Redis.** Postgres in a hot render path is a design bug.

## 3. Why the hot paths stay fast at 100× traffic

- **Tiles:** PMTiles static range-reads from R2 behind CDN — origin does ~zero work; cost and latency are CDN-shaped. Dynamic (Martin) tiles are the exception, cached at CDN with tile-key TTLs.
- **Choropleth values:** one small immutable JSON per (layer, time, level) — the whole catalogue's hot artefacts fit in CDN cache. Timeline animation prefetches ±5 steps.
- **Search:** Typesense holds the whole catalogue in RAM; scales by replicas.
- **Feature layers:** bbox-limited, zoom-gated (clustering below thresholds), paginated; deck.gl handles 100k+ points client-side, and we cap server responses with "zoom in for detail" semantics.
- **SSR pages:** ISR — rendered once per publish, then static.

## 4. Origin scaling

- API: stateless Fastify on ECS Fargate, target-tracking autoscaling on p95 latency + CPU; 2 AZ minimum.
- Postgres: primary + 1 read replica; API reads pinned to replica. Vertical headroom to r6g.4xlarge covers years; Timescale compression keeps working set in RAM.
- ClickHouse: single node → replicated pair at Phase 4; correlation scans are embarrassingly parallel.
- Workers: BullMQ consumers autoscale on queue depth; exports/AI generation are isolated pools so a burst can't starve ingest jobs.

## 5. Incremental data updates

Publish flow (02-data §4) rebuilds only artefacts whose inputs changed: a World Bank yearly refresh touches values JSONs + summaries for changed datasets, **not** boundary tiles. Content-hash comparison skips unchanged artefacts; CDN purge lists are exact, not wildcard. `/changes` + webhooks (05-api §6) let API consumers sync deltas instead of re-downloading.

## 6. Live layers (earthquakes, fires, weather)

Separate lightweight path: poller/stream consumer → `features` insert + Redis recent-buffer → clients poll `GET /layers/{id}/features?since=` every 60 s (SSE push is a Phase 4 upgrade). Live layers bypass the CDN with short TTLs (30–60 s) — acceptable because payloads are tiny.

## 7. Load & resilience testing

- Locust scenarios: browse-heavy (95% cached), search storm, correlation burst, export burst. Run against staging before each release; scale test at 10× current peak quarterly.
- Chaos basics: kill an API task, fail the Redis primary, replica-lag injection — verify graceful degradation (stale cache served, AI features degrade to cached-only per 06-ai §5).
- Synthetic monitoring: world-map load + search + layer-toggle journey from 5 geographies every minute (Grafana synthetic).
