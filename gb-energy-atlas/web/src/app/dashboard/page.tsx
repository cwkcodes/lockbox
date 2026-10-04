"use client";
import Link from "next/link";
import { Suspense, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { Page } from "@/components/SiteHeader";
import { HBars, StackedColumns } from "@/components/charts";
import { useJson } from "@/components/ui";
import { filtersToParams, parseFilters } from "@/lib/filters";
import { fmtGw, fmtMw, fmtNum } from "@/lib/format";
import { FAMILY_COLOUR } from "@/lib/mapStyle";
import type { AssetRow, Facets, Stats } from "@/lib/types";

function Dash() {
  const sp = useSearchParams();
  const f = useMemo(() => parseFilters(sp), [sp]);
  const qs = useMemo(() => filtersToParams(f).toString(), [f]);
  const { data: s } = useJson<Stats>(`/api/statistics?${qs}`);
  const { data: facets } = useJson<Facets>("/api/facets");
  const la = f.la[0];
  const { data: top } = useJson<{ items: AssetRow[] }>(la ? `/api/assets?${qs}&sort=capacity&pageSize=8` : null);
  const { data: planning } = useJson<{ items: { case_id: number; canonical_name: string; asset_id: string; reference: string; authority: string; application_date: string | null; decision: string | null }[] }>(la ? `/api/planning-cases?${qs}&pageSize=8` : null);
  const base = qs ? `&${qs}` : "";
  const age15 = useJson<Stats>(`/api/statistics?fam=wind&stage=operational&age=15&scope=gb&cat=generation`).data?.headline;
  const age20 = useJson<Stats>(`/api/statistics?fam=wind&stage=operational&age=20&scope=gb&cat=generation`).data?.headline;
  const age25 = useJson<Stats>(`/api/statistics?fam=wind&stage=operational&age=25&scope=gb&cat=generation`).data?.headline;
  const h = s?.headline;
  const famLabel: Record<string, string> = { wind: "Wind", solar: "Solar", storage: "Storage", hydro: "Hydro", marine: "Marine", bioenergy: "Bioenergy", hybrid: "Hybrid", geothermal: "Geothermal", other_low_carbon: "Other low-carbon", unknown: "Unknown" };
  return (
    <Page title="National dashboard" current="/dashboard" wide>
      <p className="muted" style={{ marginTop: -6 }}>Charts respond to the filters in the address bar – <Link href={`/?${qs}`}>refine them on the map</Link>. Figures reflect REPD-reported capacities; “operational” and “pipeline” use the normalised status taxonomy.</p>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", margin: "8px 0 14px" }}>
        <label>Local area analysis:&nbsp;
          <select className="input" value={la ?? ""} onChange={(e) => { const p = filtersToParams({ ...f, la: e.target.value ? [e.target.value] : [] }); window.location.search = p.toString(); }} aria-label="Select a local authority">
            <option value="">All Great Britain</option>{facets?.localAuthority.map((l) => <option key={l.value} value={l.value}>{l.value}</option>)}</select></label>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10, marginBottom: 14 }}>
        {h && [["Projects", fmtNum(h.projects, 0)], ["Operational", fmtGw(h.operational_mw)], ["Pipeline", fmtGw(h.pipeline_mw)], ["Storage power", fmtGw(h.storage_mw)], ["Storage energy", h.storage_with_mwh ? `${fmtNum(h.storage_mwh, 0)} MWh (${h.storage_with_mwh} records)` : "not published"], ["Turbines (reported)", fmtNum(h.turbines_reported, 0)], ["Without stated capacity", fmtNum(h.without_capacity, 0)], ["With source conflicts", fmtNum(h.with_conflicts, 0)]].map(([k, v]) => <div key={k} className="panel" style={{ padding: 10 }}><div className="muted">{k}</div><div style={{ fontSize: 20, fontWeight: 600 }}>{v}</div></div>)}
      </div>
      {s && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 12 }}>
          <HBars title="Capacity by technology (MW, all stages)" data={s.byTechnology.map((b) => ({ label: b.label ?? String(b.key), value: b.mw, colour: b.colour }))} format={(v) => fmtGw(v)} />
          <HBars title="Operational capacity by technology" data={s.byTechnology.map((b) => ({ label: b.label ?? String(b.key), value: b.operational_mw ?? 0, colour: b.colour })).filter((b) => b.value > 0).sort((a, b) => b.value - a.value)} format={(v) => fmtGw(v)} />
          <HBars title="Projects by status" data={s.byStatus.map((b) => ({ label: b.label ?? String(b.key), value: b.n }))} />
          <HBars title="Capacity by country (MW)" data={s.byCountry.map((b) => ({ label: String(b.key), value: b.mw }))} format={(v) => fmtGw(v)} />
          <HBars title="Capacity by local authority (derived)" data={s.byLocalAuthority.map((b) => ({ label: String(b.key), value: b.mw }))} format={(v) => fmtGw(v)} max={15} />
          <HBars title="Capacity by operator / developer (top 12)" data={s.byDeveloper.map((b) => ({ label: String(b.key), value: b.mw }))} format={(v) => fmtGw(v)} />
          <div style={{ gridColumn: "1 / -1" }}><StackedColumns title="Operational capacity by commissioning year" data={s.byYearTech} colours={FAMILY_COLOUR} labels={famLabel} /></div>
          <HBars title="Wind capacity by turbine manufacturer" data={s.byManufacturer.map((b) => ({ label: String(b.key), value: b.mw }))} format={(v) => fmtGw(v)} />
          <figure className="panel" style={{ margin: 0, padding: 12 }}>
            <figcaption><strong>Repowering context: operational wind by age</strong></figcaption>
            <table className="data"><thead><tr><th scope="col">Operational wind</th><th scope="col" style={{ textAlign: "right" }}>Projects</th><th scope="col" style={{ textAlign: "right" }}>Capacity</th></tr></thead>
              <tbody>{[["> 15 years", age15], ["> 20 years", age20], ["> 25 years", age25]].map(([l, a]) => <tr key={String(l)}><td>{String(l)}</td><td className="num">{a ? fmtNum((a as Stats["headline"]).projects, 0) : "…"}</td><td className="num">{a ? fmtGw((a as Stats["headline"]).operational_mw) : "…"}</td></tr>)}</tbody></table>
            <p className="muted">Age alone does not show repowering feasibility. Turbine model, tip height and planning status are needed (largely “not publicly identified” in loaded sources).</p>
          </figure>
        </div>
      )}
      {la && (
        <section style={{ marginTop: 16 }} aria-label={`Local area analysis for ${la}`}>
          <h2 style={{ fontSize: 17, marginBottom: 8 }}>{la}: largest projects and recent planning activity</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 12 }}>
            <div className="panel" style={{ padding: 10 }}><strong>Largest projects</strong><table className="data"><tbody>{top?.items.map((a) => <tr key={a.asset_id}><td><Link href={`/assets/${a.asset_id}`}>{a.canonical_name}</Link><div className="muted">{a.technology_label} · {a.status_label}</div></td><td className="num">{fmtMw(a.installed_capacity_mw)}</td></tr>)}</tbody></table></div>
            <div className="panel" style={{ padding: 10 }}><strong>Planning cases (most recent applications)</strong><table className="data"><tbody>{planning?.items.map((p) => <tr key={p.case_id}><td><Link href={`/assets/${p.asset_id}`}>{p.canonical_name}</Link><div className="muted">{p.authority} · {p.reference ?? "no ref"}</div></td><td>{p.decision ?? "—"}</td></tr>)}</tbody></table></div>
          </div>
        </section>
      )}
      <p className="muted" style={{ marginTop: 14 }}>Base: {base ? "filtered selection" : "all GB projects with default filters"}. Lease-area records and Northern Ireland are excluded unless selected.</p>
    </Page>
  );
}
export default function DashboardPage() { return <Suspense fallback={<Page title="National dashboard" current="/dashboard"><p>Loading…</p></Page>}><Dash /></Suspense>; }
