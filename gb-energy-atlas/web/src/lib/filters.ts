/**
 * The ONE filter implementation. Tiles, list, statistics, facets, export and the proximity tools all build their
 * WHERE clause here, from the same URL parameters, so the map, table, statistics and exports always describe the
 * same set of records. Only allow-listed columns are interpolated; every value is a bound parameter.
 */
export type Multi = string[];

export interface Filters {
  q: string;
  cat: Multi; fam: Multi; tech: Multi; wt: Multi;
  stage: Multi; st: Multi;
  ctry: Multi; reg: Multi; la: Multi;
  mw0?: number; mw1?: number; mwh0?: number; mwh1?: number; h0?: number; h1?: number;
  dno: Multi; conn: Multi; kv0?: number; kv1?: number; cs: Multi;
  dev: Multi; own: Multi; opr: Multi; mfr: Multi; mdl: Multi;
  nt0?: number; nt1?: number; hub0?: number; hub1?: number; rot0?: number; rot1?: number; tip0?: number; tip1?: number;
  cy0?: number; cy1?: number; py0?: number; py1?: number;
  sup: Multi; pa: Multi; src: Multi; conf: Multi; rp: Multi;
  tp?: "yes" | "no"; colo?: "yes" | "no"; age?: number;
  kind: Multi; scale: Multi; scope: "gb" | "all"; comp0?: number;
  conflict?: "yes";
  bbox?: [number, number, number, number];
  ids: Multi;
}

export const DEFAULT_CAT = ["generation", "storage", "hybrid"];
export const DEFAULT_STAGE = ["operational", "pipeline", "historic", "unknown"];
export const DEFAULT_KIND = ["project"];

const MULTI_KEYS = ["cat", "fam", "tech", "wt", "stage", "st", "ctry", "reg", "la", "dno", "conn", "cs", "dev", "own", "opr", "mfr", "mdl", "sup", "pa", "src", "conf", "rp", "kind", "scale", "ids"] as const;
const NUM_KEYS = ["mw0", "mw1", "mwh0", "mwh1", "h0", "h1", "kv0", "kv1", "nt0", "nt1", "hub0", "hub1", "rot0", "rot1", "tip0", "tip1", "cy0", "cy1", "py0", "py1", "age", "comp0"] as const;

type SP = URLSearchParams | Record<string, string | string[] | undefined>;
function get(sp: SP, k: string): string | undefined {
  if (sp instanceof URLSearchParams) return sp.get(k) ?? undefined;
  const v = sp[k];
  return Array.isArray(v) ? v[0] : v;
}

const list = (v?: string): string[] => (v ? v.split(",").map((s) => s.trim()).filter(Boolean).slice(0, 200) : []);
const num = (v?: string): number | undefined => {
  if (v === undefined || v === "") return undefined;
  const n = Number(v);
  return Number.isFinite(n) ? n : undefined;
};

export function parseFilters(sp: SP): Filters {
  const f = { q: (get(sp, "q") ?? "").slice(0, 200), scope: get(sp, "scope") === "all" ? "all" : "gb" } as Filters;
  for (const k of MULTI_KEYS) (f as unknown as Record<string, Multi>)[k] = list(get(sp, k));
  for (const k of NUM_KEYS) (f as unknown as Record<string, number | undefined>)[k] = num(get(sp, k));
  if (f.ids.length) f.scope = "all"; // an explicit selection (popup, compare, export-selected) is not subject to the browsing defaults
  else {
    if (!f.cat.length) f.cat = [...DEFAULT_CAT];
    if (!f.stage.length && !f.st.length) f.stage = [...DEFAULT_STAGE];
    if (!f.kind.length) f.kind = [...DEFAULT_KIND];
  }
  const tp = get(sp, "tp"); if (tp === "yes" || tp === "no") f.tp = tp;
  const colo = get(sp, "colo"); if (colo === "yes" || colo === "no") f.colo = colo;
  if (get(sp, "conflict") === "yes") f.conflict = "yes";
  const bb = list(get(sp, "bbox")).map(Number);
  if (bb.length === 4 && bb.every(Number.isFinite)) f.bbox = bb as [number, number, number, number];
  return f;
}

/** Serialise only what differs from the defaults so URLs stay short and shareable. */
export function filtersToParams(f: Partial<Filters>): URLSearchParams {
  const p = new URLSearchParams();
  if (f.q) p.set("q", f.q);
  if (f.scope === "all") p.set("scope", "all");
  const eq = (a: string[] | undefined, b: string[]) => !!a && a.length === b.length && b.every((x) => a.includes(x));
  for (const k of MULTI_KEYS) {
    const v = (f as unknown as Record<string, Multi | undefined>)[k];
    if (!v || !v.length) continue;
    if (k === "cat" && eq(v, DEFAULT_CAT)) continue;
    if (k === "stage" && eq(v, DEFAULT_STAGE)) continue;
    if (k === "kind" && eq(v, DEFAULT_KIND)) continue;
    p.set(k, v.join(","));
  }
  for (const k of NUM_KEYS) {
    const v = (f as unknown as Record<string, number | undefined>)[k];
    if (v !== undefined && Number.isFinite(v)) p.set(k, String(v));
  }
  if (f.tp) p.set("tp", f.tp);
  if (f.colo) p.set("colo", f.colo);
  if (f.conflict) p.set("conflict", "yes");
  if (f.bbox) p.set("bbox", f.bbox.join(","));
  return p;
}

export interface Where { sql: string; params: unknown[] }

/** Build `WHERE …` conditions over alias `f` (atlas.asset_flat). `start` = first $n index. */
export function buildWhere(f: Filters, start = 1): Where {
  const c: string[] = [];
  const params: unknown[] = [];
  const p = (v: unknown): string => { params.push(v); return `$${start + params.length - 1}`; };
  const anyOf = (col: string, vals: string[]) => c.push(`${col} = ANY(${p(vals)}::text[])`);

  if (f.scope === "gb") c.push("f.in_scope_gb");
  if (f.cat.length) anyOf("f.category", f.cat);
  if (f.fam.length) anyOf("f.family", f.fam);
  if (f.tech.length) anyOf("f.technology_code", f.tech);
  if (f.wt.length) {
    const parts: string[] = [];
    if (f.wt.includes("onshore")) parts.push("f.technology_code = 'wind_onshore'");
    if (f.wt.includes("offshore")) parts.push("f.technology_code LIKE 'wind_offshore%'");
    if (f.wt.includes("fixed")) parts.push("f.technology_code = 'wind_offshore_fixed'");
    if (f.wt.includes("floating")) parts.push("f.technology_code = 'wind_offshore_floating'");
    if (parts.length) c.push(`(${parts.join(" OR ")})`);
  }
  if (f.st.length) anyOf("f.status_code", f.st); else if (f.stage.length) anyOf("f.stage_group", f.stage);
  if (f.ctry.length) anyOf("f.country", f.ctry);
  if (f.reg.length) anyOf("f.region", f.reg);
  if (f.la.length) anyOf("f.local_authority", f.la);
  const range = (col: string, lo?: number, hi?: number) => {
    if (lo !== undefined) c.push(`${col} >= ${p(lo)}`);
    if (hi !== undefined) c.push(`${col} <= ${p(hi)}`);
  };
  range("f.installed_capacity_mw", f.mw0, f.mw1);
  range("f.storage_capacity_mwh", f.mwh0, f.mwh1);
  range("f.storage_duration_h", f.h0, f.h1);
  range("f.connection_voltage_kv", f.kv0, f.kv1);
  range("f.turbine_count", f.nt0, f.nt1);
  range("f.hub_height_m", f.hub0, f.hub1);
  range("f.rotor_diameter_m", f.rot0, f.rot1);
  range("f.tip_height_m", f.tip0, f.tip1);
  range("f.commissioning_year", f.cy0, f.cy1);
  range("f.planning_year", f.py0, f.py1);
  if (f.comp0 !== undefined) c.push(`f.completeness_pct >= ${p(f.comp0)}`);
  if (f.dno.length) anyOf("f.dno", f.dno);
  if (f.conn.length) anyOf("f.connection_type", f.conn);
  if (f.cs.length) anyOf("f.connection_status", f.cs);
  const contains = (arr: string, vals: string[]) => {
    const likes = vals.map((v) => `%${v.replace(/[%_\\]/g, "\\$&")}%`);
    c.push(`EXISTS (SELECT 1 FROM unnest(${arr}) x WHERE x ILIKE ANY(${p(likes)}::text[]))`);
  };
  if (f.dev.length) contains("f.developers", f.dev);
  if (f.own.length) contains("f.owners", f.own);
  if (f.opr.length) contains("f.operators", f.opr);
  const likeCol = (col: string, vals: string[]) => c.push(`${col} ILIKE ANY(${p(vals.map((v) => `%${v.replace(/[%_\\]/g, "\\$&")}%`))}::text[])`);
  if (f.mfr.length) likeCol("f.turbine_manufacturer", f.mfr);
  if (f.mdl.length) likeCol("f.turbine_model", f.mdl);
  if (f.sup.length) {
    const parts: string[] = [];
    if (f.sup.includes("CfD")) parts.push("f.has_cfd");
    if (f.sup.includes("RO")) parts.push("f.has_ro");
    if (f.sup.includes("REGO")) parts.push("f.has_rego");
    if (f.sup.includes("FIT")) parts.push("f.has_fit");
    if (f.sup.includes("none")) parts.push("NOT (f.has_cfd OR f.has_ro OR f.has_rego OR f.has_fit)");
    if (parts.length) c.push(`(${parts.join(" OR ")})`);
  }
  if (f.pa.length) anyOf("f.planning_authority", f.pa);
  if (f.src.length) c.push(`f.source_keys && ${p(f.src)}::text[]`);
  if (f.conf.length) anyOf("f.confidence", f.conf);
  if (f.rp.length) anyOf("f.repowering_status", f.rp);
  if (f.tp === "yes") c.push("f.individual_turbines_known");
  if (f.tp === "no") c.push("NOT f.individual_turbines_known AND f.family = 'wind'");
  if (f.colo === "yes") c.push("f.co_located_storage");
  if (f.colo === "no") c.push("NOT f.co_located_storage");
  if (f.age !== undefined) c.push(`f.stage_group = 'operational' AND f.commissioning_year IS NOT NULL AND f.commissioning_year <= EXTRACT(YEAR FROM now())::int - ${p(f.age)}::int`);
  if (f.kind.length) anyOf("f.asset_kind", f.kind);
  if (f.scale.length) anyOf("f.scale_class", f.scale);
  if (f.conflict) c.push("f.has_conflict");
  if (f.ids.length) anyOf("f.asset_id", f.ids);
  if (f.bbox) c.push(`f.geom && ST_MakeEnvelope(${p(f.bbox[0])}, ${p(f.bbox[1])}, ${p(f.bbox[2])}, ${p(f.bbox[3])}, 4326)`);
  if (f.q.trim()) {
    const raw = f.q.trim();
    const like = `%${raw.replace(/[%_\\]/g, "\\$&")}%`;
    const tokens = raw.toLowerCase().split(/\s+/).filter((t) => t.length > 0).slice(0, 8);
    const tsq = tokens.map((t) => t.replace(/[^a-z0-9._/-]/g, "")).filter(Boolean).map((t) => `${t}:*`).join(" & ");
    const conds = [`f.name_norm ILIKE ${p(like)}`, `f.canonical_name ILIKE ${p(like)}`];
    if (tsq) conds.push(`to_tsvector('simple', coalesce(f.search_doc,'')) @@ to_tsquery('simple', ${p(tsq)})`);
    c.push(`(${conds.join(" OR ")})`);
  }
  return { sql: c.length ? c.join(" AND ") : "TRUE", params };
}

export const SORTABLE: Record<string, string> = {
  name: "f.canonical_name", technology: "f.technology_label", status: "f.status_label", capacity: "f.installed_capacity_mw",
  country: "f.country", la: "f.local_authority", developer: "f.developer", owner: "f.owner", operator: "f.operator",
  year: "f.commissioning_year", planref: "f.planning_reference", grid: "f.grid_operator", confidence: "f.confidence",
  verified: "f.last_verified", completeness: "f.completeness_pct", turbines: "f.turbine_count", mwh: "f.storage_capacity_mwh",
  mfr: "f.turbine_manufacturer", model: "f.turbine_model", tip: "f.tip_height_m", hub: "f.hub_height_m", rotor: "f.rotor_diameter_m",
};
