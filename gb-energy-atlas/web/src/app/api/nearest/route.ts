import { NextRequest } from "next/server";
import { query } from "@/lib/db";
import { apiError, filtersFrom, intParam, json } from "@/lib/api";
import { bearingDeg, compass } from "@/lib/geo";

export const dynamic = "force-dynamic";

/** Nearest assets (kind=asset) or nearest verified wind-turbine positions (kind=turbine). */
export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  const lat = Number(sp.get("lat")), lon = Number(sp.get("lon"));
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return apiError(400, "lat/lon required");
  const k = intParam(req, "n", 5, 1, 50);
  const { where } = filtersFrom(req);
  const n = where.params.length;
  const kind = sp.get("kind") === "turbine" ? "turbine" : "asset";
  const rows = kind === "asset"
    ? await query(`SELECT f.asset_id, f.canonical_name, f.technology_label, f.status_label, f.installed_capacity_mw, f.lat, f.lon,
                          ST_Distance(f.geom::geography, ST_SetSRID(ST_MakePoint($${n + 1}, $${n + 2}), 4326)::geography) AS distance_m
                   FROM atlas.asset_flat f WHERE ${where.sql} AND f.geom IS NOT NULL ORDER BY f.geom <-> ST_SetSRID(ST_MakePoint($${n + 1}, $${n + 2}), 4326) LIMIT ${k}`, [...where.params, lon, lat])
    : await query(`SELECT t.unit_id, t.asset_id, t.unit_code, t.asset_name AS canonical_name, t.manufacturer, t.model, t.lat, t.lon, t.coordinate_class,
                          ST_Distance(t.geom::geography, ST_SetSRID(ST_MakePoint($${n + 1}, $${n + 2}), 4326)::geography) AS distance_m
                   FROM atlas.turbine_flat t JOIN atlas.asset_flat f USING (asset_id) WHERE ${where.sql} ORDER BY t.geom <-> ST_SetSRID(ST_MakePoint($${n + 1}, $${n + 2}), 4326) LIMIT ${k}`, [...where.params, lon, lat]);
  const items = rows.map((r) => ({ ...r, distance_m: Math.round(Number(r.distance_m)), bearing_deg: Math.round(bearingDeg(lat, lon, Number(r.lat), Number(r.lon))), compass: compass(bearingDeg(lat, lon, Number(r.lat), Number(r.lon))) }));
  return json({ kind, items, note: kind === "turbine" && !items.length ? "No individual turbine positions have been verified yet; the platform never infers turbine positions from site centroids." : undefined });
}
