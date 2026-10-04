"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useDebounced, useJson, useLocalStorage } from "./ui";
import { Page } from "./SiteHeader";
import FilterPanel from "./FilterPanel";
import { filtersToParams, parseFilters, type Filters } from "@/lib/filters";
import { fmtDateShort, fmtNum } from "@/lib/format";
import type { AssetRow, Facets, Meta } from "@/lib/types";

interface Col { id: string; label: string; sort?: string; num?: boolean; get: (a: AssetRow) => React.ReactNode }
const COLS: Col[] = [
  { id: "name", label: "Asset", sort: "name", get: (a) => <Link href={`/assets/${a.asset_id}`}>{a.canonical_name}</Link> },
  { id: "tech", label: "Technology", sort: "technology", get: (a) => a.technology_label },
  { id: "status", label: "Status", sort: "status", get: (a) => a.status_label },
  { id: "cap", label: "Capacity (MW)", sort: "capacity", num: true, get: (a) => (a.installed_capacity_mw != null ? fmtNum(a.installed_capacity_mw, 1) : "—") },
  { id: "mwh", label: "Storage (MWh)", sort: "mwh", num: true, get: (a) => (a.storage_capacity_mwh != null ? fmtNum(a.storage_capacity_mwh, 1) : "—") },
  { id: "turb", label: "Turbines*", sort: "turbines", num: true, get: (a) => (a.turbine_count != null ? fmtNum(a.turbine_count, 0) : "—") },
  { id: "ctry", label: "Country", sort: "country", get: (a) => a.country ?? "—" },
  { id: "la", label: "Local authority", sort: "la", get: (a) => a.local_authority ?? "—" },
  { id: "dev", label: "Developer", sort: "developer", get: (a) => a.developer ?? "—" },
  { id: "own", label: "Owner", sort: "owner", get: (a) => a.owner ?? "—" },
  { id: "opr", label: "Operator / applicant", sort: "operator", get: (a) => a.operator ?? "—" },
  { id: "year", label: "Commissioned", sort: "year", num: true, get: (a) => a.commissioning_year ?? "—" },
  { id: "plan", label: "Planning ref.", sort: "planref", get: (a) => a.planning_reference ?? "—" },
  { id: "grid", label: "Grid operator", sort: "grid", get: (a) => a.grid_operator ?? "—" },
  { id: "mfr", label: "Turbine mfr", sort: "mfr", get: (a) => a.turbine_manufacturer ?? "—" },
  { id: "model", label: "Turbine model", sort: "model", get: (a) => a.turbine_model ?? "—" },
  { id: "conf", label: "Confidence", sort: "confidence", get: (a) => a.confidence },
  { id: "comp", label: "Complete", sort: "completeness", num: true, get: (a) => (a.completeness_pct != null ? `${a.completeness_pct}%` : "—") },
  { id: "ver", label: "Last verified", sort: "verified", get: (a) => fmtDateShort(a.last_verified) },
  { id: "repd", label: "REPD ref", get: (a) => a.repd_ref ?? "—" },
];
const DEFAULT_COLS = ["name", "tech", "status", "cap", "ctry", "la", "opr", "year", "plan", "conf", "ver"];

export default function DataTable({ initialQuery }: { initialQuery: string }) {
  const [f, setF] = useState<Filters>(() => parseFilters(new URLSearchParams(initialQuery)));
  const { data: meta } = useJson<Meta>("/api/meta");
  const { data: facets } = useJson<Facets>("/api/facets");
  const [cols, setCols] = useLocalStorage<string[]>("atlas.cols", DEFAULT_COLS);
  const [sort, setSort] = useState("capacity"), [dir, setDir] = useState<"asc" | "desc">("desc"), [page, setPage] = useState(1), [showCols, setShowCols] = useState(false), [showFilters, setShowFilters] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const qs = useMemo(() => filtersToParams(f).toString(), [f]);
  const dq = useDebounced(qs, 250);
  useEffect(() => setPage(1), [dq, sort, dir]);
  useEffect(() => { window.history.replaceState(null, "", `/assets${qs ? `?${qs}` : ""}`); }, [qs]);
  const { data, loading } = useJson<{ total: number; items: AssetRow[] }>(`/api/assets?${dq}&sort=${sort}&dir=${dir}&page=${page}&pageSize=100`);
  const shown = COLS.filter((c) => cols.includes(c.id));
  const pages = data ? Math.max(1, Math.ceil(data.total / 100)) : 1;
  return (
    <Page title="Asset database" current="/assets" wide>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 10 }}>
        <input className="input" style={{ width: 280 }} placeholder="Search name, developer, reference…" aria-label="Search assets" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} />
        <button type="button" className="btn" aria-expanded={showFilters} onClick={() => setShowFilters(!showFilters)}>Filters</button>
        <button type="button" className="btn" aria-expanded={showCols} onClick={() => setShowCols(!showCols)}>Columns</button>
        <Link className="btn" href={`/?${qs}`}>Show on map</Link>
        {["csv", "xlsx", "geojson"].map((fmt) => <a key={fmt} className="btn" href={`/api/export?${qs}${qs ? "&" : ""}format=${fmt}`} download>{fmt.toUpperCase()}</a>)}
        <strong style={{ marginLeft: "auto" }} aria-live="polite">{data ? `${fmtNum(data.total, 0)} assets` : "…"}</strong>
      </div>
      {showCols && <div className="panel" style={{ padding: 10, marginBottom: 10, display: "flex", flexWrap: "wrap", gap: "4px 14px" }}>{COLS.map((c) => <label key={c.id} style={{ display: "flex", gap: 4 }}><input type="checkbox" checked={cols.includes(c.id)} onChange={(e) => setCols(e.target.checked ? [...cols, c.id] : cols.filter((x) => x !== c.id))} />{c.label}</label>)}</div>}
      <div style={{ display: "grid", gridTemplateColumns: showFilters ? "300px 1fr" : "1fr", gap: 12, alignItems: "start" }}>
        {showFilters && <div className="panel" style={{ maxHeight: "75vh", overflow: "auto" }}><FilterPanel f={f} patch={(p) => setF((x) => ({ ...x, ...p }))} facets={facets} meta={meta} onClear={() => setF(parseFilters(new URLSearchParams()))} /></div>}
        <div className="panel" style={{ overflow: "auto", maxHeight: "74vh" }}>
          <table className="data" aria-busy={loading}>
            <caption className="sr-only">Renewable-energy assets matching the current filters</caption>
            <thead><tr>{shown.map((c) => <th key={c.id} scope="col" aria-sort={sort === c.sort ? (dir === "asc" ? "ascending" : "descending") : "none"} style={c.num ? { textAlign: "right" } : undefined}>
              {c.sort ? <button type="button" onClick={() => { if (sort === c.sort) setDir(dir === "asc" ? "desc" : "asc"); else { setSort(c.sort!); setDir(c.num ? "desc" : "asc"); } }}>{c.label}{sort === c.sort ? (dir === "asc" ? " ▲" : " ▼") : ""}</button> : c.label}</th>)}</tr></thead>
            <tbody>{data?.items.map((a) => <tr key={a.asset_id} aria-selected={selected === a.asset_id} onClick={() => setSelected(a.asset_id)}>{shown.map((c) => <td key={c.id} className={c.num ? "num" : undefined} style={c.id === "name" ? { minWidth: 240 } : c.id === "opr" || c.id === "dev" || c.id === "own" ? { minWidth: 160 } : { whiteSpace: "nowrap" }}>{c.get(a)}</td>)}</tr>)}
              {data && !data.items.length && <tr><td colSpan={shown.length} className="muted" style={{ padding: 16 }}>No assets match these filters.</td></tr>}</tbody>
          </table>
        </div>
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center", justifyContent: "center", marginTop: 10 }}>
        <button type="button" className="btn sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>← Previous</button><span>Page {page} of {pages}</span><button type="button" className="btn sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next →</button>
      </div>
      <p className="muted">* Turbine counts are as reported by the source register and are not verified as built. “—” means unknown / not publicly identified. Column choices are remembered in this browser.</p>
    </Page>
  );
}
