import { NextRequest } from "next/server";
import { query } from "@/lib/db";
import { intParam, json } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  const role = sp.get("role");
  const q = sp.get("q");
  const page = intParam(req, "page", 1, 1, 10000), pageSize = intParam(req, "pageSize", 50, 1, 200);
  const params: unknown[] = [];
  const cond: string[] = ["a.is_published", "a.in_scope_gb", "a.asset_kind = 'project'"];
  if (role) { params.push(role); cond.push(`ao.role = $${params.length}`); }
  if (q) { params.push(`%${q.replace(/[%_\\]/g, "\\$&")}%`); cond.push(`(o.canonical_name ILIKE $${params.length} OR o.name_norm ILIKE $${params.length})`); }
  const items = await query(
    `SELECT o.org_id, o.canonical_name, o.aliases, count(DISTINCT a.asset_id)::int AS assets,
            coalesce(sum(a.installed_capacity_mw) FILTER (WHERE s.stage_group='operational'), 0)::float AS operational_mw,
            coalesce(sum(a.installed_capacity_mw) FILTER (WHERE s.stage_group='pipeline'), 0)::float AS pipeline_mw,
            array_agg(DISTINCT ao.role) AS roles
     FROM atlas.organisations o JOIN atlas.asset_organisations ao USING (org_id) JOIN atlas.assets a USING (asset_id) JOIN atlas.status s ON s.code = a.status_code
     WHERE ${cond.join(" AND ")} GROUP BY o.org_id ORDER BY operational_mw DESC, assets DESC LIMIT ${pageSize} OFFSET ${(page - 1) * pageSize}`, params);
  return json({ page, pageSize, items });
}
