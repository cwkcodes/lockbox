# Architecture

## 1. Layers and data flow

```
 publisher ──download──▶  raw        immutable: raw.snapshot (file hash, URL, dates, licence) · raw.record · raw.reject
                           │ adapter.normalise()                       (rebuildable from raw)
                           ▼
                          norm       norm.source_record – every source mapped to ONE common shape, with per-field raw provenance
                           │ canonical.Builder.build()                 (rebuildable from norm)
                           ▼
                          atlas      canonical assets, units, organisations, planning, grid, support, provenance, QA flags
                           │ qa.run / research_queue / refresh_views
                           ▼
                  atlas.asset_flat   materialised read model ──▶ Next.js (tiles, list, stats, export, API)
 ops: source registry, ingestion runs, change log, match candidates, manual decisions, audit log, research/report queues
```

* **Raw is never changed or deleted.** A re-import of identical bytes is a no-op (`UNIQUE (source_key, resource_label, sha256)`);
  a new edition becomes a new snapshot and the previous one stays (`is_current=false`) for history/pipeline analysis.
* **Normalisation may change freely**; truncate `norm` and re-run the adapters over `raw`, or re-run only `build` over `norm`.
* **Stable identifiers.** `atlas.asset_anchor (scheme,value) → GBA-0000001` makes asset IDs survive rebuilds; manual decisions
  (`ops.manual_links`, `ops.manual_overrides`) are keyed by those anchors, not by per-snapshot row ids.

## 2. Ingestion pipeline (`ingest/atlas_ingest/pipeline.py`)

`discover → fetch (cached, robots-checked, rate-limited) → hash → parse → structural validation → normalise → store raw +
norm (bad rows to raw.reject with reason) → change detection vs previous different edition → registry status`.

* Adapters (`adapters/*.py`) only parse and normalise; they never touch the database and raise one of three honest outcomes:
  `SourceUnavailable`, `SourceRestricted`, `ManualReviewRequired`. The pipeline records the outcome and the reason; it never
  substitutes data.
* `http.py` enforces robots.txt (per host, cached), a per-host minimum request interval, retries with back-off and an
  identifying User-Agent (`ATLAS_CONTACT`); downloads are content-hashed and cached on disk, and ETag / Last-Modified are
  recorded on the snapshot (conditional requests are not yet sent, so a scheduled run re-downloads and relies on the hash to detect "unchanged"). Compliant routes for blocked sources: a manually downloaded file (`--file`, recorded as
  *MANUALLY SUPPLIED*) or an explicit, logged `ATLAS_ROBOTS_OVERRIDE=<host>`.
* Units are normalised (kW/MW/GW, kWh/MWh, m/km, m²/ha) with original value and unit retained in `fields`.
* Coordinates: WGS84 and BNG (EPSG:27700 via PROJ) are both stored; accuracy classes are `exact_published`, `site_reference`,
  `grid_1km`, `postcode_centroid`, `digitised_from_drawing`, `open_source_mapped`, `approximate`, `none`. Implausible
  coordinates are *rejected as coordinates* (point left unplaced), never repaired.

## 3. Entity resolution (`matching.py`, `canonical.py`)

REPD records seed assets (their reference is the anchor). Every other source record is scored against nearby/like-named
candidates:

| component | weight | notes |
|---|---|---|
| name | 0.25 | normalised, generic words removed; **sibling guard**: digits, number words, compass words, single letters a–d and `phase/extension/repower` must agree |
| spatial | 0.25 | tolerance by accuracy class (100 m exact … 5 km approximate); polygon containment for lease areas; offshore far distance = no evidence |
| technology | 0.10 | veto on incompatible families |
| capacity | 0.15 | |
| organisation | 0.10 | positive-only evidence (a mismatch does not penalise) |
| planning ref | 0.10 | |
| date | 0.05 | positive-only |

Scores are re-normalised over the components actually available (minimum evidence 0.40). **Auto-link needs ≥ 0.80 and hard
evidence** (spatial, polygon, planning or identifier match) and no phase conflict; 0.55–0.80 goes to `ops.match_candidates`
for review; below that, a new asset is created. Name similarity alone can never link. Phases, extensions and repowers are
separate assets joined by `atlas.asset_relationships` (`phase_of`, `extension_of`, `repowers`, `supersedes`, …).

## 4. Provenance and conflicts

Every value on a canonical asset has one or more rows in `atlas.field_provenance` (value, unit, kind
`published|calculated|derived_spatial|manual|research`, source record, raw column + raw string, publication date, retrieval
time, `is_preferred`, reason). `choose()` ranks by kind → source tier (A…E) → (for location) accuracy class → recency and
writes the explanation. Non-specific values are kept as context rather than competing: `unknown`/`cfd_awarded` become
`status_context`; a generic "offshore wind" vs floating becomes `technology_context`. A CfD-only project, with no stage stated
anywhere, is shown as *CfD awarded (development stage not stated)* rather than *Unknown*. The `atlas.field_conflicts` view lists
fields where observations disagree. "Last verified" is the latest date a *current source edition* contained the record;
the source's own "record updated" date is kept separately.

## 5. Quality assurance (`qa.py`)

Rules write to `atlas.data_quality_flags` (missing/approximate coordinates, capacity discrepancy, status conflict,
duplicate candidate, potential repower duplicate, turbine-count conflict, capacity arithmetic mismatch, coordinate not on land /
country mismatch (against ONS polygons), MW-vs-kW suspicion, identical coordinates, date order, unknown operator/owner, old
source …). `research_queue()` ranks missing high-value fields (operational wind first, then solar, BESS, hydro …) with the
sources to consult; only URLs actually consulted may be recorded as evidence. Completeness (information availability) and confidence are computed separately (`completeness.py`).

## 6. Web application (`web/`)

* **One filter implementation** (`src/lib/filters.ts`): tiles, list, statistics, facets, export, nearby and within all build
  their `WHERE` from the same URL parameters over `atlas.asset_flat`, so map, table, statistics and exports describe the same
  records (asserted by `e2e/consistency.spec.ts`). Only allow-listed columns are interpolated; values are bound parameters.
* **Vector tiles generated in PostGIS** (`/api/tiles/{z}/{x}/{y}.mvt`, `ST_AsMVT`): `clusters` (z ≤ 7), `assets`,
  `lease_areas`, `turbines` (verified positions only). No GeoJSON of the whole database is ever sent to the browser.
* **MapLibre GL 5**; symbols are canvas-drawn on demand (technology shape × status pattern, plus text/pattern so status is
  never colour-only). A self-hosted *Plain* basemap (ONS boundary tiles) works offline.
* **Pages:** `/` map · `/assets`, `/assets/{id}` · `/turbines` · `/organisations` · `/dashboard` · `/compare` · `/data` ·
  `/methodology` · `/about` · `/api-docs` · `/admin`. **API:** `/api/*` (OpenAPI at `/api/openapi.json`).
* **Exports** (CSV/XLSX/GeoJSON/GeoPackage) apply licence policy (`ops.source_registry.export_policy`), include provenance and
  attribution, and neutralise spreadsheet formula injection. **Evidence pack** (`/api/evidence-pack/{id}`) is a printable HTML record.
* **Security:** external text is rendered through React or an XSS-safe DOM builder; only http(s) URLs become links; admin
  needs `ADMIN_TOKEN` (disabled in production while unset or `change-me`, timing-safe comparison, httpOnly cookie);
  corrections need an evidence URL and are rate-limited.

## 7. What is deliberately not built / not possible from the build environment

Turbine-level table is implemented (`atlas.wind_turbines`, `/turbines`, the map layer and the asset "Units" tab) but **empty**:
no loaded source provides verified turbine coordinates. Planning-document extraction, manufacturer specification retrieval and
developer-site research are modelled (tables, queue, evidence documents with page/snippet fields) but not automated – they
need sources and access that were unavailable here. User accounts (and therefore server-side saved views) are not implemented.
