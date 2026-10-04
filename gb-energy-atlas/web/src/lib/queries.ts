import { query, queryOne } from "./db";

type Row = Record<string, unknown>;

export async function getAssetDetail(id: string) {
  const asset = await queryOne<Row>(
    `SELECT to_jsonb(a) - 'geom' - 'search_doc' AS a, t.label AS technology_label, t.family, t.category, t.colour, s.label AS status_label, s.stage_group, s.pattern AS status_pattern
     FROM atlas.assets a JOIN atlas.technology t ON t.code = a.technology_code JOIN atlas.status s ON s.code = a.status_code
     WHERE a.asset_id = $1 AND a.is_published`, [id]);
  if (!asset) return null;
  const [wind, solar, storage, hydro, bio, orgs, planning, grid, support, idents, history, geoms, units, sources, prov, flags, rels, research, parent, flat] = await Promise.all([
    queryOne("SELECT * FROM atlas.wind_details WHERE asset_id=$1", [id]),
    queryOne("SELECT * FROM atlas.solar_details WHERE asset_id=$1", [id]),
    queryOne("SELECT * FROM atlas.storage_systems WHERE asset_id=$1", [id]),
    queryOne("SELECT * FROM atlas.hydro_details WHERE asset_id=$1", [id]),
    queryOne("SELECT * FROM atlas.bioenergy_details WHERE asset_id=$1", [id]),
    query(`SELECT o.org_id, o.canonical_name, o.aliases, ao.role, ao.raw_name, ao.ownership_pct, ao.effective_from, ao.effective_to, ao.source_record_id
           FROM atlas.asset_organisations ao JOIN atlas.organisations o USING (org_id) WHERE ao.asset_id=$1 ORDER BY ao.role, o.canonical_name`, [id]),
    query("SELECT * FROM atlas.planning_cases WHERE asset_id=$1 ORDER BY application_date NULLS LAST, case_id", [id]),
    query("SELECT * FROM atlas.grid_connections WHERE asset_id=$1 ORDER BY conn_id", [id]),
    query("SELECT * FROM atlas.support_schemes WHERE asset_id=$1 ORDER BY scheme, support_id", [id]),
    query("SELECT scheme, identifier, source_record_id FROM atlas.asset_identifiers WHERE asset_id=$1 ORDER BY scheme, identifier", [id]),
    query("SELECT event_id, event_date, event_type, description, source_record_id, evidence_id, url FROM atlas.asset_history WHERE asset_id=$1 ORDER BY event_date NULLS LAST, event_id", [id]),
    query(`SELECT g.geom_id, g.geom_type, g.label, g.accuracy_class, g.original_crs, g.source_record_id, g.match_score, ST_AsGeoJSON(g.geom, 6)::json AS geometry,
                  sr.source_key, reg.attribution, reg.export_policy
           FROM atlas.asset_geometries g LEFT JOIN norm.source_record sr USING (source_record_id) LEFT JOIN ops.source_registry reg ON reg.source_key = sr.source_key
           WHERE g.asset_id=$1`, [id]),
    query(`SELECT u.unit_id, u.unit_code, u.unit_type, u.rated_mw, u.status_code, u.commissioning_year, u.lat, u.lon, u.bng_e, u.bng_n, u.coordinate_class, u.coordinate_accuracy_m, u.original_crs,
                  u.source_record_id, wt.manufacturer, wt.model, wt.hub_height_m, wt.rotor_diameter_m, wt.tip_height_m, wt.model_status
           FROM atlas.generating_units u LEFT JOIN atlas.wind_turbines wt USING (unit_id) WHERE u.asset_id=$1 ORDER BY u.unit_code`, [id]),
    query(`SELECT sr.source_record_id, sr.source_key, g.organisation, g.dataset, g.tier, g.source_type, g.licence_name, g.attribution, g.export_policy, g.access_status,
                  sr.record_key, sr.record_url, sr.name AS source_name, sr.status_raw, sr.capacity_mw, sr.capacity_basis, sr.coord_accuracy,
                  s.publication_date, s.retrieved_at, s.source_url AS snapshot_url, left(s.sha256, 12) AS sha12, s.notes AS snapshot_notes, l.link_type, l.match_score, l.match_components,
                  (SELECT array_agg(DISTINCT p.field_name ORDER BY p.field_name) FROM atlas.field_provenance p WHERE p.source_record_id = sr.source_record_id AND p.asset_id = l.asset_id) AS fields_supported,
                  (SELECT jsonb_build_object('ok', c.ok, 'http_status', c.http_status, 'checked_at', c.checked_at) FROM ops.url_checks c WHERE c.url = coalesce(sr.record_url, s.source_url) ORDER BY c.checked_at DESC LIMIT 1) AS link_check
           FROM atlas.asset_source_links l JOIN norm.source_record sr USING (source_record_id) JOIN raw.snapshot s USING (snapshot_id)
           JOIN ops.source_registry g ON g.source_key = sr.source_key WHERE l.asset_id=$1 ORDER BY g.tier, sr.source_key`, [id]),
    query(`SELECT prov_id, field_name, value_text, value_num, value_unit, value_kind, calc_expression, source_record_id, source_key, raw_column, raw_value, raw_unit,
                  observed_at, is_preferred, selection_reason, doc_page, doc_snippet
           FROM atlas.field_provenance WHERE asset_id=$1 ORDER BY field_name, is_preferred DESC, observed_at DESC NULLS LAST`, [id]),
    query("SELECT flag_id, flag_code, severity, message, detail, raised_at FROM atlas.data_quality_flags WHERE asset_id=$1 AND resolved_at IS NULL ORDER BY severity DESC, flag_code", [id]),
    query(`SELECT r.relation, r.basis, CASE WHEN r.from_asset_id=$1 THEN 'out' ELSE 'in' END AS direction,
                  CASE WHEN r.from_asset_id=$1 THEN r.to_asset_id ELSE r.from_asset_id END AS other_id,
                  a.canonical_name AS other_name, a.status_code AS other_status, a.installed_capacity_mw AS other_mw
           FROM atlas.asset_relationships r JOIN atlas.assets a ON a.asset_id = CASE WHEN r.from_asset_id=$1 THEN r.to_asset_id ELSE r.from_asset_id END
           WHERE r.from_asset_id=$1 OR r.to_asset_id=$1`, [id]),
    query("SELECT missing_field, priority, status, suggested_sources FROM ops.research_queue WHERE asset_id=$1 ORDER BY priority", [id]),
    queryOne("SELECT parent_asset_id, (SELECT canonical_name FROM atlas.assets p WHERE p.asset_id=a.parent_asset_id) AS parent_name FROM atlas.assets a WHERE asset_id=$1", [id]),
    queryOne("SELECT local_authority, dno, point_of_connection, grid_supply_point, repowering_status, co_located_storage, has_conflict, individual_turbines_known FROM atlas.asset_flat WHERE asset_id=$1", [id]),
  ]);

  // group provenance by field and mark alternatives (numbers differ by >1 %, text differs)
  const byField = new Map<string, Row[]>();
  for (const p of prov) {
    const k = p.field_name as string;
    if (!byField.has(k)) byField.set(k, []);
    byField.get(k)!.push(p);
  }
  const conflicts: { field: string; observations: Row[] }[] = [];
  for (const [field, obs] of byField) {
    if (obs.length < 2 || field === "location_bng" || field === "status_context") continue;
    const vals = obs.filter((o) => o.value_kind !== "calculated").map((o) => (o.value_num !== null ? Number(o.value_num) : String(o.value_text)));
    const differs = vals.some((v, i) => i > 0 && (typeof v === "number" && typeof vals[0] === "number" ? Math.abs(v - (vals[0] as number)) > Math.max(1e-9, Math.abs(vals[0] as number)) * 0.01 : v !== vals[0]));
    if (differs) conflicts.push({ field, observations: obs });
  }
  return { ...asset, wind, solar, storage, hydro, bio, orgs, planning, grid, support, identifiers: idents, history, geometries: geoms, units, sources, provenance: prov, conflicts, flags, relationships: rels, research, hierarchy: parent, derived: flat };
}
