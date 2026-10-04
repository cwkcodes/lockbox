import { NextRequest } from "next/server";
import { query } from "@/lib/db";
import { adminAllowed, apiError, json } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  if (!adminAllowed(req)) return apiError(401, "admin authentication required");
  const [rejects, jobs, changes] = await Promise.all([
    query(`SELECT s.source_key, rj.reason, count(*)::int AS n FROM raw.reject rj JOIN raw.snapshot s USING (snapshot_id) WHERE s.is_current GROUP BY 1,2 ORDER BY n DESC LIMIT 50`),
    query("SELECT * FROM ops.job_requests ORDER BY job_id DESC LIMIT 30"),
    query("SELECT source_key, change_type, count(*)::int AS n FROM ops.change_log GROUP BY 1,2 ORDER BY 1,2"),
  ]);
  return json({ rejects, jobs, changes });
}

/** POST { source_key } or { job_type: 'build' } – queue a re-ingestion/build for the worker (`atlas-ingest worker`). */
export async function POST(req: NextRequest) {
  if (!adminAllowed(req)) return apiError(401, "admin authentication required");
  const b = await req.json().catch(() => ({}));
  const type = b.job_type === "build" ? "build" : "ingest";
  if (type === "ingest" && !/^[a-z0-9_]{2,40}$/.test(String(b.source_key ?? ""))) return apiError(400, "valid source_key required");
  const r = await query("INSERT INTO ops.job_requests (job_type, source_key, requested_by) VALUES ($1,$2,'admin') RETURNING job_id", [type, type === "ingest" ? b.source_key : null]);
  return json({ ok: true, job_id: r[0].job_id });
}
