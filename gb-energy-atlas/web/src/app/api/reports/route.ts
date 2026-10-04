import { NextRequest } from "next/server";
import { query } from "@/lib/db";
import { apiError, json } from "@/lib/api";
import { safeUrl } from "@/lib/format";

export const dynamic = "force-dynamic";
const TYPES = ["incorrect_info", "missing_project", "incorrect_turbine_location", "incorrect_status", "broken_source", "other"];
const hits = new Map<string, number[]>();

/** Community corrections go to a review queue; nothing is published automatically and evidence is mandatory. */
export async function POST(req: NextRequest) {
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "local";
  const now = Date.now();
  const recent = (hits.get(ip) ?? []).filter((t) => now - t < 3_600_000);
  if (recent.length >= 10) return apiError(429, "Too many reports from this address; please try again later");
  hits.set(ip, [...recent, now]);
  let b: Record<string, unknown>;
  try { b = await req.json(); } catch { return apiError(400, "invalid JSON"); }
  const type = String(b.report_type ?? ""), description = String(b.description ?? "").trim(), evidence = safeUrl(String(b.evidence_url ?? ""));
  const asset = b.asset_id ? String(b.asset_id) : null;
  if (!TYPES.includes(type)) return apiError(400, `report_type must be one of ${TYPES.join(", ")}`);
  if (description.length < 10 || description.length > 2000) return apiError(400, "description must be 10–2000 characters");
  if (!evidence) return apiError(400, "a supporting evidence URL (http/https) is required");
  if (asset && !/^GBA-\d{7}$/.test(asset)) return apiError(400, "invalid asset id");
  const contact = b.contact ? String(b.contact).slice(0, 200) : null;
  const r = await query("INSERT INTO ops.user_reports (asset_id, report_type, description, evidence_url, contact) VALUES ($1,$2,$3,$4,$5) RETURNING report_id", [asset, type, description, evidence, contact]);
  return json({ ok: true, report_id: r[0].report_id, status: "pending_review", message: "Thank you – your report has been queued for review. It will not be published until verified." }, { status: 201 });
}
