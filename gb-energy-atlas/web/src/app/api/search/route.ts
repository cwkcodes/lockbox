import { NextRequest } from "next/server";
import { query } from "@/lib/db";
import { json } from "@/lib/api";
import { parseCoordinateInput } from "@/lib/geo";

export const dynamic = "force-dynamic";

const TECH_WORDS: Record<string, { tech?: string[]; fam?: string[]; wt?: string[] }> = {
  battery: { fam: ["storage"] }, bess: { fam: ["storage"] }, storage: { fam: ["storage"] }, solar: { tech: ["solar_pv"] }, pv: { tech: ["solar_pv"] },
  wind: { fam: ["wind"] }, onshore: { wt: ["onshore"] }, offshore: { wt: ["offshore"] }, hydro: { fam: ["hydro"] }, tidal: { tech: ["tidal_stream", "tidal_range"] },
  wave: { tech: ["wave"] }, biomass: { tech: ["biomass"] }, "anaerobic": { tech: ["anaerobic_digestion"] }, landfill: { tech: ["landfill_gas"] },
};
const STATUS_WORDS: Record<string, string[]> = { operational: ["operational"], consented: ["consented", "awaiting_construction"], construction: ["under_construction"], planning: ["planning", "planning_submitted"] };
const COUNTRIES = ["england", "scotland", "wales"];

/** Turn "battery 50 MW Scotland" into structured filters (shown to the user as an editable interpretation, never silently applied). */
function interpret(q: string) {
  const f: Record<string, string> = {};
  const tokens = q.toLowerCase().split(/\s+/);
  const rest: string[] = [];
  const fam = new Set<string>(), tech = new Set<string>(), wt = new Set<string>(), st = new Set<string>();
  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i].replace(/[^a-z0-9.+<>]/g, "");
    const next = (tokens[i + 1] ?? "").replace(/[^a-z]/g, "");
    if (/^[<>+]?\d+(\.\d+)?$/.test(t) && (next === "mw" || next === "gw" || next === "mwh")) {
      const v = parseFloat(t.replace(/[<>+]/g, "")) * (next === "gw" ? 1000 : 1);
      const key = next === "mwh" ? "mwh" : "mw";
      if (tokens[i - 1] === "under" || tokens[i - 1] === "below" || t.startsWith("<")) f[`${key}1`] = String(v); else f[`${key}0`] = String(v);
      i++; continue;
    }
    if (t.endsWith("mw") && /^\d/.test(t)) { f.mw0 = String(parseFloat(t)); continue; }
    const w = TECH_WORDS[t];
    if (w) { w.fam?.forEach((x) => fam.add(x)); w.tech?.forEach((x) => tech.add(x)); w.wt?.forEach((x) => wt.add(x)); continue; }
    if (STATUS_WORDS[t]) { STATUS_WORDS[t].forEach((x) => st.add(x)); continue; }
    if (COUNTRIES.includes(t)) { f.ctry = t[0].toUpperCase() + t.slice(1); continue; }
    if (["mw", "over", "above", "under", "below", "in", "at", "the", "of", "farm", "projects", "project"].includes(t)) continue;
    rest.push(tokens[i]);
  }
  if (fam.size) f.fam = [...fam].join(",");
  if (tech.size) f.tech = [...tech].join(",");
  if (wt.size) f.wt = [...wt].join(",");
  if (st.size) f.st = [...st].join(",");
  const structured = Object.keys(f).length >= 1 && (f.fam || f.tech || f.wt || f.ctry || f.st || f.mw0 || f.mw1);
  if (!structured) return null;
  if (rest.length) f.q = rest.join(" ");
  return f;
}

export async function GET(req: NextRequest) {
  const q = (req.nextUrl.searchParams.get("q") ?? "").trim().slice(0, 120);
  if (q.length < 2) return json({ assets: [], organisations: [], places: [], identifiers: [], models: [] });
  const like = `%${q.replace(/[%_\\]/g, "\\$&")}%`;
  const prefix = `${q.replace(/[%_\\]/g, "\\$&")}%`;
  const ref = q.toUpperCase().replace(/\s+/g, "");
  const tsq = q.toLowerCase().split(/\s+/).map((t) => t.replace(/[^a-z0-9._/-]/g, "")).filter(Boolean).map((t) => `${t}:*`).join(" & ");
  const base = "f.in_scope_gb AND f.asset_kind IN ('project','lease_area')";
  const [assets, orgs, places, idents, models] = await Promise.all([
    query(`SELECT f.asset_id, f.canonical_name, f.technology_label, f.status_label, f.country, f.local_authority, f.installed_capacity_mw, f.lat, f.lon, f.colour,
                  similarity(f.name_norm, lower($1)) AS sim
           FROM atlas.asset_flat f WHERE ${base} AND (f.canonical_name ILIKE $2 OR CASE WHEN $3 = '' THEN false ELSE to_tsvector('simple', coalesce(f.search_doc,'')) @@ to_tsquery('simple', $3) END)
           ORDER BY (lower(f.canonical_name) = lower($1)) DESC, (f.canonical_name ILIKE $4) DESC, sim DESC, f.installed_capacity_mw DESC NULLS LAST LIMIT 8`,
          [q, like, tsq, prefix]),
    query(`SELECT o.org_id, o.canonical_name, count(DISTINCT ao.asset_id)::int AS n FROM atlas.organisations o JOIN atlas.asset_organisations ao USING (org_id)
           WHERE o.canonical_name ILIKE $1 OR o.name_norm ILIKE $1 GROUP BY 1,2 ORDER BY n DESC LIMIT 5`, [like]),
    query(`SELECT local_authority AS name, count(*)::int AS n FROM atlas.asset_flat WHERE local_authority ILIKE $1 OR region ILIKE $1 GROUP BY 1 ORDER BY n DESC LIMIT 5`, [like]),
    query(`SELECT i.scheme, i.identifier, a.asset_id, a.canonical_name FROM atlas.asset_identifiers i JOIN atlas.assets a USING (asset_id)
           WHERE a.is_published AND (upper(replace(i.identifier,' ','')) = $1 OR i.identifier ILIKE $2) ORDER BY i.scheme LIMIT 6`, [ref, prefix]),
    query(`SELECT DISTINCT turbine_manufacturer, turbine_model, count(*) OVER (PARTITION BY turbine_manufacturer, turbine_model)::int AS n FROM atlas.asset_flat
           WHERE turbine_model ILIKE $1 OR turbine_manufacturer ILIKE $1 LIMIT 5`, [like]),
  ]);
  const planning = await query(`SELECT pc.reference, pc.authority, a.asset_id, a.canonical_name FROM atlas.planning_cases pc JOIN atlas.assets a USING (asset_id)
                                WHERE a.is_published AND pc.reference ILIKE $1 LIMIT 5`, [prefix]);
  return json({ assets, organisations: orgs, places, identifiers: [...idents, ...planning.map((p) => ({ scheme: "planning", identifier: p.reference, asset_id: p.asset_id, canonical_name: p.canonical_name }))],
                models, coordinate: parseCoordinateInput(q), interpretation: interpret(q) });
}
