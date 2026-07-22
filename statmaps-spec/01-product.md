# 01 — Product Specification

## 1. Vision

StatMaps makes learning about the world addictive. Every statistic, event, and phenomenon becomes an interactive map layer. Users search inside the app instead of the web, and the answer appears geographically — comparable, combinable, animatable through time, and explainable by AI.

### 1.1 Product pillars

1. **Instant answer** — any search returns renderable map layers in < 1 second.
2. **Composability** — any layers can be stacked, blended, compared side-by-side, and saved.
3. **Time** — a first-class timeline; history is a dimension, not a category.
4. **Discovery** — AI + Correlation Mode + Discover feed surface things you didn't know to search for.
5. **Trust** — provenance, licensing, methodology, and confidence visible on every layer.

### 1.2 Personas

| Persona | Needs | Key features |
|---|---|---|
| **Curious explorer** (consumer, 60% of traffic) | "Show me something interesting", casual browsing, sharing | Discover Mode, search, share cards, quizzes |
| **Student / teacher** | Curriculum topics, presentations, citations | Collections, lesson packs, export, source citations |
| **Journalist / content creator** | Fast, credible, embeddable visuals | Export PNG/PDF/SVG, embeds, provenance, custom styling |
| **Analyst / researcher** | Raw data, correlations, sub-national detail | Correlation Mode, bulk download, API, GeoParquet export |
| **Developer** | Programmatic access | REST/GraphQL API, tiles-as-a-service, embed SDK |

### 1.3 North-star metric

**Weekly Explored Layers per Active User** (WELAU) — number of distinct layers a user views per week. It captures the "addictive learning" loop better than session time. Supporting metrics: D7 retention, saved maps created, shares, correlation queries run.

---

## 2. Core Feature Specification

### 2.1 The Map

- **Rendering:** vector base map (MapLibre GL JS), smooth 60 fps pan/zoom from z0 (world) to z16 (city block) where data exists.
- **Projections:** Web Mercator default; equal-area (Equal Earth) toggle for world-level choropleths — Mercator visually lies about country areas and StatMaps is a statistics product, so this is not optional polish. 3D globe view (MapLibre globe projection) at low zooms is Phase 3.
- **Basemap styles:** `light`, `dark`, `terrain`, `satellite` (Phase 3), `minimal` (near-blank canvas designed for choropleths — this is the default). Theme follows system dark/light mode with manual override.
- **Labels:** localised place labels (OpenMapTiles `name:*` fields); label density adapts to active layers (fewer labels when choropleth legend is dense).

### 2.2 Search

- **One search box, three result types:** layers, places, and questions.
  - `coffee` → layer results grouped by dataset family (Production, Consumption, Imports, …).
  - `tokyo` → geocoded place result → flies to Tokyo, offers "layers with data here".
  - `what correlates with life expectancy?` → routed to AI/Correlation Mode.
- **Engine:** Typesense with typo tolerance, synonyms (`GDP` = `gross domestic product`), multilingual analyzers, and ranking by (text relevance × layer popularity × data quality score).
- **Latency budget:** ≤ 50 ms server-side, results-as-you-type after 2 characters.
- **Zero-result rescue:** if no layer matches, AI suggests nearest datasets and files a "requested dataset" signal to the data team (this becomes the ingestion backlog's demand signal).

### 2.3 Layer System (the heart of the product)

Every dataset is a **layer**. A layer has: id, title, category, unit, geometry type (choropleth / point / line / raster / flow / hex), time extent, source(s), licence, confidence score, and default style.

**User controls per layer:**

| Control | Spec |
|---|---|
| Toggle on/off | Instant; layer state is URL-encoded (see 2.8) |
| Opacity | 0–100% slider, per layer |
| Colour ramp | Curated ramps only (ColorBrewer + viridis family), sequential/diverging/qualitative auto-matched to data type; colour-blind-safe by default |
| Classification | Quantile (default), equal interval, natural breaks (Jenks), continuous; class count 3–9 |
| Year filter | Snap to available years; shows data coverage sparkline |
| Category filter | For categorical layers (e.g. power stations by fuel type) |
| Country/region filter | Isolate or exclude geographies; supports UN regions, continents, custom selections |
| Blend mode | `normal`, `multiply` (default when stacking two choropleths — makes overlaps legible) |

**Stacking rules (opinionated, enforced by UI):**
- Unlimited layers *technically*, but the UI warns beyond 2 choropleths + 3 point/line layers — beyond that the map is unreadable and we should nudge toward Compare or Correlation Mode instead.
- One raster layer at a time (bottom of stack, below choropleths).
- Legend panel auto-composes; each layer's legend is collapsible.

**Compare mode:** two synced maps, side-by-side (desktop) or swipe-divider (mobile). Both inherit the same viewport, timeline position, and filters. Any layer set on each side.

### 2.4 Time Travel

- Global **timeline scrubber** docked at the bottom, appearing whenever ≥ 1 active layer has a time dimension.
- Resolution adapts to data: yearly (most statistics), monthly/daily (weather, conflicts), or era-based (historical empires: -3000 to present with non-linear scale — one pixel-year at 1900 CE ≠ one at 3000 BCE).
- **Play** animates at user-set speed; frames are pre-fetched (next 5 time slices) so animation never stutters.
- Historical boundary layers (empires, country borders by year) come from historical basemap data (see 02-data §History) and swap the *geometry itself*, not just the values — this requires the temporal geometry model in 04-database §5.
- Multiple time-enabled layers scrub together; a layer with no data at the current time shows its nearest year with a "data from YYYY" badge (never silently shows stale data as current).

### 2.5 Layer detail panel

Tapping a layer name or a map feature opens a panel with:
- Value for the selected feature, rank among peers, sparkline over time.
- **Provenance block:** source org, licence badge, last updated, methodology summary, link to raw data, confidence score with explanation.
- AI summary (pre-generated, cached — see 06-ai §2).
- Related layers ("people who viewed this also explored…") and one-tap "Correlate this" entry into Correlation Mode.

### 2.6 Accounts, profiles, and social

- **Auth:** email magic link + OAuth (Google, Apple — Apple required for iOS). Anonymous users get full explore access; accounts unlock saving/sharing.
- **Saved maps:** a saved map = layer set + styles + viewport + timeline position + filters + optional annotation notes. Fork-able (like GitHub — "remix this map").
- **Collections:** ordered groups of saved maps with a description (e.g. "Energy transition in Europe" — 8 maps). Collections are the unit of curation and education content.
- **Bookmarks:** lightweight single-layer saves.
- **Public profiles:** `/u/{handle}` — avatar, bio, public maps and collections, follower counts. Private by default; publishing is explicit per map.
- **Moderation:** user-generated titles/descriptions pass a moderation check before public listing; report flow on all public content.

### 2.7 Sharing, export, embeds

- **Share link:** every map state is a URL (see 2.8). Share sheet generates an OG image server-side (screenshot service) so links unfurl beautifully in Slack/X/WhatsApp.
- **Export image:** PNG at 1×/2×/4×, with legend, title, attribution footer (attribution is non-removable on free tier — it's both licence compliance and marketing).
- **Export PDF:** print-quality single map or whole collection as a multi-page document.
- **Export data:** CSV/GeoJSON per layer (respecting per-layer licence terms — some sources allow viewing but restrict redistribution; the export button is licence-aware and explains why when disabled).
- **Embeds:** `<iframe>` embed with interactivity levels (static / pan-zoom / full), plus a JS SDK (`@statmaps/embed`) for developers. Embeds carry attribution and a "Made with StatMaps" badge (removable on Business tier).

### 2.8 URL state (load-bearing design decision)

Everything needed to reproduce a view lives in the URL:

```
https://statmaps.app/m?l=coffee-production@1;gdp-per-capita@0.6:multiply
   &v=12.5,48.2,4.1z&t=2019&f=region:europe&cmp=off&style=dark
```

`l` = layers with opacity/blend, `v` = viewport, `t` = time, `f` = filters. Saved maps are just persisted URL states + metadata. This gives us shareability, embeds, server-side OG rendering, and undo/redo almost for free. Long states overflow to a short-link (`/s/{id}`).

### 2.9 Platforms

| Platform | Approach |
|---|---|
| **Web (desktop + mobile)** | Next.js PWA — the canonical product |
| **PWA** | Installable, offline shell + cached basemap tiles for last-viewed regions + saved maps' data cached via Service Worker (Workbox); IndexedDB for layer data (~50 MB budget) |
| **iOS / Android** | React Native (Expo) apps sharing the TypeScript core (state, API client, styling tokens) with `maplibre-react-native` for the map. Native apps are Phase 3 — the PWA must prove retention first. Push notifications ("New dataset: Global EV sales 2025") are the main native-only value. |

**Offline spec (PWA + native):** app shell, fonts, and UI always cached; basemap tiles cached for viewed areas (LRU, 200 MB cap native / 50 MB web); saved maps marked "available offline" pre-download their layer data + tiles for the saved viewport ±1 zoom. Correlation Mode and AI features require connectivity and degrade with a clear message.

### 2.10 Accessibility & i18n

- WCAG 2.2 AA. Choropleth ramps are colour-blind safe by default; patterns/hatching available as a redundant channel.
- Full keyboard navigation of map (arrow pan, +/- zoom, feature focus ring with screen-reader value announcements).
- Every map has an auto-generated data-table view (also good for SEO).
- UI localised (i18n from day one, translations phased: EN → ES, FR, DE, PT, JA); data labels use source-provided localisation where available.

### 2.11 SEO (a growth pillar, not an afterthought)

Every layer gets a server-rendered landing page (`/layers/coffee-production`) with a static map image, data table, top-10 rankings, AI-written summary, and structured data (schema.org `Dataset`). Thousands of datasets × long-tail queries ("countries that produce the most coffee") = the primary organic acquisition channel. This is why Next.js SSR/ISR is non-negotiable in the stack.

---

## 3. UX flows (key screens)

1. **Home / Explore:** full-bleed map, search bar top-centre, Discover carousel bottom ("Tonight's fascinating maps"), category chips.
2. **Search results:** overlay panel; layer results show mini-map thumbnails (pre-rendered at ingest), one tap adds to map.
3. **Layer stack panel:** left rail (desktop) / bottom sheet (mobile); drag to reorder, controls per 2.3.
4. **Compare:** entered from layer stack ("Compare with…") or search; exits back to single map preserving left side.
5. **Correlation Mode:** entered from search (question-type queries), from a layer's "Correlate this", or from nav. Spec in 06-ai §4.
6. **Profile / Collections:** grid of map cards (pre-rendered thumbnails), follow/fork actions.

Design system: tokens shared web/native, Radix primitives + Tailwind on web; dark mode is a first-class theme (map style + UI swap together).
