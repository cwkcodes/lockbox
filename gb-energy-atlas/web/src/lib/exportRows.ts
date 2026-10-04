import { query } from "./db";
import { buildWhere, type Filters } from "./filters";
import { LIST_COLUMNS } from "./api";

export interface ExportResult {
  rows: Record<string, unknown>[];
  attribution: string[];
  notes: string[];
  columns: string[];
}

/**
 * Filtered export that carries source URLs and provenance and obeys per-source licence policy:
 * sources with export_policy='exclude' (e.g. The Crown Estate GIS licence until reviewed) are not redistributed –
 * rows supported only by them are dropped and fields whose preferred value came from them are blanked, with a note.
 */
export async function exportRows(filters: Filters): Promise<ExportResult> {
  const where = buildWhere(filters);
  const registry = await query<{ source_key: string; export_policy: string; attribution: string | null; organisation: string; dataset: string; licence_name: string | null; export_policy_reason: string | null }>(
    "SELECT source_key, export_policy, attribution, organisation, dataset, licence_name, export_policy_reason FROM ops.source_registry");
  const reviewed = process.env.TCE_EXPORT_REVIEWED === "true";
  const excluded = new Set(registry.filter((r) => r.export_policy === "exclude" && !(reviewed && r.source_key === "crown_estate_wind_sites")).map((r) => r.source_key));
  const raw = await query(
    `SELECT ${LIST_COLUMNS}, f.status_original, f.status_source_key, f.coordinate_source_key,
            (SELECT string_agg(g.organisation || ' – ' || g.dataset || ' [tier ' || g.tier || ']' ||
                    ' | published ' || coalesce(s.publication_date::text, 'n/a') || ' | retrieved ' || s.retrieved_at::date::text ||
                    ' | record ' || sr.record_key || ' | ' || coalesce(sr.record_url, s.source_url, ''), E'\\n' ORDER BY g.tier, sr.source_key)
             FROM atlas.asset_source_links l JOIN norm.source_record sr USING (source_record_id) JOIN raw.snapshot s USING (snapshot_id)
             JOIN ops.source_registry g ON g.source_key = sr.source_key WHERE l.asset_id = f.asset_id AND NOT (g.source_key = ANY($${where.params.length + 1}::text[]))) AS sources,
            (SELECT string_agg(DISTINCT p.field_name || '=' || coalesce(p.value_num::text, p.value_text) || coalesce(' ' || p.value_unit, '') || ' [' || p.source_key || ']' ||
                    CASE WHEN p.is_preferred THEN ' (preferred)' ELSE '' END, '; ')
             FROM atlas.field_provenance p WHERE p.asset_id = f.asset_id AND p.field_name IN ('installed_capacity_mw','registered_capacity_mw','cfd_capacity_mw','status')
               AND NOT (p.source_key = ANY($${where.params.length + 1}::text[]))) AS provenance
     FROM atlas.asset_flat f WHERE ${where.sql} ORDER BY f.installed_capacity_mw DESC NULLS LAST, f.asset_id`,
    [...where.params, [...excluded]]);

  const attrByKey = new Map(registry.map((r) => [r.source_key, r]));
  const used = new Set<string>();
  const rows: Record<string, unknown>[] = [];
  let dropped = 0, blanked = 0;
  for (const r of raw) {
    const keys = (r.source_keys as string[]) ?? [];
    if (keys.length && keys.every((k) => excluded.has(k))) { dropped++; continue; }
    const out: Record<string, unknown> = { ...r };
    if (r.status_source_key && excluded.has(String(r.status_source_key))) { out.status_label = null; out.status_original = null; out.status_code = null; blanked++; }
    if (r.coordinate_source_key && excluded.has(String(r.coordinate_source_key))) { out.lat = null; out.lon = null; out.bng_e = null; out.bng_n = null; blanked++; }
    keys.forEach((k) => used.add(k));
    delete out.status_source_key; delete out.coordinate_source_key; delete out.source_keys; delete out.aliases; delete out.colour;
    out.attribution = keys.map((k) => attrByKey.get(k)?.attribution).filter(Boolean).join(" | ");
    rows.push(out);
  }
  const notes: string[] = [
    "Every value originates from the cited public sources; see the 'sources' and 'provenance' columns. Calculated values are never mixed with published values.",
    "This platform consolidates publicly available information and is not a definitive register of every installation in Great Britain.",
  ];
  for (const k of excluded) {
    const r = attrByKey.get(k);
    if (r && keys_in(raw, k)) notes.push(`Excluded from this export: ${r.organisation} – ${r.dataset}. ${r.export_policy_reason ?? "Licence does not permit redistribution here."}`);
  }
  if (dropped) notes.push(`${dropped} record(s) supported only by excluded sources were omitted.`);
  if (blanked) notes.push(`${blanked} field value(s) derived from excluded sources were blanked.`);
  const attribution = [...new Set([...used].map((k) => attrByKey.get(k)?.attribution).filter((x): x is string => !!x))];
  return { rows, attribution, notes, columns: rows[0] ? Object.keys(rows[0]) : [] };
}

function keys_in(raw: Record<string, unknown>[], k: string): boolean {
  return raw.some((r) => ((r.source_keys as string[]) ?? []).includes(k));
}
