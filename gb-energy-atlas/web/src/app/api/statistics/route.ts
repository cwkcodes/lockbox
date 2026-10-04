import { NextRequest } from "next/server";
import { query } from "@/lib/db";
import { filtersFrom, json } from "@/lib/api";

export const dynamic = "force-dynamic";

/** Headline statistics for exactly the records the current filters select. */
export async function GET(req: NextRequest) {
  const { where } = filtersFrom(req);
  const base = `FROM atlas.asset_flat f WHERE ${where.sql}`;
  const [head, byTech, byStatus, byCountry, byDeveloper, byMfr, byYear, byLa] = await Promise.all([
    query(`SELECT count(*)::int AS projects,
                  coalesce(sum(installed_capacity_mw) FILTER (WHERE stage_group = 'operational'), 0)::float AS operational_mw,
                  coalesce(sum(installed_capacity_mw) FILTER (WHERE stage_group = 'pipeline'), 0)::float AS pipeline_mw,
                  coalesce(sum(installed_capacity_mw) FILTER (WHERE family = 'storage'), 0)::float AS storage_mw,
                  coalesce(sum(storage_capacity_mwh), 0)::float AS storage_mwh,
                  count(storage_capacity_mwh) FILTER (WHERE family = 'storage')::int AS storage_with_mwh,
                  coalesce(sum(turbine_count) FILTER (WHERE family = 'wind'), 0)::int AS turbines_reported,
                  coalesce(sum(verified_turbine_positions), 0)::int AS turbines_positioned,
                  coalesce(avg(installed_capacity_mw), 0)::float AS avg_mw,
                  count(*) FILTER (WHERE installed_capacity_mw IS NULL)::int AS without_capacity,
                  count(*) FILTER (WHERE has_conflict)::int AS with_conflicts
           ${base}`, where.params),
    query(`SELECT technology_code AS key, max(technology_label) AS label, max(colour) AS colour, count(*)::int AS n, coalesce(sum(installed_capacity_mw),0)::float AS mw,
                  coalesce(sum(installed_capacity_mw) FILTER (WHERE stage_group='operational'),0)::float AS operational_mw
           ${base} GROUP BY 1 ORDER BY mw DESC`, where.params),
    query(`SELECT status_code AS key, max(status_label) AS label, max(stage_group) AS stage_group, count(*)::int AS n, coalesce(sum(installed_capacity_mw),0)::float AS mw
           ${base} GROUP BY 1 ORDER BY n DESC`, where.params),
    query(`SELECT coalesce(country, 'Not stated') AS key, count(*)::int AS n, coalesce(sum(installed_capacity_mw),0)::float AS mw,
                  coalesce(sum(installed_capacity_mw) FILTER (WHERE stage_group='operational'),0)::float AS operational_mw
           ${base} GROUP BY 1 ORDER BY mw DESC`, where.params),
    query(`SELECT d AS key, count(*)::int AS n, coalesce(sum(installed_capacity_mw),0)::float AS mw
           FROM atlas.asset_flat f, LATERAL unnest(CASE WHEN cardinality(f.developers) > 0 THEN f.operators || f.developers ELSE f.operators END) d
           WHERE ${where.sql} GROUP BY 1 ORDER BY mw DESC LIMIT 12`, where.params),
    query(`SELECT coalesce(turbine_manufacturer, 'Not publicly identified') AS key, count(*)::int AS n, coalesce(sum(installed_capacity_mw),0)::float AS mw,
                  coalesce(sum(turbine_count),0)::int AS turbines
           ${base} AND family = 'wind' GROUP BY 1 ORDER BY mw DESC LIMIT 12`, where.params),
    query(`SELECT commissioning_year AS key, count(*)::int AS n, coalesce(sum(installed_capacity_mw),0)::float AS mw, max(family) AS fam
           ${base} AND commissioning_year IS NOT NULL AND commissioning_year >= 1990 GROUP BY 1 ORDER BY 1`, where.params),
    query(`SELECT CASE WHEN is_offshore THEN 'Offshore (no local authority)' ELSE coalesce(local_authority, 'Not derived') END AS key, count(*)::int AS n, coalesce(sum(installed_capacity_mw),0)::float AS mw
           ${base} GROUP BY 1 ORDER BY mw DESC LIMIT 15`, where.params),
  ]);
  const byYearTech = await query(
    `SELECT commissioning_year AS year, family, coalesce(sum(installed_capacity_mw),0)::float AS mw
     ${base} AND commissioning_year IS NOT NULL AND commissioning_year >= 1995 AND stage_group = 'operational' GROUP BY 1,2 ORDER BY 1`, where.params);
  return json({ headline: head[0], byTechnology: byTech, byStatus, byCountry, byDeveloper, byManufacturer: byMfr, byYear, byYearTech, byLocalAuthority: byLa });
}
