"use client";
import { useState } from "react";
import { fmtGw, fmtNum } from "@/lib/format";

export interface Bar { label: string; value: number; colour?: string; sub?: string }

/** Horizontal bar chart (SVG) with an accessible table alternative. */
export function HBars({ title, data, unit = "", max = 12, format }: { title: string; data: Bar[]; unit?: string; max?: number; format?: (v: number) => string }) {
  const [asTable, setAsTable] = useState(false);
  const rows = data.slice(0, max);
  const top = Math.max(1, ...rows.map((r) => r.value));
  const f = format ?? ((v: number) => `${fmtNum(v, 0)}${unit}`);
  return (
    <figure className="panel" style={{ margin: 0, padding: 12 }}>
      <figcaption style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}><strong>{title}</strong><button type="button" className="btn ghost sm" onClick={() => setAsTable(!asTable)}>{asTable ? "Chart" : "Table"}</button></figcaption>
      {asTable ? (
        <table className="data"><thead><tr><th scope="col">Category</th><th scope="col" style={{ textAlign: "right" }}>Value</th></tr></thead><tbody>{rows.map((r) => <tr key={r.label}><td>{r.label}</td><td className="num">{f(r.value)}</td></tr>)}</tbody></table>
      ) : (
        <div role="img" aria-label={`${title}: ${rows.map((r) => `${r.label} ${f(r.value)}`).join("; ")}`}>
          {rows.map((r) => (
            <div key={r.label} style={{ display: "grid", gridTemplateColumns: "minmax(90px, 36%) 1fr 74px", gap: 8, alignItems: "center", margin: "3px 0" }}>
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={r.label}>{r.label}</span>
              <span style={{ background: "var(--surface-2)", height: 14, borderRadius: 2 }}><span style={{ display: "block", height: 14, width: `${Math.max(1.5, (r.value / top) * 100)}%`, background: r.colour ?? "var(--brand-2)", borderRadius: 2 }} /></span>
              <span className="num" style={{ fontSize: 12 }}>{f(r.value)}</span>
            </div>
          ))}
        </div>
      )}
    </figure>
  );
}

/** Stacked columns by year and family. */
export function StackedColumns({ title, data, colours, labels }: { title: string; data: { year: number; family: string; mw: number }[]; colours: Record<string, string>; labels?: Record<string, string> }) {
  const years = [...new Set(data.map((d) => d.year))].sort((a, b) => a - b);
  const fams = [...new Set(data.map((d) => d.family))];
  const by = new Map<number, Record<string, number>>();
  for (const d of data) { const r = by.get(d.year) ?? {}; r[d.family] = (r[d.family] ?? 0) + d.mw; by.set(d.year, r); }
  const totals = years.map((y) => Object.values(by.get(y)!).reduce((a, b) => a + b, 0));
  const top = Math.max(1, ...totals);
  const W = 760, H = 220, pad = { l: 44, r: 8, t: 8, b: 22 }, bw = (W - pad.l - pad.r) / Math.max(1, years.length);
  return (
    <figure className="panel" style={{ margin: 0, padding: 12 }}>
      <figcaption><strong>{title}</strong></figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={`${title}. ${years.map((y, i) => `${y}: ${fmtGw(totals[i])}`).join(", ")}`}>
        {[0, 0.25, 0.5, 0.75, 1].map((t) => <g key={t}><line x1={pad.l} x2={W - pad.r} y1={pad.t + (1 - t) * (H - pad.t - pad.b)} y2={pad.t + (1 - t) * (H - pad.t - pad.b)} stroke="var(--line-2)" /><text x={pad.l - 4} y={pad.t + (1 - t) * (H - pad.t - pad.b) + 3} fontSize="9.5" textAnchor="end" fill="var(--ink-3)">{fmtGw(top * t)}</text></g>)}
        {years.map((y, i) => {
          let acc = 0; const row = by.get(y)!;
          return <g key={y}>{fams.map((f) => { const v = row[f] ?? 0; if (!v) return null; const h = (v / top) * (H - pad.t - pad.b); acc += h; return <rect key={f} x={pad.l + i * bw + 1} width={Math.max(1, bw - 2)} y={H - pad.b - acc} height={h} fill={colours[f] ?? "#64748b"}><title>{`${y} · ${labels?.[f] ?? f}: ${fmtGw(v)}`}</title></rect>; })}
            {(i % Math.ceil(years.length / 14) === 0) && <text x={pad.l + i * bw + bw / 2} y={H - 6} fontSize="9.5" textAnchor="middle" fill="var(--ink-3)">{y}</text>}</g>;
        })}
      </svg>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>{fams.map((f) => <span key={f} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}><span aria-hidden style={{ width: 10, height: 10, background: colours[f] ?? "#64748b", display: "inline-block" }} />{labels?.[f] ?? f}</span>)}</div>
    </figure>
  );
}
