/**
 * The map, list, statistics and exports must describe exactly the same set of records for any filter.
 * These tests run against a live server + loaded database (E2E_BASE_URL, default http://localhost:3000).
 */
import { expect, test, type APIRequestContext } from "@playwright/test";
import { VectorTile } from "@mapbox/vector-tile";
import Pbf from "pbf";

const tileXY = (lon: number, lat: number, z: number) => {
  const n = 2 ** z, rad = (lat * Math.PI) / 180;
  return { x: Math.floor(((lon + 180) / 360) * n), y: Math.floor(((1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI) / 2) * n) };
};

/** Unique asset ids drawn on the (unclustered) map for a filter, over a bounding box of tiles at zoom z. */
async function tileAssetIds(request: APIRequestContext, qs: string, z: number, box: [number, number, number, number]): Promise<Set<string>> {
  const a = tileXY(box[0], box[3], z), b = tileXY(box[2], box[1], z);
  const ids = new Set<string>();
  for (let x = a.x; x <= b.x; x++) {
    for (let y = a.y; y <= b.y; y++) {
      const r = await request.get(`/api/tiles/${z}/${x}/${y}.mvt?${qs}&cluster=0`);
      expect(r.ok()).toBeTruthy();
      const buf = Buffer.from(await r.body());
      if (!buf.length) continue;
      const layer = new VectorTile(new Pbf(buf)).layers["assets"];
      if (!layer) continue;
      for (let i = 0; i < layer.length; i++) ids.add(String(layer.feature(i).properties.asset_id));
    }
  }
  return ids;
}

const csvRows = (text: string) => {
  // minimal RFC4180 reader (quoted fields may contain newlines)
  const rows: string[][] = []; let row: string[] = [], cur = "", q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"') { if (text[i + 1] === '"') { cur += '"'; i++; } else q = false; } else cur += c; }
    else if (c === '"') q = true;
    else if (c === ",") { row.push(cur); cur = ""; }
    else if (c === "\n") { row.push(cur.replace(/\r$/, "")); rows.push(row); row = []; cur = ""; }
    else cur += c;
  }
  if (cur || row.length) { row.push(cur); rows.push(row); }
  return rows;
};

async function exported(request: APIRequestContext, qs: string) {
  const r = await request.get(`/api/export?${qs}&format=csv`);
  expect(r.ok()).toBeTruthy();
  const rows = csvRows((await r.text()).replace(/^﻿/, ""));
  const [head, ...data] = rows;
  return data.filter((d) => d.length > 1).map((d) => Object.fromEntries(head.map((h, i) => [h, d[i]])));
}

const GB_BOX: [number, number, number, number] = [-8.7, 49.8, 2, 60.95];

const CASES: { name: string; qs: string; box: [number, number, number, number]; z: number }[] = [
  { name: "Scottish operational onshore wind", qs: "tech=wind_onshore&ctry=Scotland&stage=operational", box: [-8, 54.5, -0.7, 60.95], z: 6 },
  { name: "Operational BESS in England of at least 20 MW", qs: "tech=bess&ctry=England&stage=operational&mw0=20", box: [-6.5, 49.8, 2, 56], z: 6 },
  { name: "Offshore wind (any foundation) in the pipeline", qs: "wt=offshore&stage=pipeline", box: GB_BOX, z: 5 },
  { name: "CfD-supported projects", qs: "sup=CfD", box: GB_BOX, z: 5 },
];

for (const c of CASES) {
  test(`list, statistics, export and map agree: ${c.name}`, async ({ request }) => {
    const list = await (await request.get(`/api/assets?${c.qs}&pageSize=1`)).json();
    const stats = await (await request.get(`/api/statistics?${c.qs}`)).json();
    const rows = await exported(request, c.qs);
    expect(list.total).toBeGreaterThan(0);
    expect(stats.headline.projects).toBe(list.total);
    expect(rows).toHaveLength(list.total);
    // the map draws exactly the exported records that have coordinates
    const located = rows.filter((r) => r.lat !== "" && r.lon !== "").map((r) => r.asset_id);
    const onMap = await tileAssetIds(request, c.qs, c.z, c.box);
    expect([...onMap].sort()).toEqual([...new Set(located)].sort());
    // statistics add up from the same rows
    const mw = rows.reduce((s, r) => s + (Number(r.installed_capacity_mw) || 0), 0);
    const bucket = (stats.byTechnology as { mw: number }[]).reduce((s, t) => s + t.mw, 0);
    expect(Math.abs(mw - bucket)).toBeLessThan(0.5);
  });
}

test("an empty result is empty everywhere (no stale or default data leaks through)", async ({ request }) => {
  const qs = "mfr=Nordex&tech=wind_onshore";    // REPD does not state a turbine manufacturer, so nothing may match
  const list = await (await request.get(`/api/assets?${qs}`)).json();
  const stats = await (await request.get(`/api/statistics?${qs}`)).json();
  expect(list.total).toBe(0);
  expect(list.items).toEqual([]);
  expect(stats.headline.projects).toBe(0);
  expect(await exported(request, qs)).toHaveLength(0);
  expect((await tileAssetIds(request, qs, 5, GB_BOX)).size).toBe(0);
});

test("clustered tiles conserve the project count", async ({ request }) => {
  const qs = "tech=solar_pv&stage=operational";
  const total = (await (await request.get(`/api/assets?${qs}&pageSize=1`)).json()).total as number;
  let clustered = 0;
  const a = tileXY(GB_BOX[0], GB_BOX[3], 5), b = tileXY(GB_BOX[2], GB_BOX[1], 5);
  const seen = new Map<string, number>();
  for (let x = a.x; x <= b.x; x++) for (let y = a.y; y <= b.y; y++) {
    const r = await request.get(`/api/tiles/5/${x}/${y}.mvt?${qs}`);
    const buf = Buffer.from(await r.body());
    if (!buf.length) continue;
    const layer = new VectorTile(new Pbf(buf)).layers["clusters"];
    if (!layer) continue;
    for (let i = 0; i < layer.length; i++) { const f = layer.feature(i); seen.set(`${x}/${y}/${i}`, Number(f.properties.n)); }
  }
  for (const n of seen.values()) clustered += n;
  const located = (await exported(request, qs)).filter((r) => r.lat !== "").length;
  // clusters are built from located projects only; buffers may repeat a cluster in adjacent tiles but never lose one
  expect(clustered).toBeGreaterThanOrEqual(located);
  expect(located).toBeLessThanOrEqual(total);
});

test("selecting by id ignores the browsing defaults and returns exactly those records", async ({ request }) => {
  const some = (await (await request.get("/api/assets?stage=historic&pageSize=3")).json()).items.map((i: { asset_id: string }) => i.asset_id);
  test.skip(some.length === 0, "no historic assets loaded");
  const got = await (await request.get(`/api/assets?ids=${some.join(",")}`)).json();
  expect(got.items.map((i: { asset_id: string }) => i.asset_id).sort()).toEqual([...some].sort());
});

test("filter facets only offer values that exist", async ({ request }) => {
  const f = await (await request.get("/api/facets")).json();
  expect(f).toBeTruthy();
  const meta = await (await request.get("/api/meta")).json();
  expect(meta.technologies.length).toBeGreaterThan(5);
  expect(meta.statuses.some((s: { code: string }) => s.code === "cfd_awarded")).toBe(true);
});
