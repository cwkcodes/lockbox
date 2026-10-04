import { json } from "@/lib/api";

export const dynamic = "force-static";

const filterParams = [
  ["q", "Free text (name, aliases, developer, refs, models, LA)"], ["cat", "Technology categories: generation,storage,hybrid,other_low_carbon (default: generation,storage,hybrid)"],
  ["fam", "Technology family: wind,solar,storage,hydro,marine,bioenergy,geothermal,hybrid"], ["tech", "Technology codes, e.g. wind_onshore,bess"], ["wt", "Wind type: onshore,offshore,fixed,floating"],
  ["stage", "Stage group: operational,pipeline,historic,unsuccessful,unknown"], ["st", "Status codes (overrides stage)"], ["ctry", "England,Scotland,Wales"], ["reg", "Region"], ["la", "Local authority"],
  ["mw0", "Min MW"], ["mw1", "Max MW"], ["mwh0", "Min MWh"], ["mwh1", "Max MWh"], ["h0", "Min duration h"], ["h1", "Max duration h"], ["dno", "DNO"], ["conn", "transmission|distribution"], ["kv0", "Min kV"], ["kv1", "Max kV"],
  ["dev", "Developer contains"], ["own", "Owner contains"], ["opr", "Operator contains"], ["mfr", "Turbine manufacturer contains"], ["mdl", "Turbine model contains"],
  ["nt0", "Min turbines"], ["nt1", "Max turbines"], ["hub0", "Min hub height m"], ["rot0", "Min rotor diameter m"], ["tip0", "Min tip height m"], ["cy0", "Commissioning year from"], ["cy1", "Commissioning year to"],
  ["py0", "Planning year from"], ["py1", "Planning year to"], ["sup", "CfD,RO,REGO,FIT,none"], ["pa", "Planning authority"], ["src", "Source key present"], ["conf", "verified,high,medium,low"],
  ["rp", "none,has_repower,is_repower"], ["tp", "yes|no – individual turbine positions known"], ["colo", "yes|no – co-located storage"], ["age", "Operational and at least N years old"],
  ["kind", "project|lease_area (default project)"], ["scale", "utility|small"], ["scope", "gb (default) | all"], ["bbox", "minLon,minLat,maxLon,maxLat"], ["ids", "Comma-separated asset ids"],
].map(([name, description]) => ({ name, in: "query", required: false, schema: { type: "string" }, description }));

const get = (summary: string, extra: unknown[] = []) => ({ get: { summary, parameters: [...filterParams, ...extra], responses: { "200": { description: "OK" } } } });

export function GET() {
  return json({
    openapi: "3.0.3",
    info: { title: "GB Renewable Energy Atlas API", version: "0.1.0", description: "Read API over the canonical asset database. Every list endpoint accepts the same filter parameters, so counts, tiles, statistics and exports always agree. Source attribution must be retained when redistributing data (see /data)." },
    paths: {
      "/api/assets": get("List assets (paginated, sortable)", [{ name: "page", in: "query", schema: { type: "integer" } }, { name: "pageSize", in: "query", schema: { type: "integer", maximum: 500 } }, { name: "sort", in: "query", schema: { type: "string" } }, { name: "dir", in: "query", schema: { type: "string", enum: ["asc", "desc"] } }]),
      "/api/assets/{id}": { get: { summary: "Full asset record incl. provenance, sources, conflicts, units", parameters: [{ name: "id", in: "path", required: true, schema: { type: "string", example: "GBA-0000001" } }], responses: { "200": { description: "OK" }, "404": { description: "Not found" } } } },
      "/api/assets/{id}/sources": { get: { summary: "Sources, field provenance and conflicts", parameters: [{ name: "id", in: "path", required: true, schema: { type: "string" } }], responses: { "200": { description: "OK" } } } },
      "/api/assets/{id}/history": { get: { summary: "Dated timeline events", parameters: [{ name: "id", in: "path", required: true, schema: { type: "string" } }], responses: { "200": { description: "OK" } } } },
      "/api/assets/{id}/units": { get: { summary: "Generating units / individual turbines (verified positions only)", parameters: [{ name: "id", in: "path", required: true, schema: { type: "string" } }], responses: { "200": { description: "OK" } } } },
      "/api/wind-turbines": get("Individual turbine records"),
      "/api/planning-cases": get("Planning cases", [{ name: "pq", in: "query", schema: { type: "string" }, description: "Reference contains" }]),
      "/api/organisations": { get: { summary: "Organisations with role counts and capacity", parameters: [{ name: "role", in: "query", schema: { type: "string" } }, { name: "q", in: "query", schema: { type: "string" } }], responses: { "200": { description: "OK" } } } },
      "/api/statistics": get("Headline statistics and breakdowns for the filtered set"),
      "/api/facets": { get: { summary: "Filter option lists with counts", responses: { "200": { description: "OK" } } } },
      "/api/search": { get: { summary: "Typeahead search incl. identifiers, planning refs, coordinates and natural-language interpretation", parameters: [{ name: "q", in: "query", required: true, schema: { type: "string" } }], responses: { "200": { description: "OK" } } } },
      "/api/nearby": get("Assets within a radius (distance + bearing + summary)", [{ name: "lat", in: "query", required: true, schema: { type: "number" } }, { name: "lon", in: "query", required: true, schema: { type: "number" } }, { name: "radius_m", in: "query", schema: { type: "number" } }]),
      "/api/nearest": get("Nearest assets or turbine positions", [{ name: "lat", in: "query", required: true, schema: { type: "number" } }, { name: "lon", in: "query", required: true, schema: { type: "number" } }, { name: "kind", in: "query", schema: { type: "string", enum: ["asset", "turbine"] } }]),
      "/api/within": { post: { summary: "Assets within a GeoJSON polygon", requestBody: { content: { "application/json": { schema: { type: "object", properties: { polygon: { type: "object" } } } } } }, responses: { "200": { description: "OK" } } } },
      "/api/tiles/{z}/{x}/{y}": { get: { summary: "Mapbox Vector Tile (layers: clusters, assets, lease_areas, turbines); accepts the same filters; cluster=0 disables clustering", parameters: [{ name: "z", in: "path", required: true, schema: { type: "integer" } }, { name: "x", in: "path", required: true, schema: { type: "integer" } }, { name: "y", in: "path", required: true, schema: { type: "integer" } }], responses: { "200": { description: "application/vnd.mapbox-vector-tile" } } } },
      "/api/export": get("Export filtered data (csv|xlsx|geojson|gpkg) with provenance and attribution", [{ name: "format", in: "query", schema: { type: "string", enum: ["csv", "xlsx", "geojson", "gpkg"] } }]),
      "/api/compare": { get: { summary: "Compare 2–5 assets", parameters: [{ name: "ids", in: "query", required: true, schema: { type: "string" } }], responses: { "200": { description: "OK" } } } },
      "/api/evidence-pack/{id}": { get: { summary: "Printable HTML evidence pack", parameters: [{ name: "id", in: "path", required: true, schema: { type: "string" } }], responses: { "200": { description: "text/html" } } } },
      "/api/data-sources": { get: { summary: "Source registry, freshness and licences", responses: { "200": { description: "OK" } } } },
      "/api/reports": { post: { summary: "Submit a correction (evidence URL mandatory; queued for review, never auto-published)", responses: { "201": { description: "Queued" } } } },
    },
  }, { cache: "public, max-age=300" });
}
