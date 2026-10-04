import { NextRequest } from "next/server";
import { query } from "@/lib/db";
import { adminAllowed, apiError, intParam, json } from "@/lib/api";

export const dynamic = "force-dynamic";

/** QA dashboard data for administrators. */
export async function GET(req: NextRequest) {
  if (!adminAllowed(req)) return apiError(401, "admin authentication required");
  const code = req.nextUrl.searchParams.get("code");
  const page = intParam(req, "page", 1, 1, 10000);
  const [byCode, flagged, queue, runs, reports, candidates, stale] = await Promise.all([
    query(`SELECT flag_code, severity, count(*)::int AS n FROM atlas.data_quality_flags WHERE resolved_at IS NULL GROUP BY 1,2 ORDER BY n DESC`),
    code ? query(`SELECT fl.flag_id, fl.asset_id, a.canonical_name, a.technology_code, a.country, fl.severity, fl.message, fl.detail FROM atlas.data_quality_flags fl JOIN atlas.assets a USING (asset_id)
                  WHERE fl.resolved_at IS NULL AND fl.flag_code = $1 ORDER BY fl.severity DESC, a.installed_capacity_mw DESC NULLS LAST LIMIT 100 OFFSET ${(page - 1) * 100}`, [code]) : Promise.resolve([]),
    query(`SELECT missing_field, status, count(*)::int AS n FROM ops.research_queue GROUP BY 1,2 ORDER BY n DESC`),
    query(`SELECT r.run_id, r.source_key, r.started_at, r.finished_at, r.outcome, r.rows_ok, r.rows_rejected, left(r.message, 300) AS message FROM ops.ingestion_run r ORDER BY r.run_id DESC LIMIT 40`),
    query(`SELECT status, count(*)::int AS n FROM ops.user_reports GROUP BY 1`),
    query(`SELECT decision, count(*)::int AS n FROM ops.match_candidates GROUP BY 1`),
    query(`SELECT count(*)::int AS n FROM atlas.data_quality_flags WHERE flag_code='old_source' AND resolved_at IS NULL`),
  ]);
  return json({ byCode, flagged, researchQueue: queue, ingestionRuns: runs, userReports: reports, matchCandidates: candidates, staleRecords: stale[0].n });
}
