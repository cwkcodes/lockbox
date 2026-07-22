/**
 * StatMaps Phase 1 API — implements the hot-path read endpoints from
 * statmaps-spec/05-api.md against PostGIS.
 *
 * Design notes (see spec 03-architecture §5, 07-performance §2):
 *  - /values responses are immutable per (layer, year) and carry long
 *    Cache-Control headers — in production a CDN absorbs them.
 *  - The response shape matches what the prototype consumes client-side via
 *    MapLibre feature-state: a small JSON keyed by region.
 *  - Search here is ILIKE-ranked; production adds Typesense (spec 03 §4).
 */
import Fastify from "fastify";
import pg from "pg";

const pool = new pg.Pool({
  connectionString:
    process.env.DATABASE_URL ?? "postgres://statmaps@127.0.0.1:5544/statmaps",
  max: 10,
});

const app = Fastify({ logger: false });

const CACHE_IMMUTABLE = "public, max-age=86400, stale-while-revalidate=604800";

app.get("/v1/health", async () => {
  const r = await pool.query("SELECT count(*)::int AS n FROM datasets");
  return { ok: true, datasets: r.rows[0].n };
});

app.get<{ Querystring: { q?: string; limit?: string } }>(
  "/v1/search",
  async (req) => {
    const q = (req.query.q ?? "").trim();
    if (!q) return { layers: [] };
    const r = await pool.query(
      `SELECT l.layer_id, l.title, d.category, d.unit, l.geometry_kind
         FROM layers l JOIN datasets d USING (dataset_id)
        WHERE l.title ILIKE '%' || $1 || '%' OR d.category ILIKE '%' || $1 || '%'
        ORDER BY position(lower($1) in lower(l.title)) NULLS LAST, l.popularity DESC, l.title
        LIMIT $2`,
      [q, Math.min(Number(req.query.limit ?? 20), 100)],
    );
    return { layers: r.rows };
  },
);

app.get<{ Querystring: { category?: string } }>("/v1/layers", async (req) => {
  const r = await pool.query(
    `SELECT l.layer_id, l.title, d.category, d.unit, l.geometry_kind,
            d.time_min, d.time_max
       FROM layers l JOIN datasets d USING (dataset_id)
      WHERE $1::text IS NULL OR d.category = $1
      ORDER BY d.category, l.title`,
    [req.query.category ?? null],
  );
  return { layers: r.rows };
});

app.get<{ Params: { id: string } }>("/v1/layers/:id", async (req, reply) => {
  const r = await pool.query(
    `SELECT l.layer_id, l.title, l.geometry_kind, l.default_style,
            d.description, d.unit, d.category, d.time_min, d.time_max,
            s.name AS source_name, s.url AS source_url,
            li.name AS licence, li.allow_export, li.allow_api
       FROM layers l
       JOIN datasets d USING (dataset_id)
       JOIN sources s USING (source_id)
       JOIN licences li ON li.licence_id = d.licence_id
      WHERE l.layer_id = $1`,
    [req.params.id],
  );
  if (!r.rowCount) return reply.code(404).send({ error: "layer not found" });
  return r.rows[0];
});

/** The hot path: choropleth values for one layer at one year. */
app.get<{ Params: { id: string }; Querystring: { t?: string } }>(
  "/v1/layers/:id/values",
  async (req, reply) => {
    const year = Number(req.query.t);
    if (!Number.isInteger(year))
      return reply.code(400).send({ error: "t=<year> is required" });
    const meta = await pool.query(
      `SELECT d.unit FROM layers l JOIN datasets d USING (dataset_id) WHERE l.layer_id = $1`,
      [req.params.id],
    );
    if (!meta.rowCount) return reply.code(404).send({ error: "layer not found" });
    const r = await pool.query(
      `SELECT replace(region_id, 'iso:', '') AS iso, value
         FROM observations WHERE dataset_id = $1 AND year = $2`,
      [req.params.id, year],
    );
    const values: Record<string, number> = {};
    for (const row of r.rows) values[row.iso] = row.value;
    reply.header("Cache-Control", CACHE_IMMUTABLE);
    return { layer: req.params.id, t: year, unit: meta.rows[0].unit, n: r.rowCount, values };
  },
);

app.get<{ Params: { id: string }; Querystring: { region?: string } }>(
  "/v1/layers/:id/series",
  async (req, reply) => {
    if (!req.query.region)
      return reply.code(400).send({ error: "region=<ISO3> is required" });
    const r = await pool.query(
      `SELECT year, value FROM observations
        WHERE dataset_id = $1 AND region_id = 'iso:' || $2 ORDER BY year`,
      [req.params.id, req.query.region],
    );
    reply.header("Cache-Control", CACHE_IMMUTABLE);
    return { layer: req.params.id, region: req.query.region, series: r.rows };
  },
);

app.get<{ Params: { id: string } }>("/v1/layers/:id/timeline", async (req) => {
  const r = await pool.query(
    `SELECT year, count(*)::int AS regions FROM observations
      WHERE dataset_id = $1 GROUP BY year ORDER BY year`,
    [req.params.id],
  );
  return { layer: req.params.id, steps: r.rows };
});

app.get<{ Params: { id: string }; Querystring: { t?: string } }>(
  "/v1/regions/:id/profile",
  async (req, reply) => {
    const year = Number(req.query.t ?? new Date().getFullYear() - 1);
    const region = await pool.query(
      `SELECT region_id, name, iso_a3 FROM regions WHERE region_id = 'iso:' || $1 OR region_id = $1`,
      [req.params.id],
    );
    if (!region.rowCount) return reply.code(404).send({ error: "region not found" });
    const r = await pool.query(
      `SELECT o.dataset_id, d.title, d.unit, o.value, o.year
         FROM observations o JOIN datasets d USING (dataset_id)
        WHERE o.region_id = $1 AND o.year = (
          SELECT max(year) FROM observations oi
           WHERE oi.dataset_id = o.dataset_id AND oi.region_id = o.region_id AND oi.year <= $2)
        ORDER BY d.category, d.title`,
      [region.rows[0].region_id, year],
    );
    return { region: region.rows[0], asOf: year, indicators: r.rows };
  },
);

/** Point features in a bounding box, optionally filtered by year. */
app.get<{
  Params: { id: string };
  Querystring: { bbox?: string; year?: string; limit?: string };
}>("/v1/features/:id", async (req, reply) => {
  const bbox = (req.query.bbox ?? "-180,-90,180,90").split(",").map(Number);
  if (bbox.length !== 4 || bbox.some((n) => !Number.isFinite(n)))
    return reply.code(400).send({ error: "bbox=minLon,minLat,maxLon,maxLat" });
  const year = req.query.year ? Number(req.query.year) : null;
  const r = await pool.query(
    `SELECT ST_X(geom) AS lon, ST_Y(geom) AS lat, year, properties
       FROM features
      WHERE dataset_id = $1
        AND geom && ST_MakeEnvelope($2, $3, $4, $5, 4326)
        AND ($6::int IS NULL OR year = $6)
      LIMIT $7`,
    [req.params.id, ...bbox, year, Math.min(Number(req.query.limit ?? 5000), 20000)],
  );
  reply.header("Cache-Control", CACHE_IMMUTABLE);
  return {
    type: "FeatureCollection",
    features: r.rows.map((f) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [f.lon, f.lat] },
      properties: { ...f.properties, year: f.year },
    })),
  };
});

/**
 * Live layer relay (spec 07-performance §6): the API polls the upstream feed
 * and serves it with a short cache so thousands of clients produce one
 * upstream request per minute. Same pattern extends to NASA FIRMS wildfires
 * and ADS-B flights (those upstreams require API keys).
 */
let liveQuakes: { at: number; body: unknown } | null = null;
app.get("/v1/live/earthquakes", async (_req, reply) => {
  if (!liveQuakes || Date.now() - liveQuakes.at > 60_000) {
    const r = await fetch(
      "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
    );
    liveQuakes = { at: Date.now(), body: await r.json() };
  }
  reply.header("Cache-Control", "public, max-age=60");
  return liveQuakes.body;
});

const port = Number(process.env.PORT ?? 8787);
app.listen({ port, host: "0.0.0.0" }).then(() => {
  console.log(`statmaps api listening on :${port}`);
});
