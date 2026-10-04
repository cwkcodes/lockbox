"use client";
import { Page } from "@/components/SiteHeader";
import { useJson } from "@/components/ui";

/* eslint-disable @typescript-eslint/no-explicit-any */
export default function ApiDocs() {
  const { data } = useJson<any>("/api/openapi.json");
  return (
    <Page title="API documentation" current="/data">
      <p>Read-only JSON API. Machine-readable description: <a href="/api/openapi.json">/api/openapi.json</a>. Filter parameters are shared by every list endpoint, so a URL that filters the map also filters the table, statistics and export.</p>
      {data && Object.entries<any>(data.paths).map(([path, ops]) => Object.entries<any>(ops).map(([method, op]) => (
        <section key={path + method} className="panel" style={{ padding: 10, marginBottom: 8 }}>
          <div><span className="chip" style={{ textTransform: "uppercase" }}>{method}</span> <code>{path}</code></div>
          <div>{op.summary}</div>
          {op.parameters?.length > 0 && <details><summary className="muted" style={{ cursor: "pointer" }}>{op.parameters.length} parameters</summary><table className="data"><tbody>{op.parameters.map((p: any) => <tr key={p.name}><td><code>{p.name}</code></td><td>{p.in}{p.required ? " · required" : ""}</td><td className="muted">{p.description ?? ""}</td></tr>)}</tbody></table></details>}
        </section>)))}
      <h2 style={{ fontSize: 16 }}>Examples</h2>
      <pre className="panel" style={{ padding: 10, overflow: "auto" }}>{`# Operational onshore wind in Scotland, 20 MW and above
/api/assets?wt=onshore&stage=operational&ctry=Scotland&mw0=20&pageSize=100

# Same selection as GeoJSON with provenance and attribution
/api/export?wt=onshore&stage=operational&ctry=Scotland&mw0=20&format=geojson

# Assets within 10 km of a point
/api/nearby?lat=55.68&lon=-4.28&radius_m=10000&fam=wind

# Where did this capacity figure come from?
/api/assets/GBA-0002750/sources`}</pre>
    </Page>
  );
}
