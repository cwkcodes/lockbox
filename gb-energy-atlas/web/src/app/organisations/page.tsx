"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Page } from "@/components/SiteHeader";
import { useDebounced, useJson } from "@/components/ui";
import { fmtGw, fmtNum } from "@/lib/format";

function Orgs() {
  const sp = useSearchParams();
  const [q, setQ] = useState(sp.get("q") ?? ""), [role, setRole] = useState("");
  const dq = useDebounced(q, 250);
  const { data } = useJson<{ items: { org_id: number; canonical_name: string; aliases: string[]; assets: number; operational_mw: number; pipeline_mw: number; roles: string[] }[] }>(`/api/organisations?q=${encodeURIComponent(dq)}&role=${role}&pageSize=100`);
  useEffect(() => { window.history.replaceState(null, "", q ? `/organisations?q=${encodeURIComponent(q)}` : "/organisations"); }, [q]);
  return (
    <Page title="Organisations" current="/organisations">
      <p className="muted" style={{ marginTop: -6 }}>One canonical record per organisation; spelling variants are kept as aliases. Roles are independent (developer, owner, operator/applicant, lessee, customer…). Corporate parent/subsidiary links are never inferred from names.</p>
      <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
        <input className="input" style={{ width: 300 }} placeholder="Search organisations…" aria-label="Search organisations" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="input" aria-label="Role" value={role} onChange={(e) => setRole(e.target.value)}><option value="">Any role</option>{["operator", "applicant", "developer", "owner", "lessee", "customer"].map((r) => <option key={r} value={r}>{r}</option>)}</select>
      </div>
      <div className="panel" style={{ overflow: "auto" }}>
        <table className="data"><caption className="sr-only">Organisations by operational capacity</caption><thead><tr><th scope="col">Organisation</th><th scope="col">Roles</th><th scope="col" style={{ textAlign: "right" }}>Assets</th><th scope="col" style={{ textAlign: "right" }}>Operational</th><th scope="col" style={{ textAlign: "right" }}>Pipeline</th></tr></thead>
          <tbody>{data?.items.map((o) => <tr key={o.org_id}><td><Link href={`/?opr=${encodeURIComponent(o.canonical_name)}`}>{o.canonical_name}</Link>{o.aliases.length > 0 && <div className="muted">also: {o.aliases.slice(0, 3).join("; ")}</div>}</td><td>{o.roles.join(", ")}</td><td className="num">{fmtNum(o.assets, 0)}</td><td className="num">{fmtGw(o.operational_mw)}</td><td className="num">{fmtGw(o.pipeline_mw)}</td></tr>)}</tbody></table>
      </div>
      <p className="muted">Capacity shown is the sum of headline capacity of assets where the organisation appears; shared ventures are counted for each participant, so figures are not additive across organisations.</p>
    </Page>
  );
}
export default function OrganisationsPage() { return <Suspense fallback={null}><Orgs /></Suspense>; }
