import { Page } from "@/components/SiteHeader";
export const metadata = { title: "About" };
export default function About() {
  return (
    <Page title="About the platform" current="/about">
      <p>The <strong>GB Renewable Energy Atlas</strong> is a source-driven geospatial database of renewable-energy generation and storage in England, Scotland and Wales. It is built from public government, regulator, network, planning and industry datasets; each figure carries its source, date and licence, and conflicts between sources are shown rather than hidden.</p>
      <div className="panel" style={{ padding: 14, margin: "14px 0" }}>
        <strong>Coverage statement.</strong> This platform consolidates publicly available renewable-energy and storage information from government, regulator, network, planning and industry sources. Although designed to provide broad coverage, it should not be interpreted as a definitive register of every installation in Great Britain. Coverage and data quality vary by technology, project scale, geography and source.
      </div>
      <h2 style={{ fontSize: 16 }}>What you can do</h2>
      <ul>
        <li>Explore the <a href="/">map</a>: national clusters → individual sites → lease polygons → verified turbine positions (where they exist), with status shown by fill pattern as well as colour.</li>
        <li>Filter by technology, status, size, location, grid, organisation, equipment, dates, support scheme, planning authority, confidence and more; the map, table, statistics and exports always agree.</li>
        <li>Open any asset for ten tabs of detail with field-level provenance, a dated timeline and a printable <em>evidence pack</em>.</li>
        <li>Use the GIS tools (coordinates in WGS84 and British National Grid, measure, radius and polygon search, nearest asset/turbine), compare 2–5 assets, and export CSV / XLSX / GeoJSON with attribution.</li>
        <li>Report an error or missing project with supporting evidence; reports are queued for human review.</li>
      </ul>
      <h2 style={{ fontSize: 16 }}>How to cite and reuse</h2>
      <p>Cite the underlying sources shown on each record and keep the attribution statements in exports. See <a href="/data">Data</a> for licences and <a href="/methodology">Methodology</a> for how values are chosen. Information is provided as-is, without warranty; verify against primary sources before relying on it for investment, planning or engineering decisions.</p>
      <h2 style={{ fontSize: 16 }}>Technology</h2>
      <p>Next.js, React and TypeScript front end; MapLibre GL JS with vector tiles generated in PostGIS (ST_AsMVT); PostgreSQL 16 + PostGIS 3; Python ingestion, normalisation, entity resolution and QA. The code, schema, tests and deployment notes are in the project repository.</p>
    </Page>
  );
}
