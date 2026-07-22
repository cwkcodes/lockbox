# 04 — Database Design

Primary store: PostgreSQL 17 + PostGIS + TimescaleDB + pgvector. ClickHouse holds a denormalised analytics copy of observations (schema at §9). Conventions: `snake_case`, UUIDv7 PKs for user-generated content, stable text slugs for catalogue entities, `created_at/updated_at timestamptz` everywhere (omitted below for brevity).

## 1. Geography spine (regions & versioned geometry)

Everything joins here. Regions are stable *identities*; their geometries are *versioned in time* — this one design choice powers both routine boundary updates and the historical time-travel feature.

```sql
CREATE TABLE regions (
    region_id     text PRIMARY KEY,          -- 'iso:USA', 'iso:USA-CA', 'm49:150', 'hist:roman-empire'
    kind          text NOT NULL CHECK (kind IN
                    ('country','subdivision','city','un_region','continent',
                     'historical_entity','ocean','custom')),
    iso_a3        text,                      -- NULL for non-country kinds
    parent_id     text REFERENCES regions(region_id),
    name          text NOT NULL,
    names_i18n    jsonb NOT NULL DEFAULT '{}',   -- {"ja": "アメリカ合衆国", ...}
    valid_from    date,                      -- entity existence (Soviet Union: 1922-12-30..1991-12-26)
    valid_to      date,
    properties    jsonb NOT NULL DEFAULT '{}'    -- capital, wikidata QID, etc.
);

CREATE TABLE region_geometries (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    region_id     text NOT NULL REFERENCES regions(region_id),
    valid_from    date NOT NULL,             -- geometry validity window
    valid_to      date NOT NULL DEFAULT 'infinity',
    resolution    text NOT NULL CHECK (resolution IN ('10m','50m','110m')),
    geom          geometry(MultiPolygon, 4326) NOT NULL,
    geom_simplified geometry(MultiPolygon, 4326),    -- pre-simplified for low zooms
    source_id     text NOT NULL REFERENCES sources(source_id),
    disputed_variant text DEFAULT 'un',      -- 'un' | 'india' | 'china' ... (disputed borders)
    EXCLUDE USING gist (region_id WITH =, resolution WITH =, disputed_variant WITH =,
                        daterange(valid_from, valid_to) WITH &&)
);
CREATE INDEX ON region_geometries USING gist (geom);
CREATE INDEX ON region_geometries (region_id, valid_from, valid_to);
```

- Query "the world map in 1975" = `WHERE daterange(valid_from, valid_to) @> DATE '1975-06-01'`. Boundary tilesets are pre-built per era-bucket (see §8), not generated at request time.
- Cities are `regions` rows with point geometry (stored in `region_geometries` as degenerate polygons or in `properties`) sourced from GeoNames, keyed `geonames:{id}`.
- `disputed_variant` lets us serve legally-required boundary views per audience without forking datasets.

## 2. Catalogue: sources, datasets, layers

```sql
CREATE TABLE sources (
    source_id     text PRIMARY KEY,           -- 'world-bank', 'usgs'
    name          text NOT NULL,
    url           text,
    org_type      text,                       -- 'igo','government','ngo','academic','commercial','community'
    default_licence_id text REFERENCES licences(licence_id)
);

CREATE TABLE licences (
    licence_id    text PRIMARY KEY,           -- 'cc-by-4.0', 'odbl', 'cc-by-nc-4.0', 'custom:acled'
    name          text NOT NULL,
    url           text,
    -- machine-readable gates consumed by API/export/UI (02-data §3 posture):
    allow_display        boolean NOT NULL DEFAULT true,
    allow_export         boolean NOT NULL,    -- user CSV/GeoJSON download
    allow_api            boolean NOT NULL,    -- redistribution via our public API
    allow_commercial     boolean NOT NULL,
    share_alike          boolean NOT NULL DEFAULT false,
    attribution_text     text NOT NULL
);

CREATE TABLE datasets (
    dataset_id    text PRIMARY KEY,           -- 'wb-coffee-production'
    source_id     text NOT NULL REFERENCES sources(source_id),
    licence_id    text NOT NULL REFERENCES licences(licence_id),
    title         text NOT NULL,
    description   text,
    methodology   text,
    unit          text,                       -- 'tonnes', '% of GDP', 'people per km²'
    value_type    text NOT NULL CHECK (value_type IN ('numeric','categorical','boolean')),
    spatial_level text NOT NULL,              -- 'country','adm1','city','point','grid'
    temporal_resolution text,                 -- 'year','month','day','static','era'
    time_min      date, time_max date,
    update_frequency text,                    -- 'realtime','daily','monthly','quarterly','yearly','static'
    confidence    smallint CHECK (confidence BETWEEN 1 AND 5),
    coverage_pct  numeric,                    -- % of applicable regions with data (computed at ingest)
    tags          text[] NOT NULL DEFAULT '{}',
    category_id   text REFERENCES categories(category_id),
    embedding     vector(1024)                -- pgvector; semantic search + similar-layers
);
CREATE INDEX ON datasets USING gin (tags);
CREATE INDEX ON datasets USING hnsw (embedding vector_cosine_ops);

CREATE TABLE categories (
    category_id  text PRIMARY KEY,            -- 'energy', 'weird-fun'
    parent_id    text REFERENCES categories(category_id),
    name         text NOT NULL,
    sort_order   int NOT NULL DEFAULT 0
);

-- A LAYER is the user-facing renderable unit over a dataset (a dataset may
-- power several layers, e.g. power-stations → points layer + capacity choropleth).
CREATE TABLE layers (
    layer_id      text PRIMARY KEY,           -- 'coffee-production'
    dataset_id    text NOT NULL REFERENCES datasets(dataset_id),
    title         text NOT NULL,
    geometry_kind text NOT NULL CHECK (geometry_kind IN
                    ('choropleth','point','line','raster','flow','hex')),
    default_style jsonb NOT NULL,             -- ramp, classification, class count, blend
    tile_url      text,                       -- PMTiles path or Martin endpoint (NULL for choropleth = uses boundary tiles + values API)
    is_live       boolean NOT NULL DEFAULT false,
    popularity    bigint NOT NULL DEFAULT 0,  -- decayed view counter (search ranking)
    published_version_id bigint               -- FK → dataset_versions, set on publish
);
```

## 3. Observations (the statistics themselves)

TimescaleDB hypertable; the workhorse table — billions of rows at maturity.

```sql
CREATE TABLE observations (
    dataset_id    text NOT NULL,
    version_id    bigint NOT NULL,            -- immutable ingest version (§6)
    region_id     text NOT NULL,
    t             date NOT NULL,              -- observation time (year → Jan 1)
    value         double precision,           -- numeric datasets
    value_text    text,                       -- categorical datasets
    flags         smallint NOT NULL DEFAULT 0,-- bitmask: estimated, provisional, imputed, outlier
    PRIMARY KEY (dataset_id, version_id, region_id, t)
);
SELECT create_hypertable('observations', 't', chunk_time_interval => interval '10 years');
ALTER TABLE observations SET (timescaledb.compress,
    timescaledb.compress_segmentby = 'dataset_id, region_id');
```

- The hot read path (`layer values at time t`) is served from Redis/CDN-cached JSON built at publish time, **not** from this table — Postgres is the source of truth, not the hot path.
- Gridded/raster observations do NOT go here: rasters live as COGs in object storage with a `raster_assets` metadata table (dataset_id, time, COG path, band info, stats).

## 4. Point/event features (POIs, earthquakes, battles, power stations)

```sql
CREATE TABLE features (
    feature_id    uuid PRIMARY KEY DEFAULT uuidv7(),
    dataset_id    text NOT NULL REFERENCES datasets(dataset_id),
    version_id    bigint NOT NULL,
    geom          geometry(Geometry, 4326) NOT NULL,   -- point/line/polygon
    t_start       timestamptz,                -- event window (battle, eruption); NULL = timeless POI
    t_end         timestamptz,
    h3_r5         bigint,                     -- precomputed H3 index for fast aggregation
    properties    jsonb NOT NULL DEFAULT '{}'-- magnitude, fuel_type, name, wikidata QID …
);
CREATE INDEX ON features USING gist (geom);
CREATE INDEX ON features (dataset_id, t_start);
CREATE INDEX ON features (h3_r5);
```

Live events (quakes, fires) append here via the streaming path and are also pushed to a Redis-backed recent-events cache for the live layer endpoint.

## 5. Historical boundaries

No separate model needed — §1's `region_geometries.valid_from/valid_to` + `regions.valid_from/valid_to` covers it. Historical entities (empires) are `regions` rows of kind `historical_entity` with era-versioned geometries from the historical basemaps source. Statistical observations attach to historical entities exactly like countries (e.g. estimated population of the Roman Empire over time), so time-travel is uniform across the whole model.

## 6. Dataset versioning

```sql
CREATE TABLE dataset_versions (
    version_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dataset_id    text NOT NULL REFERENCES datasets(dataset_id),
    ingest_run_id text NOT NULL,              -- Dagster run
    status        text NOT NULL CHECK (status IN ('staged','published','superseded','rolled_back')),
    row_count     bigint,
    coverage_pct  numeric,
    validation_report jsonb,
    published_at  timestamptz,
    diff_summary  jsonb                       -- vs previous version: rows added/changed/removed, value drift
);
```

Publishing = flip `layers.published_version_id`, rebuild derived artefacts (values JSON, tiles if geometric, thumbnails), purge CDN. Old versions retained ≥ 2 for instant rollback and for the "dataset version history" stretch feature.

## 7. Users & user content

```sql
CREATE TABLE users (
    user_id       uuid PRIMARY KEY DEFAULT uuidv7(),
    email         citext UNIQUE NOT NULL,
    handle        citext UNIQUE,
    display_name  text,
    avatar_url    text,
    plan          text NOT NULL DEFAULT 'free' CHECK (plan IN ('free','plus','pro','edu','business')),
    is_public     boolean NOT NULL DEFAULT false
);

CREATE TABLE saved_maps (
    map_id        uuid PRIMARY KEY DEFAULT uuidv7(),
    owner_id      uuid NOT NULL REFERENCES users(user_id),
    title         text NOT NULL,
    description   text,
    state         jsonb NOT NULL,             -- canonical URL-state object (layers, styles, viewport, time, filters)
    thumbnail_url text,
    visibility    text NOT NULL DEFAULT 'private' CHECK (visibility IN ('private','unlisted','public')),
    forked_from   uuid REFERENCES saved_maps(map_id),
    stats         jsonb NOT NULL DEFAULT '{"views":0,"forks":0,"likes":0}'
);

CREATE TABLE collections (
    collection_id uuid PRIMARY KEY DEFAULT uuidv7(),
    owner_id      uuid NOT NULL REFERENCES users(user_id),
    title         text NOT NULL,
    description   text,
    visibility    text NOT NULL DEFAULT 'private'
);
CREATE TABLE collection_items (
    collection_id uuid REFERENCES collections(collection_id) ON DELETE CASCADE,
    map_id        uuid REFERENCES saved_maps(map_id) ON DELETE CASCADE,
    position      int NOT NULL,
    PRIMARY KEY (collection_id, map_id)
);

CREATE TABLE bookmarks (
    user_id   uuid REFERENCES users(user_id) ON DELETE CASCADE,
    layer_id  text REFERENCES layers(layer_id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, layer_id)
);

CREATE TABLE api_keys (
    key_id      uuid PRIMARY KEY DEFAULT uuidv7(),
    user_id     uuid NOT NULL REFERENCES users(user_id),
    key_hash    text NOT NULL,                -- store hash only
    name        text NOT NULL,
    scopes      text[] NOT NULL,
    rate_tier   text NOT NULL DEFAULT 'free',
    last_used_at timestamptz,
    revoked_at  timestamptz
);
```

## 8. AI artefacts & precomputed stats

```sql
CREATE TABLE ai_summaries (
    dataset_id   text REFERENCES datasets(dataset_id),
    kind         text NOT NULL CHECK (kind IN ('summary','fact','quiz','anomaly','story_section')),
    locale       text NOT NULL DEFAULT 'en',
    content      jsonb NOT NULL,
    model        text NOT NULL,
    input_version_id bigint NOT NULL,         -- regenerate when the dataset version changes
    reviewed     boolean NOT NULL DEFAULT false,
    PRIMARY KEY (dataset_id, kind, locale, input_version_id)
);

-- Correlation engine output cache (computed in ClickHouse, results persisted here)
CREATE TABLE correlation_results (
    id            uuid PRIMARY KEY DEFAULT uuidv7(),
    target_dataset_id text NOT NULL,
    scope         jsonb NOT NULL,             -- region filter, year, transformations
    results       jsonb NOT NULL,             -- ranked [{dataset_id, r, spearman, n, p_adj, caveats[]}]
    computed_at   timestamptz NOT NULL,
    engine_version text NOT NULL
);
```

Boundary tilesets and values artefacts are tracked in a small `published_artifacts` table (artefact kind, dataset/boundary version, R2 path, content hash) so CDN purging and rollback are deterministic.

## 9. ClickHouse (analytics copy)

```sql
CREATE TABLE obs (
    dataset_id LowCardinality(String),
    region_id  LowCardinality(String),
    iso_a3     LowCardinality(String),
    year       UInt16,
    value      Float64,
    flags      UInt8
) ENGINE = ReplacingMergeTree
ORDER BY (dataset_id, region_id, year);
```

Synced from Postgres on each dataset publish. This flat table is what the correlation engine scans (06-ai §4): pairwise stats across the full catalogue for one target complete in low seconds; the hot pairs matrix is precomputed nightly.

## 10. Sizing & scaling notes

- 3,000 country-level datasets × 250 regions × 60 years ≈ 45M rows — trivial. The growth risks are sub-national data (Eurostat NUTS-3 × monthly), point features (OSM-derived POI layers: 10⁷ rows), and raster (kept out of Postgres entirely). Timescale compression + fat chunks handle the first; `features` partitioning by dataset_id if needed for the second.
- Read scaling: hot paths never hit Postgres (CDN/Redis-first); one read replica for API queries; the primary is effectively an ingest/OLTP box. Sharding is a non-problem before tens of millions of MAU.
