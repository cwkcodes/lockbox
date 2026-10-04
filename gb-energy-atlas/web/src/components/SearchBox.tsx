"use client";
import { useEffect, useId, useRef, useState } from "react";
import { useDebounced } from "./ui";
import type { Filters } from "@/lib/filters";
import { fmtMw } from "@/lib/format";

/* eslint-disable @typescript-eslint/no-explicit-any */
interface Opt { key: string; group: string; primary: string; secondary?: string; run: () => void }

export default function SearchBox({ onAsset, onFilters, onGoto, onText }: {
  onAsset: (id: string, lon?: number | null, lat?: number | null) => void;
  onFilters: (p: Partial<Filters>) => void; onGoto: (lat: number, lon: number, label: string) => void; onText: (q: string) => void;
}) {
  const [q, setQ] = useState(""), [open, setOpen] = useState(false), [res, setRes] = useState<any>(null), [idx, setIdx] = useState(0);
  const dq = useDebounced(q, 200);
  const id = useId();
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (dq.trim().length < 2) { setRes(null); return; }
    const ac = new AbortController();
    fetch(`/api/search?q=${encodeURIComponent(dq.trim())}`, { signal: ac.signal }).then((r) => r.json()).then((d) => { setRes(d); setIdx(0); }).catch(() => undefined);
    return () => ac.abort();
  }, [dq]);
  useEffect(() => { const h = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false); }; document.addEventListener("mousedown", h); return () => document.removeEventListener("mousedown", h); }, []);

  const close = () => { setOpen(false); };
  const opts: Opt[] = [];
  if (res) {
    if (res.interpretation) {
      const f = res.interpretation as Record<string, string>;
      const label = Object.entries(f).map(([k, v]) => `${k}=${v}`).join(" · ");
      opts.push({ key: "interp", group: "Interpret as filters", primary: `Apply filters: ${label}`, secondary: "Edit in the Filters panel", run: () => {
        const split = (s?: string) => (s ? s.split(",") : []);
        onFilters({ fam: split(f.fam), tech: split(f.tech), wt: split(f.wt) as never, st: split(f.st), ctry: split(f.ctry), mw0: f.mw0 ? Number(f.mw0) : undefined, mw1: f.mw1 ? Number(f.mw1) : undefined, mwh0: f.mwh0 ? Number(f.mwh0) : undefined, q: f.q ?? "" });
        close();
      } });
    }
    if (res.coordinate) opts.push({ key: "coord", group: "Location", primary: `Go to ${res.coordinate.lat.toFixed(4)}, ${res.coordinate.lon.toFixed(4)}`, secondary: res.coordinate.kind, run: () => { onGoto(res.coordinate.lat, res.coordinate.lon, res.coordinate.kind); close(); } });
    for (const a of res.assets ?? []) opts.push({ key: a.asset_id, group: "Assets", primary: a.canonical_name, secondary: `${a.technology_label} · ${a.status_label}${a.installed_capacity_mw != null ? ` · ${fmtMw(a.installed_capacity_mw)}` : ""}${a.local_authority ? ` · ${a.local_authority}` : ""}`, run: () => { onAsset(a.asset_id, a.lon, a.lat); setQ(a.canonical_name); close(); } });
    for (const i of res.identifiers ?? []) opts.push({ key: `id-${i.scheme}-${i.identifier}`, group: "Identifiers", primary: `${String(i.scheme).toUpperCase()} ${i.identifier}`, secondary: i.canonical_name, run: () => { onAsset(i.asset_id); close(); } });
    for (const o of res.organisations ?? []) opts.push({ key: `org-${o.org_id}`, group: "Organisations", primary: o.canonical_name, secondary: `${o.n} assets – filter by this organisation`, run: () => { onFilters({ q: "", dev: [], own: [], opr: [o.canonical_name] }); close(); } });
    for (const p of res.places ?? []) opts.push({ key: `la-${p.name}`, group: "Local authorities", primary: p.name ?? "—", secondary: `${p.n} assets`, run: () => { onFilters({ la: [p.name] }); close(); } });
    for (const m of res.models ?? []) opts.push({ key: `m-${m.turbine_manufacturer}-${m.turbine_model}`, group: "Turbine models", primary: `${m.turbine_manufacturer ?? ""} ${m.turbine_model ?? ""}`.trim(), secondary: `${m.n} projects`, run: () => { onFilters({ mfr: m.turbine_manufacturer ? [m.turbine_manufacturer] : [], mdl: m.turbine_model ? [m.turbine_model] : [] }); close(); } });
  }
  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setOpen(true); setIdx((i) => Math.min(i + 1, opts.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setIdx((i) => Math.max(i - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); if (open && opts[idx]) opts[idx].run(); else { onText(q); close(); } }
    else if (e.key === "Escape") close();
  };
  let last = "";
  return (
    <div ref={box} style={{ position: "relative", flex: 1, maxWidth: 620, minWidth: 120 }}>
      <input className="input" role="combobox" aria-expanded={open && opts.length > 0} aria-controls={`${id}-list`} aria-autocomplete="list" aria-activedescendant={open && opts[idx] ? `${id}-o${idx}` : undefined}
        aria-label="Search projects, developers, references, turbine models, places or coordinates" placeholder="Search projects, developers, references, places…"
        value={q} onChange={(e) => { setQ(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)} onKeyDown={onKey} style={{ width: "100%", boxSizing: "border-box", height: 32 }} />
      {open && opts.length > 0 && (
        <ul id={`${id}-list`} role="listbox" className="panel" style={{ position: "absolute", top: 36, left: 0, right: 0, zIndex: 30, margin: 0, padding: 4, listStyle: "none", boxShadow: "var(--shadow)", maxHeight: "60vh", overflow: "auto" }}>
          {opts.map((o, i) => {
            const head = o.group !== last ? (last = o.group, <li role="presentation" key={`h-${o.group}`} className="muted" style={{ padding: "6px 8px 2px", fontSize: 11, textTransform: "uppercase", letterSpacing: ".05em" }}>{o.group}</li>) : null;
            return [head, <li key={o.key} id={`${id}-o${i}`} role="option" aria-selected={i === idx} onMouseDown={(e) => { e.preventDefault(); o.run(); }} onMouseEnter={() => setIdx(i)}
              style={{ padding: "5px 8px", borderRadius: 3, cursor: "pointer", background: i === idx ? "var(--surface-3)" : undefined }}><div style={{ fontWeight: 600 }}>{o.primary}</div>{o.secondary && <div className="muted" style={{ fontSize: 12 }}>{o.secondary}</div>}</li>];
          })}
        </ul>
      )}
    </div>
  );
}
