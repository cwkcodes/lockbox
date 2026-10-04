import { NextRequest } from "next/server";
import { query } from "@/lib/db";
import { adminAllowed, apiError, json } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  if (!adminAllowed(req)) return apiError(401, "admin authentication required");
  return json({ items: await query("SELECT * FROM ops.user_reports ORDER BY (status='pending_review') DESC, submitted_at DESC LIMIT 100") });
}

export async function POST(req: NextRequest) {
  if (!adminAllowed(req)) return apiError(401, "admin authentication required");
  const b = await req.json().catch(() => ({}));
  if (!["accepted", "rejected"].includes(b.status) || !Number.isInteger(b.report_id)) return apiError(400, "report_id and status (accepted|rejected) required");
  await query("UPDATE ops.user_reports SET status=$2, reviewed_by='admin', reviewed_at=now() WHERE report_id=$1", [b.report_id, b.status]);
  await query("INSERT INTO ops.audit_log (entity_type, entity_id, field_name, old_value, new_value, reason, actor, actor_type) VALUES ('user_report',$1,'status','pending_review',$2,$3,'admin','user')", [String(b.report_id), b.status, String(b.note ?? "")]);
  return json({ ok: true });
}
