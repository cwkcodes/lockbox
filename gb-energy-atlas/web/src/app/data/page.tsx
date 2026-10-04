"use client";
import { Page } from "@/components/SiteHeader";
import { Chip, useJson } from "@/components/ui";
import { fmtDate, fmtNum, safeUrl } from "@/lib/format";

/* eslint-disable @typescript-eslint/no-explicit-any */
const STATUS_TONE: Record<string, "ok" | "warn" | "bad" | undefined> = { current: "ok", update_available: "warn", source_unavailable: "bad", restricted: "bad", manual_review_required: "warn", never_run: undefined };
const STATUS_LABEL: Record<string, string> = { current: "Current", update_available: "Update available", source_unavailable: "Source unavailable", restricted: "Access restricted", manual_review_required: "Manual review required", never_run: "Not yet run" };

export default function DataPage() {
  const { data } = useJson<{ sources: any[]; counts: any; changeLog: { source_key: string; change_type: string; n: number }[] }>("/api/data-sources");
  return (
    <Page title="Data sources, coverage and downloads" current="/data" wide>
      <div className="panel" style={{ padding: 14, marginBottom: 14 }}>
        <strong>Coverage statement.</strong> This platform consolidates publicly available renewable-energy and storage information from government, regulator, network, planning and industry sources. Although designed to provide broad coverage, it should not be interpreted as a definitive register of every installation in Great Britain. Coverage and data quality vary by technology, project scale, geography and source.
      </div>
      {data && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 10, marginBottom: 14 }}>
          {[["Canonical assets", data.counts.assets], ["Great Britain assets", data.counts.gb_assets], ["With coordinates", data.counts.located], ["Lease-area records", data.counts.lease_areas]].map(([k, v]) => <div key={String(k)} className="panel" style={{ padding: 10 }}><div className="muted">{k}</div><div style={{ fontSize: 20, fontWeight: 600 }}>{fmtNum(Number(v), 0)}</div></div>)}
        </div>
      )}
      <h2 style={{ fontSize: 16, margin: "6px 0" }}>Source registry</h2>
      <p className="muted">Every source investigated is listed – including those that could not be ingested – with the exact reason. Nothing is replaced by invented data. Authority tier: A statutory / regulator / network / official dataset · B developer or manufacturer primary · C reputable industry / recognised open data · D secondary media · E community maintained.</p>
      <div className="panel" style={{ overflow: "auto" }}>
        <table className="data"><caption className="sr-only">Data sources</caption>
          <thead><tr><th scope="col">Source</th><th scope="col">Tier</th><th scope="col">Status</th><th scope="col">Latest publication</th><th scope="col">Last checked</th><th scope="col">Update freq.</th><th scope="col" style={{ textAlign: "right" }}>Records</th><th scope="col">Licence</th><th scope="col">Export</th></tr></thead>
          <tbody>{[...(data?.sources ?? [])].sort((a, b) => (a.access_status === "current" ? 0 : 1) - (b.access_status === "current" ? 0 : 1) || a.tier.localeCompare(b.tier) || a.source_key.localeCompare(b.source_key)).map((s) => (
            <tr key={s.source_key}>
              <td><strong>{s.organisation}</strong><br />{safeUrl(s.landing_url) ? <a href={safeUrl(s.landing_url)!} target="_blank" rel="noopener noreferrer">{s.dataset}</a> : s.dataset}
                {(s.access_notes || s.known_limitations) && <details><summary className="muted" style={{ cursor: "pointer" }}>Notes & limitations</summary>{s.access_notes && <p style={{ margin: "4px 0" }}><strong>Access:</strong> {s.access_notes}</p>}{s.known_limitations && <p style={{ margin: "4px 0" }}><strong>Limitations:</strong> {s.known_limitations}</p>}{s.commercial_use_notes && <p style={{ margin: "4px 0" }}><strong>Licence conditions:</strong> {s.commercial_use_notes}</p>}{s.snapshot?.notes && <p style={{ margin: "4px 0" }}><strong>Snapshot:</strong> {s.snapshot.notes}</p>}</details>}</td>
              <td>{s.tier}</td><td><Chip tone={STATUS_TONE[s.access_status]}>{STATUS_LABEL[s.access_status] ?? s.access_status}</Chip></td>
              <td>{s.latest_publication_date ? fmtDate(s.latest_publication_date) : "—"}</td><td>{s.last_checked_at ? fmtDate(s.last_checked_at) : "—"}</td><td>{s.update_frequency ?? "—"}</td>
              <td className="num">{s.records_imported != null ? fmtNum(s.records_imported, 0) : "—"}{s.records_rejected ? <div className="muted">{fmtNum(s.records_rejected, 0)} quarantined</div> : null}</td>
              <td>{s.licence_url && safeUrl(s.licence_url) ? <a href={safeUrl(s.licence_url)!} target="_blank" rel="noopener noreferrer">{s.licence_name}</a> : s.licence_name ?? "—"}<div className="muted">{s.attribution}</div></td>
              <td>{!s.records_imported ? <span className="muted">no data loaded</span> : s.export_policy === "exclude" ? <Chip tone="warn">excluded</Chip> : s.export_policy === "conditional" ? <Chip>conditional</Chip> : <Chip tone="ok">included</Chip>}{s.export_policy_reason && <div className="muted">{s.export_policy_reason}</div>}</td>
            </tr>))}</tbody></table>
      </div>
      <h2 style={{ fontSize: 16, margin: "18px 0 6px" }}>Downloads, API and data model</h2>
      <ul>
        <li>Filtered exports on the <a href="/assets">asset database</a> or map (CSV, XLSX, GeoJSON; GeoPackage when GDAL is configured). Exports carry source URLs, provenance and the required attribution; sources whose licence restricts redistribution are excluded and the exclusion is stated in the file.</li>
        <li>REST API with OpenAPI description: <a href="/api-docs">API documentation</a> (<a href="/api/openapi.json">openapi.json</a>). Every list endpoint accepts the same filter parameters.</li>
        <li>Data model: raw source layer → normalised source layer → canonical assets (with phases, units/turbines, organisations, planning, grid, support schemes, geometries, field-level provenance, conflicts, history, QA flags and audit trail). See <a href="/methodology">Methodology</a>.</li>
      </ul>
      <h2 style={{ fontSize: 16, margin: "18px 0 6px" }}>Change log (latest refresh vs previous edition)</h2>
      {data && data.changeLog.length ? <ul>{data.changeLog.map((c, i) => <li key={i}>{c.source_key}: {c.n} × {c.change_type.replace(/_/g, " ")}</li>)}</ul> : <p className="muted">No previous edition has been imported yet, so no changes have been detected. Each re-import is compared with the prior snapshot (new/removed projects, status, capacity, date, developer and connection changes).</p>}
    </Page>
  );
}
