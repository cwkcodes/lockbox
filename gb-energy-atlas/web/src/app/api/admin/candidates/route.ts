import { NextRequest } from "next/server";
import { query, queryOne } from "@/lib/db";
import { adminAllowed, apiError, intParam, json } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  if (!adminAllowed(req)) return apiError(401, "admin authentication required");
  const page = intParam(req, "page", 1, 1, 10000);
  const items = await query(
    `SELECT mc.cand_id, mc.score, mc.components, mc.reason, mc.decision,
            sr.source_key, sr.record_key, sr.name AS source_name, sr.capacity_mw AS source_mw, sr.technology_code AS source_tech, sr.status_raw AS source_status,
            a.asset_id, a.canonical_name, a.installed_capacity_mw AS asset_mw, a.technology_code AS asset_tech, a.status_code AS asset_status, a.country
     FROM ops.match_candidates mc JOIN norm.source_record sr ON sr.source_record_id = mc.record_a JOIN atlas.assets a ON a.asset_id = mc.asset_b
     WHERE mc.decision = 'pending' ORDER BY mc.score DESC LIMIT 50 OFFSET ${(page - 1) * 50}`);
  return json({ items });
}

/** POST { cand_id, decision: 'approved'|'rejected', reason } – recorded durably in ops.manual_links (+ audit trail); applied on the next build. */
export async function POST(req: NextRequest) {
  if (!adminAllowed(req)) return apiError(401, "admin authentication required");
  const b = await req.json().catch(() => ({}));
  const reason = String(b.reason ?? "").trim();
  if (!["approved", "rejected"].includes(b.decision) || reason.length < 5) return apiError(400, "decision (approved|rejected) and a reason of at least 5 characters are required");
  const c = await queryOne<{ record_a: number; asset_b: string; source_key: string; record_key: string; anchor_scheme: string; anchor_value: string }>(
    `SELECT mc.record_a, mc.asset_b, sr.source_key, sr.record_key, an.anchor_scheme, an.anchor_value FROM ops.match_candidates mc
     JOIN norm.source_record sr ON sr.source_record_id = mc.record_a JOIN atlas.asset_anchor an ON an.asset_id = mc.asset_b WHERE mc.cand_id = $1 LIMIT 1`, [b.cand_id]);
  if (!c) return apiError(404, "candidate not found");
  await query(`INSERT INTO ops.manual_links (source_key, record_key, anchor_scheme, anchor_value, decision, reason, decided_by)
               VALUES ($1,$2,$3,$4,$5,$6,'admin') ON CONFLICT (source_key, record_key, anchor_scheme, anchor_value) DO UPDATE SET decision=EXCLUDED.decision, reason=EXCLUDED.reason, decided_at=now()`,
    [c.source_key, c.record_key, c.anchor_scheme, c.anchor_value, b.decision === "approved" ? "link" : "never_link", reason]);
  await query("UPDATE ops.match_candidates SET decision=$2, decided_by='admin', decided_at=now(), reason=coalesce(reason,'') || ' | decision: ' || $3 WHERE cand_id=$1", [b.cand_id, b.decision, reason]);
  await query(`INSERT INTO ops.audit_log (entity_type, entity_id, field_name, old_value, new_value, reason, actor, actor_type)
               VALUES ('match_candidate', $1, 'decision', 'pending', $2, $3, 'admin', 'user')`, [String(b.cand_id), b.decision, reason]);
  return json({ ok: true, note: "Decision stored; it takes effect at the next canonical build (atlas-ingest build)." });
}
