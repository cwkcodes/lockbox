-- 002: source registry + raw layer + normalised source layer
-- Principle: raw is immutable, norm is rebuildable from raw, canonical is rebuildable from norm.

CREATE TABLE ops.source_registry (
  source_key           text PRIMARY KEY,
  organisation         text NOT NULL,
  dataset              text NOT NULL,
  landing_url          text,
  endpoint_url         text,
  format               text,
  tier                 char(1) NOT NULL CHECK (tier IN ('A','B','C','D','E')),
  source_type          text NOT NULL,
  update_frequency     text,
  adapter              text,
  licence_name         text,
  licence_url          text,
  attribution          text,
  redistribution       text NOT NULL DEFAULT 'unknown' CHECK (redistribution IN ('permitted','conditional','prohibited','unknown')),
  commercial_use_notes text,
  export_policy        text NOT NULL DEFAULT 'include' CHECK (export_policy IN ('include','exclude','conditional')),
  export_policy_reason text,
  access_status        text NOT NULL DEFAULT 'never_run'
                       CHECK (access_status IN ('current','update_available','source_unavailable','restricted','manual_review_required','never_run')),
  access_notes         text,
  known_limitations    text,
  last_checked_at      timestamptz,
  latest_publication_date date,
  records_imported     int,
  records_rejected     int,
  active               boolean NOT NULL DEFAULT true
);

CREATE TABLE raw.snapshot (
  snapshot_id       bigserial PRIMARY KEY,
  source_key        text NOT NULL REFERENCES ops.source_registry,
  resource_label    text NOT NULL DEFAULT '',   -- distinguishes several files published under one source (e.g. CfD rounds)
  retrieved_at      timestamptz NOT NULL DEFAULT now(),
  publication_date  date,
  source_url        text NOT NULL,
  http_status       int,
  content_type      text,
  etag              text,
  sha256            text NOT NULL,
  byte_size         bigint,
  local_path        text,                 -- cached copy on disk (data/raw/...)
  row_count         int,
  rejected_count    int NOT NULL DEFAULT 0,
  licence_snapshot  text,                 -- licence text/URL as seen at retrieval
  parser_version    text,
  encoding          text,
  is_current        boolean NOT NULL DEFAULT true,
  notes             text,
  UNIQUE (source_key, resource_label, sha256)
);
CREATE INDEX ON raw.snapshot (source_key, retrieved_at DESC);

CREATE TABLE raw.record (
  snapshot_id  bigint NOT NULL REFERENCES raw.snapshot ON DELETE CASCADE,
  row_number   int    NOT NULL,
  record_key   text,
  payload      jsonb  NOT NULL,         -- original column -> original string, untouched
  PRIMARY KEY (snapshot_id, row_number)
);
CREATE INDEX ON raw.record (snapshot_id, record_key);

CREATE TABLE raw.reject (
  snapshot_id  bigint NOT NULL REFERENCES raw.snapshot ON DELETE CASCADE,
  row_number   int    NOT NULL,
  reason       text   NOT NULL,
  payload      jsonb  NOT NULL,
  PRIMARY KEY (snapshot_id, row_number)
);

CREATE TABLE norm.source_record (
  source_record_id  bigserial PRIMARY KEY,
  snapshot_id       bigint NOT NULL REFERENCES raw.snapshot ON DELETE CASCADE,
  source_key        text   NOT NULL REFERENCES ops.source_registry,
  record_key        text   NOT NULL,
  row_number        int    NOT NULL,
  record_url        text,
  name              text,
  name_norm         text,
  alt_names         text[] NOT NULL DEFAULT '{}',
  entity_kind       text   NOT NULL DEFAULT 'project',
  technology_code   text REFERENCES atlas.technology,
  technology_raw    text,
  technologies_raw  text[] NOT NULL DEFAULT '{}',
  status_code       text REFERENCES atlas.status,
  status_raw        text,
  capacity_mw       numeric,
  capacity_basis    text,
  export_capacity_mw numeric,
  import_capacity_mw numeric,
  storage_mwh       numeric,
  storage_duration_h numeric,
  turbine_count     int,
  turbine_rated_mw  numeric,
  turbine_height_m  numeric,
  site_area_ha      numeric,
  bng_e             numeric,
  bng_n             numeric,
  lat               double precision,
  lon               double precision,
  geom              geometry(Geometry,4326),
  geom_kind         text,                -- point | lease_area | planning_boundary ...
  coord_accuracy    text NOT NULL DEFAULT 'none'
                    CHECK (coord_accuracy IN ('exact_published','site_reference','grid_1km','postcode_centroid','digitised_from_drawing','open_source_mapped','approximate','none')),
  coord_note        text,
  country           text,
  region            text,
  county            text,
  local_authority   text,
  planning_authority text,
  postcode_public   text,                -- only for non-sensitive records
  operator_raw      text,
  developer_raw     text,
  owner_raw         text,
  planning_ref      text,
  appeal_ref        text,
  sos_ref           text,
  dno               text,
  host_to           text,
  connection_site   text,
  connection_voltage_kv numeric,
  connection_status text,
  connection_date   date,
  gate              text,
  cfd_round         text,
  cfd_capacity_mw   numeric,
  strike_price      numeric,
  ro_banding        numeric,
  fit_tariff        numeric,
  chp_enabled       boolean,
  mounting_type     text,
  storage_type      text,
  record_updated    date,
  application_date  date,
  consent_date      date,
  construction_date date,
  operational_date  date,
  expected_operational_date date,
  decommissioned_date date,
  in_scope_gb       boolean NOT NULL DEFAULT true,
  scope_note        text,
  privacy_class     text NOT NULL DEFAULT 'public' CHECK (privacy_class IN ('public','sub_1mw_masked')),
  ids               jsonb NOT NULL DEFAULT '{}',   -- external identifiers: {"repd":"..","tec":".."}
  attrs             jsonb NOT NULL DEFAULT '{}',   -- source-specific extras
  fields            jsonb NOT NULL DEFAULT '{}',   -- per-field raw provenance {"capacity_mw":{"col":..,"raw":..,"unit":..}}
  qa_notes          text[] NOT NULL DEFAULT '{}',
  excluded_reason   text,                 -- non-NULL: retained here but not promoted to the canonical layer
  UNIQUE (snapshot_id, record_key, row_number)
);
CREATE INDEX ON norm.source_record (source_key, snapshot_id);
CREATE INDEX ON norm.source_record (technology_code);
CREATE INDEX ON norm.source_record USING gist (geom);
CREATE INDEX ON norm.source_record USING gin (name_norm gin_trgm_ops);
CREATE INDEX ON norm.source_record ((ids->>'repd'));
