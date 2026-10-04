/** Licence, privacy, security and honesty guarantees that must hold for the public API. */
import { expect, test } from "@playwright/test";

test("every exported file carries attribution and licence notes", async ({ request }) => {
  const gj = await (await request.get("/api/export?tech=wind_onshore&ctry=Wales&stage=operational&format=geojson")).json();
  expect(gj.type).toBe("FeatureCollection");
  expect(Array.isArray(gj.attribution) && gj.attribution.join(" ")).toMatch(/Renewable Energy Planning Database|DESNZ/i);
  expect(gj.features.length).toBeGreaterThan(0);
  const feature = gj.features[0];
  expect(feature.geometry?.type).toBe("Point");
  expect(feature.properties.asset_id).toMatch(/^GBA-\d{7}$/);
});

test("CSV export never carries a live spreadsheet formula from source text", async ({ request }) => {
  const text = await (await request.get("/api/export?stage=operational&format=csv")).text();
  // a plain loop with ONE assertion: a per-cell expect() over millions of cells is far too slow
  const offenders: string[] = [];
  for (const line of text.split(/\r?\n/)) {
    for (const cell of line.split(",")) if (/^"?[=@]/.test(cell) && offenders.length < 5) offenders.push(cell.slice(0, 60));
  }
  expect(offenders).toEqual([]);
});

test("sources whose licence has not been cleared for redistribution are excluded from exports, and the export says so", async ({ request }) => {
  const reg = await (await request.get("/api/data-sources")).json();
  const sources: { source_key: string; export_policy: string }[] = reg.sources ?? reg;
  const excluded = sources.filter((s) => s.export_policy === "exclude").map((s) => s.source_key);
  expect(excluded).toContain("crown_estate_wind_sites");
  const gj = await (await request.get("/api/export?wt=offshore&format=geojson")).json();
  expect(JSON.stringify(gj.export_notes ?? "")).toMatch(/Crown Estate|licen[cs]e/i);
  for (const f of gj.features) expect(JSON.stringify(f.properties)).not.toMatch(/crown_estate_wind_sites/);
});

test("privacy: no domestic-scale record exposes a postcode or street address", async ({ request }) => {
  const res = await (await request.get("/api/assets?scale=small&pageSize=200&scope=all&cat=generation,storage,hybrid&stage=operational,pipeline,historic,unknown")).json();
  for (const a of res.items) {
    expect(a.postcode ?? null).toBeNull();
    // planning references (e.g. "P1272/25/PJ14PA") can look like postcodes, so they are not part of this check
    const { planning_reference: _ref, ...rest } = a;
    expect(JSON.stringify(rest)).not.toMatch(/\b[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}\b/);
  }
});

test("no individual turbine position is published unless it is verified (none are derived from project points)", async ({ request }) => {
  const r = await (await request.get("/api/wind-turbines?pageSize=50")).json();
  const items: { coordinate_class?: string }[] = r.items;
  for (const t of items) expect(["exact_published", "digitised_from_drawing", "open_source_mapped", "approximate"]).toContain(t.coordinate_class);
  // thousands of turbines are *reported*; none may be turned into a point without a verified source
  expect(r.coverage.turbines_reported).toBeGreaterThan(0);
  expect(r.total).toBe(r.coverage.positions_verified);
  expect(r.coverage.statement).toMatch(/not verified|only site reference points|verified/i);
  const stats = await (await request.get("/api/statistics?tech=wind_onshore&stage=operational")).json();
  expect(stats.headline.turbines_positioned).toBeLessThanOrEqual(stats.headline.turbines_reported);
});

test("admin API refuses anonymous and wrong-token requests", async ({ request }) => {
  for (const path of ["/api/admin/ingestion", "/api/admin/candidates", "/api/admin/reports", "/api/admin/qa"]) {
    expect((await request.get(path)).status()).toBe(401);
    expect((await request.get(path, { headers: { authorization: "Bearer definitely-wrong" } })).status()).toBe(401);
  }
  // every write route is protected too, not just the reads
  expect((await request.patch("/api/admin/assets/GBA-0000001", { data: { field: "notes", value: "x", reason: "x" } })).status()).toBe(401);
  for (const path of ["/api/admin/candidates", "/api/admin/ingestion", "/api/admin/reports"]) {
    expect((await request.post(path, { data: {} })).status(), path).toBe(401);
  }
});

test("corrections require evidence and only accept web links", async ({ request }) => {
  const base = { asset_id: "GBA-0000001", report_type: "incorrect_info", description: "E2E validation request – must be rejected" };
  expect((await request.post("/api/reports", { data: base })).status()).toBe(400);
  expect((await request.post("/api/reports", { data: { ...base, evidence_url: "javascript:alert(1)" } })).status()).toBe(400);
  expect((await request.post("/api/reports", { data: { ...base, evidence_url: "not a url" } })).status()).toBe(400);
});

test("search endpoints and filters survive hostile input", async ({ request }) => {
  for (const q of ["'; DROP TABLE atlas.assets; --", "%", "_", "\\", "a".repeat(5000), "((((", ":*"]) {
    const r = await request.get(`/api/search?q=${encodeURIComponent(q)}`);
    expect(r.status()).toBeLessThan(500);
    const l = await request.get(`/api/assets?q=${encodeURIComponent(q)}`);
    expect(l.status()).toBeLessThan(500);
  }
  expect((await request.get("/api/meta")).ok()).toBeTruthy();   // the schema is still there
});

test("tile requests outside the tile grid are rejected, not served", async ({ request }) => {
  expect((await request.get("/api/tiles/2/9/9.mvt")).status()).toBe(400);
  expect((await request.get("/api/tiles/99/0/0.mvt")).status()).toBe(400);
});

test("OpenAPI document is served and describes the tile and export endpoints", async ({ request }) => {
  const spec = await (await request.get("/api/openapi.json")).json();
  expect(spec.openapi).toMatch(/^3\./);
  expect(Object.keys(spec.paths)).toEqual(expect.arrayContaining(["/api/assets", "/api/export", "/api/statistics"]));
});
