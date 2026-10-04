import type { StyleSpecification } from "maplibre-gl";
import type { Tech } from "./types";

export type BaseId = "light" | "dark" | "topo" | "imagery" | "plain";
const GLYPHS = "https://tiles.basemaps.cartocdn.com/fonts/{fontstack}/{range}.pbf";
export const FONT = ["Montserrat Medium", "Open Sans Bold", "Noto Sans Regular"];

const raster = (tiles: string[], attribution: string, maxzoom: number): StyleSpecification => ({
  version: 8, glyphs: GLYPHS,
  sources: { base: { type: "raster", tiles, tileSize: 256, attribution, maxzoom } },
  layers: [{ id: "base", type: "raster", source: "base" }],
});

/**
 * Basemap catalogue. Licensing differs per provider (CARTO basemaps: attribution + terms for commercial use;
 * OpenTopoMap CC-BY-SA with fair use; Esri imagery under Esri's terms). Override with NEXT_PUBLIC_BASEMAPS_JSON for production.
 */
const plainStyle = (bg: string): StyleSpecification => ({ version: 8, glyphs: GLYPHS, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": bg } }] });

export const BASEMAPS: Record<BaseId, { label: string; style: string | StyleSpecification; attribution: string; dark: boolean }> = {
  light: { label: "Light", style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json", attribution: "© CARTO · © OpenStreetMap contributors", dark: false },
  dark: { label: "Dark", style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json", attribution: "© CARTO · © OpenStreetMap contributors", dark: true },
  topo: {
    label: "Topographic",
    style: raster(["https://a.tile.opentopomap.org/{z}/{x}/{y}.png", "https://b.tile.opentopomap.org/{z}/{x}/{y}.png", "https://c.tile.opentopomap.org/{z}/{x}/{y}.png"],
      "Map data © OpenStreetMap contributors, SRTM · Style © OpenTopoMap (CC-BY-SA)", 17),
    attribution: "© OpenStreetMap contributors, SRTM · © OpenTopoMap", dark: false,
  },
  plain: { label: "Plain (offline – ONS outlines)", style: plainStyle("#cfdae7"), attribution: "Boundaries: ONS (OGL v3.0), Contains OS data © Crown copyright and database right", dark: false },
  imagery: {
    label: "Aerial imagery",
    style: raster(["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
      "Imagery © Esri, Maxar, Earthstar Geographics and the GIS User Community", 19),
    attribution: "Imagery © Esri, Maxar, Earthstar Geographics", dark: true,
  },
};

export const FAMILY_COLOUR: Record<string, string> = {
  wind: "#2f7fb5", solar: "#d98e04", storage: "#7048b8", hydro: "#1c8a8a", marine: "#2b9348", bioenergy: "#8a5a2b",
  geothermal: "#c2410c", hybrid: "#4c6ef5", other_low_carbon: "#6b7280", unknown: "#94a3b8",
};

export function familyColours(techs: Tech[]): Record<string, string> {
  const out = { ...FAMILY_COLOUR };
  for (const t of techs) if (!(t.family in out) || out[t.family] === FAMILY_COLOUR[t.family]) out[t.family] = out[t.family] ?? t.colour;
  return out;
}

export const SRC = "atlas";
export const LAYERS = {
  leaseFill: "lease-fill", leaseLine: "lease-line", clusterCircle: "clusters-circle", clusterCount: "clusters-count", clusterSingle: "clusters-single",
  assets: "assets", assetLabels: "assets-label", turbines: "turbines", turbineLabels: "turbines-label", selected: "selected-ring",
  drawFill: "draw-fill", drawLine: "draw-line", drawPoints: "draw-points",
} as const;
export const CLICKABLE = [LAYERS.assets, LAYERS.clusterCircle, LAYERS.clusterSingle, LAYERS.turbines];

type Expr = unknown[];

export interface LayerOpts { tilesUrl: string; techs: Tech[]; dark: boolean; sizeByMw: boolean; showLeases: boolean; showTurbines: boolean; showLabels: boolean; plain?: boolean; showBoundaries?: boolean }

/** Add sources + layers for the atlas data. Idempotent: safe to call after every style load. */
export function addAtlasLayers(map: import("maplibre-gl").Map, o: LayerOpts): void {
  const techMatch: Expr = ["match", ["get", "technology_code"]];
  for (const t of o.techs) techMatch.push(t.code, t.colour);
  techMatch.push("#64748b");
  const famColours = familyColours(o.techs);
  const famMatch: Expr = ["match", ["get", "top_family"]];
  for (const [f, c] of Object.entries(famColours)) famMatch.push(f, c);
  famMatch.push("#64748b");

  if (!map.getSource(SRC)) map.addSource(SRC, { type: "vector", tiles: [o.tilesUrl], minzoom: 0, maxzoom: 14 });
  if (!map.getSource("selected")) map.addSource("selected", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  if (!map.getSource("draw")) map.addSource("draw", { type: "geojson", data: { type: "FeatureCollection", features: [] } });

  const add = (l: Record<string, unknown>) => { if (!map.getLayer(l.id as string)) map.addLayer(l as never); };
  // ONS local-authority boundaries: land fill for the self-hosted 'Plain' basemap, thin outline overlay for any basemap
  if (!map.getSource("lad")) map.addSource("lad", { type: "vector", tiles: [`${new URL(o.tilesUrl, "http://x").origin === "http://x" ? "" : new URL(o.tilesUrl.replace("{z}/{x}/{y}", "0/0/0")).origin}/api/boundaries/{z}/{x}/{y}`], minzoom: 0, maxzoom: 12, attribution: "Boundaries: ONS (OGL v3.0)" });
  const showLad = !!o.plain || !!o.showBoundaries;
  add({ id: "lad-fill", type: "fill", source: "lad", "source-layer": "lad", layout: { visibility: o.plain ? "visible" : "none" }, paint: { "fill-color": o.dark ? "#16253a" : "#f4f6f9" } });
  add({ id: "lad-line", type: "line", source: "lad", "source-layer": "lad", layout: { visibility: showLad ? "visible" : "none" }, paint: { "line-color": o.dark ? "#3a5170" : "#8da2bb", "line-width": ["interpolate", ["linear"], ["zoom"], 4, 0.3, 10, 1.1], "line-opacity": o.plain ? 0.9 : 0.55 } });
  add({ id: "lad-label", type: "symbol", source: "lad", "source-layer": "lad", minzoom: 8.5, layout: { visibility: showLad ? "visible" : "none", "text-field": ["get", "name"], "text-font": FONT, "text-size": 11, "text-allow-overlap": false }, paint: { "text-color": o.dark ? "#8fa5c2" : "#6d819b", "text-halo-color": o.dark ? "rgba(8,17,30,.8)" : "rgba(255,255,255,.8)", "text-halo-width": 1 } });
  const capFactor: unknown = o.sizeByMw ? ["interpolate", ["linear"], ["sqrt", ["max", ["to-number", ["get", "mw"], 0], 0]], 0, 0.78, 10, 1.0, 20, 1.28, 35, 1.6] : 1;

  add({ id: LAYERS.leaseFill, type: "fill", source: SRC, "source-layer": "lease_areas", minzoom: 4, layout: { visibility: o.showLeases ? "visible" : "none" },
        paint: { "fill-color": techMatch, "fill-opacity": 0.14 } });
  add({ id: LAYERS.leaseLine, type: "line", source: SRC, "source-layer": "lease_areas", minzoom: 4, layout: { visibility: o.showLeases ? "visible" : "none" },
        paint: { "line-color": techMatch, "line-width": ["interpolate", ["linear"], ["zoom"], 4, 0.6, 12, 1.8], "line-opacity": 0.85, "line-dasharray": [3, 1.5] } });
  add({ id: LAYERS.clusterCircle, type: "circle", source: SRC, "source-layer": "clusters", filter: [">", ["get", "n"], 1],
        paint: { "circle-color": famMatch, "circle-opacity": 0.82, "circle-radius": ["min", 25, ["+", 8, ["*", 2.5, ["sqrt", ["get", "n"]]]]],
                 "circle-stroke-width": 2, "circle-stroke-color": o.dark ? "#0b1424" : "#ffffff" } });
  add({ id: LAYERS.clusterCount, type: "symbol", source: SRC, "source-layer": "clusters", filter: [">", ["get", "n"], 1],
        layout: { "text-field": ["case", [">=", ["get", "n"], 1000], ["concat", ["to-string", ["/", ["round", ["/", ["get", "n"], 100]], 10]], "k"], ["to-string", ["get", "n"]]],
                  "text-font": FONT, "text-size": 11.5, "text-allow-overlap": true },
        paint: { "text-color": "#ffffff", "text-halo-color": "rgba(10,20,40,.55)", "text-halo-width": 0.8 } });
  add({ id: LAYERS.clusterSingle, type: "symbol", source: SRC, "source-layer": "clusters", filter: ["==", ["get", "n"], 1],
        layout: { "icon-image": ["concat", ["get", "top_tech"], "|solid"], "icon-size": ["interpolate", ["linear"], ["zoom"], 3, 0.5, 7, 0.75], "icon-allow-overlap": true, "icon-ignore-placement": true } });
  add({ id: LAYERS.assets, type: "symbol", source: SRC, "source-layer": "assets",
        layout: { "icon-image": ["concat", ["get", "technology_code"], "|", ["get", "status_pattern"]],
                  "icon-size": ["interpolate", ["linear"], ["zoom"], 3, ["*", 0.5, capFactor], 8, ["*", 0.7, capFactor], 13, ["*", 0.95, capFactor]],
                  "icon-allow-overlap": true, "icon-ignore-placement": true, "symbol-sort-key": ["-", ["to-number", ["get", "mw"], 0]] } });
  add({ id: LAYERS.assetLabels, type: "symbol", source: SRC, "source-layer": "assets", minzoom: 11, layout: { visibility: o.showLabels ? "visible" : "none", "text-field": ["get", "name"], "text-font": FONT, "text-size": 11, "text-offset": [0, 1.2], "text-anchor": "top", "text-optional": true, "text-max-width": 9 },
        paint: { "text-color": o.dark ? "#e8eef7" : "#0e1b2e", "text-halo-color": o.dark ? "rgba(8,17,30,.9)" : "rgba(255,255,255,.92)", "text-halo-width": 1.4 } });
  add({ id: LAYERS.turbines, type: "circle", source: SRC, "source-layer": "turbines", minzoom: 9, layout: { visibility: o.showTurbines ? "visible" : "none" },
        paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 9, 2, 14, 4.5, 18, 8], "circle-color": "#2f7fb5", "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.3 } });
  add({ id: LAYERS.turbineLabels, type: "symbol", source: SRC, "source-layer": "turbines", minzoom: 15, layout: { visibility: o.showTurbines ? "visible" : "none", "text-field": ["get", "unit_code"], "text-font": FONT, "text-size": 10.5, "text-offset": [0, 1], "text-anchor": "top" },
        paint: { "text-color": o.dark ? "#e8eef7" : "#0e1b2e", "text-halo-color": o.dark ? "rgba(8,17,30,.9)" : "#fff", "text-halo-width": 1.2 } });
  add({ id: LAYERS.selected, type: "circle", source: "selected", paint: { "circle-radius": 17, "circle-color": "rgba(0,0,0,0)", "circle-stroke-color": "#e11d48", "circle-stroke-width": 2.6 } });
  add({ id: LAYERS.drawFill, type: "fill", source: "draw", filter: ["==", ["geometry-type"], "Polygon"], paint: { "fill-color": "#e11d48", "fill-opacity": 0.1 } });
  add({ id: LAYERS.drawLine, type: "line", source: "draw", filter: ["!=", ["geometry-type"], "Point"], paint: { "line-color": "#e11d48", "line-width": 2.2, "line-dasharray": [2, 1.2] } });
  add({ id: LAYERS.drawPoints, type: "circle", source: "draw", filter: ["==", ["geometry-type"], "Point"], paint: { "circle-radius": 4.5, "circle-color": "#ffffff", "circle-stroke-color": "#e11d48", "circle-stroke-width": 2 } });
}

export function setVisibility(map: import("maplibre-gl").Map, ids: string[], visible: boolean): void {
  for (const id of ids) if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
}
