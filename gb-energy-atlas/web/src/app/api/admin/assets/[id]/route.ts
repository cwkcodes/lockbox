import { NextRequest } from "next/server";
import { query, queryOne } from "@/lib/db";
import { adminAllowed, apiError, json } from "@/lib/api";
import { safeUrl } from "@/lib/format";

export const dynamic = "force-dynamic";
const EDITABLE: Record<string, { col: string; kind: "text" | "num" }> = {
  canonical_name: { col: "canonical_name", kind: "text" }, status_code: { col: "status_code", kind: "text" }, technology_code: { col: "technology_code", kind: "text" },
  installed_capacity_mw: { col: "installed_capacity_mw", kind: "num" }, planning_reference: { col: "planning_reference", kind: "text" },
  planning_authority: { col: "planning_authority", kind: "text" }, notes: { col: "notes", kind: "text" },
};

/** PATCH { field, value, reason, evidence_url? } – manual edit: audit-trailed, stored as a durable override re-applied on every rebuild. */
export async function PATCH(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  if (!adminAllowed(req)) return apiError(401, "admin authentication required");
  const { id } = await ctx.params;
  const b = await req.json().catch(() => ({}));
  const spec = EDITABLE[String(b.field)];
  const reason = String(b.reason ?? "").trim();
  if (!spec || reason.length < 5) return apiError(400, `field must be one of ${Object.keys(EDITABLE).join(", ")} and a reason (≥5 chars) is required`);
  const ev = b.evidence_url ? safeUrl(String(b.evidence_url)) : null;
  const cur = await queryOne<Record<string, unknown>>(`SELECT ${spec.col} AS v FROM atlas.assets WHERE asset_id=$1`, [id]);
  const anchor = await queryOne<{ anchor_scheme: string; anchor_value: string }>("SELECT anchor_scheme, anchor_value FROM atlas.asset_anchor WHERE asset_id=$1 LIMIT 1", [id]);
  if (!cur || !anchor) return apiError(404, "asset not found");
  const val = spec.kind === "num" ? Number(b.value) : String(b.value);
  if (spec.kind === "num" && !Number.isFinite(val as number)) return apiError(400, "numeric value required");
  await query(`INSERT INTO ops.manual_overrides (anchor_scheme, anchor_value, field_name, value_text, value_num, reason, evidence_url, decided_by)
               VALUES ($1,$2,$3,$4,$5,$6,$7,'admin') ON CONFLICT (anchor_scheme, anchor_value, field_name) DO UPDATE
               SET value_text=EXCLUDED.value_text, value_num=EXCLUDED.value_num, reason=EXCLUDED.reason, evidence_url=EXCLUDED.evidence_url, decided_at=now()`,
    [anchor.anchor_scheme, anchor.anchor_value, String(b.field), spec.kind === "text" ? String(val) : null, spec.kind === "num" ? val : null, reason, ev]);
  await query(`UPDATE atlas.assets SET ${spec.col} = $2, updated_at = now() WHERE asset_id = $1`, [id, val]);
  await query(`INSERT INTO ops.audit_log (entity_type, entity_id, field_name, old_value, new_value, reason, actor, actor_type, ai_assisted)
               VALUES ('asset', $1, $2, $3, $4, $5, 'admin', 'user', $6)`, [id, String(b.field), cur.v === null ? null : String(cur.v), String(val), reason + (ev ? ` (evidence: ${ev})` : ""), b.ai_assisted === true]);
  await query(`INSERT INTO atlas.field_provenance (asset_id, entity_type, entity_id, field_name, value_text, value_num, value_kind, source_key, observed_at, is_preferred, selection_reason)
               VALUES ($1,'asset',$1,$2,$3,$4,'manual','manual',current_date,true,$5)`, [id, String(b.field), spec.kind === "text" ? String(val) : null, spec.kind === "num" ? val : null, `Manual edit: ${reason}`]);
  await query("REFRESH MATERIALIZED VIEW atlas.asset_flat");
  return json({ ok: true });
}
