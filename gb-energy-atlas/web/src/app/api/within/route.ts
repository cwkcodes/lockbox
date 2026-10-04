import { NextRequest } from "next/server";
import { query } from "@/lib/db";
import { apiError, filtersFrom, json } from "@/lib/api";
import { summarise } from "@/lib/summarise";

export const dynamic = "force-dynamic";

/** POST { polygon: GeoJSON Polygon } (+ filter params in the query string) – assets inside a user-drawn polygon. */
export async function POST(req: NextRequest) {
  let body: { polygon?: { type?: string; coordinates?: number[][][] } };
  try { body = await req.json(); } catch { return apiError(400, "invalid JSON"); }
  const poly = body.polygon;
  if (!poly || poly.type !== "Polygon" || !Array.isArray(poly.coordinates) || !poly.coordinates[0] || poly.coordinates[0].length < 4 || poly.coordinates[0].length > 2000) return apiError(400, "polygon must be a GeoJSON Polygon with 4–2000 vertices");
  if (!poly.coordinates[0].every((p) => Array.isArray(p) && p.length >= 2 && Number.isFinite(p[0]) && Number.isFinite(p[1]) && Math.abs(p[0]) <= 180 && Math.abs(p[1]) <= 90)) return apiError(400, "invalid coordinates");
  const { where } = filtersFrom(req);
  const n = where.params.length;
  const rows = await query(
    `SELECT f.asset_id, f.canonical_name, f.technology_code, f.technology_label, f.family, f.colour, f.status_code, f.status_label, f.stage_group, f.installed_capacity_mw,
            f.storage_capacity_mwh, f.turbine_count, f.country, f.local_authority, f.lat, f.lon
     FROM atlas.asset_flat f WHERE ${where.sql} AND f.geom IS NOT NULL AND ST_Intersects(f.geom, ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON($${n + 1}), 4326)))
     ORDER BY f.installed_capacity_mw DESC NULLS LAST LIMIT 1000`, [...where.params, JSON.stringify({ type: "Polygon", coordinates: poly.coordinates })]);
  return json({ summary: summarise(rows), truncated: rows.length >= 1000, items: rows });
}
