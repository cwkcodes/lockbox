"use client";
import Link from "next/link";
import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Page } from "@/components/SiteHeader";
import { useJson } from "@/components/ui";
import { filtersToParams, parseFilters } from "@/lib/filters";
import { fmtNum } from "@/lib/format";
import type { AssetRow } from "@/lib/types";

function Turbines() {
  const sp = useSearchParams();
  const qs = useMemo(() => filtersToParams(parseFilters(sp)).toString(), [sp]);
  const [page, setPage] = useState(1);
  const { data: t } = useJson<{ total: number; items: Record<string, any>[]; coverage: { wind_assets: number; turbines_reported: number; positions_verified: number; statement?: string } }>(`/api/wind-turbines?${qs}&page=${page}&pageSize=100`); // eslint-disable-line @typescript-eslint/no-explicit-any
  const { data: wind } = useJson<{ items: AssetRow[] }>(`/api/assets?${qs}${qs ? "&" : ""}fam=wind&sort=turbines&pageSize=25`);
  return (
    <Page title="Wind turbine database" current="/turbines" wide>
      {t && (
        <div className="panel" style={{ padding: 14, marginBottom: 14, background: t.total ? undefined : "var(--warn-bg)" }}>
          <strong>Coverage:</strong> {fmtNum(t.coverage.wind_assets, 0)} wind projects report {fmtNum(t.coverage.turbines_reported, 0)} turbines in total, of which <strong>{fmtNum(t.coverage.positions_verified, 0)}</strong> have an individually verified position.
          {t.coverage.statement && <p style={{ margin: "6px 0 0" }}>{t.coverage.statement} Turbine positions are only recorded from planning layouts (“digitised from official planning drawing”), published coordinates, or OpenStreetMap (“open-source mapped”, supplementary only) – never from a site centroid.</p>}
        </div>
      )}
      <div className="panel" style={{ overflow: "auto", marginBottom: 16 }}>
        <table className="data"><caption className="sr-only">Individual turbines with verified positions</caption>
          <thead><tr>{["ID", "Project", "Manufacturer", "Model", "MW", "Hub (m)", "Rotor (m)", "Tip (m)", "Lat", "Lon", "Easting", "Northing", "Status", "Coordinate source"].map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead>
          <tbody>{t?.items.map((u) => <tr key={u.unit_id}><td>{u.unit_code}</td><td><Link href={`/assets/${u.asset_id}`}>{u.asset_name}</Link></td><td>{u.manufacturer ?? "—"}</td><td>{u.model ?? "—"}</td><td className="num">{u.rated_mw ?? "—"}</td><td className="num">{u.hub_height_m ?? "—"}</td><td className="num">{u.rotor_diameter_m ?? "—"}</td><td className="num">{u.tip_height_m ?? "—"}</td><td className="num">{Number(u.lat).toFixed(6)}</td><td className="num">{Number(u.lon).toFixed(6)}</td><td className="num">{Math.round(u.bng_e)}</td><td className="num">{Math.round(u.bng_n)}</td><td>{u.status_code ?? "—"}</td><td>{String(u.coordinate_class ?? "").replace(/_/g, " ")}</td></tr>)}
            {t && !t.items.length && <tr><td colSpan={14} className="muted" style={{ padding: 16 }}>No verified turbine positions yet. “Individual turbine coordinates not verified.”</td></tr>}</tbody></table>
        {t && t.total > 100 && <div style={{ padding: 8, display: "flex", gap: 8 }}><button type="button" className="btn sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button><button type="button" className="btn sm" disabled={page * 100 >= t.total} onClick={() => setPage(page + 1)}>Next</button></div>}
      </div>
      <h2 style={{ fontSize: 16 }}>Wind projects with the most reported turbines</h2>
      <p className="muted">Counts are as reported by REPD and are not verified as built. Manufacturer and model remain “not publicly identified” until a planning decision, developer or manufacturer source states them.</p>
      <div className="panel" style={{ overflow: "auto" }}><table className="data"><thead><tr><th scope="col">Project</th><th scope="col">Status</th><th scope="col" style={{ textAlign: "right" }}>Turbines (reported)</th><th scope="col" style={{ textAlign: "right" }}>MW</th><th scope="col">Model</th><th scope="col">Positions</th></tr></thead>
        <tbody>{wind?.items.map((a) => <tr key={a.asset_id}><td><Link href={`/assets/${a.asset_id}`}>{a.canonical_name}</Link></td><td>{a.status_label}</td><td className="num">{a.turbine_count ?? "—"}</td><td className="num">{a.installed_capacity_mw ?? "—"}</td><td>{a.turbine_model ?? "—"}</td><td>{a.individual_turbines_known ? "verified" : "not verified"}</td></tr>)}</tbody></table></div>
    </Page>
  );
}
export default function TurbinesPage() { return <Suspense fallback={null}><Turbines /></Suspense>; }
