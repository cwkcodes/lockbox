import { query } from "@/lib/db";
import { json } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET() {
  const [technologies, statuses, sources, totals] = await Promise.all([
    query("SELECT code, label, family, category, is_renewable, sort_order, colour, symbol, description FROM atlas.technology ORDER BY sort_order"),
    query("SELECT code, label, stage_group, sort_order, pattern FROM atlas.status ORDER BY sort_order"),
    query(`SELECT source_key, organisation, dataset, tier, access_status, latest_publication_date, last_checked_at, records_imported, licence_name, attribution, export_policy
           FROM ops.source_registry WHERE active ORDER BY source_key`),
    query(`SELECT count(*)::int AS assets, max(last_verified) AS last_verified,
                  (SELECT max(retrieved_at) FROM raw.snapshot WHERE is_current) AS last_retrieved,
                  (SELECT max(publication_date) FROM raw.snapshot WHERE is_current) AS latest_publication
           FROM atlas.assets WHERE is_published`),
  ]);
  return json({ technologies, statuses, sources, totals: totals[0] }, { cache: "public, max-age=120" });
}
