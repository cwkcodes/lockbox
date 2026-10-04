"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { Glyph, CopyButton, Spinner, useDebounced, useJson, PATTERN_LABEL } from "./ui";
import { filtersToParams, type Filters } from "@/lib/filters";
import type { AssetRow, Facets, Meta, Stats } from "@/lib/types";
import { fmtGw, fmtMw, fmtNum } from "@/lib/format";
import type { Pattern } from "@/lib/glyphs";
import { bngToWgs84, wgs84ToBng } from "@/lib/geo";
import type { ToolMode } from "./MapView";

export function StatsBar({ qs, onOpenDashboard }: { qs: string; onOpenDashboard: () => void }) {
  const dq = useDebounced(qs, 180);
  const { data, loading } = useJson<Stats>(`/api/statistics?${dq}`);
  const h = data?.headline;
  const cell = (k: string, v: string, title?: string) => (
    <div key={k} title={title} style={{ padding: "2px 12px", borderRight: "1px solid var(--line-2)", minWidth: 96 }}>
      <div className="muted" style={{ fontSize: 11 }}>{k}</div><div className="num" style={{ fontSize: 15, fontWeight: 600, textAlign: "left" }}>{v}</div>
    </div>
  );
  return (
    <div className="panel" style={{ display: "flex", alignItems: "stretch", overflowX: "auto", opacity: loading ? 0.7 : 1 }} role="region" aria-label="Statistics for the current filters" aria-live="polite">
      {h ? (<>
        {cell("Projects", fmtNum(h.projects, 0), `${h.without_capacity} without a stated capacity`)}
        {cell("Operational", fmtGw(h.operational_mw))}{cell("Pipeline", fmtGw(h.pipeline_mw))}
        {cell("Storage power", fmtGw(h.storage_mw))}
        {cell("Storage energy", h.storage_with_mwh ? `${fmtNum(h.storage_mwh, 0)} MWh` : "n/a", `Only ${h.storage_with_mwh} storage records state MWh`)}
        {cell("Turbines", fmtNum(h.turbines_reported, 0), `As reported; ${h.turbines_positioned} individually positioned`)}
        {cell("Avg size", fmtMw(h.avg_mw))}
      </>) : <div style={{ padding: 8 }}><Spinner /></div>}
      <button type="button" className="btn ghost sm" style={{ margin: "auto 6px auto auto", flex: "none" }} onClick={onOpenDashboard}>Dashboard →</button>
    </div>
  );
}

export function ResultsList({ f, qs, meta, selectedId, onSelect, compare, onCompare, tableHref }: {
  f: Filters; qs: string; meta: Meta | null; selectedId: string | null; onSelect: (a: AssetRow) => void; compare: string[]; onCompare: (id: string) => void; tableHref: string;
}) {
  const [sort, setSort] = useState("capacity");
  const [pages, setPages] = useState(1);
  const dq = useDebounced(qs, 220);
  useEffect(() => setPages(1), [dq, sort]);
  const { data, loading } = useJson<{ total: number; items: AssetRow[] }>(`/api/assets?${dq}&sort=${sort}&dir=${sort === "name" ? "asc" : "desc"}&pageSize=${pages * 40}`);
  const tech = useMemo(() => new Map(meta?.technologies.map((t) => [t.code, t])), [meta]);
  const stat = useMemo(() => new Map(meta?.statuses.map((s) => [s.code, s])), [meta]);
  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: 0, height: "100%" }}>
      <div style={{ display: "flex", gap: 6, alignItems: "center", padding: "8px 12px", borderBottom: "1px solid var(--line)" }}>
        <strong aria-live="polite">{data ? `${fmtNum(data.total, 0)} results` : "…"}</strong>
        <label className="muted" style={{ marginLeft: "auto" }}>Sort <select className="input" value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort results">
          <option value="capacity">Capacity</option><option value="name">Name</option><option value="year">Commissioned</option><option value="verified">Last verified</option><option value="completeness">Completeness</option></select></label>
      </div>
      <ul style={{ listStyle: "none", margin: 0, padding: 0, overflow: "auto", flex: 1 }} aria-busy={loading} aria-label="Result list">
        {data?.items.map((a) => {
          const t = tech.get(a.technology_code), s = stat.get(a.status_code);
          return (
            <li key={a.asset_id} aria-current={selectedId === a.asset_id} style={{ display: "flex", gap: 8, padding: "7px 10px", borderBottom: "1px solid var(--line-2)", background: selectedId === a.asset_id ? "color-mix(in srgb, var(--accent) 14%, transparent)" : undefined }}>
              <input type="checkbox" aria-label={`Compare ${a.canonical_name}`} checked={compare.includes(a.asset_id)} onChange={() => onCompare(a.asset_id)} style={{ marginTop: 4 }} />
              <button type="button" onClick={() => onSelect(a)} style={{ all: "unset", cursor: "pointer", display: "flex", gap: 8, flex: 1, minWidth: 0 }}>
                <Glyph shape={t?.symbol ?? "circle"} colour={t?.colour ?? "#64748b"} pattern={(s?.pattern ?? "solid") as Pattern} size={18} title={`${a.technology_label}, ${a.status_label}`} />
                <span style={{ flex: 1, minWidth: 0 }}>
                  <span style={{ display: "block", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{a.canonical_name}</span>
                  <span className="muted" style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{a.technology_label} · {a.status_label}{a.local_authority ? ` · ${a.local_authority}` : a.country ? ` · ${a.country}` : ""}</span>
                </span>
                <span className="num" style={{ whiteSpace: "nowrap", fontWeight: 600 }}>{a.installed_capacity_mw != null ? fmtMw(a.installed_capacity_mw) : <span className="muted" style={{ fontWeight: 400 }}>—</span>}</span>
              </button>
            </li>
          );
        })}
        {data && data.items.length < data.total && <li style={{ padding: 8, textAlign: "center" }}><button type="button" className="btn sm" onClick={() => setPages(pages + 1)}>Load more ({fmtNum(data.total - data.items.length, 0)} remaining)</button></li>}
        {data && !data.items.length && <li style={{ padding: 16 }} className="muted">No assets match these filters. Try clearing a filter.</li>}
      </ul>
      <div style={{ display: "flex", gap: 6, padding: 8, borderTop: "1px solid var(--line)", flexWrap: "wrap" }}>
        <a className="btn sm" href={tableHref}>Open table</a>
        {["csv", "xlsx", "geojson"].map((fmt) => <a key={fmt} className="btn sm" href={`/api/export?${qs}${qs ? "&" : ""}format=${fmt}`} download>{fmt.toUpperCase()}</a>)}
      </div>
    </div>
  );
}

export function Legend({ meta, facets, layers, setLayers }: {
  meta: Meta | null; facets: Facets | null;
  layers: { cluster: boolean; sizeByMw: boolean; leases: boolean; turbines: boolean; labels: boolean; boundaries: boolean }; setLayers: (p: Partial<{ cluster: boolean; sizeByMw: boolean; leases: boolean; turbines: boolean; labels: boolean; boundaries: boolean }>) => void;
}) {
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(window.innerHeight > 1000), []);
  const present = new Set(facets?.technology.map((t) => t.value));
  const techs = (meta?.technologies ?? []).filter((t) => present.has(t.code) && !["wind_offshore_fixed", "wind_offshore_floating"].includes(t.code) || (t.code === "wind_offshore" && present.has(t.code)));
  const tog = (k: keyof typeof layers, l: string) => <label style={{ display: "flex", gap: 6, alignItems: "center" }}><input type="checkbox" checked={layers[k]} onChange={(e) => setLayers({ [k]: e.target.checked })} /> {l}</label>;
  return (
    <div className="panel" style={{ width: open ? 236 : "auto", boxShadow: "var(--shadow)" }}>
      <button type="button" className="btn ghost sm" aria-expanded={open} onClick={() => setOpen(!open)} style={{ width: "100%", justifyContent: "space-between" }}><strong>Legend & layers</strong><span aria-hidden>{open ? "–" : "+"}</span></button>
      {open && (
        <div style={{ padding: "2px 10px 10px", maxHeight: "46vh", overflow: "auto" }}>
          <div style={{ fontWeight: 600, margin: "4px 0 2px", color: "var(--ink-2)" }}>Technology</div>
          {techs.map((t) => <div key={t.code} style={{ display: "flex", gap: 6, alignItems: "center" }}><Glyph shape={t.symbol} colour={t.colour} size={16} /><span>{t.label}</span></div>)}
          <div style={{ fontWeight: 600, margin: "8px 0 2px", color: "var(--ink-2)" }}>Status (shape fill, not colour)</div>
          {(["solid", "half", "outline", "muted", "cross"] as Pattern[]).map((p) => <div key={p} style={{ display: "flex", gap: 6, alignItems: "center" }}><Glyph shape="circle" colour="#2f7fb5" pattern={p} size={16} /><span>{PATTERN_LABEL[p]}</span></div>)}
          <div style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 6 }}><span aria-hidden style={{ width: 16, height: 10, border: "1.5px dashed #0f4c81", background: "rgba(15,76,129,.14)" }} /><span>Crown Estate lease area</span></div>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}><span aria-hidden style={{ width: 10, height: 10, borderRadius: 5, background: "#2f7fb5", border: "1.5px solid #fff", boxShadow: "0 0 0 1px #2f7fb5" }} /><span>Verified turbine position</span></div>
          <div style={{ fontWeight: 600, margin: "8px 0 2px", color: "var(--ink-2)" }}>Layers</div>
          {tog("cluster", "Cluster at national zoom")}{tog("sizeByMw", "Marker size ∝ MW")}{tog("leases", "Lease areas")}{tog("turbines", "Turbine positions")}{tog("labels", "Labels (zoomed in)")}{tog("boundaries", "Local authority boundaries")}
        </div>
      )}
    </div>
  );
}

export interface ToolResult { title: string; lines: string[]; copy?: { label: string; text: string }[]; items?: { asset_id: string; canonical_name: string; technology_label?: string; family?: string; installed_capacity_mw?: number | null; distance_m?: number; compass?: string; stage_group?: string; turbine_count?: number | null; lat?: number; lon?: number; manufacturer?: string; unit_code?: string }[]; summary?: Record<string, unknown>; note?: string }

export function Tools({ tool, setTool, result, onClear, onPick, radiusM, setRadiusM, onGoto }: {
  tool: ToolMode; setTool: (t: ToolMode) => void; result: ToolResult | null; onClear: () => void; onPick: (id: string, lon?: number, lat?: number) => void;
  radiusM: number; setRadiusM: (r: number) => void; onGoto: (lat: number, lon: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const [goto, setGotoText] = useState("");
  const tools: { id: ToolMode; l: string; h: string }[] = [
    { id: "coords", l: "Coordinates", h: "Click the map to read WGS84 and British National Grid coordinates" }, { id: "distance", l: "Distance", h: "Click points; double-click to finish" },
    { id: "area", l: "Area", h: "Click vertices; double-click to close" }, { id: "radius", l: "Radius search", h: "Click the centre, then click again to set the radius" },
    { id: "polygon", l: "Polygon search", h: "Click vertices; double-click to search" }, { id: "nearest-asset", l: "Nearest asset", h: "Click the map" }, { id: "nearest-turbine", l: "Nearest turbine", h: "Click the map" },
  ];
  const active = tools.find((t) => t.id === tool);
  const csv = () => {
    if (!result?.items) return;
    const head = ["asset_id", "name", "technology", "capacity_mw", "distance_m", "compass", "lat", "lon"];
    const rows = result.items.map((i) => [i.asset_id, i.canonical_name, i.technology_label ?? "", i.installed_capacity_mw ?? "", i.distance_m ?? "", i.compass ?? "", i.lat ?? "", i.lon ?? ""]);
    const text = [head, ...rows].map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\r\n");
    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([text], { type: "text/csv" })); a.download = "gb-energy-atlas-selection.csv"; a.click();
  };
  return (
    <div className="panel" style={{ width: 300, boxShadow: "var(--shadow)" }}>
      <button type="button" className="btn ghost sm" aria-expanded={open || tool !== "none"} onClick={() => { setOpen(!open); if (open) { setTool("none"); onClear(); } }} style={{ width: "100%", justifyContent: "space-between" }}><strong>GIS tools</strong><span aria-hidden>{open ? "–" : "+"}</span></button>
      {open && (
        <div style={{ padding: "2px 10px 10px", maxHeight: "52vh", overflow: "auto" }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }} role="group" aria-label="Map tools">
            {tools.map((t) => <button key={t.id} type="button" className="btn sm" aria-pressed={tool === t.id} title={t.h} onClick={() => { setTool(tool === t.id ? "none" : t.id); onClear(); }}>{t.l}</button>)}
          </div>
          {active && <p className="muted" style={{ margin: "6px 0 0" }}>{active.h}</p>}
          {(tool === "radius" || tool === "nearest-asset") && <label className="muted" style={{ display: "block", marginTop: 6 }}>Radius <select className="input" value={radiusM} onChange={(e) => setRadiusM(Number(e.target.value))}>{[1, 2, 5, 10, 20, 50].map((k) => <option key={k} value={k * 1000}>{k} km</option>)}</select> <span className="muted">(or click a second point)</span></label>}
          <form style={{ display: "flex", gap: 4, marginTop: 8 }} onSubmit={(e) => { e.preventDefault(); const m = /^(-?\d+(?:\.\d+)?)[ ,]+(-?\d+(?:\.\d+)?)$/.exec(goto.trim()); if (m) { const a = parseFloat(m[1]), b = parseFloat(m[2]); if (a > 1000) { const w = bngToWgs84(a, b); onGoto(w.lat, w.lon); } else onGoto(a, b); } }}>
            <input className="input" style={{ flex: 1 }} placeholder="lat, lon  or  E, N" value={goto} onChange={(e) => setGotoText(e.target.value)} aria-label="Go to coordinates" /><button className="btn sm" type="submit">Go</button>
          </form>
          {result && (
            <div style={{ marginTop: 10, borderTop: "1px solid var(--line-2)", paddingTop: 8 }} role="status" aria-live="polite">
              <strong>{result.title}</strong>
              {result.lines.map((l, i) => <div key={i} className="num" style={{ textAlign: "left" }}>{l}</div>)}
              {result.copy && <div style={{ display: "flex", gap: 4, margin: "4px 0" }}>{result.copy.map((c) => <CopyButton key={c.label} text={c.text} label={c.label} />)}</div>}
              {result.note && <p className="muted">{result.note}</p>}
              {result.items && result.items.length > 0 && (
                <>
                  <ul style={{ listStyle: "none", margin: "6px 0", padding: 0, maxHeight: 170, overflow: "auto" }}>
                    {result.items.slice(0, 60).map((i) => <li key={i.asset_id + (i.unit_code ?? "")}><button type="button" className="btn ghost sm" style={{ width: "100%", justifyContent: "space-between" }} onClick={() => onPick(i.asset_id, i.lon, i.lat)}><span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{i.canonical_name}{i.unit_code ? ` · ${i.unit_code}` : ""}</span><span className="muted">{i.distance_m != null ? `${(i.distance_m / 1000).toFixed(1)} km ${i.compass ?? ""}` : i.installed_capacity_mw != null ? fmtMw(i.installed_capacity_mw) : ""}</span></button></li>)}
                  </ul>
                  <button type="button" className="btn sm" onClick={csv}>Export selection (CSV)</button>
                </>
              )}
              <div style={{ marginTop: 6 }}><button type="button" className="btn ghost sm" onClick={onClear}>Clear</button></div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function CoordReadout({ lat, lon }: { lat: number | null; lon: number | null }) {
  if (lat == null || lon == null) return <span className="muted">Move over the map for coordinates</span>;
  const { e, n } = wgs84ToBng(lon, lat);
  return <span className="num" style={{ textAlign: "left" }}>{lat.toFixed(5)}, {lon.toFixed(5)} · BNG E {Math.round(e)} N {Math.round(n)}</span>;
}

export { CopyButton, filtersToParams };
void useRef;
