import { NextRequest } from "next/server";
import { query } from "@/lib/db";
import { filtersFrom, intParam, json } from "@/lib/api";

export const dynamic = "force-dynamic";

/** Individual turbine units. Only verified positions exist here: nothing is derived from site centroids. */
export async function GET(req: NextRequest) {
  const { where } = filtersFrom(req);
  const page = intParam(req, "page", 1, 1, 100000), pageSize = intParam(req, "pageSize", 100, 1, 1000);
  const [items, total, withoutPositions] = await Promise.all([
    query(`SELECT t.unit_id, t.asset_id, t.asset_name, t.unit_code, t.manufacturer, t.model, t.model_status, t.rated_mw, t.hub_height_m, t.rotor_diameter_m, t.tip_height_m,
                  t.status_code, t.commissioning_year, t.lat, t.lon, t.bng_e, t.bng_n, t.coordinate_class, t.coordinate_accuracy_m, t.country, t.local_authority
           FROM atlas.turbine_flat t JOIN atlas.asset_flat f USING (asset_id) WHERE ${where.sql}
           ORDER BY t.asset_name, t.unit_code LIMIT ${pageSize} OFFSET ${(page - 1) * pageSize}`, where.params),
    query(`SELECT count(*)::int AS n FROM atlas.turbine_flat t JOIN atlas.asset_flat f USING (asset_id) WHERE ${where.sql}`, where.params),
    query(`SELECT count(*)::int AS wind_assets, coalesce(sum(turbine_count),0)::int AS turbines_reported FROM atlas.asset_flat f WHERE ${where.sql} AND f.family='wind'`, where.params),
  ]);
  return json({ total: total[0].n, page, pageSize, items, coverage: { ...withoutPositions[0], positions_verified: total[0].n,
    statement: total[0].n === 0 ? "Individual turbine coordinates not verified for any project in the current database; only site reference points are available." : undefined } });
}
