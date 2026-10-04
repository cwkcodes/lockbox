"use client";
import Link from "next/link";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Page } from "@/components/SiteHeader";
import { useJson } from "@/components/ui";
import { fmtDateShort, fmtMw, fmtNum } from "@/lib/format";

/* eslint-disable @typescript-eslint/no-explicit-any */
const U = "Unknown";
function Compare() {
  const ids = useSearchParams().get("ids") ?? "";
  const { data, error } = useJson<{ families: string[]; assets: any[] }>(ids ? `/api/compare?ids=${encodeURIComponent(ids)}` : null);
  const rows: [string, (d: any) => React.ReactNode][] = [
    ["Technology", (d) => d.technology_label], ["Status", (d) => d.status_label], ["Capacity", (d) => (d.a.installed_capacity_mw != null ? fmtMw(d.a.installed_capacity_mw) : U)],
    ["Capacity basis", (d) => d.a.capacity_basis ?? "—"], ["Country / LA", (d) => [d.a.country, d.derived?.local_authority].filter(Boolean).join(" / ") || U],
    ["Commissioned", (d) => (d.a.commissioning_date ? fmtDateShort(d.a.commissioning_date) : U)], ["Developer", (d) => d.orgs.filter((o: any) => o.role === "developer").map((o: any) => o.canonical_name).join("; ") || U],
    ["Owner", (d) => d.orgs.filter((o: any) => o.role === "owner").map((o: any) => o.canonical_name).join("; ") || "Not publicly identified"],
    ["Operator / applicant", (d) => d.orgs.filter((o: any) => ["operator", "applicant"].includes(o.role)).map((o: any) => o.canonical_name).join("; ") || U],
    ["Grid operator", (d) => d.a.grid_operator ?? U], ["Planning ref.", (d) => d.a.planning_reference ?? U], ["Confidence", (d) => d.a.confidence], ["Last verified", (d) => fmtDateShort(d.a.last_verified)],
  ];
  const fam = new Set(data?.families ?? []);
  if (fam.has("wind")) rows.push(["Turbines (as reported)", (d) => d.wind?.turbine_count_reported ?? "—"], ["Manufacturer", (d) => d.wind?.turbine_manufacturer ?? "Not publicly identified"], ["Model", (d) => d.wind?.turbine_model ?? "Not publicly identified"], ["Hub height (m)", (d) => d.wind?.hub_height_m ?? "—"], ["Rotor diameter (m)", (d) => d.wind?.rotor_diameter_m ?? "—"], ["Reported turbine rating (MW)", (d) => d.wind?.turbine_rated_mw_reported ?? "—"], ["Reported turbine height (m)", (d) => d.wind?.turbine_height_reported_m ?? "—"]);
  if (fam.has("solar")) rows.push(["Site area (ha)", (d) => d.solar?.site_area_ha != null ? fmtNum(d.solar.site_area_ha, 1) : "—"], ["Mounting", (d) => d.solar?.mounting_type ?? "—"], ["MWp (DC) / MW (AC)", (d) => d.solar ? `${d.solar.mwp_dc ?? "—"} / ${d.solar.mw_ac ?? "—"}` : "—"]);
  if (fam.has("storage")) rows.push(["Energy (MWh)", (d) => d.storage?.energy_mwh ?? "Not publicly identified"], ["Duration (h)", (d) => d.storage?.duration_h_published ?? d.storage?.duration_h_calculated ?? "—"], ["Storage type", (d) => d.storage?.storage_type?.replace(/_/g, " ") ?? "—"]);
  return (
    <Page title="Compare assets" current="/assets" wide>
      {!ids && <p>Select 2–5 assets on the map or in the results list, then press Compare.</p>}
      {error && <p role="alert">Could not compare these assets ({error}).</p>}
      {data && (
        <div className="panel" style={{ overflow: "auto" }}>
          <table className="data"><caption className="sr-only">Side-by-side comparison</caption>
            <thead><tr><th scope="col" style={{ width: 190 }}>Attribute</th>{data.assets.map((d) => <th key={d.a.asset_id} scope="col"><Link href={`/assets/${d.a.asset_id}`}>{d.a.canonical_name}</Link></th>)}</tr></thead>
            <tbody>{rows.map(([label, fn]) => <tr key={label}><th scope="row" style={{ position: "static", background: "transparent", fontWeight: 600 }}>{label}</th>{data.assets.map((d) => <td key={d.a.asset_id}>{fn(d) as React.ReactNode}</td>)}</tr>)}</tbody></table>
        </div>
      )}
      <p className="muted">“As reported” values come from registers and are not verified as built. Technology-specific rows appear automatically for the technologies selected.</p>
    </Page>
  );
}
export default function ComparePage() { return <Suspense fallback={null}><Compare /></Suspense>; }
