# 02 — Data: Sources, Licensing, and Ingestion

Data is the moat and the biggest ongoing cost centre. This document catalogues recommended sources per category with an honest assessment, then specifies the ingestion pipeline that turns them into layers.

**Ratings:** Quality/Ease are 1–5 (5 best). "Ease" = ease of integration (API quality, format sanity, stability).

---

## 1. Foundation layers (basemap & boundaries)

| Source | Use | Licence | Update | API | Coverage | Quality | Cost | Ease |
|---|---|---|---|---|---|---|---|---|
| **OpenStreetMap** (via **OpenMapTiles** / **Planetiler**) | Vector basemap: roads, water, buildings, labels | ODbL (share-alike on derived *databases* — see §5 licensing notes) | Continuous (we rebuild monthly) | Planet dumps + Overpass | Global | 4 | Free (compute ~$50/build) | 3 |
| **Natural Earth** | Country/state boundaries at 1:10m/50m/110m, physical features | Public domain | ~Yearly | Downloads | Global | 4 | Free | 5 |
| **geoBoundaries** | Admin 0–2 boundaries, versioned, openly licensed | CC BY 4.0 | Yearly | API + downloads | Global, ADM0–ADM2 | 4 | Free | 5 |
| **GeoNames** | Place names, populations, geocoding aid | CC BY 4.0 | Daily dumps | REST + dumps | Global, 12M+ places | 3 (noisy) | Free | 4 |
| **Overture Maps** | POIs, buildings, places (cleaner than raw OSM for POIs) | CDLA-Permissive 2.0 | Monthly | GeoParquet on S3 | Global | 4 | Free | 4 |

**Opinion:** use **geoBoundaries + Natural Earth** for statistical boundaries (not OSM) — cleaner licensing for choropleth joins, and disputed-boundary variants are explicit. Maintain our own `regions` table keyed on ISO 3166 + UN M49 with year-versioned geometries (see 04-database §5) because *country boundaries change* and every dataset joins on them.

## 2. Statistical workhorses (cover ~50% of the catalogue)

| Source | Categories | Licence | Update | API | Quality | Ease | Notes |
|---|---|---|---|---|---|---|---|
| **World Bank Open Data** | Economics, population, health, energy, environment — 16k indicators | CC BY 4.0 | Quarterly | Excellent REST API | 4 | 5 | The single highest-ROI integration. Build the pipeline against this first. |
| **Our World in Data** | Curated cross-domain (energy, health, CO₂, food…) | CC BY 4.0 (their processing); underlying sources vary | Continuous | ETL catalogue on GitHub, CSV/API | 5 | 5 | Best-documented methodology anywhere. Their `owid/etl` repo is also a reference architecture for our own pipeline. |
| **UN Data / UNSD** | Population (WPP), M49 regions, SDG indicators | CC BY 3.0 IGO (mostly) | Yearly | SDMX + CSV | 4 | 3 | SDMX is painful; wrap once, reuse everywhere (Eurostat, IMF, OECD also speak SDMX). |
| **WHO GHO** | Health: disease, vaccination, life expectancy, spending | CC BY-NC-SA 3.0 IGO ⚠️ | Yearly | OData API | 4 | 3 | **NC clause** — conflicts with commercial use. Prefer World Bank/OWID mirrors of the same indicators where licence is clean; use WHO direct only with legal review. |
| **Eurostat** | Everything, EU, often NUTS-2/3 sub-national | CC BY 4.0 | Monthly | SDMX + JSON-stat | 5 | 3 | Our best sub-national statistical source. |
| **OECD** | Economics, education, wellbeing | Mostly free re-use with attribution | Quarterly | SDMX | 4 | 3 | |
| **IMF** | Macro-economics, currency | Free with attribution (check per dataset) | Quarterly | SDMX/JSON | 4 | 3 | |
| **National stats offices** (US Census, ONS, StatCan, ABS, Destatis…) | Deep sub-national for key markets | Open (OGL, CC BY, public domain) | Varies | Varies (Census API is good) | 5 | 2 | Long tail; integrate top 10 economies in Phase 3+. |

## 3. Category-specific sources

### Geography & natural hazards
| Source | Data | Licence | Update | Quality | Ease | Notes |
|---|---|---|---|---|---|---|
| **USGS Earthquake Catalog** | Earthquakes, real-time + historical | Public domain | Real-time feed (GeoJSON) | 5 | 5 | Flagship "live layer". |
| **Smithsonian GVP** | Volcanoes + eruptions | CC BY (attribution requested) | Weekly | 5 | 4 | |
| **NASA EarthData / FIRMS** | Active fires, MODIS/VIIRS | Free, attribution | Near-real-time | 5 | 4 | Registration required. |
| **NOAA** | Weather, storms, sea temp, climate normals | Public domain | Real-time–monthly | 5 | 3 | Many sub-APIs; start with storm tracks + climate normals. |
| **Copernicus / ESA** | Land cover, sea level, climate reanalysis (ERA5) | Free with attribution | Monthly | 5 | 2 | Heavy raster; needs COG pipeline. |
| **HydroSHEDS / HydroRIVERS** | Rivers, lakes, basins | Free for all uses (v2 licence) | Static | 5 | 4 | |
| **EM-DAT** | Disaster events database | Free for non-commercial ⚠️; commercial licence available | Yearly | 4 | 3 | Budget for a commercial licence or use NOAA/USGS/ReliefWeb alternatives. |
| **GEBCO** | Bathymetry | Public domain-ish (free use) | Yearly | 5 | 3 | For ocean/terrain raster. |

### Environment & energy
| Source | Data | Licence | Update | Quality | Ease | Notes |
|---|---|---|---|---|---|---|
| **Global Solar Atlas / Global Wind Atlas** | Solar/wind resource rasters | CC BY 4.0 (World Bank–funded) | Static-ish | 5 | 3 | Key for the offshore-wind AI demo query. |
| **Global Power Plant Database (WRI)** | ~35k power stations | CC BY 4.0 | Stale (2021) ⚠️ | 3 | 5 | Supplement with OSM power infrastructure + Global Energy Monitor. |
| **Global Energy Monitor** | Coal/gas/wind/solar plant trackers | CC BY 4.0 (most trackers) | Bi-annual | 5 | 4 | Best-maintained plant-level data. |
| **Ember** | Electricity generation mix, carbon intensity | CC BY 4.0 | Monthly/yearly | 5 | 5 | Excellent clean licence; preferred over IEA. |
| **IEA** | Energy stats | ⚠️ Mostly **paid/CC BY-NC** | — | 5 | 2 | Avoid as a primary source; use Ember/OWID/Eurostat instead. |
| **Electricity Maps** | Live grid carbon intensity | Free tier non-commercial ⚠️; commercial API paid | Real-time | 5 | 4 | Great "live layer" — budget as a paid API in Phase 3. |
| **OpenAQ** | Air quality measurements | CC BY 4.0 | Real-time | 4 | 4 | Point sensors → hex-bin aggregation. |
| **Global Forest Watch / Hansen** | Deforestation, tree cover | CC BY 4.0 | Yearly | 5 | 3 | Raster tiles available directly. |
| **Protected Planet (WDPA)** | Protected areas | Free, no commercial redistribution of polygons ⚠️ | Monthly | 5 | 3 | Can *display*, cannot let users bulk-export polygons. Licence-aware export (01-product §2.7) handles this. |
| **OpenChargeMap** | EV charging stations | ODbL-ish (CC BY-SA data) | Continuous | 3 | 4 | |

### Population, politics, society
| Source | Data | Licence | Quality | Ease | Notes |
|---|---|---|---|---|---|
| **UN WPP** | Population, projections, age structure | CC BY 3.0 IGO | 5 | 4 | |
| **WorldPop / GHSL** | Gridded population density rasters | CC BY 4.0 | 5 | 3 | The beautiful "population density" raster layer. |
| **V-Dem** | Democracy indices | CC BY-SA | 5 | 4 | |
| **Freedom House** | Freedom index | Free with attribution | 4 | 4 | |
| **Transparency International** | Corruption (CPI) | CC BY-ND ⚠️ (no derivatives — display as-is) | 4 | 4 | ND is fine for choropleth display; no re-processing into composites. |
| **ACLED** | Conflict events | ⚠️ Registered access, attribution, **no redistribution**; commercial terms apply | 5 | 3 | Display-only layer; no export; budget for licence. |
| **UCDP** | Conflict data (academic) | Free with attribution | 5 | 4 | Cleaner licence than ACLED; prefer for historical conflict layers. |
| **SIPRI** | Military spending | Free for non-commercial ⚠️ | 5 | 4 | World Bank mirrors military expenditure with CC BY — use that. |
| **Wikidata** | Everything-graph: memberships (NATO/EU/BRICS), national animals, surnames, driving side, capitals… | CC0 | 3 (variable) | 3 | The engine of the "Weird & Fun" category. SPARQL at ingest, never at request time. |
| **World Happiness Report** | Happiness index | Free with attribution | 4 | 5 | |

### History
| Source | Data | Licence | Quality | Ease | Notes |
|---|---|---|---|---|---|
| **Historical Basemaps (aourednik)** | World borders ~123 snapshots, 2000 BCE–present | Open (GitHub, unrestricted use noted) | 3 (approximate, contested) | 4 | Best available open historical borders. Ship with prominent "boundaries are approximate/contested" framing. |
| **Seshat / OldWorldTrade / DARMC** | Ancient trade routes, Roman empire | Mixed academic open | 3 | 2 | Curated manually per story. |
| **Wikidata/Wikipedia** | Battles, castles, shipwrecks, events (coordinates + dates) | CC0 / CC BY-SA | 3 | 3 | Battles layer = Wikidata query `instance of: battle` with coords + dates. |
| **WHC UNESCO** | World Heritage sites | Free with attribution | 5 | 5 | |

### Entertainment & lifestyle
| Source | Data | Licence | Quality | Ease | Notes |
|---|---|---|---|---|---|
| **Jikan / AniList APIs** | Anime popularity (proxy: per-country member counts are NOT available — see note) | Free, rate-limited | 2 | 3 | ⚠️ Per-country anime stats barely exist openly. Honest option: Google Trends interest-by-region (allowed for display with attribution caveats) or survey data. Flag as low-confidence. |
| **TMDB** | Movies/TV production countries, filming locations | Free with attribution (non-commercial-ish terms; commercial API available) | 4 | 4 | |
| **Spotify Charts** | Top tracks per country | ⚠️ ToS restricts republishing | 4 | 2 | Legal review; likely partnership or drop. MusicBrainz + Last.fm as open alternatives. |
| **football-data.org / OpenFootball** | Leagues, clubs, stadiums | Free tier / open data | 3 | 4 | Stadium locations via Wikidata. |
| **Michelin / McDonald's / Starbucks locations** | POIs | ⚠️ No open feed — scraping violates ToS | — | — | Use OSM/Overture POIs (`amenity=cafe`, `brand=Starbucks` etc.) — legitimately open and surprisingly complete. |
| **Speedtest by Ookla Open Data** | Internet speed, global, quarterly tiles | CC BY-NC 4.0 ⚠️ | 5 | 5 | NC licence — needs commercial agreement, or use M-Lab (open) instead. |
| **Numbeo** | Cost of living | ⚠️ Paid/restrictive | 4 | 2 | Prefer national CPI + Eurostat price levels; Numbeo only under paid licence. |

**Summary of licensing posture:** ~70% of the target catalogue is achievable with CC0/CC BY/public-domain sources. The remaining 30% (WHO-direct, ACLED, Ookla, Spotify, IEA, Numbeo, EM-DAT) needs either (a) an open substitute — usually exists, listed above — (b) a commercial licence line-item, or (c) display-only integration with export disabled. **Every layer stores machine-readable licence terms that gate the export/API surface automatically** (04-database §7).

---

## 4. Ingestion pipeline

```
 Source APIs / dumps / rasters
        │
        ▼
 ┌─────────────────┐    ┌──────────────────┐    ┌───────────────────┐
 │ 1. EXTRACT      │ →  │ 2. TRANSFORM     │ →  │ 3. VALIDATE       │
 │ per-source      │    │ normalise to     │    │ Pandera schemas,  │
 │ connectors      │    │ canonical schema │    │ unit checks,      │
 │ (Python, Dagster│    │ (ISO codes, M49, │    │ outlier flags,    │
 │  assets)        │    │ units, years)    │    │ coverage report   │
 └─────────────────┘    └──────────────────┘    └───────────────────┘
        │ raw parquet          │ staged parquet        │
        ▼                      ▼                       ▼
   S3 (raw zone)         S3 (staging)           ┌───────────────────┐
                                                │ 4. LOAD           │
                                                │ Postgres (obs +   │
                                                │ meta), ClickHouse │
                                                │ (analytics copy), │
                                                │ Typesense (search)│
                                                └───────────────────┘
                                                        │
                                                        ▼
                                                ┌───────────────────┐
                                                │ 5. PUBLISH        │
                                                │ tile build (tippe-│
                                                │ canoe→PMTiles),   │
                                                │ COG for rasters,  │
                                                │ thumbnails, AI    │
                                                │ summaries, embed- │
                                                │ dings, stats pre- │
                                                │ compute, CDN purge│
                                                └───────────────────┘
```

**Orchestrator: Dagster** (over Airflow) — asset-based model maps 1:1 to "a dataset is an asset with freshness policies"; great local dev; built-in lineage UI doubles as our internal data catalogue.

**Key rules:**
- Connectors are declarative where possible: a YAML manifest (source URL/API, schedule, licence, transform recipe) + custom Python only when needed. Target: a new World-Bank-style indicator onboarded in < 1 hour, a novel source in < 1 week.
- Everything joins to canonical `region_id` (our versioned geography spine). A dataset that can't join cleanly fails validation loudly.
- Every ingest run is versioned (`dataset_version` in 04-database §6); layers point at an immutable version; rollback = repoint.
- Validation failures page the data team but *never* take down the previous good version.
- Update frequencies honoured per source: real-time feeds (USGS quakes) stream via a lightweight consumer into a `live_events` path bypassing the batch pipeline (07-performance §6).

**Team implication:** a standing **data engineering pod** (2 people at launch) owns connectors and the catalogue. Dataset breadth is an ongoing editorial operation, not a one-off import — this is the single most under-estimated cost in products like this (see 10-review).
