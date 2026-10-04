"use client";
import maplibregl, { type Map as MLMap, type MapGeoJSONFeature } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import area from "@turf/area";
import length from "@turf/length";
import { BASEMAPS, CLICKABLE, LAYERS, SRC, addAtlasLayers, setVisibility, type BaseId } from "@/lib/mapStyle";
import { drawIcon, type Pattern } from "@/lib/glyphs";
import { bngToWgs84, circlePolygon, haversineM, wgs84ToBng } from "@/lib/geo";
import type { Tech } from "@/lib/types";
import { fmtMw } from "@/lib/format";

export type ToolMode = "none" | "coords" | "distance" | "area" | "radius" | "polygon" | "nearest-asset" | "nearest-turbine";
export type ToolEvent =
  | { type: "coords"; lat: number; lon: number }
  | { type: "measure"; kind: "distance" | "area"; value: number; done: boolean }
  | { type: "radius"; lat: number; lon: number; radius_m: number }
  | { type: "polygon"; polygon: GeoJSON.Polygon }
  | { type: "nearest"; kind: "asset" | "turbine"; lat: number; lon: number };

export interface MapHandle {
  flyTo(lon: number, lat: number, zoom?: number, padding?: { left?: number; right?: number }): void;
  fitBounds(b: [number, number, number, number]): void;
  getView(): { lng: number; lat: number; zoom: number };
  clearDraw(): void;
  showPoint(lon: number, lat: number): void;
  showGeometry(g: GeoJSON.Feature | GeoJSON.FeatureCollection): void;
  resize(): void;
}

export interface MapViewProps {
  tilesUrl: string;
  techs: Tech[];
  base: BaseId;
  dark: boolean;
  sizeByMw: boolean; showLeases: boolean; showTurbines: boolean; showLabels: boolean; showBoundaries: boolean;
  initialView: { lng: number; lat: number; zoom: number };
  selected: { id: string; lon: number; lat: number } | null;
  tool: ToolMode;
  onViewChange: (v: { lng: number; lat: number; zoom: number }) => void;
  onSelect: (id: string, how: "popup" | "details", lon?: number, lat?: number) => void;
  onPointer: (lat: number, lon: number) => void;
  onTool: (e: ToolEvent) => void;
  onZoomFlag?: (z: number) => void;
}

const cap = (v: unknown) => (typeof v === "number" ? v : Number(v));

const MapView = forwardRef<MapHandle, MapViewProps>(function MapView(props, ref) {
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const propsRef = useRef(props);
  propsRef.current = props;
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const tipRef = useRef<HTMLDivElement | null>(null);
  const drawRef = useRef<{ pts: [number, number][]; center?: [number, number] }>({ pts: [] });
  const lastBase = useRef<BaseId | null>(null);

  useImperativeHandle(ref, () => ({
    flyTo: (lon, lat, zoom, padding) => mapRef.current?.flyTo({ center: [lon, lat], zoom: zoom ?? Math.max(mapRef.current.getZoom(), 12), essential: true, padding: { top: 0, bottom: 0, left: padding?.left ?? 0, right: padding?.right ?? 0 } }),
    fitBounds: (b) => mapRef.current?.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 60, maxZoom: 14 }),
    getView: () => { const m = mapRef.current!; const c = m.getCenter(); return { lng: c.lng, lat: c.lat, zoom: m.getZoom() }; },
    clearDraw: () => { drawRef.current = { pts: [] }; (mapRef.current?.getSource("draw") as maplibregl.GeoJSONSource | undefined)?.setData({ type: "FeatureCollection", features: [] }); },
    showPoint: (lon, lat) => (mapRef.current?.getSource("draw") as maplibregl.GeoJSONSource | undefined)?.setData({ type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [lon, lat] } }] }),
    showGeometry: (g) => (mapRef.current?.getSource("draw") as maplibregl.GeoJSONSource | undefined)?.setData(g.type === "FeatureCollection" ? g : { type: "FeatureCollection", features: [g] }),
    resize: () => mapRef.current?.resize(),
  }));

  // ---- create the map once --------------------------------------------------------------------------------------------
  useEffect(() => {
    if (!el.current || mapRef.current) return;
    const p = propsRef.current;
    const map = new maplibregl.Map({
      container: el.current,
      style: BASEMAPS[p.base].style as never,
      center: [p.initialView.lng, p.initialView.lat], zoom: p.initialView.zoom, minZoom: 3.2, maxZoom: 20,
      maxBounds: [[-16, 48], [8, 62]],
      attributionControl: false, dragRotate: false, pitchWithRotate: false, touchPitch: false, fadeDuration: 120,
    });
    mapRef.current = map;
    lastBase.current = p.base;
    if (process.env.NODE_ENV !== "production") (window as unknown as { __atlasMap?: MLMap }).__atlasMap = map; // handy for e2e/debugging
    map.on("error", (e) => console.warn("maplibre:", (e as { error?: Error }).error?.message ?? e));
    map.touchZoomRotate.disableRotation();
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric", maxWidth: 110 }), "bottom-left");
    map.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: [
      "Contains public sector information licensed under the OGL v3.0 (DESNZ REPD, ONS)",
      "Contains data provided by The Crown Estate that is protected by copyright and database rights.",
      BASEMAPS[p.base].attribution,
    ] }), "bottom-left");

    // icons are drawn on demand: technology shape × status pattern
    map.on("styleimagemissing", (e) => {
      const [tech, pattern] = e.id.split("|") as [string, Pattern];
      const t = propsRef.current.techs.find((x) => x.code === tech);
      if (!t || !pattern) return;
      const size = 40, c = document.createElement("canvas"); c.width = c.height = size;
      const ctx = c.getContext("2d")!;
      drawIcon(ctx, size, t.symbol, t.colour, pattern, BASEMAPS[propsRef.current.base].dark);
      if (!map.hasImage(e.id)) map.addImage(e.id, ctx.getImageData(0, 0, size, size), { pixelRatio: 2 });
    });

    const ensureLayers = () => {
      const q = propsRef.current;
      addAtlasLayers(map, { tilesUrl: q.tilesUrl, techs: q.techs, dark: BASEMAPS[q.base].dark, sizeByMw: q.sizeByMw, showLeases: q.showLeases, showTurbines: q.showTurbines, showLabels: q.showLabels, plain: q.base === "plain", showBoundaries: q.showBoundaries });
    };
    const applySelected = () => {
      const sel = propsRef.current.selected;
      (map.getSource("selected") as maplibregl.GeoJSONSource | undefined)?.setData(sel ? { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [sel.lon, sel.lat] } }] } : { type: "FeatureCollection", features: [] });
    };
    map.on("style.load", () => { ensureLayers(); applySelected(); });
    map.on("load", () => {
      ensureLayers();
      // start with the (long) attribution collapsed behind the ⓘ button so it never covers the map
      applySelected();
      const at = el.current?.querySelector(".maplibregl-ctrl-attrib");
      at?.removeAttribute("open"); at?.classList.remove("maplibregl-compact-show");
    });

    // ---- pointer & clicks ------------------------------------------------------------------------------------------
    const tip = document.createElement("div");
    tip.setAttribute("role", "tooltip");
    Object.assign(tip.style, { position: "absolute", pointerEvents: "none", zIndex: "5", display: "none", padding: "3px 7px", borderRadius: "3px", font: "12px system-ui", background: "var(--ink)", color: "var(--surface)", maxWidth: "260px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" });
    el.current.appendChild(tip);
    tipRef.current = tip;

    const hitLayers = () => CLICKABLE.filter((id) => map.getLayer(id));
    map.on("mousemove", (e) => {
      propsRef.current.onPointer(e.lngLat.lat, e.lngLat.lng);
      const tool = propsRef.current.tool;
      if (tool !== "none") { onToolMove(e.lngLat.lng, e.lngLat.lat); return; }
      const f = map.queryRenderedFeatures(e.point, { layers: hitLayers() })[0];
      map.getCanvas().style.cursor = f ? "pointer" : "";
      if (f) {
        const pr = f.properties as Record<string, unknown>;
        tip.textContent = f.layer.id === LAYERS.clusterCircle ? `${pr.n} assets · ${fmtMw(cap(pr.mw))} (zoom to expand)` : String(pr.name ?? pr.asset_name ?? pr.unit_code ?? "Asset");
        tip.style.display = "block"; tip.style.left = `${e.point.x + 12}px`; tip.style.top = `${e.point.y + 12}px`;
      } else tip.style.display = "none";
    });
    map.on("mouseout", () => { tip.style.display = "none"; });
    map.on("moveend", () => { const c = map.getCenter(); propsRef.current.onViewChange({ lng: c.lng, lat: c.lat, zoom: map.getZoom() }); });

    const showPopup = (f: MapGeoJSONFeature, lngLat: maplibregl.LngLat) => {
      const pr = f.properties as Record<string, unknown>;
      popupRef.current?.remove();
      const id = String(pr.asset_id ?? "");
      const box = document.createElement("div");
      box.style.cssText = "font:12.5px/1.45 system-ui;min-width:250px;max-width:300px";
      const title = document.createElement("div"); title.style.cssText = "font-weight:600;font-size:14px;margin-bottom:4px;padding-right:14px"; title.textContent = String(pr.name ?? "Asset"); box.appendChild(title);
      const meta = document.createElement("div"); meta.className = "muted"; meta.textContent = "Loading…"; box.appendChild(meta);
      const btns = document.createElement("div"); btns.style.cssText = "display:flex;gap:6px;margin-top:8px;flex-wrap:wrap";
      const mk = (label: string, fn: () => void, primary = false) => { const b = document.createElement("button"); b.type = "button"; b.className = `btn sm${primary ? " primary" : ""}`; b.textContent = label; b.onclick = fn; btns.appendChild(b); };
      mk("View full details", () => propsRef.current.onSelect(id, "details", lngLat.lng, lngLat.lat), true);
      mk("Zoom to project", () => { map.flyTo({ center: lngLat, zoom: Math.max(map.getZoom(), 13.5), essential: true }); });
      mk("View sources", () => propsRef.current.onSelect(id, "details", lngLat.lng, lngLat.lat));
      box.appendChild(btns);
      const popup = new maplibregl.Popup({ closeButton: true, maxWidth: "320px", offset: 14 }).setLngLat(lngLat).setDOMContent(box).addTo(map);
      popupRef.current = popup;
      propsRef.current.onSelect(id, "popup", lngLat.lng, lngLat.lat);
      fetch(`/api/assets?ids=${encodeURIComponent(id)}&pageSize=1`).then((r) => r.json()).then((d) => {
        const a = d.items?.[0]; if (!a) { meta.textContent = ""; return; }
        meta.textContent = "";
        const rows: [string, string][] = [
          ["Technology", a.technology_label], ["Status", a.status_label],
          ["Capacity", a.installed_capacity_mw != null ? fmtMw(a.installed_capacity_mw) : "Unknown"],
          ...(a.family === "wind" ? [["Turbines", a.turbine_count != null ? `${a.turbine_count} (as reported)` : "Unknown"] as [string, string]] : []),
          ...(a.family === "storage" ? [["Energy", a.storage_capacity_mwh != null ? `${a.storage_capacity_mwh} MWh` : "Not publicly identified"] as [string, string]] : []),
          ["Operator", a.operator ?? "Unknown"], ["Commissioned", a.commissioning_year ?? "—"], ["Confidence", a.confidence],
        ];
        const dl = document.createElement("dl"); dl.className = "kv"; dl.style.gridTemplateColumns = "88px 1fr";
        for (const [k, v] of rows) { const dt = document.createElement("dt"); dt.textContent = k; const dd = document.createElement("dd"); dd.textContent = String(v); dl.append(dt, dd); }
        meta.appendChild(dl);
      }).catch(() => { meta.textContent = "Summary unavailable"; });
    };

    // ---- tools ------------------------------------------------------------------------------------------------------
    const drawData = (features: GeoJSON.Feature[]) => (map.getSource("draw") as maplibregl.GeoJSONSource | undefined)?.setData({ type: "FeatureCollection", features });
    const line = (pts: [number, number][]): GeoJSON.Feature => ({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: pts } });
    const poly = (pts: [number, number][]): GeoJSON.Feature<GeoJSON.Polygon> => ({ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[...pts, pts[0]]] } });
    const dots = (pts: [number, number][]): GeoJSON.Feature[] => pts.map((c) => ({ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: c } }));
    const refresh = (hover?: [number, number]) => {
      const t = propsRef.current.tool, d = drawRef.current;
      if (t === "distance") { const pts = hover && d.pts.length ? [...d.pts, hover] : d.pts; drawData([...(pts.length > 1 ? [line(pts)] : []), ...dots(d.pts)]); if (pts.length > 1) propsRef.current.onTool({ type: "measure", kind: "distance", value: length(line(pts) as GeoJSON.Feature<GeoJSON.LineString>, { units: "kilometers" }) * 1000, done: false }); }
      if ((t === "area" || t === "polygon") && d.pts.length) { const pts = hover ? [...d.pts, hover] : d.pts; drawData([...(pts.length > 2 ? [poly(pts)] : [line(pts)]), ...dots(d.pts)]); if (pts.length > 2 && t === "area") propsRef.current.onTool({ type: "measure", kind: "area", value: area(poly(pts)), done: false }); }
      if (t === "radius" && d.center) { const r = hover ? haversineM(d.center[1], d.center[0], hover[1], hover[0]) : 0; drawData([...dots([d.center]), ...(r > 0 ? [circlePolygon(d.center[1], d.center[0], r)] : [])]); }
    };
    function onToolMove(lng: number, lat: number) { if (propsRef.current.tool !== "none") refresh([lng, lat]); }
    map.on("click", (e) => {
      const tool = propsRef.current.tool, p = e.lngLat;
      if (tool === "none") {
        const f = map.queryRenderedFeatures(e.point, { layers: hitLayers() })[0];
        if (!f) { popupRef.current?.remove(); return; }
        const pr = f.properties as Record<string, unknown>;
        if (f.layer.id === LAYERS.clusterCircle) { map.easeTo({ center: p, zoom: Math.min(map.getZoom() + 2.2, 9), duration: 450 }); return; }
        showPopup(f, p); return;
      }
      const pt: [number, number] = [p.lng, p.lat];
      if (tool === "coords") { propsRef.current.onTool({ type: "coords", lat: p.lat, lon: p.lng }); drawData(dots([pt])); }
      else if (tool === "nearest-asset" || tool === "nearest-turbine") { drawData(dots([pt])); propsRef.current.onTool({ type: "nearest", kind: tool === "nearest-asset" ? "asset" : "turbine", lat: p.lat, lon: p.lng }); }
      else if (tool === "radius") {
        const d = drawRef.current;
        if (!d.center) { d.center = pt; refresh(pt); }
        else { const r = haversineM(d.center[1], d.center[0], p.lat, p.lng); propsRef.current.onTool({ type: "radius", lat: d.center[1], lon: d.center[0], radius_m: Math.max(100, r) }); drawData([...dots([d.center]), circlePolygon(d.center[1], d.center[0], Math.max(100, r))]); drawRef.current = { pts: [] }; }
      } else { drawRef.current.pts.push(pt); refresh(); }
    });
    map.on("dblclick", (e) => {
      const tool = propsRef.current.tool, d = drawRef.current;
      if (tool === "distance" && d.pts.length > 1) { e.preventDefault(); propsRef.current.onTool({ type: "measure", kind: "distance", value: length(line(d.pts) as GeoJSON.Feature<GeoJSON.LineString>, { units: "kilometers" }) * 1000, done: true }); drawRef.current = { pts: [] }; }
      if ((tool === "area" || tool === "polygon") && d.pts.length > 2) {
        e.preventDefault();
        const pts = d.pts.slice(0, -1).length > 2 ? d.pts.slice(0, -1) : d.pts; // the double-click registered one extra vertex
        drawData([poly(pts)]);
        if (tool === "area") propsRef.current.onTool({ type: "measure", kind: "area", value: area(poly(pts)), done: true });
        else propsRef.current.onTool({ type: "polygon", polygon: poly(pts).geometry });
        drawRef.current = { pts: [] };
      }
    });
    return () => { map.remove(); mapRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- reactive updates -----------------------------------------------------------------------------------------------
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const src = map.getSource(SRC) as maplibregl.VectorTileSource | undefined;
    if (src?.setTiles) src.setTiles([props.tilesUrl]);
  }, [props.tilesUrl]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || lastBase.current === props.base) return;
    lastBase.current = props.base;
    map.setStyle(BASEMAPS[props.base].style as never, { diff: false });
  }, [props.base]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    setVisibility(map, [LAYERS.leaseFill, LAYERS.leaseLine], props.showLeases);
    setVisibility(map, [LAYERS.turbines, LAYERS.turbineLabels], props.showTurbines);
    setVisibility(map, [LAYERS.assetLabels], props.showLabels);
    const lad = props.base === "plain" || props.showBoundaries;
    setVisibility(map, ["lad-line", "lad-label"], lad);
    setVisibility(map, ["lad-fill"], props.base === "plain");
  }, [props.showLeases, props.showTurbines, props.showLabels, props.showBoundaries, props.base]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer(LAYERS.assets)) return;
    const capFactor = props.sizeByMw ? ["interpolate", ["linear"], ["sqrt", ["max", ["to-number", ["get", "mw"], 0], 0]], 0, 0.78, 10, 1.0, 20, 1.28, 35, 1.6] : 1;
    map.setLayoutProperty(LAYERS.assets, "icon-size", ["interpolate", ["linear"], ["zoom"], 3, ["*", 0.5, capFactor], 8, ["*", 0.7, capFactor], 13, ["*", 0.95, capFactor]]);
  }, [props.sizeByMw]);

  useEffect(() => {
    const map = mapRef.current;
    const s = map?.getSource("selected") as maplibregl.GeoJSONSource | undefined;
    s?.setData(props.selected ? { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [props.selected.lon, props.selected.lat] } }] } : { type: "FeatureCollection", features: [] });
  }, [props.selected]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    drawRef.current = { pts: [] };
    (map.getSource("draw") as maplibregl.GeoJSONSource | undefined)?.setData({ type: "FeatureCollection", features: [] });
    map.getCanvas().style.cursor = props.tool === "none" ? "" : "crosshair";
    if (props.tool === "polygon" || props.tool === "area" || props.tool === "distance") map.doubleClickZoom.disable(); else map.doubleClickZoom.enable();
    popupRef.current?.remove();
  }, [props.tool]);

  return <div ref={el} style={{ position: "absolute", inset: 0 }} role="application" aria-label="Interactive map of renewable-energy assets in Great Britain" />;
});

export default MapView;
export { bngToWgs84, wgs84ToBng };
