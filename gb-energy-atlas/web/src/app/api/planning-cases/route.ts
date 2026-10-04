import { NextRequest } from "next/server";
import { query } from "@/lib/db";
import { filtersFrom, intParam, json } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const { where } = filtersFrom(req);
  const sp = req.nextUrl.searchParams;
  const page = intParam(req, "page", 1, 1, 100000), pageSize = intParam(req, "pageSize", 100, 1, 500);
  const n = where.params.length;
  const extra: string[] = [];
  const params = [...where.params];
  if (sp.get("pq")) { params.push(`%${sp.get("pq")!.replace(/[%_\\]/g, "\\$&")}%`); extra.push(`pc.reference ILIKE $${params.length}`); }
  if (sp.get("ref_type")) { params.push(sp.get("ref_type")); extra.push(`pc.ref_type = $${params.length}`); }
  void n;
  const cond = [where.sql, ...extra].join(" AND ");
  const items = await query(`SELECT pc.case_id, pc.asset_id, f.canonical_name, pc.authority, pc.reference, pc.ref_type, pc.application_date, pc.decision_date, pc.decision, pc.stage, pc.url, pc.notes
                             FROM atlas.planning_cases pc JOIN atlas.asset_flat f USING (asset_id) WHERE ${cond}
                             ORDER BY pc.application_date DESC NULLS LAST, pc.case_id LIMIT ${pageSize} OFFSET ${(page - 1) * pageSize}`, params);
  const total = await query(`SELECT count(*)::int AS n FROM atlas.planning_cases pc JOIN atlas.asset_flat f USING (asset_id) WHERE ${cond}`, params);
  return json({ total: total[0].n, page, pageSize, items });
}
