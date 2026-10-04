-- 003: canonical asset model (rebuildable from the norm layer + manual/research evidence)

CREATE SEQUENCE atlas.asset_seq START 1;

-- ---------------------------------------------------------------------------
-- Organisations (one record per legal/trading entity; spelling variants as aliases)
-- ---------------------------------------------------------------------------
CREATE TABLE atlas.organisations (
  org_id        bigserial PRIMARY KEY,
  canonical_name text NOT NULL,
  name_norm     text NOT NULL UNIQUE,
  aliases       text[] NOT NULL DEFAULT '{}',
  org_type      text,                      -- developer | owner | operator | dno | tso | epc | om | planning_authority | other
  parent_org_id bigint REFERENCES atlas.organisations,
  notes         text,
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON atlas.organisations USING gin (name_norm gin_trgm_ops);

-- ---------------------------------------------------------------------------
-- Evidence documents (planning documents, developer pages, manufacturer sheets ...)
-- ---------------------------------------------------------------------------
CREATE TABLE atlas.evidence_documents (
  evidence_id   bigserial PRIMARY KEY,
  organisation  text NOT NULL,
  title         text NOT NULL,
  url           text,
  doc_type      text,                      -- planning_application | decision_notice | developer_page | manufacturer_spec | press | ...
  tier          char(1) NOT NULL CHECK (tier IN ('A','B','C','D','E')),
  doc_date      date,
  retrieved_at  timestamptz NOT NULL DEFAULT now(),
  licence       text,
  archived_url  text,
  link_status   text NOT NULL DEFAULT 'unchecked' CHECK (link_status IN ('unchecked','ok','unavailable')),
  previous_url  text,
  notes         text
);

-- ---------------------------------------------------------------------------
-- Canonical assets
-- ---------------------------------------------------------------------------
CREATE TABLE atlas.assets (
  asset_id         text PRIMARY KEY DEFAULT ('GBA-' || lpad(nextval('atlas.asset_seq')::text, 7, '0')),
  canonical_name   text NOT NULL,
  name_norm        text NOT NULL,
  aliases          text[] NOT NULL DEFAULT '{}',
  technology_code  text NOT NULL REFERENCES atlas.technology,
  subtechnology    text,
  status_code      text NOT NULL REFERENCES atlas.status,
  status_original  text,
  status_source_key text,
  country          text,
  region           text,
  local_authority  text,
  local_authority_basis text,              -- e.g. 'derived: ONS LAD Dec 2025 point-in-polygon'
  location_description text,
  postcode         text,                   -- only where public and privacy policy allows
  lat              double precision,
  lon              double precision,
  bng_e            numeric,
  bng_n            numeric,
  geom             geometry(Point,4326),
  coordinate_accuracy text NOT NULL DEFAULT 'none',
  coordinate_source_key text,
  is_offshore      boolean NOT NULL DEFAULT false,
  installed_capacity_mw numeric,
  capacity_basis   text,
  export_capacity_mw numeric,
  storage_capacity_mwh numeric,
  storage_duration_h numeric,
  storage_duration_basis text CHECK (storage_duration_basis IN ('published','calculated')),
  commissioning_date date,
  expected_commissioning_date date,
  decommissioning_date date,
  planning_authority text,
  planning_reference text,
  grid_operator    text,
  connection_type  text CHECK (connection_type IN ('transmission','distribution','unknown')),
  connection_voltage_kv numeric,
  connection_status text,
  repd_ref         text,
  tec_ref          text,
  ecr_ref          text,
  ofgem_ref        text,
  cfd_ref          text,
  parent_asset_id  text REFERENCES atlas.assets,
  phase_label      text,
  repowers_asset_id text REFERENCES atlas.assets,
  asset_kind       text NOT NULL DEFAULT 'project' CHECK (asset_kind IN ('project','lease_area')),
  scale_class      text NOT NULL DEFAULT 'utility' CHECK (scale_class IN ('utility','small')),
  privacy_class    text NOT NULL DEFAULT 'public' CHECK (privacy_class IN ('public','sub_1mw_masked')),
  in_scope_gb      boolean NOT NULL DEFAULT true,
  scope_note       text,
  last_verified    date,                  -- most recent date a CURRENT source edition confirmed this record
  source_updated   date,                  -- the source's own 'record last updated' date (can be years old)
  confidence       text NOT NULL DEFAULT 'low' CHECK (confidence IN ('verified','high','medium','low')),
  completeness_pct numeric,
  is_published     boolean NOT NULL DEFAULT true,
  notes            text,
  search_doc       text,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON atlas.assets USING gist (geom);
CREATE INDEX ON atlas.assets (technology_code, status_code);
CREATE INDEX ON atlas.assets (country);
CREATE INDEX ON atlas.assets (repd_ref);
CREATE INDEX ON atlas.assets USING gin (name_norm gin_trgm_ops);
CREATE INDEX ON atlas.assets USING gin (to_tsvector('simple', coalesce(search_doc,'')));
CREATE INDEX ON atlas.assets (parent_asset_id);
CREATE INDEX ON atlas.assets (repowers_asset_id);

-- Stable canonical IDs: an asset is anchored to the first identifier that created it, so a rebuild
-- from the norm layer re-uses the same asset_id (URLs, evidence links and audit history stay valid).
CREATE TABLE atlas.asset_anchor (
  anchor_scheme text NOT NULL,
  anchor_value  text NOT NULL,
  asset_id      text NOT NULL REFERENCES atlas.assets ON DELETE CASCADE,
  PRIMARY KEY (anchor_scheme, anchor_value)
);

CREATE TABLE atlas.asset_identifiers (
  asset_id   text NOT NULL REFERENCES atlas.assets ON DELETE CASCADE,
  scheme     text NOT NULL,     -- repd | tec | neso_project | ecr | ofgem | rego | ro | fit | cfd | ecu | dns | sip | dco | lpa | marine_licence | ...
  identifier text NOT NULL,
  source_record_id bigint REFERENCES norm.source_record,
  PRIMARY KEY (asset_id, scheme, identifier)
);
CREATE INDEX ON atlas.asset_identifiers (scheme, identifier);

-- which normalised source rows contribute to which canonical asset (rebuildable)
CREATE TABLE atlas.asset_source_links (
  asset_id   text   NOT NULL REFERENCES atlas.assets ON DELETE CASCADE,
  source_record_id bigint NOT NULL REFERENCES norm.source_record ON DELETE CASCADE,
  link_type  text   NOT NULL CHECK (link_type IN ('primary','matched','manual')),
  match_score numeric,
  match_components jsonb,
  linked_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (asset_id, source_record_id)
);
CREATE INDEX ON atlas.asset_source_links (source_record_id);

-- ---------------------------------------------------------------------------
-- Hierarchy / relationships / phases
-- ---------------------------------------------------------------------------
CREATE TABLE atlas.asset_relationships (
  from_asset_id text NOT NULL REFERENCES atlas.assets ON DELETE CASCADE,
  to_asset_id   text NOT NULL REFERENCES atlas.assets ON DELETE CASCADE,
  relation      text NOT NULL CHECK (relation IN ('phase_of','extension_of','repowers','supersedes','co_located_with','possible_duplicate_of','same_site_as')),
  basis         text,
  source_record_id bigint REFERENCES norm.source_record,
  created_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (from_asset_id, to_asset_id, relation)
);

CREATE TABLE atlas.asset_phases (
  phase_id   bigserial PRIMARY KEY,
  asset_id   text NOT NULL REFERENCES atlas.assets ON DELETE CASCADE,
  phase_name text NOT NULL,
  capacity_mw numeric,
  status_code text REFERENCES atlas.status,
  expected_date date,
  commissioning_date date,
  notes      text,
  source_record_id bigint REFERENCES norm.source_record
);

-- ---------------------------------------------------------------------------
-- Technology specific detail
-- ---------------------------------------------------------------------------
CREATE TABLE atlas.wind_details (
  asset_id text PRIMARY KEY REFERENCES atlas.assets ON DELETE CASCADE,
  offshore boolean NOT NULL DEFAULT false,
  foundation_type text,                    -- fixed | floating | NULL = not stated
  offshore_round text,
  turbine_count_reported int,              -- as reported by a register (not verified as built)
  consented_max_turbines int,
  installed_turbines int,                  -- only where as-built evidence exists
  consented_tip_height_m numeric,
  installed_tip_height_m numeric,
  consented_capacity_mw numeric,
  installed_capacity_mw numeric,
  turbine_rated_mw_reported numeric,       -- as reported (REPD 'Turbine Capacity (MW)')
  turbine_height_reported_m numeric,       -- as reported (REPD 'Height of Turbines (m)'; semantics not stated)
  turbine_manufacturer text,
  turbine_model text,
  model_status text NOT NULL DEFAULT 'unknown'
       CHECK (model_status IN ('installed','planning_candidate','consented_envelope','suspected','unknown')),
  hub_height_m numeric,
  rotor_diameter_m numeric,
  individual_turbines_known boolean NOT NULL DEFAULT false,
  lease_area_km2 numeric
);

CREATE TABLE atlas.solar_details (
  asset_id text PRIMARY KEY REFERENCES atlas.assets ON DELETE CASCADE,
  mwp_dc numeric,
  mw_ac numeric,
  export_mw numeric,
  site_area_ha numeric,
  mounting_type text,
  tracking text,
  tilt_deg numeric,
  orientation text,
  module_manufacturer text,
  module_model text,
  module_wp numeric,
  module_count_published bigint,
  inverter_manufacturer text,
  inverter_model text,
  epc_contractor text,
  co_located_storage boolean
);

CREATE TABLE atlas.storage_systems (
  asset_id text PRIMARY KEY REFERENCES atlas.assets ON DELETE CASCADE,
  power_mw numeric,
  energy_mwh numeric,
  duration_h_published numeric,
  duration_h_calculated numeric,
  import_mw numeric,
  export_mw numeric,
  chemistry text,
  cell_manufacturer text,
  system_manufacturer text,
  pcs_manufacturer text,
  integrator text,
  container_count int,
  optimiser text,
  storage_type text,                       -- stand_alone | co_located_re | co_located_fossil | NULL
  co_located_asset_id text REFERENCES atlas.assets,
  fire_safety_doc_url text
);

CREATE TABLE atlas.hydro_details (
  asset_id text PRIMARY KEY REFERENCES atlas.assets ON DELETE CASCADE,
  classification text,                     -- run_of_river | storage | pumped_storage
  watercourse text, catchment text, unit_count int, turbine_type text, turbine_manufacturer text,
  head_m numeric, design_flow_m3s numeric, annual_generation_mwh numeric, reservoir text
);

CREATE TABLE atlas.bioenergy_details (
  asset_id text PRIMARY KEY REFERENCES atlas.assets ON DELETE CASCADE,
  electrical_mw numeric, thermal_mw numeric, chp boolean, feedstock text, digester_technology text,
  engine_count int, engine_manufacturer text, engine_model text, biogas_upgrading boolean, biomethane_injection boolean
);

-- ---------------------------------------------------------------------------
-- Generating units / individual turbines (never synthesised)
-- ---------------------------------------------------------------------------
CREATE TABLE atlas.turbine_models (
  model_id bigserial PRIMARY KEY,
  manufacturer text NOT NULL,
  model text NOT NULL,
  rated_power_mw numeric,
  rotor_diameter_m numeric,
  hub_heights_m numeric[],
  iec_class text,
  evidence_id bigint REFERENCES atlas.evidence_documents,
  notes text,
  UNIQUE (manufacturer, model)
);

CREATE TABLE atlas.generating_units (
  unit_id    bigserial PRIMARY KEY,
  asset_id   text NOT NULL REFERENCES atlas.assets ON DELETE CASCADE,
  unit_code  text NOT NULL,                -- e.g. ACH-T01
  unit_type  text NOT NULL CHECK (unit_type IN ('wind_turbine','solar_array','battery_block','hydro_unit','engine','other')),
  rated_mw   numeric,
  status_code text REFERENCES atlas.status,
  commissioning_year int,
  lat        double precision,
  lon        double precision,
  bng_e      numeric,
  bng_n      numeric,
  geom       geometry(Point,4326),
  coordinate_class text CHECK (coordinate_class IN ('exact_published','digitised_from_drawing','open_source_mapped','approximate')),
  coordinate_accuracy_m numeric,
  original_crs text,
  source_record_id bigint REFERENCES norm.source_record,
  evidence_id bigint REFERENCES atlas.evidence_documents,
  notes      text,
  UNIQUE (asset_id, unit_code)
);
CREATE INDEX ON atlas.generating_units USING gist (geom);

CREATE TABLE atlas.wind_turbines (
  unit_id bigint PRIMARY KEY REFERENCES atlas.generating_units ON DELETE CASCADE,
  manufacturer text,
  model text,
  rated_mw numeric,
  hub_height_m numeric,
  rotor_diameter_m numeric,
  tip_height_m numeric,
  model_status text NOT NULL DEFAULT 'unknown'
       CHECK (model_status IN ('installed','planning_candidate','consented_envelope','suspected','unknown')),
  model_id bigint REFERENCES atlas.turbine_models,
  iec_class text,
  min_blade_clearance_m numeric
);

-- ---------------------------------------------------------------------------
-- Organisations, planning, grid, support, geometries, history
-- ---------------------------------------------------------------------------
CREATE TABLE atlas.asset_organisations (
  asset_org_id bigserial PRIMARY KEY,
  asset_id  text NOT NULL REFERENCES atlas.assets ON DELETE CASCADE,
  org_id    bigint NOT NULL REFERENCES atlas.organisations,
  role      text NOT NULL CHECK (role IN ('developer','original_developer','owner','operator','asset_manager','epc','om','optimiser','applicant','customer','lessee')),
  raw_name  text,
  ownership_pct numeric CHECK (ownership_pct BETWEEN 0 AND 100),
  effective_from date,
  effective_to   date,
  source_record_id bigint REFERENCES norm.source_record,
  evidence_id bigint REFERENCES atlas.evidence_documents
);
CREATE INDEX ON atlas.asset_organisations (asset_id);
CREATE INDEX ON atlas.asset_organisations (org_id, role);

CREATE TABLE atlas.planning_cases (
  case_id   bigserial PRIMARY KEY,
  asset_id  text NOT NULL REFERENCES atlas.assets ON DELETE CASCADE,
  authority text,
  reference text,
  ref_type  text NOT NULL DEFAULT 'lpa' CHECK (ref_type IN ('lpa','s36','ecu','dco','dns','sip','appeal','secretary_of_state','marine_licence','other')),
  application_date date,
  decision_date date,
  decision  text,
  stage     text,
  url       text,
  notes     text,
  source_record_id bigint REFERENCES norm.source_record,
  evidence_id bigint REFERENCES atlas.evidence_documents
);
CREATE INDEX ON atlas.planning_cases (asset_id);
CREATE INDEX ON atlas.planning_cases (reference);

CREATE TABLE atlas.grid_connections (
  conn_id   bigserial PRIMARY KEY,
  asset_id  text NOT NULL REFERENCES atlas.assets ON DELETE CASCADE,
  network_operator text,
  connection_type text CHECK (connection_type IN ('transmission','distribution','unknown')),
  dno text,
  point_of_connection text,
  grid_supply_point text,
  bulk_supply_point text,
  primary_substation text,
  voltage_kv numeric,
  registered_capacity_mw numeric,
  import_mw numeric,
  export_mw numeric,
  tec_mw numeric,
  connection_status text,
  connection_date date,
  effective_from date,
  gate text,
  ecr_id text,
  neso_project_id text,
  neso_project_number text,
  source_record_id bigint REFERENCES norm.source_record
);
CREATE INDEX ON atlas.grid_connections (asset_id);

CREATE TABLE atlas.support_schemes (
  support_id bigserial PRIMARY KEY,
  asset_id  text NOT NULL REFERENCES atlas.assets ON DELETE CASCADE,
  scheme    text NOT NULL CHECK (scheme IN ('CfD','RO','REGO','FIT')),
  reference text,
  accredited_capacity_mw numeric,         -- scheme capacity: NOT assumed equal to physical capacity
  allocation_round text,
  delivery_year int,
  strike_price_gbp_mwh numeric,
  price_base_year int,
  banding numeric,
  tariff_p_per_kwh numeric,
  status    text,
  notes     text,
  source_record_id bigint REFERENCES norm.source_record
);
CREATE INDEX ON atlas.support_schemes (asset_id);

CREATE TABLE atlas.asset_geometries (
  geom_id   bigserial PRIMARY KEY,
  asset_id  text NOT NULL REFERENCES atlas.assets ON DELETE CASCADE,
  geom_type text NOT NULL CHECK (geom_type IN ('site_reference','planning_boundary','operational_boundary','lease_area','array_area','export_cable','substation_compound','battery_compound','solar_area')),
  geom      geometry(Geometry,4326) NOT NULL,
  original_crs text,
  accuracy_class text,
  label     text,
  source_record_id bigint REFERENCES norm.source_record,
  match_score numeric,
  UNIQUE (asset_id, geom_type, source_record_id)
);
CREATE INDEX ON atlas.asset_geometries USING gist (geom);

CREATE TABLE atlas.asset_history (
  event_id  bigserial PRIMARY KEY,
  asset_id  text NOT NULL REFERENCES atlas.assets ON DELETE CASCADE,
  event_date date,
  event_type text NOT NULL,
  description text NOT NULL,
  source_record_id bigint REFERENCES norm.source_record,
  evidence_id bigint REFERENCES atlas.evidence_documents,
  url text
);
CREATE INDEX ON atlas.asset_history (asset_id, event_date);

-- context layers (derived-attribute sources, also usable as overlays)
CREATE TABLE atlas.admin_areas (
  area_id   bigserial PRIMARY KEY,
  layer     text NOT NULL,                  -- 'lad'
  code      text NOT NULL,
  name      text NOT NULL,
  country   text,
  geom      geometry(MultiPolygon,4326) NOT NULL,
  source_key text NOT NULL,
  UNIQUE (layer, code)
);
CREATE INDEX ON atlas.admin_areas USING gist (geom);
