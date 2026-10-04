"use client";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { shapePath, type Pattern } from "@/lib/glyphs";

export function Glyph({ shape, colour, pattern = "solid", size = 16, title }: { shape: string; colour: string; pattern?: Pattern; size?: number; title?: string }) {
  const c = size / 2, r = size * 0.34, d = shapePath(shape, c, c, r);
  const fillOp = pattern === "solid" ? 1 : pattern === "half" ? 0.5 : pattern === "muted" ? 0.6 : 0.12;
  const col = pattern === "muted" ? "#8593a6" : colour;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={title} style={{ flex: "none" }}>
      {title && <title>{title}</title>}
      <path d={d} fill={col} fillOpacity={fillOp} fillRule="evenodd" stroke={pattern === "solid" || pattern === "muted" ? "none" : colour} strokeWidth={size * 0.09} strokeLinejoin="round" />
      {pattern === "cross" && <path d={`M${c - r},${c - r}L${c + r},${c + r}M${c + r},${c - r}L${c - r},${c + r}`} stroke={colour} strokeWidth={size * 0.08} />}
    </svg>
  );
}

export const PATTERN_LABEL: Record<string, string> = { solid: "Solid – operational", half: "Half-filled – in construction", outline: "Outline – consented / planning / proposed", muted: "Muted – decommissioned / inactive", cross: "Struck through – refused / withdrawn / expired / superseded" };

export function Chip({ children, tone }: { children: ReactNode; tone?: "ok" | "warn" | "bad" }) { return <span className={`chip${tone ? " " + tone : ""}`}>{children}</span>; }

export function ConfidenceChip({ level }: { level: string }) {
  const tone = level === "verified" || level === "high" ? "ok" : level === "low" ? "warn" : undefined;
  return <span className={`chip${tone ? " " + tone : ""}`} title="Overall confidence in this record (see Methodology)">Confidence: {level}</span>;
}

export function CopyButton({ text, label = "Copy", className = "btn sm" }: { text: string; label?: string; className?: string }) {
  const [done, setDone] = useState(false);
  return (
    <button type="button" className={className} onClick={async () => { try { await navigator.clipboard.writeText(text); } catch { /* clipboard may be blocked */ } setDone(true); setTimeout(() => setDone(false), 1400); }} aria-live="polite">
      {done ? "Copied" : label}
    </button>
  );
}

export function Tabs({ tabs, active, onChange, label }: { tabs: { id: string; label: string; badge?: ReactNode }[]; active: string; onChange: (id: string) => void; label: string }) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  const onKey = (e: React.KeyboardEvent, i: number) => {
    const n = e.key === "ArrowRight" ? (i + 1) % tabs.length : e.key === "ArrowLeft" ? (i - 1 + tabs.length) % tabs.length : e.key === "Home" ? 0 : e.key === "End" ? tabs.length - 1 : -1;
    if (n >= 0) { e.preventDefault(); onChange(tabs[n].id); refs.current[tabs[n].id]?.focus(); }
  };
  return (
    <div role="tablist" aria-label={label} style={{ display: "flex", gap: 2, borderBottom: "1px solid var(--line)", overflowX: "auto" }}>
      {tabs.map((t, i) => (
        <button key={t.id} ref={(el) => { refs.current[t.id] = el; }} role="tab" id={`tab-${t.id}`} aria-selected={active === t.id} aria-controls={`panel-${t.id}`} tabIndex={active === t.id ? 0 : -1}
          onClick={() => onChange(t.id)} onKeyDown={(e) => onKey(e, i)}
          style={{ all: "unset", cursor: "pointer", padding: "7px 8px", fontSize: 12.5, whiteSpace: "nowrap", fontWeight: active === t.id ? 600 : 400, color: active === t.id ? "var(--brand)" : "var(--ink-2)", borderBottom: `2px solid ${active === t.id ? "var(--brand)" : "transparent"}`, marginBottom: -1 }}>
          {t.label}{t.badge}
        </button>
      ))}
    </div>
  );
}

export function Section({ title, children, defaultOpen = true, count }: { title: string; children: ReactNode; defaultOpen?: boolean; count?: number }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section style={{ borderBottom: "1px solid var(--line-2)" }}>
      <h3 style={{ margin: 0 }}>
        <button type="button" aria-expanded={open} onClick={() => setOpen(!open)} style={{ all: "unset", cursor: "pointer", display: "flex", width: "100%", boxSizing: "border-box", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: ".04em", color: "var(--ink-2)" }}>
          <span>{title}{count ? <span className="chip" style={{ marginLeft: 6 }}>{count}</span> : null}</span><span aria-hidden>{open ? "–" : "+"}</span>
        </button>
      </h3>
      {open && <div style={{ padding: "2px 12px 12px" }}>{children}</div>}
    </section>
  );
}

export function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => { const t = setTimeout(() => setV(value), ms); return () => clearTimeout(t); }, [value, ms]);
  return v;
}

/** fetch JSON with abort + loading/error state, re-run when `url` changes. */
export function useJson<T>(url: string | null): { data: T | null; loading: boolean; error: string | null } {
  const [state, setState] = useState<{ data: T | null; loading: boolean; error: string | null }>({ data: null, loading: !!url, error: null });
  useEffect(() => {
    if (!url) { setState({ data: null, loading: false, error: null }); return; }
    const ac = new AbortController();
    setState((s) => ({ ...s, loading: true, error: null }));
    fetch(url, { signal: ac.signal }).then(async (r) => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); })
      .then((d) => setState({ data: d, loading: false, error: null }))
      .catch((e) => { if (e.name !== "AbortError") setState({ data: null, loading: false, error: String(e.message ?? e) }); });
    return () => ac.abort();
  }, [url]);
  return state;
}

export function Spinner({ label = "Loading" }: { label?: string }) { return <span role="status" className="muted">{label}…</span>; }
export function useLocalStorage<T>(key: string, initial: T): [T, (v: T | ((p: T) => T)) => void] {
  const [val, setVal] = useState<T>(initial);
  useEffect(() => { try { const raw = localStorage.getItem(key); if (raw) setVal(JSON.parse(raw)); } catch { /* storage unavailable */ } }, [key]);
  const set = useCallback((v: T | ((p: T) => T)) => setVal((prev) => { const next = typeof v === "function" ? (v as (p: T) => T)(prev) : v; try { localStorage.setItem(key, JSON.stringify(next)); } catch { /* ignore */ } return next; }), [key]);
  return [val, set];
}
