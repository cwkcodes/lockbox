"use client";
import { useMemo, useState, type ReactNode } from "react";
import { Chip, ConfidenceChip, CopyButton, Glyph, Section, Tabs, useJson, PATTERN_LABEL } from "./ui";
import { fmtDate, fmtDateShort, fmtMw, fmtNum, safeUrl, NOT_IDENTIFIED, UNKNOWN } from "@/lib/format";
import type { Meta } from "@/lib/types";
import type { Pattern } from "@/lib/glyphs";

/* eslint-disable @typescript-eslint/no-explicit-any */
type D = Record<string, any>;
export const TABS = [
  { id: "overview", label: "Overview" }, { id: "technical", label: "Technical" }, { id: "planning", label: "Planning" }, { id: "grid", label: "Grid" }, { id: "ownership", label: "Ownership" },
  { id: "support", label: "Support" }, { id: "units", label: "Units" }, { id: "map", label: "Map" }, { id: "sources", label: "Sources" }, { id: "history", label: "History" },
];

const FIELD_LABEL: Record<string, string> = {
  installed_capacity_mw: "Capacity (installed / headline)", registered_capacity_mw: "Registered capacity (grid register)", cfd_capacity_mw: "CfD contracted capacity", status: "Development status",
  commissioning_date: "Commissioning date", expected_commissioning_date: "Expected commissioning (target)", turbine_count: "Number of turbines", turbine_rated_mw_reported: "Reported turbine rating (MW)",
  turbine_height_reported_m: "Reported turbine height (m)", site_area_ha: "Site area (ha)", planning_reference: "Planning reference", technology: "Technology", location_bng: "Location (BNG)",
  operator: "Operator", applicant: "Applicant", developer: "Developer", storage_capacity_mwh: "Storage energy (MWh)", storage_duration_h: "Duration (h)", export_capacity_mw: "Export capacity (MW)",
  import_capacity_mw: "Import capacity (MW)", connection_voltage_kv: "Connection voltage (kV)", implied_turbine_mean_mw: "Implied mean turbine rating (calculated)",
};

function fieldConfidence(obs: D[]): string {
  const pref = obs.find((o) => o.is_preferred) ?? obs[0];
  if (!pref) return "—";
  if (pref.value_kind === "manual" || pref.value_kind === "research") return "Verified";
  if (pref.value_kind === "calculated") return "Calculated";
  const distinct = new Set(obs.filter((o) => o.value_kind === "published").map((o) => String(o.value_num ?? o.value_text)));
  const srcs = new Set(obs.map((o) => o.source_key));
  if (srcs.size >= 2 && distinct.size === 1) return "High (corroborated)";
  return "Medium (single source)";
}

function ProvPopover({ fields, d }: { fields: string[]; d: D }) {
  const [open, setOpen] = useState(false);
  const obs: D[] = (d.provenance as D[]).filter((p) => fields.includes(p.field_name));
  const srcByKey = new Map<string, D>((d.sources as D[]).map((s) => [s.source_key, s]));
  if (!obs.length) return null;
  const conflicting = (d.conflicts as D[]).some((c) => fields.includes(c.field));
  return (
    <span style={{ position: "relative", display: "inline-block" }}>
      <button type="button" className="btn ghost sm" aria-expanded={open} aria-label={`Show sources for ${fields[0]}`} onClick={() => setOpen(!open)} style={{ padding: "0 4px", height: 18 }}>{conflicting ? "⚠" : "ⓘ"}</button>
      {open && (
        <div role="dialog" aria-label="Field provenance" className="panel" style={{ position: "absolute", zIndex: 20, left: 0, top: 22, width: 330, padding: 10, boxShadow: "var(--shadow)" }}>
          {conflicting && <p style={{ margin: "0 0 6px", color: "var(--warn)", fontWeight: 600 }}>Alternative reported values available</p>}
          <div className="muted" style={{ marginBottom: 6 }}>Field confidence: {fieldConfidence(obs)}</div>
          {obs.map((o) => {
            const s = srcByKey.get(o.source_key);
            return (
              <div key={o.prov_id} style={{ borderTop: "1px solid var(--line-2)", padding: "6px 0" }}>
                <div><strong>{o.value_num ?? o.value_text}{o.value_unit ? ` ${o.value_unit}` : ""}</strong> {o.is_preferred && <Chip tone="ok">preferred</Chip>} {o.value_kind !== "published" && <Chip>{o.value_kind}</Chip>}</div>
                <div className="muted">{s ? `${s.organisation} – ${s.dataset}` : o.source_key} · tier {s?.tier ?? "—"} · dated {fmtDateShort(o.observed_at)}</div>
                {o.raw_column && <div className="muted">Source field “{o.raw_column}” = “{o.raw_value}”</div>}
                {o.calc_expression && <div className="muted">Calculation: {o.calc_expression}</div>}
                {o.selection_reason && <div style={{ fontSize: 12 }}>{o.selection_reason}</div>}
              </div>
            );
          })}
        </div>
      )}
    </span>
  );
}

function F({ label, children, fields, d, unknown }: { label: string; children?: ReactNode; fields?: string[]; d: D; unknown?: string }) {
  const empty = children === null || children === undefined || children === "" || children === "—";
  return (
    <>
      <dt>{label}</dt>
      <dd>{empty ? <span className="muted">{unknown ?? UNKNOWN}</span> : children} {fields && <ProvPopover fields={fields} d={d} />}</dd>
    </>
  );
}

const roleOrder = ["developer", "original_developer", "owner", "operator", "applicant", "lessee", "customer", "asset_manager", "epc", "om", "optimiser"];
const searchLink = (type: string, ref: string | null): string | null => {
  if (!ref) return null;
  if (type === "s36" || type === "ecu") return "https://www.energyconsents.scot/";
  return null;
};

function Overview({ d, meta }: { d: D; meta: Meta | null }) {
  const a = d.a;
  const tech = meta?.technologies.find((t) => t.code === a.technology_code);
  return (
    <div>
      <dl className="kv">
        <F label="Technology" d={d}>{d.technology_label}{a.subtechnology ? ` · ${a.subtechnology}` : ""}</F>
        <F label="Status" d={d} fields={["status"]}>{d.status_label} <span className="muted">(source wording: {a.status_original ?? "—"})</span></F>
        <F label="Capacity" d={d} fields={["installed_capacity_mw", "registered_capacity_mw", "cfd_capacity_mw"]}>{a.installed_capacity_mw != null ? <>{fmtMw(a.installed_capacity_mw)} <span className="muted">· {a.capacity_basis}</span></> : null}</F>
        <F label="Location" d={d} fields={["location_bng"]}>{[...new Set([a.local_authority, a.region, a.country].filter(Boolean))].join(", ") || null}{a.location_description ? <div className="muted">{a.location_description}</div> : null}</F>
        <F label="Developer" d={d}>{(d.orgs as D[]).filter((o) => o.role === "developer").map((o) => o.canonical_name).join("; ") || null}</F>
        <F label="Owner" d={d} unknown={NOT_IDENTIFIED}>{(d.orgs as D[]).filter((o) => o.role === "owner").map((o) => o.canonical_name).join("; ") || null}</F>
        <F label="Operator / applicant" d={d} fields={["operator", "applicant"]}>{(d.orgs as D[]).filter((o) => o.role === "operator" || o.role === "applicant").map((o) => `${o.canonical_name} (${o.role})`).join("; ") || null}</F>
        <F label="Commissioned" d={d} fields={["commissioning_date"]}>{a.commissioning_date ? fmtDate(a.commissioning_date) : null}</F>
        <F label="Development stage" d={d}>{d.stage_group}</F>
        <F label="Project description" d={d} unknown="Not available from loaded sources">{null}</F>
      </dl>
      <Section title="Last verified & data quality">
        <p style={{ margin: "0 0 6px" }}><strong>Last verified: {fmtDate(a.last_verified)}</strong> <span className="muted">(latest date a current source edition confirmed this record)</span><br /><span className="muted">The source’s own “record last updated” date: {a.source_updated ? fmtDate(a.source_updated) : "not stated"}</span></p>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          <ConfidenceChip level={a.confidence} />
          <span className="chip" title="Information completeness: share of expected fields for this technology that are populated. Separate from confidence.">Completeness: {a.completeness_pct ?? "—"}%</span>
          {d.conflicts.length > 0 && <Chip tone="warn">Alternative reported values available ({d.conflicts.length})</Chip>}
          <Chip>{a.coordinate_accuracy}</Chip>
        </div>
        {(d.flags as D[]).length > 0 && <ul style={{ margin: "8px 0 0", paddingLeft: 16 }}>{(d.flags as D[]).map((f) => <li key={f.flag_id}><span className={`chip ${f.severity === "error" ? "bad" : f.severity === "warning" ? "warn" : ""}`}>{f.flag_code.replace(/_/g, " ")}</span> <span className="muted">{f.message}</span></li>)}</ul>}
      </Section>
      <Section title="Key identifiers">
        <dl className="kv">
          {(d.identifiers as D[]).map((i, k) => <F key={k} label={i.scheme.toUpperCase()} d={d}>{i.identifier}</F>)}
          <F label="Canonical ID" d={d}>{a.asset_id} <CopyButton text={a.asset_id} /></F>
        </dl>
      </Section>
      {(d.relationships as D[]).length > 0 && (
        <Section title="Related assets">
          <ul style={{ margin: 0, paddingLeft: 16 }}>{(d.relationships as D[]).map((r, i) => <li key={i}><span className="chip">{r.direction === "out" ? r.relation.replace(/_/g, " ") : `${r.relation.replace(/_/g, " ")} (reverse)`}</span> <a href={`/assets/${r.other_id}`}>{r.other_name}</a> <span className="muted">· {r.other_status} · {fmtMw(r.other_mw)} · {r.basis}</span></li>)}</ul>
        </Section>
      )}
      {(d.research as D[]).length > 0 && (
        <Section title="Missing high-value information" defaultOpen={false}>
          <ul style={{ margin: 0, paddingLeft: 16 }}>{(d.research as D[]).map((r, i) => <li key={i}>{r.missing_field.replace(/_/g, " ")} <span className="muted">– queued for research (look in: {r.suggested_sources.join(", ")})</span></li>)}</ul>
        </Section>
      )}
      <p className="muted" style={{ marginTop: 10 }}>Symbol: <Glyph shape={tech?.symbol ?? "circle"} colour={tech?.colour ?? "#64748b"} pattern={(d.status_pattern ?? "solid") as Pattern} size={14} /> {PATTERN_LABEL[d.status_pattern] ?? ""}</p>
    </div>
  );
}

function Technical({ d }: { d: D }) {
  const a = d.a, w = d.wind, so = d.solar, st = d.storage, hy = d.hydro, bio = d.bio;
  const implied = (d.provenance as D[]).find((p) => p.field_name === "implied_turbine_mean_mw");
  return (
    <div>
      {w && (
        <>
          <p className="muted" style={{ marginTop: 0 }}>Planning/consented design, reported values and as-built facts are kept separate. Values marked <em>as reported</em> come from a register and are not verified as built.</p>
          <dl className="kv">
            <F label="Onshore / offshore" d={d}>{w.offshore ? "Offshore" : "Onshore"}</F>
            <F label="Fixed / floating" d={d}>{w.foundation_type}</F>
            <F label="Turbines (as reported)" d={d} fields={["turbine_count"]}>{w.turbine_count_reported}</F>
            <F label="Consented maximum turbines" d={d} unknown={NOT_IDENTIFIED}>{w.consented_max_turbines}</F>
            <F label="Installed turbines (as built)" d={d} unknown={NOT_IDENTIFIED}>{w.installed_turbines}</F>
            <F label="Turbine manufacturer" d={d} unknown={NOT_IDENTIFIED}>{w.turbine_manufacturer}</F>
            <F label="Turbine model" d={d} unknown={NOT_IDENTIFIED}>{w.turbine_model ? `${w.turbine_model} (${w.model_status})` : null}</F>
            <F label="Turbine rating (as reported)" d={d} fields={["turbine_rated_mw_reported"]}>{w.turbine_rated_mw_reported != null ? `${fmtNum(w.turbine_rated_mw_reported, 2)} MW` : null}</F>
            <F label="Implied mean rating (calculated)" d={d} fields={["implied_turbine_mean_mw"]}>{implied ? <>{fmtNum(implied.value_num, 2)} MW <span className="muted">· calculated: {implied.calc_expression}. Not a turbine model or a published rating.</span></> : null}</F>
            <F label="Hub height" d={d} unknown={NOT_IDENTIFIED}>{w.hub_height_m != null ? `${w.hub_height_m} m` : null}</F>
            <F label="Rotor diameter" d={d} unknown={NOT_IDENTIFIED}>{w.rotor_diameter_m != null ? `${w.rotor_diameter_m} m` : null}</F>
            <F label="Height (as reported)" d={d} fields={["turbine_height_reported_m"]} unknown={NOT_IDENTIFIED}>{w.turbine_height_reported_m != null ? <>{w.turbine_height_reported_m} m <span className="muted">· REPD “Height of Turbines”; whether tip or hub height is not stated</span></> : null}</F>
            <F label="Consented tip height" d={d} unknown={NOT_IDENTIFIED}>{w.consented_tip_height_m != null ? `${w.consented_tip_height_m} m` : null}</F>
            <F label="Installed tip height" d={d} unknown={NOT_IDENTIFIED}>{w.installed_tip_height_m != null ? `${w.installed_tip_height_m} m` : null}</F>
            <F label="Individual positions" d={d}>{w.individual_turbines_known ? "Verified positions available (Units tab)" : <span className="muted">Individual turbine coordinates not verified.</span>}</F>
            {w.offshore_round && <F label="Offshore round" d={d}>{w.offshore_round}</F>}
            {w.lease_area_km2 != null && <F label="Crown Estate lease area" d={d}>{fmtNum(w.lease_area_km2, 1)} km²</F>}
          </dl>
        </>
      )}
      {so && (
        <dl className="kv">
          <F label="Capacity" d={d}>{a.installed_capacity_mw != null ? `${fmtMw(a.installed_capacity_mw)} – REPD “MWelec”; AC/DC basis not stated` : null}</F>
          <F label="MWp (DC)" d={d} unknown={NOT_IDENTIFIED}>{so.mwp_dc}</F><F label="MW (AC)" d={d} unknown={NOT_IDENTIFIED}>{so.mw_ac}</F>
          <F label="Export capacity" d={d} unknown={NOT_IDENTIFIED}>{so.export_mw}</F>
          <F label="Site area" d={d} fields={["site_area_ha"]} unknown={NOT_IDENTIFIED}>{so.site_area_ha != null ? `${fmtNum(so.site_area_ha, 1)} ha` : null}</F>
          <F label="Mounting" d={d}>{so.mounting_type}</F><F label="Tracking / tilt / orientation" d={d} unknown={NOT_IDENTIFIED}>{[so.tracking, so.tilt_deg, so.orientation].filter(Boolean).join(" / ") || null}</F>
          <F label="Module manufacturer / model" d={d} unknown={NOT_IDENTIFIED}>{[so.module_manufacturer, so.module_model].filter(Boolean).join(" ") || null}</F>
          <F label="Inverter manufacturer / model" d={d} unknown={NOT_IDENTIFIED}>{[so.inverter_manufacturer, so.inverter_model].filter(Boolean).join(" ") || null}</F>
          <F label="Module count (published)" d={d} unknown={NOT_IDENTIFIED}>{so.module_count_published}</F>
        </dl>
      )}
      {st && (
        <dl className="kv">
          <F label="Power" d={d} fields={["installed_capacity_mw"]}>{st.power_mw != null ? fmtMw(st.power_mw) : null}</F>
          <F label="Energy" d={d} fields={["storage_capacity_mwh"]} unknown={NOT_IDENTIFIED}>{st.energy_mwh != null ? `${fmtNum(st.energy_mwh)} MWh` : null}</F>
          <F label="Duration (published)" d={d} fields={["storage_duration_h"]} unknown={NOT_IDENTIFIED}>{st.duration_h_published != null ? `${st.duration_h_published} h` : null}</F>
          <F label="Duration (calculated)" d={d} unknown="Needs both MW and MWh">{st.duration_h_calculated != null ? <>{st.duration_h_calculated} h <span className="muted">· calculated: {st.energy_mwh} MWh ÷ {st.power_mw} MW</span></> : null}</F>
          <F label="Import / export" d={d} unknown={NOT_IDENTIFIED}>{st.import_mw != null || st.export_mw != null ? `${st.import_mw ?? "?"} / ${st.export_mw ?? "?"} MW` : null}</F>
          <F label="Storage type" d={d}>{st.storage_type?.replace(/_/g, " ")}</F>
          <F label="Chemistry / supplier / PCS / integrator" d={d} unknown={NOT_IDENTIFIED}>{[st.chemistry, st.system_manufacturer, st.pcs_manufacturer, st.integrator].filter(Boolean).join(" · ") || null}</F>
          <F label="Containers" d={d} unknown={NOT_IDENTIFIED}>{st.container_count}</F>
        </dl>
      )}
      {hy && <dl className="kv"><F label="Classification" d={d}>{hy.classification?.replace(/_/g, " ")}</F><F label="Watercourse / head / flow" d={d} unknown={NOT_IDENTIFIED}>{[hy.watercourse, hy.head_m, hy.design_flow_m3s].filter(Boolean).join(" / ") || null}</F><F label="Units / turbine type" d={d} unknown={NOT_IDENTIFIED}>{[hy.unit_count, hy.turbine_type].filter(Boolean).join(" / ") || null}</F></dl>}
      {bio && <dl className="kv"><F label="Electrical capacity" d={d}>{bio.electrical_mw != null ? fmtMw(bio.electrical_mw) : null}</F><F label="CHP" d={d}>{bio.chp == null ? null : bio.chp ? "Yes" : "No"}</F><F label="Feedstock / digester / engines" d={d} unknown={NOT_IDENTIFIED}>{[bio.feedstock, bio.digester_technology, bio.engine_manufacturer].filter(Boolean).join(" · ") || null}</F></dl>}
      {!w && !so && !st && !hy && !bio && <p className="muted">No technology-specific parameters are held for this record yet.</p>}
      <p className="muted" style={{ marginTop: 10 }}>Capacity basis: {a.capacity_basis ?? "—"}. Scheme/accredited capacity, grid export capacity and physical installed capacity are different quantities and are stored separately.</p>
    </div>
  );
}

function Planning({ d }: { d: D }) {
  const cases: D[] = d.planning;
  return (
    <div>
      {cases.length ? (
        <table className="data"><caption className="sr-only">Planning cases</caption>
          <thead><tr><th scope="col">Type</th><th scope="col">Authority</th><th scope="col">Reference</th><th scope="col">Applied</th><th scope="col">Decision</th><th scope="col">Link</th></tr></thead>
          <tbody>{cases.map((c) => {
            const direct = safeUrl(c.url), search = searchLink(c.ref_type, c.reference);
            return <tr key={c.case_id}><td>{c.ref_type.toUpperCase()}</td><td>{c.authority ?? "—"}</td><td>{c.reference ?? "—"}</td><td>{fmtDateShort(c.application_date)}</td><td>{c.decision ?? "—"}{c.decision_date ? ` · ${fmtDateShort(c.decision_date)}` : ""}</td>
              <td>{direct ? <a href={direct} target="_blank" rel="noopener noreferrer">Application</a> : search ? <a href={search} target="_blank" rel="noopener noreferrer" title="Search the register for this reference">Register (search)</a> : <span className="muted" title={c.notes ?? ""}>No direct link</span>}</td></tr>;
          })}</tbody></table>
      ) : <p className="muted">No planning case recorded in the loaded sources.</p>}
      <dl className="kv" style={{ marginTop: 12 }}>
        <F label="Planning authority" d={d}>{d.a.planning_authority}</F><F label="Planning reference" d={d} fields={["planning_reference"]} unknown={NOT_IDENTIFIED}>{d.a.planning_reference}</F>
        <F label="Section 36 / DCO / DNS / SIP" d={d} unknown={NOT_IDENTIFIED}>{cases.filter((c) => ["s36", "dco", "dns", "sip", "ecu"].includes(c.ref_type)).map((c) => `${c.ref_type.toUpperCase()} ${c.reference ?? ""}`).join("; ") || null}</F>
      </dl>
      <p className="muted" style={{ marginTop: 8 }}>REPD publishes references and dates but not links to the underlying application. Scottish Energy Consents, PINS and Welsh registers could not be ingested automatically (see Data page); a planning application may also describe a maximum design envelope that differs from what was built.</p>
    </div>
  );
}

function Grid({ d }: { d: D }) {
  const rows: D[] = d.grid;
  return (
    <div>
      {rows.length ? rows.map((g) => (
        <dl className="kv" key={g.conn_id} style={{ marginBottom: 10, paddingBottom: 8, borderBottom: "1px solid var(--line-2)" }}>
          <F label="Network operator" d={d}>{g.network_operator}</F><F label="Connection type" d={d}>{g.connection_type}</F><F label="DNO" d={d}>{g.dno}</F>
          <F label="Point of connection" d={d}>{g.point_of_connection}</F><F label="GSP / BSP / primary" d={d} unknown={NOT_IDENTIFIED}>{[g.grid_supply_point, g.bulk_supply_point, g.primary_substation].filter(Boolean).join(" / ") || null}</F>
          <F label="Voltage" d={d} fields={["connection_voltage_kv"]}>{g.voltage_kv != null ? `${g.voltage_kv} kV` : null}</F><F label="Registered capacity" d={d}>{g.registered_capacity_mw != null ? fmtMw(g.registered_capacity_mw) : null}</F>
          <F label="Import / export" d={d} unknown={NOT_IDENTIFIED}>{g.import_mw != null || g.export_mw != null ? `${g.import_mw ?? "?"} / ${g.export_mw ?? "?"} MW` : null}</F>
          <F label="TEC" d={d}>{g.tec_mw != null ? fmtMw(g.tec_mw) : null}</F><F label="Connection status" d={d}>{g.connection_status}</F><F label="Gate" d={d}>{g.gate}</F>
          <F label="ECR / NESO IDs" d={d}>{[g.ecr_id, g.neso_project_id, g.neso_project_number].filter(Boolean).join(" · ") || null}</F><F label="Connection date" d={d}>{g.connection_date ? fmtDate(g.connection_date) : null}</F>
        </dl>
      )) : <p className="muted">No grid-connection record in the loaded sources. NESO TEC/Embedded registers and DNO Embedded Capacity Registers are ingestible but were not available to automated access in this build – see the Data page for the exact reason per source.</p>}
      <p className="muted">Project capacity, registered capacity and grid export capacity are different quantities and are never assumed equal.</p>
    </div>
  );
}

function Ownership({ d }: { d: D }) {
  const orgs = [...(d.orgs as D[])].sort((a, b) => roleOrder.indexOf(a.role) - roleOrder.indexOf(b.role));
  return (
    <div>
      {orgs.length ? <table className="data"><caption className="sr-only">Organisations</caption><thead><tr><th scope="col">Role</th><th scope="col">Organisation</th><th scope="col">As published</th><th scope="col">Effective</th><th scope="col">Share</th></tr></thead>
        <tbody>{orgs.map((o, i) => <tr key={i}><td>{o.role.replace(/_/g, " ")}</td><td><a href={`/organisations?q=${encodeURIComponent(o.canonical_name)}`}>{o.canonical_name}</a></td><td className="muted">{o.raw_name !== o.canonical_name ? o.raw_name : ""}</td><td>{o.effective_from ? fmtDateShort(o.effective_from) : "—"} → {o.effective_to ? fmtDateShort(o.effective_to) : "present/unknown"}</td><td>{o.ownership_pct ?? "—"}</td></tr>)}</tbody></table> : <p className="muted">No organisation is recorded.</p>}
      <p className="muted" style={{ marginTop: 8 }}>Owner: {(orgs.some((o) => o.role === "owner")) ? "recorded above" : NOT_IDENTIFIED}. REPD’s “Operator (or Applicant)” is the operator once operational and the applicant before; no loaded source states ownership percentages, so none are shown. Corporate relationships are never inferred from names.</p>
    </div>
  );
}

function Support({ d }: { d: D }) {
  const rows: D[] = d.support;
  return (
    <div>
      {rows.length ? <table className="data"><caption className="sr-only">Support schemes</caption><thead><tr><th scope="col">Scheme</th><th scope="col">Reference / round</th><th scope="col">Scheme capacity</th><th scope="col">Strike price</th><th scope="col">Delivery</th><th scope="col">Banding / tariff</th><th scope="col">Notes</th></tr></thead>
        <tbody>{rows.map((s) => <tr key={s.support_id}><td>{s.scheme}</td><td>{s.reference ?? s.allocation_round ?? "—"}</td><td className="num">{s.accredited_capacity_mw != null ? fmtMw(s.accredited_capacity_mw) : "—"}</td><td className="num">{s.strike_price_gbp_mwh != null ? `£${fmtNum(s.strike_price_gbp_mwh, 2)}/MWh${s.price_base_year ? ` (${s.price_base_year} prices)` : ""}` : "—"}</td><td>{s.delivery_year ?? "—"}</td><td>{s.banding ?? s.tariff_p_per_kwh ?? "—"}</td><td className="muted">{s.notes ?? ""}</td></tr>)}</tbody></table>
        : <p className="muted">No CfD, RO, REGO or FIT information in the loaded sources. Ofgem station-level data was not available (see Data page).</p>}
      <p className="muted" style={{ marginTop: 8 }}>Scheme (accredited / contracted) capacity is stored separately from physical installed capacity and may legitimately differ from it.</p>
    </div>
  );
}

function Units({ d, onZoom }: { d: D; onZoom: (lon: number, lat: number) => void }) {
  const a = d.a, w = d.wind, units: D[] = d.units;
  return (
    <div>
      {units.length ? (
        <table className="data"><caption className="sr-only">Generating units</caption><thead><tr><th scope="col">ID</th><th scope="col">Manufacturer</th><th scope="col">Model</th><th scope="col">MW</th><th scope="col">Hub</th><th scope="col">Rotor</th><th scope="col">Tip</th><th scope="col">Lat</th><th scope="col">Lon</th><th scope="col">E</th><th scope="col">N</th><th scope="col">Status</th><th scope="col">Coordinate source</th></tr></thead>
          <tbody>{units.map((u) => <tr key={u.unit_id} tabIndex={0} onClick={() => u.lon != null && onZoom(u.lon, u.lat)} onKeyDown={(e) => e.key === "Enter" && u.lon != null && onZoom(u.lon, u.lat)} style={{ cursor: "pointer" }}>
            <td>{u.unit_code}</td><td>{u.manufacturer ?? "—"}</td><td>{u.model ?? "—"}</td><td className="num">{u.rated_mw ?? "—"}</td><td className="num">{u.hub_height_m ?? "—"}</td><td className="num">{u.rotor_diameter_m ?? "—"}</td><td className="num">{u.tip_height_m ?? "—"}</td>
            <td className="num">{u.lat?.toFixed(6) ?? "—"}</td><td className="num">{u.lon?.toFixed(6) ?? "—"}</td><td className="num">{u.bng_e ? Math.round(u.bng_e) : "—"}</td><td className="num">{u.bng_n ? Math.round(u.bng_n) : "—"}</td><td>{u.status_code ?? "—"}</td><td>{u.coordinate_class?.replace(/_/g, " ") ?? "—"}</td></tr>)}</tbody></table>
      ) : (
        <div className="panel" style={{ padding: 12, background: "var(--surface-2)" }}>
          <strong>Individual turbine coordinates not verified.</strong>
          <p style={{ margin: "6px 0 0" }}>{w ? `The source reports ${w.turbine_count_reported ?? "an unknown number of"} turbine(s) for this project but no published turbine positions are held. The map shows only the project reference point (${a.coordinate_accuracy}); positions are never inferred from a site centroid.` : "No generating-unit records are held for this asset."}</p>
          <p className="muted" style={{ margin: "6px 0 0" }}>Candidate evidence (not yet used): planning site-layout drawings and EIA figures (coordinates would be labelled “digitised from official planning drawing”), and OpenStreetMap (labelled “open-source mapped”; supplementary only).</p>
        </div>
      )}
    </div>
  );
}

function MapTab({ d, onZoom }: { d: D; onZoom: (lon: number, lat: number) => void }) {
  const a = d.a;
  return (
    <div>
      <dl className="kv">
        <F label="WGS84 (lat, lon)" d={d} fields={["location_bng"]}>{a.lat != null ? <>{a.lat.toFixed(6)}, {a.lon.toFixed(6)} <CopyButton text={`${a.lat.toFixed(6)}, ${a.lon.toFixed(6)}`} label="Copy WGS84" /></> : null}</F>
        <F label="British National Grid" d={d}>{a.bng_e != null ? <>E {Math.round(a.bng_e)}, N {Math.round(a.bng_n)} <CopyButton text={`${Math.round(a.bng_e)}, ${Math.round(a.bng_n)}`} label="Copy BNG" /></> : null}</F>
        <F label="Coordinate accuracy" d={d}>{a.coordinate_accuracy?.replace(/_/g, " ")}</F><F label="Coordinate source" d={d}>{a.coordinate_source_key}</F>
      </dl>
      {a.lat != null && <p><button type="button" className="btn sm" onClick={() => onZoom(a.lon, a.lat)}>Zoom to project</button></p>}
      <h4 style={{ margin: "10px 0 4px" }}>Geometries (kept separate)</h4>
      <ul style={{ margin: 0, paddingLeft: 16 }}>
        <li>Site reference point: {a.lat != null ? a.coordinate_accuracy : "none"}</li>
        {(d.geometries as D[]).map((g) => <li key={g.geom_id}>{g.geom_type.replace(/_/g, " ")} – {g.label} <span className="muted">({g.original_crs}; source {g.source_key})</span>{g.export_policy === "exclude" && <span className="chip warn" style={{ marginLeft: 6 }}>display only – export restricted by licence</span>}</li>)}
        {!(d.geometries as D[]).length && <li className="muted">No planning boundary, operational boundary, array or lease polygons are held for this asset.</li>}
      </ul>
      <p className="muted">A planning red-line boundary is never shown as the operational footprint; each geometry type is stored and styled separately.</p>
    </div>
  );
}

function Sources({ d }: { d: D }) {
  const [showProv, setShowProv] = useState(false);
  const srcByKey = new Map<string, D>((d.sources as D[]).map((s) => [s.source_key, s]));
  const fields = useMemo(() => {
    const by = new Map<string, D[]>();
    for (const p of d.provenance as D[]) { if (!by.has(p.field_name)) by.set(p.field_name, []); by.get(p.field_name)!.push(p); }
    return [...by.entries()];
  }, [d.provenance]);
  return (
    <div>
      {(d.sources as D[]).map((s) => {
        const url = safeUrl(s.record_url ?? s.snapshot_url);
        const lc = s.link_check;
        return (
          <article key={s.source_record_id} className="panel" style={{ padding: 10, marginBottom: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}><strong>{s.organisation}</strong><span><Chip>Tier {s.tier}</Chip> <Chip>{s.link_type}{s.match_score ? ` ${Math.round(s.match_score * 100)}%` : ""}</Chip></span></div>
            <div>{s.dataset}</div>
            <dl className="kv" style={{ marginTop: 6, gridTemplateColumns: "120px 1fr" }}>
              <dt>Record</dt><dd>{s.record_key}{s.source_name ? ` – ${s.source_name}` : ""}</dd>
              <dt>Published</dt><dd>{fmtDate(s.publication_date)}</dd><dt>Retrieved</dt><dd>{fmtDate(s.retrieved_at)} <span className="muted">· file hash {s.sha12}</span></dd>
              <dt>Type</dt><dd>{s.source_type.replace(/_/g, " ")}</dd><dt>Licence</dt><dd>{s.licence_name ?? "see source"}</dd>
              <dt>Fields supported</dt><dd>{(s.fields_supported ?? []).map((f: string) => FIELD_LABEL[f] ?? f.replace(/_/g, " ")).join(", ") || "—"}</dd>
              <dt>Link</dt><dd>{url ? <a href={url} target="_blank" rel="noopener noreferrer">{url}</a> : "—"} {lc && !lc.ok && <Chip tone="warn">Source currently unavailable</Chip>}</dd>
              {s.snapshot_notes && <><dt>Note</dt><dd className="muted">{s.snapshot_notes}</dd></>}
            </dl>
            {s.attribution && <div className="muted" style={{ marginTop: 4 }}>{s.attribution}</div>}
          </article>
        );
      })}
      <label style={{ display: "flex", gap: 6, alignItems: "center", margin: "10px 0" }}><input type="checkbox" checked={showProv} onChange={(e) => setShowProv(e.target.checked)} /> Show field provenance</label>
      {showProv && (
        <table className="data"><caption className="sr-only">Field provenance</caption><thead><tr><th scope="col">Field</th><th scope="col">Value</th><th scope="col">Source</th><th scope="col">Dated</th><th scope="col">Kind</th></tr></thead>
          <tbody>{fields.flatMap(([f, obs]) => obs.map((o, i) => <tr key={o.prov_id}><td>{i === 0 ? (FIELD_LABEL[f] ?? f.replace(/_/g, " ")) : ""}</td><td>{o.value_num ?? o.value_text}{o.value_unit ? ` ${o.value_unit}` : ""} {o.is_preferred && obs.length > 1 && <Chip tone="ok">preferred</Chip>}</td><td>{srcByKey.get(o.source_key)?.organisation ?? o.source_key}{o.raw_column ? <span className="muted"> · “{o.raw_column}”</span> : ""}</td><td>{fmtDateShort(o.observed_at)}</td><td>{o.value_kind}</td></tr>))}</tbody></table>
      )}
      {d.conflicts.length > 0 && (
        <Section title="Discrepancies between sources" count={d.conflicts.length}>
          {(d.conflicts as D[]).map((c) => <div key={c.field} style={{ marginBottom: 8 }}><strong>{FIELD_LABEL[c.field] ?? c.field}</strong><ul style={{ margin: "2px 0", paddingLeft: 16 }}>{c.observations.map((o: D) => <li key={o.prov_id}>{o.value_num ?? o.value_text} {o.value_unit ?? ""} – {srcByKey.get(o.source_key)?.organisation ?? o.source_key}, {fmtDateShort(o.observed_at)} {o.is_preferred && <Chip tone="ok">preferred</Chip>}{o.selection_reason && o.is_preferred ? <div className="muted">{o.selection_reason}</div> : null}</li>)}</ul></div>)}
        </Section>
      )}
    </div>
  );
}

function History({ d }: { d: D }) {
  const ev: D[] = d.history;
  return ev.length ? (
    <ol style={{ listStyle: "none", margin: 0, padding: 0, borderLeft: "2px solid var(--line)" }}>
      {ev.map((e) => <li key={e.event_id} style={{ padding: "0 0 12px 14px", position: "relative" }}><span aria-hidden style={{ position: "absolute", left: -6, top: 4, width: 10, height: 10, borderRadius: 5, background: "var(--brand)" }} />
        <div><strong>{e.event_date ? fmtDate(e.event_date) : "Date unknown"}</strong></div><div>{e.description}</div>
        {safeUrl(e.url) && <a href={safeUrl(e.url)!} target="_blank" rel="noopener noreferrer" className="muted">evidence</a>}</li>)}
    </ol>
  ) : <p className="muted">No dated events recorded.</p>;
}

export default function AssetDetail({ id, meta, tab, onTab, onZoom, compare, onCompare, onReport, variant = "drawer" }: {
  id: string; meta: Meta | null; tab: string; onTab: (t: string) => void; onZoom: (lon: number, lat: number) => void;
  compare?: string[]; onCompare?: (id: string) => void; onReport?: () => void; variant?: "drawer" | "page";
}) {
  const { data: d, loading, error } = useJson<D>(`/api/assets/${id}`);
  if (loading) return <div style={{ padding: 16 }}><span role="status">Loading asset…</span></div>;
  if (error || !d) return <div style={{ padding: 16 }}>Could not load this asset ({error}).</div>;
  const a = d.a;
  const tech = meta?.technologies.find((t) => t.code === a.technology_code);
  const inCompare = compare?.includes(id);
  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: 0, height: variant === "drawer" ? "100%" : undefined }}>
      <header style={{ padding: "12px 14px 8px", borderBottom: "1px solid var(--line)" }}>
        <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
          <Glyph shape={tech?.symbol ?? "circle"} colour={tech?.colour ?? "#64748b"} pattern={(d.status_pattern ?? "solid") as Pattern} size={22} title={`${d.technology_label}, ${d.status_label}`} />
          <div style={{ minWidth: 0 }}>
            <h2 style={{ fontSize: 17, lineHeight: 1.25 }}>{a.canonical_name}</h2>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
              <Chip>{d.technology_label}</Chip><Chip>{d.status_label}</Chip><ConfidenceChip level={a.confidence} />
              {a.asset_kind === "lease_area" && <Chip tone="warn">Lease-area record</Chip>}
            </div>
            <div className="muted" style={{ marginTop: 4 }}><strong style={{ color: "var(--ink)" }}>Last verified: {fmtDate(a.last_verified)}</strong> · source updated {a.source_updated ? fmtDateShort(a.source_updated) : "n/a"} · {a.asset_id}</div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 6, marginTop: 8, flexWrap: "wrap" }} className="no-print">
          {a.lat != null && <button type="button" className="btn sm" onClick={() => onZoom(a.lon, a.lat)}>Zoom to project</button>}
          {a.lat != null && <CopyButton text={`${a.lat.toFixed(6)}, ${a.lon.toFixed(6)}`} label="Copy coordinates" />}
          <a className="btn sm" href={`/api/evidence-pack/${id}`} target="_blank" rel="noopener noreferrer">Evidence pack</a>
          {onCompare && <button type="button" className="btn sm" aria-pressed={!!inCompare} onClick={() => onCompare(id)}>{inCompare ? "In compare ✓" : "Add to compare"}</button>}
          {variant === "drawer" && <a className="btn sm" href={`/assets/${id}`}>Open page</a>}
          {onReport && <button type="button" className="btn sm ghost" onClick={onReport}>Report an issue</button>}
        </div>
      </header>
      <Tabs tabs={TABS.map((t) => (t.id === "units" ? { ...t, label: a.family === "wind" || d.wind ? "Units / Turbines" : "Units" } : t))} active={tab} onChange={onTab} label="Asset detail sections" />
      <div id={`panel-${tab}`} role="tabpanel" aria-labelledby={`tab-${tab}`} style={{ padding: 14, overflow: "auto", flex: 1, minHeight: 0 }}>
        {tab === "overview" && <Overview d={d} meta={meta} />}
        {tab === "technical" && <Technical d={d} />}
        {tab === "planning" && <Planning d={d} />}
        {tab === "grid" && <Grid d={d} />}
        {tab === "ownership" && <Ownership d={d} />}
        {tab === "support" && <Support d={d} />}
        {tab === "units" && <Units d={d} onZoom={onZoom} />}
        {tab === "map" && <MapTab d={d} onZoom={onZoom} />}
        {tab === "sources" && <Sources d={d} />}
        {tab === "history" && <History d={d} />}
      </div>
    </div>
  );
}
