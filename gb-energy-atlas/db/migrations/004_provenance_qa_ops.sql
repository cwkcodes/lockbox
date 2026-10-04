-- 004: field-level provenance, conflicts, QA flags, audit trail, review queues

CREATE TABLE atlas.field_provenance (
  prov_id     bigserial PRIMARY KEY,
  asset_id    text NOT NULL REFERENCES atlas.assets ON DELETE CASCADE,
  entity_type text NOT NULL DEFAULT 'asset' CHECK (entity_type IN ('asset','unit','organisation')),
  entity_id   text NOT NULL,
  field_name  text NOT NULL,
  value_text  text,
  value_num   numeric,
  value_unit  text,
  value_kind  text NOT NULL DEFAULT 'published' CHECK (value_kind IN ('published','calculated','derived_spatial','manual','research')),
  calc_expression text,                    -- shown to the user for calculated values
  source_record_id bigint REFERENCES norm.source_record,
  evidence_id bigint REFERENCES atlas.evidence_documents,
  source_key  text,
  raw_column  text,
  raw_value   text,
  raw_unit    text,
  observed_at date,                        -- publication/update date of the source value
  retrieved_at timestamptz,
  is_preferred boolean NOT NULL DEFAULT false,
  selection_reason text,
  doc_page    text,                        -- document-derived facts: page / section / figure
  doc_snippet text,
  effective_from date,
  effective_to   date
);
CREATE INDEX ON atlas.field_provenance (asset_id, field_name);
CREATE INDEX ON atlas.field_provenance (source_record_id);

-- values reported by more than one source that do not agree
CREATE VIEW atlas.field_conflicts AS
SELECT asset_id, field_name,
       count(DISTINCT coalesce(value_num::text, value_text)) AS distinct_values,
       jsonb_agg(jsonb_build_object(
          'value', coalesce(value_num::text, value_text), 'unit', value_unit, 'source_key', source_key,
          'observed_at', observed_at, 'preferred', is_preferred, 'kind', value_kind,
          'prov_id', prov_id) ORDER BY is_preferred DESC, observed_at DESC NULLS LAST) AS observations
FROM atlas.field_provenance
WHERE entity_type = 'asset' AND field_name NOT IN ('location_bng','status_context','technology_context')
GROUP BY asset_id, field_name
HAVING count(DISTINCT coalesce(value_num::text, value_text)) > 1;

CREATE TABLE atlas.data_quality_flags (
  flag_id    bigserial PRIMARY KEY,
  asset_id   text REFERENCES atlas.assets ON DELETE CASCADE,
  source_record_id bigint REFERENCES norm.source_record ON DELETE CASCADE,
  flag_code  text NOT NULL,
  severity   text NOT NULL DEFAULT 'info' CHECK (severity IN ('info','warning','error')),
  detail     jsonb NOT NULL DEFAULT '{}',
  message    text,
  raised_at  timestamptz NOT NULL DEFAULT now(),
  resolved_at timestamptz,
  resolved_by text,
  resolution_note text
);
CREATE INDEX ON atlas.data_quality_flags (flag_code) WHERE resolved_at IS NULL;
CREATE INDEX ON atlas.data_quality_flags (asset_id) WHERE resolved_at IS NULL;

-- ---------------------------------------------------------------------------
-- ops: runs, audit, matching, change log, review queues
-- ---------------------------------------------------------------------------
CREATE TABLE ops.ingestion_run (
  run_id     bigserial PRIMARY KEY,
  source_key text NOT NULL REFERENCES ops.source_registry,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  outcome    text CHECK (outcome IN ('success','unchanged','source_unavailable','restricted','manual_review_required','error')),
  snapshot_id bigint REFERENCES raw.snapshot ON DELETE SET NULL,
  rows_read  int,
  rows_ok    int,
  rows_rejected int,
  message    text
);

CREATE TABLE ops.audit_log (
  audit_id   bigserial PRIMARY KEY,
  ts         timestamptz NOT NULL DEFAULT now(),
  entity_type text NOT NULL,
  entity_id  text NOT NULL,
  field_name text,
  old_value  text,
  new_value  text,
  reason     text,
  source_record_id bigint,
  actor      text NOT NULL,
  actor_type text NOT NULL CHECK (actor_type IN ('system','user','ai')),
  ai_assisted boolean NOT NULL DEFAULT false
);
CREATE INDEX ON ops.audit_log (entity_type, entity_id, ts DESC);

CREATE TABLE ops.match_candidates (
  cand_id    bigserial PRIMARY KEY,
  record_a   bigint NOT NULL REFERENCES norm.source_record ON DELETE CASCADE,
  record_b   bigint REFERENCES norm.source_record ON DELETE CASCADE,
  asset_b    text,                         -- when the counterpart is a canonical asset
  score      numeric NOT NULL,
  components jsonb NOT NULL,
  decision   text NOT NULL DEFAULT 'pending' CHECK (decision IN ('auto_linked','pending','approved','rejected')),
  reason     text,
  decided_by text,
  decided_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON ops.match_candidates (decision, score DESC);

CREATE TABLE ops.change_log (
  change_id  bigserial PRIMARY KEY,
  source_key text NOT NULL,
  detected_at timestamptz NOT NULL DEFAULT now(),
  from_snapshot_id bigint,
  to_snapshot_id bigint NOT NULL,
  record_key text NOT NULL,
  record_name text,
  change_type text NOT NULL CHECK (change_type IN ('new_project','removed_project','status_change','capacity_change','date_change','developer_change','connection_change','other_change')),
  field_name text,
  old_value  text,
  new_value  text
);
CREATE INDEX ON ops.change_log (source_key, to_snapshot_id);

CREATE TABLE ops.research_queue (
  item_id    bigserial PRIMARY KEY,
  asset_id   text NOT NULL REFERENCES atlas.assets ON DELETE CASCADE,
  missing_field text NOT NULL,
  priority   int NOT NULL DEFAULT 100,
  status     text NOT NULL DEFAULT 'open' CHECK (status IN ('open','in_progress','done','wont_do')),
  suggested_sources text[] NOT NULL DEFAULT '{}',
  evidence_used jsonb NOT NULL DEFAULT '[]',   -- only URLs actually consulted
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (asset_id, missing_field)
);

CREATE TABLE ops.user_reports (
  report_id  bigserial PRIMARY KEY,
  asset_id   text,
  report_type text NOT NULL CHECK (report_type IN ('incorrect_info','missing_project','incorrect_turbine_location','incorrect_status','broken_source','other')),
  description text NOT NULL,
  evidence_url text NOT NULL,              -- supporting evidence is mandatory
  contact    text,
  status     text NOT NULL DEFAULT 'pending_review' CHECK (status IN ('pending_review','accepted','rejected')),
  submitted_at timestamptz NOT NULL DEFAULT now(),
  reviewed_by text,
  reviewed_at timestamptz
);

CREATE TABLE ops.url_checks (
  check_id   bigserial PRIMARY KEY,
  url        text NOT NULL,
  checked_at timestamptz NOT NULL DEFAULT now(),
  http_status int,
  ok         boolean NOT NULL,
  note       text
);
CREATE INDEX ON ops.url_checks (url, checked_at DESC);

CREATE TABLE ops.conflict_reviews (
  review_id  bigserial PRIMARY KEY,
  asset_id   text NOT NULL REFERENCES atlas.assets ON DELETE CASCADE,
  field_name text NOT NULL,
  status     text NOT NULL DEFAULT 'open' CHECK (status IN ('open','accepted','overridden','dismissed')),
  chosen_prov_id bigint,
  explanation text,
  reviewed_by text,
  reviewed_at timestamptz,
  UNIQUE (asset_id, field_name)
);

-- Durable human decisions, keyed by stable identifiers (not by per-snapshot record ids) so they survive a rebuild.
CREATE TABLE ops.manual_links (
  link_id    bigserial PRIMARY KEY,
  source_key text NOT NULL,
  record_key text NOT NULL,
  anchor_scheme text NOT NULL,
  anchor_value  text NOT NULL,
  decision   text NOT NULL CHECK (decision IN ('link','never_link')),
  reason     text NOT NULL,
  decided_by text NOT NULL,
  decided_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_key, record_key, anchor_scheme, anchor_value)
);

CREATE TABLE ops.manual_overrides (
  override_id bigserial PRIMARY KEY,
  anchor_scheme text NOT NULL,
  anchor_value  text NOT NULL,
  field_name  text NOT NULL,
  value_text  text,
  value_num   numeric,
  reason      text NOT NULL,
  evidence_url text,
  decided_by  text NOT NULL,
  decided_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (anchor_scheme, anchor_value, field_name)
);

CREATE TABLE ops.job_requests (
  job_id     bigserial PRIMARY KEY,
  job_type   text NOT NULL CHECK (job_type IN ('ingest','build')),
  source_key text,
  requested_by text NOT NULL,
  requested_at timestamptz NOT NULL DEFAULT now(),
  status     text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','done','failed')),
  finished_at timestamptz,
  message    text
);
