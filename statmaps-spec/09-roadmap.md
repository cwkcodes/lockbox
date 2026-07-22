# 09 — Roadmap

Team assumption at start: **6 people** — 2 full-stack (TS), 1 data engineer, 1 GIS/backend, 1 designer, 1 PM/founder. Grows to ~12 by Phase 3. Estimates are calendar time with that staffing; ranges reflect data-source surprises (the usual slippage source).

## Phase 1 — "The Atlas Works" (Months 0–4) · MVP beta

**Goal:** search → layer → beautiful map → share link. Prove the core loop retains.

| Deliverable | Notes | Effort |
|---|---|---|
| Monorepo, CI/CD, IaC, envs | Foundation week-one | 2 wk |
| Geography spine + boundary tiles (current era) | geoBoundaries + Natural Earth → PMTiles | 3 wk |
| Ingestion pipeline v1 + World Bank + OWID connectors | ~300 launch datasets, country-level | 6 wk |
| Map app: MapLibre, layer stack (toggle/opacity/ramp/classify), legend, light/dark | The core UX | 8 wk |
| Search (Typesense) + category browse | | 2 wk |
| URL state + share links + OG images | | 2 wk |
| Layer landing pages (SSR/SEO) + data tables | | 3 wk |
| Accounts, saved maps, bookmarks | better-auth | 3 wk |
| Year filter + basic timeline scrub (values swap, no historical geometry) | | 2 wk |
| Provenance panel (source/licence/confidence) | Non-negotiable for launch | 1 wk |

**Exit criteria:** 300+ layers, first-map-paint < 2.5 s, D7 retention ≥ 15% among beta invitees, 500 beta users.

## Phase 2 — "Discovery & Intelligence" (Months 4–9) · Public launch

| Deliverable | Effort |
|---|---|
| AI query → map (06-ai §3) + pre-generated summaries/facts | 6 wk |
| **Correlation Mode v1** (country-level, marquee-500 precompute, honest-stats cards) | 8 wk |
| Compare mode (side-by-side synced) | 3 wk |
| Timeline v2: animation, playback, pre-fetch | 3 wk |
| Live layers v1: earthquakes, wildfires | 3 wk |
| PNG/PDF export + embeds v1 | 4 wk |
| Public profiles, collections, fork/remix | 4 wk |
| Catalogue growth → 1,000+ layers (Eurostat, UN WPP, energy pack, Wikidata fun pack) | continuous |
| PWA offline v1, GraphQL read API, public REST API + keys (Pro tier) | 6 wk |
| Billing (Stripe): Free/Plus/Pro | 3 wk |

**Exit criteria:** public launch, 50k MAU, WELAU ≥ 8, first revenue, correlation cards cited/shared organically without embarrassing-statistics incidents.

## Phase 3 — "Depth & Platforms" (Months 9–16)

| Deliverable | Effort |
|---|---|
| Historical boundaries + era timeline (empires, borders-through-time) | 8 wk |
| Sub-national data pack (Eurostat NUTS, US states/counties) | 8 wk |
| Raster layers (population density, solar/wind resource, land cover) via COG/TiTiler | 6 wk |
| Native apps (React Native/Expo) + push notifications | 12 wk |
| 3D terrain + globe view | 3 wk |
| Discover Mode (daily feed, quizzes) | 4 wk |
| Education tier: lesson packs, classroom features | 8 wk |
| White-label embeds + Business tier; webhooks | 6 wk |
| Search v2: semantic (pgvector) blended with lexical; i18n UI (ES/FR/DE) | 5 wk |

**Exit criteria:** 500k MAU, native app store presence, first education + business contracts.

## Phase 4 — "Platform & Moat" (Months 16–24+)

- Map Stories (AI-drafted, human-edited narrative journeys) · Correlation Engine v2 (pooled panel stats, spatial regression, partial-correlation explorer) · Community datasets marketplace with validation pipeline · Multiplayer sessions (shared cursors via CRDT) · Plugin architecture (sandboxed iframe plugins with a typed postMessage API — deck.gl custom layers are explicitly *not* exposed in v1 for security) · Live layers v2 (flights, shipping, weather radar; SSE push) · AR mode exploration (spike first; ship only if the spike convinces) · Custom dashboards.

**Prioritisation rule for everything above:** WELAU and retention first, revenue features second, spectacle third.
