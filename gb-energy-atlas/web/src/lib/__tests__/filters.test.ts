import { describe, expect, it } from "vitest";
import { buildWhere, DEFAULT_CAT, DEFAULT_KIND, DEFAULT_STAGE, filtersToParams, parseFilters, SORTABLE } from "../filters";

const parse = (qs: string) => parseFilters(new URLSearchParams(qs));

describe("parseFilters", () => {
  it("applies the browsing defaults and serialises them back to nothing", () => {
    const f = parse("");
    expect(f.cat).toEqual(DEFAULT_CAT);
    expect(f.stage).toEqual(DEFAULT_STAGE);
    expect(f.kind).toEqual(DEFAULT_KIND);
    expect(f.scope).toBe("gb");
    expect(filtersToParams(f).toString()).toBe("");
  });

  it("round-trips non-default filters through the URL", () => {
    const qs = "tech=wind_onshore%2Cbess&ctry=Scotland&mw0=10&mw1=250&tp=no&q=whitelee&bbox=-5%2C55%2C-3%2C56&stage=operational";
    const f = parse(qs);
    expect(f.tech).toEqual(["wind_onshore", "bess"]);
    expect(f.mw0).toBe(10);
    expect(f.bbox).toEqual([-5, 55, -3, 56]);
    const again = parseFilters(filtersToParams(f));
    expect(again).toEqual(f);
  });

  it("ignores junk numbers, bad bbox and unknown enum values instead of passing them on", () => {
    const f = parse("mw0=abc&mw1=Infinity&bbox=1,2,3&tp=maybe&scope=everything&conflict=no");
    expect(f.mw0).toBeUndefined();
    expect(f.mw1).toBeUndefined();
    expect(f.bbox).toBeUndefined();
    expect(f.tp).toBeUndefined();
    expect(f.scope).toBe("gb");
    expect(f.conflict).toBeUndefined();
  });

  it("an explicit id selection is not subject to the browsing defaults", () => {
    const f = parse("ids=GBA-0000001,GBA-0000002");
    expect(f.scope).toBe("all");
    expect(f.cat).toEqual([]);
    expect(f.stage).toEqual([]);
    expect(f.kind).toEqual([]);
  });

  it("caps list length and query length", () => {
    const many = Array.from({ length: 500 }, (_, i) => `t${i}`).join(",");
    expect(parse(`tech=${many}`).tech).toHaveLength(200);
    expect(parse(`q=${"x".repeat(1000)}`).q).toHaveLength(200);
  });

  it("accepts Next.js style search-param records", () => {
    const f = parseFilters({ tech: ["bess", "hydro"], ctry: "Wales", q: undefined });
    expect(f.tech).toEqual(["bess"]);   // first value only: arrays are not silently merged
    expect(f.ctry).toEqual(["Wales"]);
  });
});

describe("buildWhere", () => {
  it("binds every user value and never interpolates it", () => {
    const evil = "x'); DROP TABLE atlas.assets;--";
    const f = parse(`q=${encodeURIComponent(evil)}&opr=${encodeURIComponent(evil)}&mfr=${encodeURIComponent(evil)}&ctry=${encodeURIComponent(evil)}`);
    const w = buildWhere(f);
    expect(w.sql).not.toContain("DROP TABLE");
    expect(w.sql).not.toContain(evil);
    expect(w.params.some((p) => JSON.stringify(p).includes("DROP TABLE"))).toBe(true);
  });

  it("numbers placeholders from the requested start index with one parameter per placeholder", () => {
    const w = buildWhere(parse("tech=bess&mw0=5&mw1=50"), 4);
    const idx = [...w.sql.matchAll(/\$(\d+)/g)].map((m) => Number(m[1]));
    expect(Math.min(...idx)).toBe(4);
    expect(Math.max(...idx)).toBe(3 + w.params.length);
    expect(new Set(idx).size).toBe(w.params.length);
  });

  it("escapes LIKE wildcards in free text and organisation filters", () => {
    const w = buildWhere(parse("q=100%25_x&opr=a%25b"));
    const likes = w.params.flat().filter((p) => typeof p === "string" && p.startsWith("%")) as string[];
    expect(likes.some((p) => p === "%100\\%\\_x%")).toBe(true);
    expect(likes.some((p) => p === "%a\\%b%")).toBe(true);
  });

  it("restricts to GB scope, default categories and project assets by default", () => {
    const w = buildWhere(parse(""));
    expect(w.sql).toContain("f.in_scope_gb");
    expect(w.sql).toContain("f.category = ANY(");
    expect(w.sql).toContain("f.stage_group = ANY(");
    expect(w.sql).toContain("f.asset_kind = ANY(");
  });

  it("an explicit status overrides the stage group instead of combining with it", () => {
    const w = buildWhere(parse("st=under_construction&stage=operational"));
    expect(w.sql).toContain("f.status_code = ANY(");
    expect(w.sql).not.toContain("f.stage_group");
  });

  it("builds range, turbine-position, support-scheme and bbox conditions", () => {
    const w = buildWhere(parse("mw0=10&tip0=150&tp=no&sup=CfD,none&bbox=-5,55,-3,56"));
    expect(w.sql).toContain("f.installed_capacity_mw >=");
    expect(w.sql).toContain("f.tip_height_m >=");
    expect(w.sql).toContain("NOT f.individual_turbines_known AND f.family = 'wind'");
    expect(w.sql).toContain("f.has_cfd");
    expect(w.sql).toContain("NOT (f.has_cfd OR f.has_ro OR f.has_rego OR f.has_fit)");
    expect(w.sql).toContain("ST_MakeEnvelope");
    expect(w.params).toEqual(expect.arrayContaining([10, 150, -5, 55, -3, 56]));
  });

  it("with scope=all and no other filters is a no-op condition", () => {
    const f = { ...parse("ids=a"), ids: [] as string[] };
    expect(buildWhere(f).sql).toBe("TRUE");
  });

  it("identical URL parameters always yield identical SQL (one source of truth for map, list, stats and export)", () => {
    const qs = "tech=wind_onshore&ctry=Scotland&stage=operational&mw0=10";
    expect(buildWhere(parse(qs))).toEqual(buildWhere(parse(qs)));
  });
});

describe("SORTABLE", () => {
  it("only maps to columns of the read model alias", () => {
    for (const col of Object.values(SORTABLE)) expect(col).toMatch(/^f\.[a-z_]+$/);
  });
});
