import { NextRequest } from "next/server";
import { query } from "@/lib/db";
import { apiError, filtersFrom, intParam, json } from "@/lib/api";
import { bearingDeg, compass } from "@/lib/geo";
import { summarise } from "@/lib/summarise";

export const dynamic = "force-dynamic";

/** Assets within a radius of a point, with distance, bearing and a capacity/turbine summary. Filters apply. */
export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  const lat = Number(sp.get("lat")), lon = Number(sp.get("lon"));
  const radius = Math.min(Number(sp.get("radius_m")) || 10_000, 200_000);
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || lat < 40 || lat > 70 || lon < -15 || lon > 10) return apiError(400, "lat/lon required (WGS84, UK extent)");
  const { where } = filtersFrom(req);
  const n = where.params.length;
  const limit = intParam(req, "limit", 300, 1, 1000);
  const rows = await query(
    `SELECT f.asset_id, f.canonical_name, f.technology_code, f.technology_label, f.family, f.colour, f.status_code, f.status_label, f.stage_group, f.installed_capacity_mw,
            f.storage_capacity_mwh, f.turbine_count, f.country, f.local_authority, f.lat, f.lon, f.coordinate_accuracy,
            ST_Distance(f.geom::geography, ST_SetSRID(ST_MakePoint($${n + 1}, $${n + 2}), 4326)::geography) AS distance_m
     FROM atlas.asset_flat f WHERE ${where.sql} AND f.geom IS NOT NULL
       AND ST_DWithin(f.geom::geography, ST_SetSRID(ST_MakePoint($${n + 1}, $${n + 2}), 4326)::geography, $${n + 3})
     ORDER BY distance_m LIMIT ${limit}`, [...where.params, lon, lat, radius]);
  const items = rows.map((r) => ({ ...r, distance_m: Math.round(Number(r.distance_m)), bearing_deg: Math.round(bearingDeg(lat, lon, Number(r.lat), Number(r.lon))), compass: compass(bearingDeg(lat, lon, Number(r.lat), Number(r.lon))) }));
  return json({ center: { lat, lon }, radius_m: radius, summary: summarise(items), truncated: items.length >= limit, items });
}
