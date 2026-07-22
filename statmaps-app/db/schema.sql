-- StatMaps Phase 1 schema — walking-skeleton subset of statmaps-spec/04-database.md.
-- Omitted here (documented in the spec, added when their engines are provisioned):
-- TimescaleDB hypertable/compression on observations, pgvector embeddings,
-- dataset_versions workflow, users/saved_maps, disputed boundary variants.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE licences (
    licence_id       text PRIMARY KEY,
    name             text NOT NULL,
    url              text,
    allow_display    boolean NOT NULL DEFAULT true,
    allow_export     boolean NOT NULL DEFAULT true,
    allow_api        boolean NOT NULL DEFAULT true,
    allow_commercial boolean NOT NULL DEFAULT true,
    share_alike      boolean NOT NULL DEFAULT false,
    attribution_text text NOT NULL DEFAULT ''
);

CREATE TABLE sources (
    source_id  text PRIMARY KEY,
    name       text NOT NULL,
    url        text,
    licence_id text NOT NULL REFERENCES licences(licence_id)
);

-- Geography spine (spec §1). valid_from/valid_to carry temporal versioning even
-- though Phase 1 loads only the current era.
CREATE TABLE regions (
    region_id  text PRIMARY KEY,           -- 'iso:USA'
    kind       text NOT NULL CHECK (kind IN ('country','subdivision','city','un_region','continent','historical_entity','custom')),
    iso_a3     text,
    name       text NOT NULL,
    names_i18n jsonb NOT NULL DEFAULT '{}',
    valid_from date,
    valid_to   date
);

CREATE TABLE region_geometries (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    region_id  text NOT NULL REFERENCES regions(region_id),
    valid_from date NOT NULL DEFAULT '1900-01-01',
    valid_to   date NOT NULL DEFAULT 'infinity',
    resolution text NOT NULL DEFAULT '110m',
    geom       geometry(MultiPolygon, 4326) NOT NULL,
    source_id  text NOT NULL REFERENCES sources(source_id)
);
CREATE INDEX ON region_geometries USING gist (geom);
CREATE INDEX ON region_geometries (region_id, valid_from, valid_to);

CREATE TABLE datasets (
    dataset_id          text PRIMARY KEY,
    source_id           text NOT NULL REFERENCES sources(source_id),
    licence_id          text NOT NULL REFERENCES licences(licence_id),
    title               text NOT NULL,
    description         text,
    unit                text,
    value_type          text NOT NULL DEFAULT 'numeric',
    spatial_level       text NOT NULL DEFAULT 'country',
    temporal_resolution text DEFAULT 'year',
    time_min            smallint,
    time_max            smallint,
    coverage_pct        numeric,
    category            text NOT NULL,
    tags                text[] NOT NULL DEFAULT '{}'
);

-- User-facing renderable unit over a dataset (spec §2).
CREATE TABLE layers (
    layer_id      text PRIMARY KEY,
    dataset_id    text NOT NULL REFERENCES datasets(dataset_id),
    title         text NOT NULL,
    geometry_kind text NOT NULL CHECK (geometry_kind IN ('choropleth','point','line','raster','flow','hex')),
    default_style jsonb NOT NULL DEFAULT '{}',
    popularity    bigint NOT NULL DEFAULT 0
);

-- Statistical observations (spec §3). Becomes a TimescaleDB hypertable in
-- production; year is a smallint here because Phase 1 data is annual.
CREATE TABLE observations (
    dataset_id text NOT NULL REFERENCES datasets(dataset_id),
    region_id  text NOT NULL REFERENCES regions(region_id),
    year       smallint NOT NULL,
    value      double precision NOT NULL,
    PRIMARY KEY (dataset_id, region_id, year)
);
CREATE INDEX ON observations (dataset_id, year);

-- Point/event features (spec §4).
CREATE TABLE features (
    feature_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dataset_id text NOT NULL REFERENCES datasets(dataset_id),
    geom       geometry(Point, 4326) NOT NULL,
    year       smallint,                -- event/inscription year, NULL = timeless
    properties jsonb NOT NULL DEFAULT '{}'
);
CREATE INDEX ON features USING gist (geom);
CREATE INDEX ON features (dataset_id, year);
