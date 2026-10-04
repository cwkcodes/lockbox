import { NextRequest } from "next/server";
import { getAssetDetail } from "@/lib/queries";
import { fmtDate, fmtNum, safeUrl } from "@/lib/format";

export const dynamic = "force-dynamic";
const esc = (v: unknown): string => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
type R = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

/** Printable evidence pack (HTML; use the browser's Print → Save as PDF). Escapes every external string. */
export async function GET(_req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  if (!/^GBA-\d{7}$/.test(id)) return new Response("bad id", { status: 400 });
  const d = (await getAssetDetail(id)) as R | null;
  if (!d) return new Response("not found", { status: 404 });
  const a: R = d.a;
  const row = (k: string, v: unknown) => `<tr><th>${esc(k)}</th><td>${v === null || v === undefined || v === "" ? "<span class=u>Not publicly identified</span>" : esc(v)}</td></tr>`;
  const link = (u: string | null) => { const s = safeUrl(u); return s ? `<a href="${esc(s)}">${esc(s)}</a>` : "—"; };
  const srcs = (d.sources as R[]).map((s) => `<tr><td>${esc(s.organisation)}<br><small>${esc(s.dataset)}</small></td><td>${esc(s.tier)}</td><td>${esc(s.record_key)}</td>
      <td>${esc(fmtDate(s.publication_date))}</td><td>${esc(fmtDate(s.retrieved_at))}</td><td>${esc(s.licence_name ?? "see source")}</td><td>${link(s.record_url ?? s.snapshot_url)}</td></tr>`).join("");
  const conflicts = (d.conflicts as R[]).map((c) => `<h4>${esc(c.field)}</h4><table>${(c.observations as R[]).map((o) => `<tr><td>${esc(o.value_num ?? o.value_text)} ${esc(o.value_unit ?? "")}</td><td>${esc(o.source_key)}</td><td>${esc(o.observed_at ?? "")}</td><td>${o.is_preferred ? "<b>preferred</b>" : ""}</td><td>${esc(o.selection_reason ?? "")}</td></tr>`).join("")}</table>`).join("") || "<p>No conflicting values recorded between sources.</p>";
  const hist = (d.history as R[]).map((h) => `<tr><td>${esc(fmtDate(h.event_date))}</td><td>${esc(h.description)}</td></tr>`).join("");
  const plan = (d.planning as R[]).map((p) => `<tr><td>${esc(p.ref_type)}</td><td>${esc(p.authority)}</td><td>${esc(p.reference)}</td><td>${esc(fmtDate(p.application_date))}</td><td>${esc(fmtDate(p.decision_date))}</td><td>${esc(p.decision)}</td></tr>`).join("");
  const grid = (d.grid as R[]).map((g) => `<tr><td>${esc(g.network_operator)}</td><td>${esc(g.point_of_connection)}</td><td>${esc(g.voltage_kv)}</td><td>${esc(g.registered_capacity_mw)}</td><td>${esc(g.connection_status)}</td></tr>`).join("");
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Evidence pack – ${esc(a.canonical_name)}</title>
<style>body{font:14px/1.5 system-ui,Segoe UI,Arial;color:#0f1b2d;max-width:900px;margin:24px auto;padding:0 16px}h1{font-size:22px;margin:0}h2{font-size:16px;border-bottom:2px solid #0b3a6e;padding-bottom:4px;margin-top:28px;color:#0b3a6e}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{border:1px solid #d5dbe5;padding:5px 8px;text-align:left;vertical-align:top}th{background:#f1f4f9;width:30%}.u{color:#6b7a90}small{color:#5b6b82}
.meta{color:#5b6b82;margin:4px 0 16px}.warn{background:#fff7e6;border:1px solid #f0d28a;padding:8px 12px;margin-top:20px}@media print{a{color:inherit;text-decoration:none}h2{break-after:avoid}table{break-inside:auto}tr{break-inside:avoid}}</style></head><body>
<h1>${esc(a.canonical_name)}</h1><div class="meta">GB Renewable Energy Atlas – evidence pack · asset ${esc(a.asset_id)} · generated ${esc(fmtDate(new Date()))} · last verified ${esc(fmtDate(a.last_verified))}</div>
<h2>Project details</h2><table>${row("Technology", d.technology_label)}${row("Status", d.status_label)}${row("Original source status", a.status_original)}${row("Capacity", a.installed_capacity_mw !== null ? `${fmtNum(a.installed_capacity_mw)} MW (${a.capacity_basis ?? "basis not stated"})` : null)}
${row("Country / region / local authority", [a.country, a.region, a.local_authority].filter(Boolean).join(" / "))}${row("Location (WGS84)", a.lat !== null ? `${Number(a.lat).toFixed(5)}, ${Number(a.lon).toFixed(5)} – ${a.coordinate_accuracy}` : null)}
${row("British National Grid", a.bng_e !== null ? `E ${Math.round(Number(a.bng_e))}, N ${Math.round(Number(a.bng_n))}` : null)}${row("Commissioning date", a.commissioning_date ? fmtDate(a.commissioning_date) : null)}
${row("Developer / owner / operator", (d.orgs as R[]).map((o) => `${o.role}: ${o.canonical_name}`).join("; ") || null)}${row("Confidence / completeness", `${a.confidence} / ${a.completeness_pct}%`)}</table>
<h2>Technical parameters</h2><table>${d.wind ? row("Turbines (as reported)", d.wind.turbine_count_reported) + row("Turbine model", d.wind.turbine_model) + row("Reported turbine rating (MW)", d.wind.turbine_rated_mw_reported) + row("Reported turbine height (m)", d.wind.turbine_height_reported_m) : ""}
${d.storage ? row("Power (MW)", d.storage.power_mw) + row("Energy (MWh)", d.storage.energy_mwh) + row("Duration (h) – published", d.storage.duration_h_published) : ""}${d.solar ? row("Site area (ha)", d.solar.site_area_ha) + row("Mounting", d.solar.mounting_type) : ""}</table>
<h2>Planning</h2><table><tr><th>Type</th><th>Authority</th><th>Reference</th><th>Application</th><th>Decision date</th><th>Decision</th></tr>${plan || "<tr><td colspan=6>No planning case recorded.</td></tr>"}</table>
<h2>Grid</h2><table><tr><th>Operator</th><th>Point of connection</th><th>kV</th><th>Registered MW</th><th>Status</th></tr>${grid || "<tr><td colspan=5>No grid connection record from loaded sources.</td></tr>"}</table>
<h2>Timeline</h2><table>${hist || "<tr><td>No dated events recorded.</td></tr>"}</table>
<h2>Data discrepancies</h2>${conflicts}
<h2>Supporting sources</h2><table><tr><th>Source</th><th>Tier</th><th>Record</th><th>Published</th><th>Retrieved</th><th>Licence</th><th>Link</th></tr>${srcs}</table>
<div class="warn">Information is consolidated from public sources and may be incomplete or out of date. Source tiers: A statutory/regulator/network/official dataset · B developer/operator primary · C reputable industry/open data · D secondary media · E community maintained. See the Methodology page. Attribution: ${(d.sources as R[]).map((s) => esc(s.attribution)).filter(Boolean).join(" · ")}</div></body></html>`;
  return new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" } });
}
