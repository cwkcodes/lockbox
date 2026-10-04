import proj4 from "proj4";

// EPSG:27700 British National Grid (OSGB36, Transverse Mercator). The Helmert (towgs84) shift used here is accurate to
// roughly ±5 m; the ingestion layer uses PROJ (EPSG:27700 -> 4326) and stores BNG alongside WGS84 for every asset.
const BNG = "+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 +y_0=-100000 +ellps=airy +towgs84=446.448,-125.157,542.06,0.15,0.247,0.842,-20.489 +units=m +no_defs";
const WGS = "EPSG:4326";

export function wgs84ToBng(lon: number, lat: number): { e: number; n: number } {
  const [e, n] = proj4(WGS, BNG, [lon, lat]);
  return { e, n };
}
export function bngToWgs84(e: number, n: number): { lon: number; lat: number } {
  const [lon, lat] = proj4(BNG, WGS, [e, n]);
  return { lon, lat };
}

const R = 6371008.8;
const rad = (d: number) => (d * Math.PI) / 180;
export function haversineM(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const dLat = rad(lat2 - lat1), dLon = rad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}
export function bearingDeg(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const y = Math.sin(rad(lon2 - lon1)) * Math.cos(rad(lat2));
  const x = Math.cos(rad(lat1)) * Math.sin(rad(lat2)) - Math.sin(rad(lat1)) * Math.cos(rad(lat2)) * Math.cos(rad(lon2 - lon1));
  return (((Math.atan2(y, x) * 180) / Math.PI) + 360) % 360;
}
const COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
export const compass = (deg: number) => COMPASS[Math.round(deg / 22.5) % 16];

/** OS grid reference (e.g. "NT 730 745", "TQ3080") -> BNG metres at the SW corner of the square. */
export function gridRefToBng(ref: string): { e: number; n: number; res: number } | null {
  const s = ref.replace(/\s+/g, "").toUpperCase();
  const m = /^([A-HJ-Z])([A-HJ-Z])(\d{2,10})$/.exec(s);
  if (!m || m[3].length % 2) return null;
  let l1 = m[1].charCodeAt(0) - 65, l2 = m[2].charCodeAt(0) - 65;
  if (l1 > 7) l1--; if (l2 > 7) l2--;
  const e100 = ((l1 - 2) % 5 + 5) % 5 * 5 + (l2 % 5);
  const n100 = 19 - Math.floor(l1 / 5) * 5 - Math.floor(l2 / 5);
  const h = m[3].length / 2, res = 10 ** (5 - h);
  return { e: e100 * 100000 + parseInt(m[3].slice(0, h), 10) * res, n: n100 * 100000 + parseInt(m[3].slice(h), 10) * res, res };
}

/** UK postcode sector/centroid lookups need an external licensed dataset; we only parse coordinate-like text here. */
export function parseCoordinateInput(text: string): { lat: number; lon: number; kind: string } | null {
  const t = text.trim();
  const ll = /^(-?\d{1,2}(?:\.\d+)?)\s*[, ]\s*(-?\d{1,3}(?:\.\d+)?)$/.exec(t);
  if (ll) {
    const lat = parseFloat(ll[1]), lon = parseFloat(ll[2]);
    if (lat >= 49 && lat <= 61.5 && lon >= -9 && lon <= 3.6) return { lat, lon, kind: "WGS84 lat, lon" };
  }
  const en = /^(\d{5,7})\s*[, ]\s*(\d{5,7})$/.exec(t);
  if (en) {
    const { lat, lon } = bngToWgs84(parseInt(en[1], 10), parseInt(en[2], 10));
    if (lat >= 49 && lat <= 61.5 && lon >= -9 && lon <= 3.6) return { lat, lon, kind: "British National Grid E, N" };
  }
  const g = gridRefToBng(t);
  if (g) {
    const { lat, lon } = bngToWgs84(g.e + g.res / 2, g.n + g.res / 2);
    return { lat, lon, kind: "OS grid reference" };
  }
  return null;
}

/** Geodesic circle polygon (GeoJSON, lon/lat) around a centre with radius in metres. */
export function circlePolygon(lat: number, lon: number, radiusM: number, steps = 72): GeoJSON.Feature<GeoJSON.Polygon> {
  const ring: [number, number][] = [];
  const d = radiusM / R, lat1 = rad(lat), lon1 = rad(lon);
  for (let i = 0; i <= steps; i++) {
    const brg = (2 * Math.PI * i) / steps;
    const lat2 = Math.asin(Math.sin(lat1) * Math.cos(d) + Math.cos(lat1) * Math.sin(d) * Math.cos(brg));
    const lon2 = lon1 + Math.atan2(Math.sin(brg) * Math.sin(d) * Math.cos(lat1), Math.cos(d) - Math.sin(lat1) * Math.sin(lat2));
    ring.push([(lon2 * 180) / Math.PI, (lat2 * 180) / Math.PI]);
  }
  return { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [ring] } };
}
