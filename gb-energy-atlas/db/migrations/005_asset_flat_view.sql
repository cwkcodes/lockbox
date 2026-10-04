-- 005: one flat, indexed read model. Tiles, list, statistics, search, export and the API
-- all query this view through the same filter builder so they can never disagree.

CREATE MATERIALIZED VIEW atlas.asset_flat AS
WITH org_roles AS (
  SELECT ao.asset_id, ao.role, array_agg(DISTINCT o.canonical_name ORDER BY o.canonical_name) AS names
  FROM atlas.asset_organisations ao JOIN atlas.organisations o USING (org_id)
  WHERE ao.effective_to IS NULL
  GROUP BY 1, 2
), srcs AS (
  SELECT l.asset_id, array_agg(DISTINCT sr.source_key ORDER BY sr.source_key) AS source_keys, count(*) AS source_record_count
  FROM atlas.asset_source_links l JOIN norm.source_record sr USING (source_record_id)
  GROUP BY 1
), sup AS (
  SELECT asset_id, bool_or(scheme='CfD') AS has_cfd, bool_or(scheme='RO') AS has_ro,
         bool_or(scheme='REGO') AS has_rego, bool_or(scheme='FIT') AS has_fit
  FROM atlas.support_schemes GROUP BY 1
), plan AS (
  SELECT asset_id, min(application_date) AS first_application_date,
         (array_agg(decision ORDER BY decision_date DESC NULLS LAST))[1] AS latest_decision
  FROM atlas.planning_cases GROUP BY 1
), conf AS (
  SELECT asset_id, true AS has_conflict FROM atlas.field_conflicts GROUP BY 1
), grid AS (
  SELECT DISTINCT ON (asset_id) asset_id, dno, point_of_connection, grid_supply_point, gate
  FROM atlas.grid_connections ORDER BY asset_id, conn_id
), units AS (
  SELECT asset_id, count(*) AS unit_count FROM atlas.generating_units WHERE unit_type='wind_turbine' AND geom IS NOT NULL GROUP BY 1
), repo AS (
  SELECT repowers_asset_id AS asset_id, count(*) AS n FROM atlas.assets WHERE repowers_asset_id IS NOT NULL GROUP BY 1
), colo AS (
  SELECT x.asset_id, true AS co_located_storage FROM (
    SELECT from_asset_id AS asset_id FROM atlas.asset_relationships WHERE relation='co_located_with'
    UNION SELECT to_asset_id FROM atlas.asset_relationships WHERE relation='co_located_with'
  ) x GROUP BY 1
)
SELECT
  a.asset_id, a.canonical_name, a.name_norm, a.aliases,
  a.technology_code, t.label AS technology_label, t.family, t.category, t.colour,
  a.subtechnology,
  a.status_code, a.status_original, a.status_source_key, s.label AS status_label, s.stage_group, s.pattern AS status_pattern,
  a.country, a.region, a.local_authority, a.is_offshore,
  a.lat, a.lon, a.bng_e, a.bng_n, a.geom, ST_Transform(a.geom, 3857) AS geom_3857, a.coordinate_accuracy, a.coordinate_source_key,
  a.installed_capacity_mw, a.capacity_basis, a.export_capacity_mw, a.storage_capacity_mwh, a.storage_duration_h, a.storage_duration_basis,
  a.commissioning_date, EXTRACT(YEAR FROM a.commissioning_date)::int AS commissioning_year,
  plan.first_application_date, EXTRACT(YEAR FROM plan.first_application_date)::int AS planning_year, plan.latest_decision,
  a.planning_authority, a.planning_reference,
  a.grid_operator, a.connection_type, a.connection_voltage_kv, a.connection_status,
  grid.dno, grid.point_of_connection, grid.grid_supply_point,
  a.repd_ref, a.tec_ref, a.ecr_ref, a.ofgem_ref, a.cfd_ref,
  COALESCE(dev.names, '{}') AS developers, COALESCE(own.names, '{}') AS owners, COALESCE(opr.names, '{}') AS operators,
  (COALESCE(dev.names, '{}'))[1] AS developer, (COALESCE(own.names, '{}'))[1] AS owner, (COALESCE(opr.names, '{}'))[1] AS operator,
  w.turbine_manufacturer, w.turbine_model, w.turbine_count_reported AS turbine_count, w.hub_height_m, w.rotor_diameter_m,
  COALESCE(w.installed_tip_height_m, w.consented_tip_height_m, w.turbine_height_reported_m) AS tip_height_m,
  w.model_status, w.foundation_type,
  COALESCE(units.unit_count, 0) AS verified_turbine_positions,
  (COALESCE(units.unit_count, 0) > 0) AS individual_turbines_known,
  a.parent_asset_id, a.phase_label, a.repowers_asset_id,
  CASE WHEN a.repowers_asset_id IS NOT NULL THEN 'is_repower'
       WHEN repo.n > 0 THEN 'has_repower'
       ELSE 'none' END AS repowering_status,
  COALESCE(colo.co_located_storage, false) AS co_located_storage,
  COALESCE(sup.has_cfd, false) AS has_cfd, COALESCE(sup.has_ro, false) AS has_ro,
  COALESCE(sup.has_rego, false) AS has_rego, COALESCE(sup.has_fit, false) AS has_fit,
  a.confidence, a.completeness_pct, a.last_verified, a.source_updated, a.asset_kind, a.scale_class, a.privacy_class,
  a.in_scope_gb, a.scope_note,
  COALESCE(srcs.source_keys, '{}') AS source_keys, COALESCE(srcs.source_record_count, 0) AS source_record_count,
  COALESCE(conf.has_conflict, false) AS has_conflict,
  a.search_doc
FROM atlas.assets a
JOIN atlas.technology t ON t.code = a.technology_code
JOIN atlas.status s ON s.code = a.status_code
LEFT JOIN org_roles dev ON dev.asset_id = a.asset_id AND dev.role = 'developer'
LEFT JOIN org_roles own ON own.asset_id = a.asset_id AND own.role = 'owner'
LEFT JOIN org_roles opr ON opr.asset_id = a.asset_id AND opr.role = 'operator'
LEFT JOIN atlas.wind_details w ON w.asset_id = a.asset_id
LEFT JOIN srcs ON srcs.asset_id = a.asset_id
LEFT JOIN sup ON sup.asset_id = a.asset_id
LEFT JOIN plan ON plan.asset_id = a.asset_id
LEFT JOIN conf ON conf.asset_id = a.asset_id
LEFT JOIN grid ON grid.asset_id = a.asset_id
LEFT JOIN units ON units.asset_id = a.asset_id
LEFT JOIN repo ON repo.asset_id = a.asset_id
LEFT JOIN colo ON colo.asset_id = a.asset_id
WHERE a.is_published;

CREATE UNIQUE INDEX ON atlas.asset_flat (asset_id);
CREATE INDEX ON atlas.asset_flat USING gist (geom_3857);
CREATE INDEX ON atlas.asset_flat USING gist (geom);
CREATE INDEX ON atlas.asset_flat (family, stage_group);
CREATE INDEX ON atlas.asset_flat (technology_code);
CREATE INDEX ON atlas.asset_flat (status_code);
CREATE INDEX ON atlas.asset_flat (country);
CREATE INDEX ON atlas.asset_flat (local_authority);
CREATE INDEX ON atlas.asset_flat (commissioning_year);
CREATE INDEX ON atlas.asset_flat USING gin (name_norm gin_trgm_ops);
CREATE INDEX ON atlas.asset_flat USING gin (to_tsvector('simple', coalesce(search_doc,'')));
CREATE INDEX ON atlas.asset_flat USING gin (source_keys);
CREATE INDEX ON atlas.asset_flat USING gin (developers);
CREATE INDEX ON atlas.asset_flat USING gin (owners);
CREATE INDEX ON atlas.asset_flat USING gin (operators);

-- Individual turbines for map tiles (only verified positions exist here)
CREATE VIEW atlas.turbine_flat AS
SELECT u.unit_id, u.asset_id, u.unit_code, u.rated_mw, u.status_code, u.commissioning_year,
       u.lat, u.lon, u.bng_e, u.bng_n, u.geom, ST_Transform(u.geom, 3857) AS geom_3857,
       u.coordinate_class, u.coordinate_accuracy_m,
       wt.manufacturer, wt.model, wt.hub_height_m, wt.rotor_diameter_m, wt.tip_height_m, wt.model_status,
       f.canonical_name AS asset_name, f.country, f.local_authority
FROM atlas.generating_units u
JOIN atlas.asset_flat f USING (asset_id)
LEFT JOIN atlas.wind_turbines wt USING (unit_id)
WHERE u.unit_type = 'wind_turbine' AND u.geom IS NOT NULL;
