import { NextRequest } from "next/server";
import { pool } from "@/lib/db";
import { buildWhere, parseFilters } from "@/lib/filters";

export const dynamic = "force-dynamic";
const CLUSTER_MAX_ZOOM = 7;

/**
 * Vector tiles generated in PostGIS (ST_AsMVT) from the same filter set the table/statistics use.
 * Layers: clusters (z<=7, grid clusters) | assets (points) | lease_areas (polygons) | turbines (verified positions only).
 */
export async function GET(req: NextRequest, ctx: { params: Promise<{ z: string; x: string; y: string }> }) {
  const { z: zs, x: xs, y: ys } = await ctx.params;
  const z = Number(zs), x = Number(xs), y = Number(ys.replace(/\.mvt$/, ""));
  if (![z, x, y].every(Number.isInteger) || z < 0 || z > 22 || x < 0 || y < 0 || x >= 2 ** z || y >= 2 ** z) return new Response("bad tile", { status: 400 });

  const sp = req.nextUrl.searchParams;
  const filters = parseFilters(sp);
  const useCluster = sp.get("cluster") !== "0" && z <= CLUSTER_MAX_ZOOM;
  const pointWhere = buildWhere(filters, 4);
  // lease polygons are shown for projects that have one, and for lease-only records, so the record-kind filter is not applied
  const polyFilters = { ...filters, kind: ["project", "lease_area"] };
  const polyWhere = buildWhere(polyFilters, 4);

  const env = "ST_TileEnvelope($1, $2, $3)";
  const buffers: Buffer[] = [];
  const client = await pool.connect();
  try {
    if (useCluster) {
      const q = `
        WITH env AS (SELECT ${env} AS g),
        cell AS (SELECT 40075016.68 / power(2, $1::int) / 8.0 AS size),
        pts AS (SELECT f.asset_id, f.geom_3857, f.technology_code, f.family, COALESCE(f.installed_capacity_mw, 0) AS mw
                FROM atlas.asset_flat f, env, cell
                WHERE f.geom_3857 && ST_Expand(env.g, cell.size * 2) AND ${pointWhere.sql}),
        grid AS (SELECT ST_SnapToGrid(geom_3857, (SELECT size FROM cell)) AS c, count(*) AS n, sum(mw) AS mw,
                        avg(ST_X(geom_3857)) AS cx, avg(ST_Y(geom_3857)) AS cy,
                        mode() WITHIN GROUP (ORDER BY family) AS top_family, mode() WITHIN GROUP (ORDER BY technology_code) AS top_tech,
                        min(asset_id) AS asset_id
                 FROM pts GROUP BY 1)
        SELECT ST_AsMVT(q, 'clusters', 4096, 'geom') AS tile FROM (
          SELECT n::int, round(mw)::int AS mw, top_family, top_tech, CASE WHEN n = 1 THEN asset_id END AS asset_id,
                 ST_AsMVTGeom(ST_SetSRID(ST_MakePoint(cx, cy), 3857), env.g, 4096, 64, true) AS geom
          FROM grid, env) q WHERE q.geom IS NOT NULL`;
      const r = await client.query(q, [z, x, y, ...pointWhere.params]);
      if (r.rows[0]?.tile?.length) buffers.push(r.rows[0].tile);
    } else {
      const q = `
        WITH env AS (SELECT ${env} AS g)
        SELECT ST_AsMVT(q, 'assets', 4096, 'geom') AS tile FROM (
          SELECT f.asset_id, f.technology_code, f.family, f.status_code, f.stage_group, f.status_pattern,
                 COALESCE(f.installed_capacity_mw, 0)::float AS mw, f.canonical_name AS name, f.confidence,
                 ST_AsMVTGeom(f.geom_3857, env.g, 4096, 64, true) AS geom
          FROM atlas.asset_flat f, env
          WHERE f.geom_3857 && env.g AND ${pointWhere.sql}) q WHERE q.geom IS NOT NULL`;
      const r = await client.query(q, [z, x, y, ...pointWhere.params]);
      if (r.rows[0]?.tile?.length) buffers.push(r.rows[0].tile);
    }
    if (z >= 4) {
      const tol = 360 / 2 ** z / 256 / 2;
      const q = `
        WITH env AS (SELECT ${env} AS g)
        SELECT ST_AsMVT(q, 'lease_areas', 4096, 'geom') AS tile FROM (
          SELECT g.asset_id, f.canonical_name AS name, f.technology_code, f.status_code, f.stage_group, g.label AS lease_label,
                 ST_AsMVTGeom(ST_Transform(ST_SimplifyPreserveTopology(g.geom, ${tol}), 3857), env.g, 4096, 64, true) AS geom
          FROM atlas.asset_geometries g JOIN atlas.asset_flat f USING (asset_id), env
          WHERE g.geom_type = 'lease_area' AND ST_Transform(g.geom, 3857) && env.g AND ${polyWhere.sql}) q WHERE q.geom IS NOT NULL`;
      const r = await client.query(q, [z, x, y, ...polyWhere.params]);
      if (r.rows[0]?.tile?.length) buffers.push(r.rows[0].tile);
    }
    if (z >= 9) {
      const q = `
        WITH env AS (SELECT ${env} AS g)
        SELECT ST_AsMVT(q, 'turbines', 4096, 'geom') AS tile FROM (
          SELECT t.unit_id, t.asset_id, t.unit_code, t.rated_mw::float AS mw, t.manufacturer, t.model, t.hub_height_m::float AS hub, t.rotor_diameter_m::float AS rotor,
                 t.tip_height_m::float AS tip, t.coordinate_class, t.asset_name,
                 ST_AsMVTGeom(t.geom_3857, env.g, 4096, 64, true) AS geom
          FROM atlas.turbine_flat t JOIN atlas.asset_flat f USING (asset_id), env
          WHERE t.geom_3857 && env.g AND ${pointWhere.sql}) q WHERE q.geom IS NOT NULL`;
      const r = await client.query(q, [z, x, y, ...pointWhere.params]);
      if (r.rows[0]?.tile?.length) buffers.push(r.rows[0].tile);
    }
  } finally {
    client.release();
  }
  if (!buffers.length) return new Response(null, { status: 204, headers: { "Cache-Control": "public, max-age=60" } });
  // concatenated Tile messages are a valid Tile (repeated `layers` field)
  return new Response(new Uint8Array(Buffer.concat(buffers)), {
    headers: { "Content-Type": "application/vnd.mapbox-vector-tile", "Cache-Control": "public, max-age=60, s-maxage=300" },
  });
}
