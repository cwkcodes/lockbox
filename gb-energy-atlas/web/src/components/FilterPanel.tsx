"use client";
import { useMemo, useState } from "react";
import { Section } from "./ui";
import type { Filters } from "@/lib/filters";
import type { FacetOpt, Facets, Meta } from "@/lib/types";
import { fmtNum } from "@/lib/format";

type Patch = (p: Partial<Filters>) => void;

function MultiSelect({ label, options, value, onChange, limit = 8, searchable = true, render }: {
  label: string; options: FacetOpt[]; value: string[]; onChange: (v: string[]) => void; limit?: number; searchable?: boolean; render?: (o: FacetOpt) => string;
}) {
  const [q, setQ] = useState(""), [all, setAll] = useState(false);
  const shown = useMemo(() => {
    const filtered = q ? options.filter((o) => (render?.(o) ?? o.label ?? o.value).toLowerCase().includes(q.toLowerCase())) : options;
    const sel = options.filter((o) => value.includes(o.value));
    const rest = filtered.filter((o) => !value.includes(o.value));
    const list = q ? filtered : [...sel, ...rest];
    return all || q ? list : list.slice(0, limit);
  }, [options, q, all, value, limit, render]);
  return (
    <fieldset style={{ border: 0, padding: 0, margin: "0 0 8px" }}>
      <legend className="sr-only">{label}</legend>
      {searchable && options.length > limit && <input className="input" style={{ width: "100%", marginBottom: 4, boxSizing: "border-box" }} placeholder={`Search ${label.toLowerCase()}…`} value={q} onChange={(e) => setQ(e.target.value)} aria-label={`Search ${label}`} />}
      {shown.map((o) => {
        const id = `${label}-${o.value}`.replace(/\W+/g, "_");
        return (
          <label key={o.value} htmlFor={id} style={{ display: "flex", gap: 6, alignItems: "center", padding: "1px 0", cursor: "pointer" }}>
            <input id={id} type="checkbox" checked={value.includes(o.value)} onChange={(e) => onChange(e.target.checked ? [...value, o.value] : value.filter((x) => x !== o.value))} />
            <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={render?.(o) ?? o.label ?? o.value}>{render?.(o) ?? o.label ?? o.value}</span>
            <span className="muted num" style={{ fontSize: 11.5 }}>{fmtNum(o.n, 0)}</span>
          </label>
        );
      })}
      {!q && options.length > limit && <button type="button" className="btn ghost sm" onClick={() => setAll(!all)}>{all ? "Show fewer" : `Show all ${options.length}`}</button>}
    </fieldset>
  );
}

function Range({ label, lo, hi, onLo, onHi, unit, step = "any" }: { label: string; lo?: number; hi?: number; onLo: (v?: number) => void; onHi: (v?: number) => void; unit?: string; step?: string }) {
  const parse = (s: string) => (s === "" ? undefined : Number(s));
  return (
    <div style={{ display: "grid", gridTemplateColumns: "88px 1fr 1fr", gap: 6, alignItems: "center", marginBottom: 6 }}>
      <span className="muted">{label}{unit ? ` (${unit})` : ""}</span>
      <input className="input" type="number" inputMode="decimal" step={step} min={0} placeholder="min" aria-label={`${label} minimum`} value={lo ?? ""} onChange={(e) => onLo(parse(e.target.value))} />
      <input className="input" type="number" inputMode="decimal" step={step} min={0} placeholder="max" aria-label={`${label} maximum`} value={hi ?? ""} onChange={(e) => onHi(parse(e.target.value))} />
    </div>
  );
}

function Pills<T extends string>({ label, options, value, onChange, multi = true }: { label: string; options: { v: T; l: string; n?: number }[]; value: T[]; onChange: (v: T[]) => void; multi?: boolean }) {
  return (
    <div role="group" aria-label={label} style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 6 }}>
      {options.map((o) => {
        const on = value.includes(o.v);
        return <button key={o.v} type="button" className="btn sm" aria-pressed={on} onClick={() => onChange(on ? value.filter((x) => x !== o.v) : multi ? [...value, o.v] : [o.v])}>{o.l}{o.n !== undefined && <span style={{ opacity: .7 }}> {fmtNum(o.n, 0)}</span>}</button>;
      })}
    </div>
  );
}

export function activeCount(f: Filters): number {
  let n = 0;
  const arrays: (keyof Filters)[] = ["fam", "tech", "wt", "st", "ctry", "reg", "la", "dno", "conn", "cs", "dev", "own", "opr", "mfr", "mdl", "sup", "pa", "src", "conf", "rp", "scale"];
  for (const k of arrays) if ((f[k] as string[]).length) n++;
  const nums: (keyof Filters)[] = ["mw0", "mw1", "mwh0", "mwh1", "h0", "h1", "kv0", "kv1", "nt0", "nt1", "hub0", "hub1", "rot0", "rot1", "tip0", "tip1", "cy0", "cy1", "py0", "py1", "age", "comp0"];
  for (const k of nums) if (f[k] !== undefined) n++;
  if (f.q) n++; if (f.tp) n++; if (f.colo) n++; if (f.conflict) n++; if (f.scope === "all") n++;
  if (f.stage.join() !== "operational,pipeline,historic,unknown" && !f.st.length) n++;
  if (f.cat.join() !== "generation,storage,hybrid") n++;
  if (f.kind.join() !== "project") n++;
  return n;
}

export default function FilterPanel({ f, patch, facets, meta, onClear }: { f: Filters; patch: Patch; facets: Facets | null; meta: Meta | null; onClear: () => void }) {
  const techByFamily = useMemo(() => {
    const m = new Map<string, FacetOpt[]>();
    for (const t of facets?.technology ?? []) { const k = t.family ?? "other"; if (!m.has(k)) m.set(k, []); m.get(k)!.push(t); }
    return [...m.entries()];
  }, [facets]);
  const stageCounts = useMemo(() => {
    const m: Record<string, number> = {};
    for (const s of facets?.status ?? []) m[s.stage_group ?? "unknown"] = (m[s.stage_group ?? "unknown"] ?? 0) + s.n;
    return m;
  }, [facets]);
  const setTech = (v: string[]) => {
    const needsOther = v.some((c) => facets?.technology.find((t) => t.value === c)?.category === "other_low_carbon");
    patch({ tech: v, cat: needsOther && !f.cat.includes("other_low_carbon") ? [...f.cat, "other_low_carbon"] : f.cat });
  };
  const opt = (arr: FacetOpt[] | undefined) => arr ?? [];
  const n = activeCount(f);
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", borderBottom: "1px solid var(--line)" }}>
        <strong>{n ? `${n} filter${n > 1 ? "s" : ""} active` : "No filters active"}</strong>
        <button type="button" className="btn sm" disabled={!n} onClick={onClear}>Clear all</button>
      </div>

      <Section title="Search & scope">
        <input className="input" style={{ width: "100%", boxSizing: "border-box", marginBottom: 6 }} placeholder="Name, developer, reference, model…" aria-label="Filter by text" value={f.q} onChange={(e) => patch({ q: e.target.value })} />
        <Pills label="Geography scope" value={[f.scope]} onChange={(v) => patch({ scope: (v[v.length - 1] ?? "gb") as "gb" | "all" })} multi={false} options={[{ v: "gb", l: "Great Britain" }, { v: "all", l: "Incl. Northern Ireland records" }]} />
        <Pills label="Record kind" value={f.kind} onChange={(v) => patch({ kind: v.length ? v : ["project"] })} options={[{ v: "project", l: "Projects" }, { v: "lease_area", l: "Lease-area records" }]} />
        <Pills label="Scale" value={f.scale} onChange={(v) => patch({ scale: v })} options={[{ v: "utility", l: "≥ 1 MW" }, { v: "small", l: "< 1 MW" }]} />
      </Section>

      <Section title="Technology" count={f.fam.length + f.tech.length || undefined}>
        <Pills label="Categories" value={f.cat} onChange={(v) => patch({ cat: v.length ? v : ["generation"] })} options={[{ v: "generation", l: "Generation" }, { v: "storage", l: "Storage" }, { v: "hybrid", l: "Hybrid" }, { v: "other_low_carbon", l: "Other low-carbon (optional)" }]} />
        {techByFamily.map(([fam, list]) => (
          <details key={fam} open={list.some((t) => f.tech.includes(t.value)) || fam === "wind"} style={{ marginBottom: 2 }}>
            <summary style={{ cursor: "pointer", textTransform: "capitalize", fontWeight: 600, color: "var(--ink-2)" }}>{fam.replace(/_/g, " ")}</summary>
            <MultiSelect label={`${fam} technologies`} options={list} value={f.tech} onChange={(v) => setTech([...f.tech.filter((c) => !list.some((t) => t.value === c)), ...v])} searchable={false} limit={20} />
          </details>
        ))}
        <div style={{ fontWeight: 600, color: "var(--ink-2)", margin: "6px 0 2px" }}>Wind type</div>
        <Pills label="Wind type" value={f.wt} onChange={(v) => patch({ wt: v })} options={[{ v: "onshore", l: "Onshore" }, { v: "offshore", l: "Offshore" }, { v: "fixed", l: "Fixed-bottom" }, { v: "floating", l: "Floating" }]} />
      </Section>

      <Section title="Status & stage">
        <Pills label="Stage" value={f.stage} onChange={(v) => patch({ stage: v, st: [] })} options={[
          { v: "operational", l: "Operational", n: stageCounts.operational }, { v: "pipeline", l: "Pipeline", n: stageCounts.pipeline }, { v: "historic", l: "Decommissioned / mothballed", n: stageCounts.historic },
          { v: "unsuccessful", l: "Refused / withdrawn / expired / superseded", n: stageCounts.unsuccessful }, { v: "unknown", l: "Unknown", n: stageCounts.unknown }]} />
        <details><summary style={{ cursor: "pointer", color: "var(--ink-2)" }}>Specific statuses</summary>
          <MultiSelect label="Status" options={opt(facets?.status)} value={f.st} onChange={(v) => patch({ st: v })} searchable={false} limit={30} />
        </details>
        <Pills label="Repowering" value={f.rp} onChange={(v) => patch({ rp: v })} options={[{ v: "has_repower", l: "Has repowering project" }, { v: "is_repower", l: "Is a repowering project" }]} />
      </Section>

      <Section title="Capacity & storage" defaultOpen={false}>
        <Range label="Capacity" unit="MW" lo={f.mw0} hi={f.mw1} onLo={(v) => patch({ mw0: v })} onHi={(v) => patch({ mw1: v })} />
        <Range label="Storage energy" unit="MWh" lo={f.mwh0} hi={f.mwh1} onLo={(v) => patch({ mwh0: v })} onHi={(v) => patch({ mwh1: v })} />
        <Range label="Duration" unit="h" lo={f.h0} hi={f.h1} onLo={(v) => patch({ h0: v })} onHi={(v) => patch({ h1: v })} />
        <p className="muted" style={{ margin: 0 }}>REPD does not publish MWh; storage energy appears only where a source states it.</p>
      </Section>

      <Section title="Location" defaultOpen={false}>
        <MultiSelect label="Country" options={opt(facets?.country)} value={f.ctry} onChange={(v) => patch({ ctry: v })} searchable={false} />
        <details><summary style={{ cursor: "pointer", color: "var(--ink-2)" }}>Region</summary><MultiSelect label="Region" options={opt(facets?.region)} value={f.reg} onChange={(v) => patch({ reg: v })} /></details>
        <details open={f.la.length > 0}><summary style={{ cursor: "pointer", color: "var(--ink-2)" }}>Local authority (derived)</summary><MultiSelect label="Local authority" options={opt(facets?.localAuthority)} value={f.la} onChange={(v) => patch({ la: v })} /></details>
      </Section>

      <Section title="Grid connection" defaultOpen={false}>
        <Pills label="Connection type" value={f.conn} onChange={(v) => patch({ conn: v })} options={[{ v: "transmission", l: "Transmission" }, { v: "distribution", l: "Distribution" }]} />
        <MultiSelect label="DNO" options={opt(facets?.dno)} value={f.dno} onChange={(v) => patch({ dno: v })} searchable={false} />
        <Range label="Voltage" unit="kV" lo={f.kv0} hi={f.kv1} onLo={(v) => patch({ kv0: v })} onHi={(v) => patch({ kv1: v })} />
        <p className="muted" style={{ margin: 0 }}>DNO/TEC/ECR fields populate only from registers that could be ingested (see Data page).</p>
      </Section>

      <Section title="Organisations" defaultOpen={false}>
        <div className="muted">Developer</div><MultiSelect label="Developer" options={opt(facets?.developer)} value={f.dev} onChange={(v) => patch({ dev: v })} limit={5} />
        <div className="muted">Owner</div><MultiSelect label="Owner" options={opt(facets?.owner)} value={f.own} onChange={(v) => patch({ own: v })} limit={5} />
        <div className="muted">Operator / applicant</div><MultiSelect label="Operator" options={opt(facets?.operator)} value={f.opr} onChange={(v) => patch({ opr: v })} limit={8} />
      </Section>

      <Section title="Wind equipment" defaultOpen={false}>
        <MultiSelect label="Manufacturer" options={opt(facets?.manufacturer)} value={f.mfr} onChange={(v) => patch({ mfr: v })} />
        <MultiSelect label="Model" options={opt(facets?.model)} value={f.mdl} onChange={(v) => patch({ mdl: v })} />
        <Range label="Turbines" lo={f.nt0} hi={f.nt1} onLo={(v) => patch({ nt0: v })} onHi={(v) => patch({ nt1: v })} step="1" />
        <Range label="Hub height" unit="m" lo={f.hub0} hi={f.hub1} onLo={(v) => patch({ hub0: v })} onHi={(v) => patch({ hub1: v })} />
        <Range label="Rotor dia." unit="m" lo={f.rot0} hi={f.rot1} onLo={(v) => patch({ rot0: v })} onHi={(v) => patch({ rot1: v })} />
        <Range label="Tip height" unit="m" lo={f.tip0} hi={f.tip1} onLo={(v) => patch({ tip0: v })} onHi={(v) => patch({ tip1: v })} />
        <Pills label="Individual turbine locations known" value={f.tp ? [f.tp] : []} onChange={(v) => patch({ tp: v[v.length - 1] as "yes" | "no" | undefined })} multi={false} options={[{ v: "yes", l: "Turbine positions known" }, { v: "no", l: "Not known" }]} />
        <p className="muted" style={{ margin: 0 }}>Manufacturer / model / hub / rotor / tip are empty until a primary source states them – nothing is inferred from capacity.</p>
      </Section>

      <Section title="Dates & age" defaultOpen={false}>
        <Range label="Commissioned" unit="year" lo={f.cy0} hi={f.cy1} onLo={(v) => patch({ cy0: v })} onHi={(v) => patch({ cy1: v })} step="1" />
        <Range label="Planning applied" unit="year" lo={f.py0} hi={f.py1} onLo={(v) => patch({ py0: v })} onHi={(v) => patch({ py1: v })} step="1" />
        <Pills label="Operational age" value={f.age !== undefined ? [String(f.age)] : []} onChange={(v) => patch({ age: v.length ? Number(v[v.length - 1]) : undefined })} multi={false} options={[{ v: "15", l: "> 15 years" }, { v: "20", l: "> 20 years" }, { v: "25", l: "> 25 years" }]} />
        <p className="muted" style={{ margin: 0 }}>Age alone does not show repowering feasibility.</p>
      </Section>

      <Section title="Support & planning" defaultOpen={false}>
        <Pills label="Support mechanism" value={f.sup} onChange={(v) => patch({ sup: v })} options={[{ v: "CfD", l: "CfD" }, { v: "RO", l: "RO" }, { v: "REGO", l: "REGO" }, { v: "FIT", l: "FIT" }, { v: "none", l: "None / unknown" }]} />
        <MultiSelect label="Planning authority" options={opt(facets?.planningAuthority)} value={f.pa} onChange={(v) => patch({ pa: v })} />
        <Pills label="Co-located storage" value={f.colo ? [f.colo] : []} onChange={(v) => patch({ colo: v[v.length - 1] as "yes" | "no" | undefined })} multi={false} options={[{ v: "yes", l: "Co-located storage" }, { v: "no", l: "No co-location recorded" }]} />
      </Section>

      <Section title="Data quality" defaultOpen={false}>
        <MultiSelect label="Confidence" options={opt(facets?.confidence)} value={f.conf} onChange={(v) => patch({ conf: v })} searchable={false} />
        <Range label="Completeness ≥" unit="%" lo={f.comp0} hi={undefined} onLo={(v) => patch({ comp0: v })} onHi={() => undefined} />
        <MultiSelect label="Source availability" options={opt(facets?.source).map((s) => ({ ...s, label: meta?.sources.find((x) => x.source_key === s.value)?.dataset ?? s.value }))} value={f.src} onChange={(v) => patch({ src: v })} searchable={false} />
        <label style={{ display: "flex", gap: 6, alignItems: "center" }}><input type="checkbox" checked={!!f.conflict} onChange={(e) => patch({ conflict: e.target.checked ? "yes" : undefined })} /> Only records with conflicting source values</label>
      </Section>
    </div>
  );
}
