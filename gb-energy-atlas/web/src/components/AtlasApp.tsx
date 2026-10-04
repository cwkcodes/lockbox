"use client";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import AssetDetail from "./AssetDetail";
import FilterPanel, { activeCount } from "./FilterPanel";
import SearchBox from "./SearchBox";
import { CoordReadout, Legend, ResultsList, StatsBar, Tools, type ToolResult } from "./Panels";
import { DataDate, NAV, SITE, ThemeToggle } from "./SiteHeader";
import { Tabs, useJson, useLocalStorage, CopyButton } from "./ui";
import type { MapHandle, ToolEvent, ToolMode } from "./MapView";
import { DEFAULT_CAT, DEFAULT_KIND, DEFAULT_STAGE, filtersToParams, parseFilters, type Filters } from "@/lib/filters";
import { BASEMAPS, type BaseId } from "@/lib/mapStyle";
import { fmtMw, fmtNum } from "@/lib/format";
import { wgs84ToBng } from "@/lib/geo";
import type { AssetRow, Facets, Meta } from "@/lib/types";

const MapView = dynamic(() => import("./MapView"), { ssr: false, loading: () => <div className="muted" style={{ padding: 20 }}>Loading map…</div> });

const GB_VIEW = { lng: -3.6, lat: 54.75, zoom: 5.15 };
type SideTab = "filters" | "results" | "saved";

function viewFrom(sp: URLSearchParams, mobile: boolean) {
  const v = sp.get("v")?.split(",").map(Number);
  if (v && v.length === 3 && v.every(Number.isFinite)) return { lat: v[0], lng: v[1], zoom: v[2] };
  return mobile ? { ...GB_VIEW, zoom: 4.3 } : GB_VIEW;
}

export default function AtlasApp({ initialQuery }: { initialQuery: string }) {
  const sp0 = useMemo(() => new URLSearchParams(initialQuery), [initialQuery]);
  const { data: meta } = useJson<Meta>("/api/meta");
  const { data: facets } = useJson<Facets>("/api/facets");
  const mapRef = useRef<MapHandle>(null);

  const [filters, setFilters] = useState<Filters>(() => parseFilters(sp0));
  const [view, setView] = useState(() => viewFrom(sp0, false));
  const [selected, setSelected] = useState<{ id: string; lon: number; lat: number } | null>(() => (sp0.get("sel") ? { id: sp0.get("sel")!, lon: NaN, lat: NaN } : null));
  const [drawerOpen, setDrawerOpen] = useState(!!sp0.get("sel") && sp0.get("d") === "1");
  const [tab, setTab] = useState(sp0.get("tab") ?? "overview");
  const [base, setBase] = useState<BaseId>((sp0.get("base") as BaseId) in BASEMAPS ? (sp0.get("base") as BaseId) : "light");
  const [baseExplicit, setBaseExplicit] = useState(sp0.has("base"));
  const [layers, setLayersState] = useState({ cluster: sp0.get("cl") !== "0", sizeByMw: sp0.get("sz") !== "0", leases: true, turbines: true, labels: true, boundaries: sp0.get("bd") === "1" });
  const [side, setSide] = useState<SideTab>("filters");
  const [sideOpen, setSideOpen] = useState(true);
  const [mobile, setMobile] = useState(false);
  const [tool, setTool] = useState<ToolMode>("none");
  const [toolResult, setToolResult] = useState<ToolResult | null>(null);
  const [radiusM, setRadiusM] = useState(10000);
  const [compare, setCompare] = useState<string[]>([]);
  const [pointer, setPointer] = useState<{ lat: number | null; lon: number | null }>({ lat: null, lon: null });
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [report, setReport] = useState<string | null | undefined>(undefined);
  const [views, setViews] = useLocalStorage<{ name: string; qs: string }[]>("atlas.views", []);
  const [initialView] = useState(view);

  // responsive + theme-aware default basemap -----------------------------------------------------------------------------
  useEffect(() => {
    const onResize = () => setMobile(window.innerWidth < 900);
    onResize(); window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  useEffect(() => { if (mobile) setSideOpen(false); }, [mobile]);
  useEffect(() => {
    const sync = () => {
      if (baseExplicit) return;
      const t = document.documentElement.getAttribute("data-theme");
      const dark = t === "dark" || (!t && window.matchMedia("(prefers-color-scheme: dark)").matches);
      setBase(dark ? "dark" : "light");
    };
    sync();
    window.addEventListener("atlas-theme", sync);
    const mq = window.matchMedia("(prefers-color-scheme: dark)"); mq.addEventListener("change", sync);
    return () => { window.removeEventListener("atlas-theme", sync); mq.removeEventListener("change", sync); };
  }, [baseExplicit]);

  const patch = useCallback((p: Partial<Filters>) => setFilters((f) => ({ ...f, ...p })), []);
  const clearFilters = useCallback(() => setFilters(parseFilters(new URLSearchParams())), []);
  const setLayers = useCallback((p: Partial<typeof layers>) => setLayersState((l) => ({ ...l, ...p })), []);

  const fqs = useMemo(() => filtersToParams(filters).toString(), [filters]);
  const tilesUrl = useMemo(() => `${typeof window === "undefined" ? "" : window.location.origin}/api/tiles/{z}/{x}/{y}?${fqs}${layers.cluster ? "" : `${fqs ? "&" : ""}cluster=0`}`, [fqs, layers.cluster]);

  // URL state --------------------------------------------------------------------------------------------------------------
  useEffect(() => {
    const t = setTimeout(() => {
      const p = filtersToParams(filters);
      p.set("v", `${view.lat.toFixed(4)},${view.lng.toFixed(4)},${view.zoom.toFixed(2)}`);
      if (selected) { p.set("sel", selected.id); if (drawerOpen) { p.set("d", "1"); if (tab !== "overview") p.set("tab", tab); } }
      if (baseExplicit) p.set("base", base);
      if (!layers.cluster) p.set("cl", "0");
      if (!layers.sizeByMw) p.set("sz", "0");
      if (layers.boundaries) p.set("bd", "1");
      window.history.replaceState(null, "", `${window.location.pathname}?${p.toString()}`);
    }, 350);
    return () => clearTimeout(t);
  }, [filters, view, selected, drawerOpen, tab, base, baseExplicit, layers.cluster, layers.sizeByMw, layers.boundaries]);

  // resolve coordinates of a selection that came from the URL
  useEffect(() => {
    if (selected && Number.isNaN(selected.lon)) {
      fetch(`/api/assets?ids=${selected.id}&pageSize=1`).then((r) => r.json()).then((d) => {
        const a = d.items?.[0] as AssetRow | undefined;
        if (a?.lon != null) { setSelected({ id: a.asset_id, lon: a.lon, lat: a.lat! }); mapRef.current?.flyTo(a.lon, a.lat!, 12, { right: drawerOpen && !mobile ? 456 : 0 }); }
      });
    }
  }, [selected]);

  const select = useCallback((id: string, lon?: number | null, lat?: number | null, open = true, fly = true) => {
    setSelected({ id, lon: lon ?? NaN, lat: lat ?? NaN });
    if (open) { setDrawerOpen(true); setTab("overview"); }
    if (lon != null && lat != null && fly) mapRef.current?.flyTo(lon, lat, 12.5, { right: mobile ? 0 : 456 });
    if (mobile) setSideOpen(false);
  }, [mobile]);

  const goto = useCallback((lat: number, lon: number) => { mapRef.current?.flyTo(lon, lat, 11.5); mapRef.current?.showPoint(lon, lat); }, []);

  // GIS tools --------------------------------------------------------------------------------------------------------------
  const fmtSummary = (s: Record<string, any>) => { // eslint-disable-line @typescript-eslint/no-explicit-any
    const lab: Record<string, string> = { wind: "wind", solar: "solar", storage: "storage", hydro: "hydro", marine: "marine", bioenergy: "bioenergy", hybrid: "hybrid", other_low_carbon: "other low-carbon", geothermal: "geothermal" };
    const parts = Object.entries(s.byFamily ?? {}).map(([k, v]: [string, any]) => `${v.n} ${lab[k] ?? k}`); // eslint-disable-line @typescript-eslint/no-explicit-any
    return [parts.join(" · ") || "No assets", `Turbines (as reported): ${fmtNum(s.turbines_reported, 0)}`, `Operational: ${fmtMw(s.operational_mw)} · Pipeline: ${fmtMw(s.pipeline_mw)}`, `Storage: ${fmtMw(s.storage_mw)}${s.storage_mwh ? ` / ${fmtNum(s.storage_mwh, 0)} MWh` : ""}`];
  };
  const onTool = useCallback(async (e: ToolEvent) => {
    if (e.type === "coords") {
      const { e: E, n: N } = wgs84ToBng(e.lon, e.lat);
      const w = `${e.lat.toFixed(6)}, ${e.lon.toFixed(6)}`, b = `${Math.round(E)}, ${Math.round(N)}`;
      setToolResult({ title: "Clicked location", lines: [`WGS84: ${w}`, `BNG: E ${Math.round(E)} N ${Math.round(N)}`], copy: [{ label: "Copy WGS84", text: w }, { label: "Copy BNG", text: b }] });
    } else if (e.type === "measure") {
      setToolResult({ title: e.kind === "distance" ? "Distance" : "Area", lines: e.kind === "distance" ? [`${fmtNum(e.value / 1000, 3)} km (${fmtNum(e.value, 0)} m)`] : [`${fmtNum(e.value / 10000, 2)} ha`, `${fmtNum(e.value / 1e6, 3)} km²`], note: e.done ? undefined : "Double-click to finish." });
    } else if (e.type === "radius") {
      const r = await fetch(`/api/nearby?${fqs}&lat=${e.lat}&lon=${e.lon}&radius_m=${Math.round(e.radius_m)}`).then((x) => x.json());
      setToolResult({ title: `Within ${fmtNum(e.radius_m / 1000, 1)} km`, lines: fmtSummary(r.summary), items: r.items, note: r.truncated ? "List truncated; statistics use the returned items." : "Filters apply to this search." });
    } else if (e.type === "polygon") {
      const r = await fetch(`/api/within?${fqs}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ polygon: e.polygon }) }).then((x) => x.json());
      setToolResult(r.error ? { title: "Polygon search", lines: [r.error] } : { title: "Inside polygon", lines: fmtSummary(r.summary), items: r.items });
    } else if (e.type === "nearest") {
      const r = await fetch(`/api/nearest?${fqs}&lat=${e.lat}&lon=${e.lon}&kind=${e.kind}&n=6`).then((x) => x.json());
      setToolResult({ title: e.kind === "asset" ? "Nearest assets" : "Nearest turbines", lines: [], items: r.items, note: r.note });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fqs]);

  const toggleCompare = useCallback((id: string) => setCompare((c) => (c.includes(id) ? c.filter((x) => x !== id) : c.length >= 5 ? c : [...c, id])), []);
  const n = activeCount(filters);
  const tableHref = `/assets?${fqs}`;
  const sideW = 332, drawerW = 456;

  const saveView = () => {
    const name = window.prompt("Name this view", "My view");
    if (name) setViews((v) => [...v.filter((x) => x.name !== name), { name, qs: window.location.search.replace(/^\?/, "") }]);
  };
  const applyView = (qs: string) => {
    const p = new URLSearchParams(qs);
    setFilters(parseFilters(p)); const v = viewFrom(p, mobile);
    mapRef.current?.flyTo(v.lng, v.lat, v.zoom);
    if (p.get("base") && (p.get("base") as BaseId) in BASEMAPS) { setBase(p.get("base") as BaseId); setBaseExplicit(true); }
  };

  const sidebar = (
    <aside aria-label="Filters and results" style={{ width: mobile ? "min(92vw, 360px)" : sideW, background: "var(--surface)", borderRight: "1px solid var(--line)", display: sideOpen ? "flex" : "none", flexDirection: "column", minHeight: 0, ...(mobile ? { position: "absolute", zIndex: 25, top: 0, bottom: 0, left: 0, boxShadow: "var(--shadow)" } : {}) }}>
      <Tabs label="Sidebar" active={side} onChange={(t) => setSide(t as SideTab)} tabs={[{ id: "filters", label: "Filters", badge: n ? <span className="chip" style={{ marginLeft: 4 }}>{n}</span> : undefined }, { id: "results", label: "Results" }, { id: "saved", label: "Saved views" }]} />
      <div id={`panel-${side}`} role="tabpanel" aria-labelledby={`tab-${side}`} style={{ flex: 1, minHeight: 0, overflow: side === "results" ? "hidden" : "auto" }}>
        {side === "filters" && <FilterPanel f={filters} patch={patch} facets={facets} meta={meta} onClear={clearFilters} />}
        {side === "results" && <ResultsList f={filters} qs={fqs} meta={meta} selectedId={selected?.id ?? null} onSelect={(a) => select(a.asset_id, a.lon, a.lat)} compare={compare} onCompare={toggleCompare} tableHref={tableHref} />}
        {side === "saved" && (
          <div style={{ padding: 12 }}>
            <p style={{ marginTop: 0 }} className="muted">Views are stored in this browser. Copy the address-bar URL to share the exact state (filters, map position, selection).</p>
            <div style={{ display: "flex", gap: 6, marginBottom: 10, flexWrap: "wrap" }}><button type="button" className="btn sm primary" onClick={saveView}>Save current view</button><CopyButton text={typeof window !== "undefined" ? window.location.href : ""} label="Copy link" /></div>
            {views.length === 0 && <p className="muted">No saved views yet. Examples: “Scottish operational wind”, “50 MW+ BESS pipeline in England”.</p>}
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>{views.map((v) => <li key={v.name} style={{ display: "flex", gap: 6, padding: "4px 0", borderBottom: "1px solid var(--line-2)" }}><button type="button" className="btn ghost sm" style={{ flex: 1, justifyContent: "flex-start" }} onClick={() => applyView(v.qs)}>{v.name}</button><button type="button" className="btn ghost sm" aria-label={`Delete view ${v.name}`} onClick={() => setViews((x) => x.filter((y) => y.name !== v.name))}>✕</button></li>)}</ul>
          </div>
        )}
      </div>
    </aside>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100dvh" }}>
      <header className="no-print" style={{ background: "var(--surface)", borderBottom: "1px solid var(--line)", display: "flex", alignItems: "center", gap: 10, padding: "6px 12px", flexWrap: "nowrap" }}>
        <button type="button" className="btn sm" aria-expanded={sideOpen} aria-controls="sidebar" onClick={() => setSideOpen(!sideOpen)} aria-label="Toggle filters and results panel">☰ {n ? `Filters (${n})` : "Filters"}</button>
        <div style={{ minWidth: 0, flex: "none", display: mobile ? "none" : "block" }}>
          <div style={{ fontWeight: 700, fontSize: 14.5, color: "var(--brand)", lineHeight: 1.1 }}>{SITE}</div>
          {!mobile && <div className="muted" style={{ fontSize: 11 }}>Renewable generation, storage, planning and grid intelligence across Great Britain.</div>}
        </div>
        <SearchBox onAsset={(id, lon, lat) => select(id, lon, lat)} onFilters={patch} onGoto={goto} onText={(q) => { patch({ q }); setSide("results"); setSideOpen(true); }} />
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8, position: "relative" }}>
          {!mobile && <DataDate meta={meta} />}
          <details className="pages-menu" style={{ position: "relative" }}>
            <summary className="btn sm" style={{ listStyle: "none" }}>Pages ▾</summary>
            <nav aria-label="Pages" className="panel" style={{ position: "absolute", right: 0, top: 30, zIndex: 40, minWidth: 170, padding: 4, boxShadow: "var(--shadow)", display: "flex", flexDirection: "column" }}>
              {NAV.slice(1).map((l) => <Link key={l.href} href={l.href} className="btn ghost sm" style={{ justifyContent: "flex-start" }}>{l.label}</Link>)}
            </nav>
          </details>
          <button type="button" className="btn sm" aria-expanded={settingsOpen} onClick={() => setSettingsOpen(!settingsOpen)}>{mobile ? "⚙" : "Settings"}</button>
          {settingsOpen && (
            <div role="dialog" aria-label="Settings" className="panel" style={{ position: "absolute", right: 0, top: 34, zIndex: 40, width: 250, padding: 12, boxShadow: "var(--shadow)" }}>
              <label style={{ display: "block", marginBottom: 8 }}>Basemap<br /><select className="input" style={{ width: "100%" }} value={base} onChange={(e) => { setBase(e.target.value as BaseId); setBaseExplicit(true); }}>{(Object.keys(BASEMAPS) as BaseId[]).map((k) => <option key={k} value={k}>{BASEMAPS[k].label}</option>)}</select></label>
              <div style={{ marginBottom: 8 }}><ThemeToggle /></div>
              <label style={{ display: "flex", gap: 6, marginBottom: 4 }}><input type="checkbox" checked={layers.cluster} onChange={(e) => setLayers({ cluster: e.target.checked })} /> Cluster markers at national zoom</label>
              <label style={{ display: "flex", gap: 6, marginBottom: 4 }}><input type="checkbox" checked={layers.boundaries} onChange={(e) => setLayers({ boundaries: e.target.checked })} /> Local authority boundaries (ONS)</label>
              <label style={{ display: "flex", gap: 6 }}><input type="checkbox" checked={layers.sizeByMw} onChange={(e) => setLayers({ sizeByMw: e.target.checked })} /> Marker size reflects MW</label>
              <p className="muted" style={{ marginBottom: 0 }}>Basemap licences vary by provider; see Methodology › Licensing.</p>
            </div>
          )}
        </div>
      </header>

      <div style={{ flex: 1, minHeight: 0, display: "flex", position: "relative" }}>
        {sidebar}
        <div style={{ flex: 1, position: "relative", minWidth: 0 }} id="main" role="main">
          <MapView ref={mapRef} tilesUrl={tilesUrl} techs={meta?.technologies ?? []} base={base} dark={BASEMAPS[base].dark} sizeByMw={layers.sizeByMw} showLeases={layers.leases} showTurbines={layers.turbines} showLabels={layers.labels} showBoundaries={layers.boundaries}
            initialView={initialView} selected={selected && !Number.isNaN(selected.lon) ? selected : null} tool={tool}
            onViewChange={setView} onSelect={(id, how, lon, lat) => (how === "popup" ? setSelected({ id, lon: lon ?? NaN, lat: lat ?? NaN }) : select(id, lon, lat, true, false))}
            onPointer={(lat, lon) => setPointer({ lat, lon })} onTool={onTool} />
          {meta && (
            <div style={{ position: "absolute", top: 10, left: 10, right: drawerOpen && !mobile ? drawerW + 20 : 10, zIndex: 3, pointerEvents: "none" }}>
              <div style={{ pointerEvents: "auto", maxWidth: 820 }}><StatsBar qs={fqs} onOpenDashboard={() => { window.location.href = `/dashboard?${fqs}`; }} /></div>
            </div>
          )}
          {!mobile && <div style={{ position: "absolute", left: 8, bottom: 62, zIndex: 3 }} className="panel"><div style={{ padding: "2px 8px", fontSize: 11.5 }}><CoordReadout lat={pointer.lat} lon={pointer.lon} /></div></div>}
          <div style={{ position: "absolute", right: drawerOpen && !mobile ? drawerW + 12 : 10, bottom: 64, display: "flex", flexDirection: "column", gap: 8, alignItems: "flex-end", zIndex: 3, maxWidth: "calc(100% - 20px)" }}>
            <Tools tool={tool} setTool={setTool} result={toolResult} onClear={() => { setToolResult(null); mapRef.current?.clearDraw(); }} radiusM={radiusM} setRadiusM={setRadiusM}
              onPick={(id, lon, lat) => select(id, lon, lat)} onGoto={goto} />
            {!mobile && <Legend meta={meta} facets={facets} layers={layers} setLayers={setLayers} />}
          </div>
          {compare.length > 0 && (
            <div className="panel" style={{ position: "absolute", left: "50%", transform: "translateX(-50%)", bottom: 70, zIndex: 4, padding: "6px 10px", display: "flex", gap: 8, alignItems: "center", boxShadow: "var(--shadow)" }}>
              <strong>Compare</strong>{compare.map((id) => <span key={id} className="chip">{id}<button type="button" aria-label={`Remove ${id}`} onClick={() => toggleCompare(id)} style={{ all: "unset", cursor: "pointer", marginLeft: 4 }}>✕</button></span>)}
              <Link className={`btn sm ${compare.length >= 2 ? "primary" : ""}`} aria-disabled={compare.length < 2} href={compare.length >= 2 ? `/compare?ids=${compare.join(",")}` : "#"}>Compare ({compare.length}/5)</Link>
            </div>
          )}
        </div>
        {drawerOpen && selected && (
          <aside aria-label="Asset details" style={mobile
            ? { position: "absolute", left: 0, right: 0, bottom: 0, height: "64vh", background: "var(--surface)", borderTop: "1px solid var(--line)", boxShadow: "var(--shadow)", zIndex: 26, display: "flex", flexDirection: "column", borderRadius: "10px 10px 0 0" }
            : { position: "absolute", top: 0, right: 0, bottom: 0, width: drawerW, background: "var(--surface)", borderLeft: "1px solid var(--line)", boxShadow: "var(--shadow)", zIndex: 6, display: "flex", flexDirection: "column" }}>
            <button type="button" className="btn ghost sm" aria-label="Close details" onClick={() => setDrawerOpen(false)} style={{ position: "absolute", top: 6, right: 6, zIndex: 2 }}>✕</button>
            <AssetDetail id={selected.id} meta={meta} tab={tab} onTab={setTab} onZoom={(lon, lat) => mapRef.current?.flyTo(lon, lat, 15, { right: mobile ? 0 : 456 })} compare={compare} onCompare={toggleCompare} onReport={() => setReport(selected.id)} />
          </aside>
        )}
      </div>

      {report !== undefined && <ReportDialog assetId={report} onClose={() => setReport(undefined)} />}
    </div>
  );
}

export function ReportDialog({ assetId, onClose }: { assetId: string | null; onClose: () => void }) {
  const [state, setState] = useState<{ ok?: string; err?: string; busy?: boolean }>({});
  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setState({ busy: true });
    const r = await fetch("/api/reports", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ asset_id: assetId, report_type: fd.get("type"), description: fd.get("description"), evidence_url: fd.get("evidence"), contact: fd.get("contact") }) });
    const d = await r.json();
    setState(r.ok ? { ok: d.message } : { err: d.error });
  };
  return (
    <div role="dialog" aria-modal="true" aria-label="Report an issue" style={{ position: "fixed", inset: 0, background: "rgba(8,17,30,.5)", zIndex: 60, display: "grid", placeItems: "center", padding: 12 }} onClick={onClose}>
      <form className="panel" onSubmit={submit} onClick={(e) => e.stopPropagation()} style={{ width: 460, maxWidth: "100%", padding: 16, boxShadow: "var(--shadow)" }}>
        <h2 style={{ fontSize: 16, marginBottom: 8 }}>Report an issue{assetId ? ` – ${assetId}` : ""}</h2>
        <p className="muted" style={{ marginTop: 0 }}>Corrections are reviewed by a person and never published automatically. A link to supporting evidence is required.</p>
        <label style={{ display: "block", marginBottom: 8 }}>Type<br /><select name="type" className="input" style={{ width: "100%" }}><option value="incorrect_info">Incorrect information</option><option value="missing_project">Missing project</option><option value="incorrect_turbine_location">Incorrect turbine location</option><option value="incorrect_status">Incorrect status</option><option value="broken_source">Broken source link</option><option value="other">Other</option></select></label>
        <label style={{ display: "block", marginBottom: 8 }}>What is wrong?<br /><textarea name="description" required minLength={10} maxLength={2000} rows={4} className="input" style={{ width: "100%", height: "auto", padding: 6, boxSizing: "border-box" }} /></label>
        <label style={{ display: "block", marginBottom: 8 }}>Evidence URL (required)<br /><input name="evidence" required type="url" className="input" style={{ width: "100%", boxSizing: "border-box" }} placeholder="https://…" /></label>
        <label style={{ display: "block", marginBottom: 8 }}>Contact (optional)<br /><input name="contact" className="input" style={{ width: "100%", boxSizing: "border-box" }} /></label>
        {state.err && <p role="alert" style={{ color: "var(--bad)" }}>{state.err}</p>}{state.ok && <p role="status" style={{ color: "var(--ok)" }}>{state.ok}</p>}
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}><button type="button" className="btn" onClick={onClose}>Close</button><button className="btn primary" disabled={state.busy || !!state.ok}>Submit for review</button></div>
      </form>
    </div>
  );
}
void DEFAULT_CAT; void DEFAULT_KIND; void DEFAULT_STAGE;
