"use client";
import { useCallback, useEffect, useState } from "react";
import { Page } from "@/components/SiteHeader";
import { Chip, Tabs } from "@/components/ui";
import { fmtDateShort, fmtNum } from "@/lib/format";

/* eslint-disable @typescript-eslint/no-explicit-any */
async function api(path: string, init?: RequestInit) { const r = await fetch(path, init); return { ok: r.ok, status: r.status, data: await r.json().catch(() => ({})) }; }

export default function Admin() {
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [token, setToken] = useState(""), [err, setErr] = useState("");
  const [tab, setTab] = useState("qa");
  const check = useCallback(async () => setAuthed((await api("/api/admin/qa")).ok), []);
  useEffect(() => { check(); }, [check]);
  const login = async (e: React.FormEvent) => { e.preventDefault(); const r = await api("/api/admin/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }) }); if (r.ok) { setErr(""); check(); } else setErr(r.data.error ?? "Login failed"); };
  if (authed === null) return <Page title="Administration" current="/admin"><p>Checking…</p></Page>;
  if (!authed) return (
    <Page title="Administration" current="/admin">
      <p>Restricted to data administrators. Set <code>ADMIN_TOKEN</code> on the server and enter it here.</p>
      <form onSubmit={login} style={{ display: "flex", gap: 8 }}><input className="input" type="password" autoComplete="current-password" aria-label="Admin token" value={token} onChange={(e) => setToken(e.target.value)} /><button className="btn primary">Sign in</button></form>
      {err && <p role="alert" style={{ color: "var(--bad)" }}>{err}</p>}
    </Page>
  );
  return (
    <Page title="Data administration" current="/admin" wide>
      <Tabs label="Admin sections" active={tab} onChange={setTab} tabs={[{ id: "qa", label: "QA dashboard" }, { id: "dups", label: "Duplicates & matches" }, { id: "reports", label: "User reports" }, { id: "ingest", label: "Ingestion & sources" }, { id: "edit", label: "Manual edit" }]} />
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} style={{ paddingTop: 14 }}>
        {tab === "qa" && <QA />}{tab === "dups" && <Dups />}{tab === "reports" && <Reports />}{tab === "ingest" && <Ingest />}{tab === "edit" && <Edit />}
      </div>
    </Page>
  );
}

function QA() {
  const [d, setD] = useState<any>(null), [code, setCode] = useState<string | null>(null);
  useEffect(() => { api(`/api/admin/qa${code ? `?code=${code}` : ""}`).then((r) => setD(r.data)); }, [code]);
  if (!d) return <p>Loading…</p>;
  return (
    <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 14, alignItems: "start" }}>
      <div className="panel"><table className="data"><caption className="sr-only">Open flags by type</caption><thead><tr><th scope="col">Flag</th><th scope="col">Sev.</th><th scope="col" style={{ textAlign: "right" }}>Open</th></tr></thead>
        <tbody>{d.byCode?.map((f: any) => <tr key={f.flag_code + f.severity} aria-selected={code === f.flag_code}><td><button type="button" className="btn ghost sm" onClick={() => setCode(f.flag_code)}>{f.flag_code.replace(/_/g, " ")}</button></td><td><Chip tone={f.severity === "error" ? "bad" : f.severity === "warning" ? "warn" : undefined}>{f.severity}</Chip></td><td className="num">{fmtNum(f.n, 0)}</td></tr>)}</tbody></table>
        <p className="muted" style={{ padding: "0 8px" }}>Stale records (old source): {fmtNum(d.staleRecords, 0)} · Research queue: {d.researchQueue?.reduce((a: number, r: any) => a + r.n, 0)} items · Pending match candidates: {d.matchCandidates?.find((m: any) => m.decision === "pending")?.n ?? 0}</p></div>
      <div className="panel" style={{ overflow: "auto" }}>{code ? <table className="data"><caption className="sr-only">Flagged assets</caption><thead><tr><th scope="col">Asset</th><th scope="col">Technology</th><th scope="col">Country</th><th scope="col">Detail</th></tr></thead><tbody>{d.flagged?.map((f: any) => <tr key={f.flag_id}><td><a href={`/assets/${f.asset_id}`}>{f.canonical_name}</a></td><td>{f.technology_code}</td><td>{f.country}</td><td className="muted">{JSON.stringify(f.detail).slice(0, 160)}</td></tr>)}</tbody></table> : <p style={{ padding: 12 }} className="muted">Select a flag type to list affected assets (highest capacity first).</p>}</div>
    </div>
  );
}

function Dups() {
  const [items, setItems] = useState<any[]>([]), [msg, setMsg] = useState("");
  const load = useCallback(() => api("/api/admin/candidates").then((r) => setItems(r.data.items ?? [])), []);
  useEffect(() => { load(); }, [load]);
  const decide = async (id: number, decision: "approved" | "rejected") => {
    const reason = window.prompt(`Reason for ${decision === "approved" ? "linking" : "NOT linking"} (stored in the audit trail)`);
    if (!reason) return;
    const r = await api("/api/admin/candidates", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cand_id: id, decision, reason }) });
    setMsg(r.ok ? r.data.note : r.data.error); load();
  };
  return (
    <div>{msg && <p role="status">{msg}</p>}
      <div className="panel" style={{ overflow: "auto" }}><table className="data"><caption className="sr-only">Match candidates awaiting review</caption><thead><tr><th scope="col">Source record</th><th scope="col">Candidate asset</th><th scope="col">Score</th><th scope="col">Why not auto-linked</th><th scope="col">Decision</th></tr></thead>
        <tbody>{items.map((c) => <tr key={c.cand_id}><td><strong>{c.source_name}</strong><div className="muted">{c.source_key} · {c.source_tech} · {c.source_mw ?? "—"} MW · {c.source_status}</div></td><td><a href={`/assets/${c.asset_id}`}>{c.canonical_name}</a><div className="muted">{c.asset_tech} · {c.asset_mw ?? "—"} MW · {c.asset_status}</div></td><td className="num">{Number(c.score).toFixed(2)}</td><td className="muted">{c.reason}</td><td style={{ whiteSpace: "nowrap" }}><button type="button" className="btn sm" onClick={() => decide(c.cand_id, "approved")}>Same asset</button> <button type="button" className="btn sm" onClick={() => decide(c.cand_id, "rejected")}>Different</button></td></tr>)}</tbody></table></div>
      <p className="muted">Decisions are stored against stable source/asset identifiers and take effect at the next canonical build.</p></div>
  );
}

function Reports() {
  const [items, setItems] = useState<any[]>([]);
  const load = useCallback(() => api("/api/admin/reports").then((r) => setItems(r.data.items ?? [])), []);
  useEffect(() => { load(); }, [load]);
  const set = async (id: number, status: string) => { await api("/api/admin/reports", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ report_id: id, status }) }); load(); };
  return <div className="panel" style={{ overflow: "auto" }}><table className="data"><caption className="sr-only">User-submitted corrections</caption><thead><tr><th scope="col">When</th><th scope="col">Type</th><th scope="col">Asset</th><th scope="col">Description</th><th scope="col">Evidence</th><th scope="col">Status</th></tr></thead>
    <tbody>{items.map((r) => <tr key={r.report_id}><td>{fmtDateShort(r.submitted_at)}</td><td>{r.report_type}</td><td>{r.asset_id ? <a href={`/assets/${r.asset_id}`}>{r.asset_id}</a> : "—"}</td><td>{r.description}</td><td><a href={r.evidence_url} target="_blank" rel="noopener noreferrer">link</a></td><td>{r.status === "pending_review" ? <><button type="button" className="btn sm" onClick={() => set(r.report_id, "accepted")}>Accept</button> <button type="button" className="btn sm" onClick={() => set(r.report_id, "rejected")}>Reject</button></> : r.status}</td></tr>)}
      {!items.length && <tr><td colSpan={6} className="muted" style={{ padding: 12 }}>No reports.</td></tr>}</tbody></table></div>;
}

function Ingest() {
  const [d, setD] = useState<any>(null), [qa, setQa] = useState<any>(null), [msg, setMsg] = useState("");
  const load = useCallback(() => { api("/api/admin/ingestion").then((r) => setD(r.data)); api("/api/admin/qa").then((r) => setQa(r.data)); }, []);
  useEffect(() => { load(); }, [load]);
  const queue = async (body: object) => { const r = await api("/api/admin/ingestion", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); setMsg(r.ok ? `Queued job ${r.data.job_id}. Run the worker: atlas-ingest worker` : r.data.error); load(); };
  return (
    <div style={{ display: "grid", gap: 14 }}>
      {msg && <p role="status">{msg}</p>}
      <div className="panel" style={{ overflow: "auto" }}><table className="data"><caption>Recent ingestion runs</caption><thead><tr><th scope="col">Source</th><th scope="col">Outcome</th><th scope="col">Rows ok</th><th scope="col">Quarantined</th><th scope="col">Message</th><th scope="col"></th></tr></thead>
        <tbody>{qa?.ingestionRuns?.map((r: any) => <tr key={r.run_id}><td>{r.source_key}</td><td><Chip tone={r.outcome === "success" || r.outcome === "unchanged" ? "ok" : "warn"}>{r.outcome}</Chip></td><td className="num">{r.rows_ok ?? "—"}</td><td className="num">{r.rows_rejected ?? "—"}</td><td className="muted">{r.message}</td><td><button type="button" className="btn sm" onClick={() => queue({ source_key: r.source_key })}>Re-ingest</button></td></tr>)}</tbody></table></div>
      <div className="panel" style={{ padding: 10 }}><strong>Quarantined rows (current snapshots)</strong><table className="data"><tbody>{d?.rejects?.map((r: any, i: number) => <tr key={i}><td>{r.source_key}</td><td>{r.reason}</td><td className="num">{r.n}</td></tr>)}{!d?.rejects?.length && <tr><td className="muted">None.</td></tr>}</tbody></table></div>
      <div><button type="button" className="btn" onClick={() => queue({ job_type: "build" })}>Queue canonical rebuild</button> <span className="muted">Jobs run when <code>atlas-ingest worker</code> is running.</span></div>
      <div className="panel" style={{ padding: 10 }}><strong>Job queue</strong><table className="data"><tbody>{d?.jobs?.map((j: any) => <tr key={j.job_id}><td>#{j.job_id}</td><td>{j.job_type} {j.source_key ?? ""}</td><td>{j.status}</td><td className="muted">{j.message}</td></tr>)}</tbody></table></div>
    </div>
  );
}

function Edit() {
  const [msg, setMsg] = useState("");
  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); const fd = new FormData(e.currentTarget);
    const r = await api(`/api/admin/assets/${fd.get("id")}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ field: fd.get("field"), value: fd.get("value"), reason: fd.get("reason"), evidence_url: fd.get("evidence"), ai_assisted: fd.get("ai") === "on" }) });
    setMsg(r.ok ? "Saved: audit entry written and override stored (re-applied on every rebuild)." : r.data.error);
  };
  return (
    <form onSubmit={submit} className="panel" style={{ padding: 14, maxWidth: 560, display: "grid", gap: 8 }}>
      <label>Asset ID<br /><input name="id" className="input" required pattern="GBA-\d{7}" placeholder="GBA-0002750" /></label>
      <label>Field<br /><select name="field" className="input">{["canonical_name", "status_code", "technology_code", "installed_capacity_mw", "planning_reference", "planning_authority", "notes"].map((f) => <option key={f}>{f}</option>)}</select></label>
      <label>New value<br /><input name="value" className="input" required style={{ width: "100%" }} /></label>
      <label>Reason (required, audited)<br /><input name="reason" className="input" required minLength={5} style={{ width: "100%" }} /></label>
      <label>Evidence URL<br /><input name="evidence" className="input" type="url" style={{ width: "100%" }} /></label>
      <label><input type="checkbox" name="ai" /> This change was AI-assisted (recorded as such)</label>
      <button className="btn primary">Apply edit</button>{msg && <p role="status">{msg}</p>}
      <p className="muted">Every manual edit writes <code>ops.audit_log</code> (timestamp, old value, new value, reason, actor, AI-assisted flag) and a manual provenance observation.</p>
    </form>
  );
}
