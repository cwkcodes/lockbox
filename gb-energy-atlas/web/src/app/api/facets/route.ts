import { query } from "@/lib/db";
import { json } from "@/lib/api";

export const dynamic = "force-dynamic";

/** Option lists with counts for the filter UI (computed over the GB-scope project base, not the current selection). */
export async function GET() {
  const base = "FROM atlas.asset_flat f WHERE f.in_scope_gb AND f.asset_kind = 'project'";
  const top = (expr: string, n: number, extra = "") => query(`SELECT ${expr} AS value, count(*)::int AS n ${base} ${extra} GROUP BY 1 ORDER BY n DESC LIMIT ${n}`);
  const [tech, status, country, region, la, dno, pa, mfr, model, conf, src, dev, own, opr, planYears, commYears] = await Promise.all([
    query(`SELECT technology_code AS value, max(technology_label) AS label, max(family) AS family, max(category) AS category, count(*)::int AS n ${base} GROUP BY 1 ORDER BY n DESC`),
    query(`SELECT status_code AS value, max(status_label) AS label, max(stage_group) AS stage_group, count(*)::int AS n ${base} GROUP BY 1 ORDER BY n DESC`),
    top("country", 10, "AND country IS NOT NULL"), top("region", 30, "AND region IS NOT NULL"), top("local_authority", 400, "AND local_authority IS NOT NULL"),
    top("dno", 20, "AND dno IS NOT NULL"), top("planning_authority", 300, "AND planning_authority IS NOT NULL"),
    top("turbine_manufacturer", 50, "AND turbine_manufacturer IS NOT NULL"), top("turbine_model", 100, "AND turbine_model IS NOT NULL"),
    top("confidence", 5),
    query(`SELECT k AS value, count(*)::int AS n FROM atlas.asset_flat f, unnest(f.source_keys) k WHERE f.in_scope_gb AND f.asset_kind='project' GROUP BY 1 ORDER BY n DESC`),
    query(`SELECT d AS value, count(*)::int AS n FROM atlas.asset_flat f, unnest(f.developers) d WHERE f.in_scope_gb AND f.asset_kind='project' GROUP BY 1 ORDER BY n DESC LIMIT 200`),
    query(`SELECT d AS value, count(*)::int AS n FROM atlas.asset_flat f, unnest(f.owners) d WHERE f.in_scope_gb AND f.asset_kind='project' GROUP BY 1 ORDER BY n DESC LIMIT 200`),
    query(`SELECT d AS value, count(*)::int AS n FROM atlas.asset_flat f, unnest(f.operators) d WHERE f.in_scope_gb AND f.asset_kind='project' GROUP BY 1 ORDER BY n DESC LIMIT 300`),
    query(`SELECT min(planning_year)::int AS min, max(planning_year)::int AS max ${base}`),
    query(`SELECT min(commissioning_year)::int AS min, max(commissioning_year)::int AS max ${base}`),
  ]);
  return json({ technology: tech, status, country, region, localAuthority: la, dno, planningAuthority: pa, manufacturer: mfr, model, confidence: conf,
                source: src, developer: dev, owner: own, operator: opr, planningYears: planYears[0], commissioningYears: commYears[0] }, { cache: "public, max-age=120" });
}
