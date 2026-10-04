import { query } from "@/lib/db";
import { json } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET() {
  const sources = await query(
    `SELECT g.source_key, g.organisation, g.dataset, g.tier, g.source_type, g.format, g.landing_url, g.update_frequency, g.licence_name, g.licence_url, g.attribution,
            g.redistribution, g.commercial_use_notes, g.export_policy, g.export_policy_reason, g.access_status, g.access_notes, g.known_limitations,
            g.last_checked_at, g.latest_publication_date, g.records_imported, g.records_rejected,
            (SELECT jsonb_build_object('outcome', r.outcome, 'finished_at', r.finished_at, 'message', r.message) FROM ops.ingestion_run r WHERE r.source_key = g.source_key ORDER BY r.run_id DESC LIMIT 1) AS last_run,
            (SELECT jsonb_build_object('retrieved_at', s.retrieved_at, 'publication_date', s.publication_date, 'url', s.source_url, 'sha12', left(s.sha256,12), 'notes', s.notes)
               FROM raw.snapshot s WHERE s.source_key = g.source_key AND s.is_current ORDER BY s.retrieved_at DESC LIMIT 1) AS snapshot
     FROM ops.source_registry g WHERE g.active ORDER BY g.tier, g.source_key`);
  const [counts, changes] = await Promise.all([
    query(`SELECT count(*)::int AS assets, count(*) FILTER (WHERE in_scope_gb)::int AS gb_assets, count(*) FILTER (WHERE geom IS NOT NULL)::int AS located,
                  count(*) FILTER (WHERE asset_kind='lease_area')::int AS lease_areas FROM atlas.assets WHERE is_published`),
    query("SELECT source_key, change_type, count(*)::int AS n FROM ops.change_log GROUP BY 1,2 ORDER BY 1,2"),
  ]);
  return json({ sources, counts: counts[0], changeLog: changes }, { cache: "public, max-age=60" });
}
