# StatMaps — Full Product & Engineering Specification

**Version:** 1.0 (Draft for implementation)
**Date:** 2026-07-16
**Status:** Ready for team review → implementation kickoff

---

## What is StatMaps?

StatMaps is an interactive world atlas for exploring, comparing, and discovering statistics, events, and phenomena through a map-first interface. A user types "coffee" and instantly sees coffee production, consumption, imports, exports, prices, and café density as toggleable, combinable map layers — with a timeline to animate through history and an AI copilot that explains, correlates, and recommends.

**Positioning:** Google Maps × Wikipedia × Our World in Data × Gapminder, with Spotify-grade UX polish and an AI-native discovery engine.

**The differentiator:** *Correlation Mode* — the ability to ask "what correlates with life expectancy?" and have the platform scan hundreds of datasets, rank statistically significant relationships (with honest correlation-vs-causation framing), and render the answer as interactive maps and scatterplots. No consumer mapping product does this well today.

---

## Document Index

| Doc | Contents |
|---|---|
| [01-product.md](./01-product.md) | Vision, personas, feature specification, layer system, timeline, UX, mobile/PWA |
| [02-data.md](./02-data.md) | Data source catalogue per category with licensing, quality, and integration assessments; ingestion pipeline design |
| [03-architecture.md](./03-architecture.md) | Full technical stack with rationale, GIS technology decisions, infrastructure, cost estimates |
| [04-database.md](./04-database.md) | Complete schema design (PostGIS + TimescaleDB), DDL, versioning, historical boundaries |
| [05-api.md](./05-api.md) | REST + GraphQL API specification, auth, rate limiting, bulk access, embeds |
| [06-ai.md](./06-ai.md) | AI feature architecture and the Correlation Engine (statistical methodology included) |
| [07-performance.md](./07-performance.md) | Performance budgets, caching strategy, CDN/edge design, scale targets |
| [08-business.md](./08-business.md) | Monetisation, pricing tiers, go-to-market segments |
| [09-roadmap.md](./09-roadmap.md) | Phased MVP roadmap with effort estimates and team plan |
| [10-review.md](./10-review.md) | Stretch goals; critical self-review — weaknesses, risks, licensing challenges, bottlenecks, and mitigations |

---

## Guiding Principles (read these first — they resolve most design arguments)

1. **The map is the interface.** Search, browse, AI — everything resolves to layers on a map. No feature ships if it pulls the user into a dashboard that could have been a map.
2. **Every layer carries its provenance.** Source, licence, update date, methodology, and a confidence score are one tap away on every layer, always. Trust is the product.
3. **Precompute aggressively, compute lazily.** Tiles, aggregations, correlation matrices, and embeddings are built at ingest time. Request time is for lookups, not computation.
4. **Country-level first, sub-national where it earns its keep.** 80% of the catalogue is country-level choropleths — cheap to store, render, and correlate. Sub-national and point data are added per-dataset where value is highest (energy infrastructure, cities, POIs, hazards).
5. **Open data, open formats.** PMTiles, GeoParquet, GeoJSON, cloud-optimised GeoTIFF. No proprietary lock-in in the data plane.
6. **Honest statistics.** Correlation Mode never says "causes". It shows effect sizes, confidence, sample sizes, and known confounders. Being the credible one is a moat.
7. **Free tier is generous; monetise depth, not access.** The Wikipedia-style breadth is the acquisition engine. Power features (export, API, unlimited saved maps, Correlation Mode depth) are the revenue engine.

---

## One-paragraph technical summary (for the impatient)

TypeScript monorepo. **Frontend:** Next.js 15 + React, MapLibre GL JS for the base map with deck.gl overlays for large point/flow/hex visualisations, Tailwind + Radix for UI, TanStack Query for data. **Backend:** Fastify (Node) API + Python (FastAPI) data/stats services, PostgreSQL 17 + PostGIS + TimescaleDB + pgvector as the primary store, ClickHouse for the correlation/analytics engine, Redis for cache/queues (BullMQ), Typesense for instant search. **Tiles:** vector tiles as PMTiles on object storage behind Cloudflare CDN, generated with tippecanoe/planetiler; Martin for dynamic tiles. **AI:** Claude API (claude-sonnet-5 for interactive, claude-haiku-4-5 for bulk generation) with tool-use over a typed layer-manipulation API. **Hosting:** AWS (or GCP) + Cloudflare, IaC in Terraform/OpenTofu, GitHub Actions CI/CD. Details and rationale in [03-architecture.md](./03-architecture.md).
