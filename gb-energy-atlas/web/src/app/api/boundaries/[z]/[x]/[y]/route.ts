import { NextRequest } from "next/server";
import { pool } from "@/lib/db";

export const dynamic = "force-dynamic";

/**
 * ONS Local Authority District boundaries (OGL v3.0) as vector tiles generated from atlas.admin_areas.
 * Used as (a) an optional context overlay and (b) the self-hosted 'Plain' basemap that works with no third-party tile host.
 */
export async function GET(_req: NextRequest, ctx: { params: Promise<{ z: string; x: string; y: string }> }) {
  const { z: zs, x: xs, y: ys } = await ctx.params;
  const z = Number(zs), x = Number(xs), y = Number(ys.replace(/\.mvt$/, ""));
  if (![z, x, y].every(Number.isInteger) || z < 0 || z > 18 || x < 0 || y < 0 || x >= 2 ** z || y >= 2 ** z) return new Response("bad tile", { status: 400 });
  const tolM = (40075016.68 / 2 ** z / 256) * 1.2; // ~1 px at this zoom
  const r = await pool.query(
    `WITH env AS (SELECT ST_TileEnvelope($1, $2, $3) AS g)
     SELECT ST_AsMVT(q, 'lad', 4096, 'geom') AS tile FROM (
       SELECT a.code, a.name, a.country,
              ST_AsMVTGeom(ST_SimplifyPreserveTopology(ST_Transform(a.geom, 3857), $4), env.g, 4096, 32, true) AS geom
       FROM atlas.admin_areas a, env WHERE a.layer = 'lad' AND ST_Transform(a.geom, 3857) && env.g) q WHERE q.geom IS NOT NULL`,
    [z, x, y, tolM]);
  const tile = r.rows[0]?.tile as Buffer | undefined;
  if (!tile || !tile.length) return new Response(null, { status: 204, headers: { "Cache-Control": "public, max-age=3600" } });
  return new Response(new Uint8Array(tile), { headers: { "Content-Type": "application/vnd.mapbox-vector-tile", "Cache-Control": "public, max-age=86400, s-maxage=604800" } });
}
