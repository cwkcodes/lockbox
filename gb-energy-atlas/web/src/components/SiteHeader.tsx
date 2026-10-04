"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { fmtDateShort } from "@/lib/format";
import type { Meta } from "@/lib/types";

export const NAV = [
  { href: "/", label: "Map" }, { href: "/assets", label: "Assets" }, { href: "/turbines", label: "Turbines" }, { href: "/organisations", label: "Organisations" },
  { href: "/dashboard", label: "Dashboard" }, { href: "/data", label: "Data" }, { href: "/methodology", label: "Methodology" }, { href: "/about", label: "About" },
];
export const SITE = "GB Renewable Energy Atlas";

export function ThemeToggle() {
  const [theme, setTheme] = useState<"system" | "light" | "dark">("system");
  useEffect(() => { try { const t = localStorage.getItem("atlas.theme"); if (t === "light" || t === "dark") setTheme(t); } catch { /* ignore */ } }, []);
  const apply = (t: "system" | "light" | "dark") => {
    setTheme(t);
    try { if (t === "system") { localStorage.removeItem("atlas.theme"); document.documentElement.removeAttribute("data-theme"); } else { localStorage.setItem("atlas.theme", t); document.documentElement.setAttribute("data-theme", t); } } catch { /* ignore */ }
    window.dispatchEvent(new Event("atlas-theme"));
  };
  return (
    <select className="input" aria-label="Colour theme" value={theme} onChange={(e) => apply(e.target.value as "system")} style={{ height: 28 }}>
      <option value="system">Theme: auto</option><option value="light">Light</option><option value="dark">Dark</option>
    </select>
  );
}

export function DataDate({ meta }: { meta: Meta | null }) {
  const t = meta?.totals;
  return <span className="muted" style={{ whiteSpace: "nowrap" }} title="Latest source publication date included · date this database was last built">Data: {t?.latest_publication ? fmtDateShort(t.latest_publication) : "—"} · built {t?.last_retrieved ? fmtDateShort(t.last_retrieved) : "—"}</span>;
}

export default function SiteHeader({ current, meta }: { current?: string; meta?: Meta | null }) {
  const [m, setM] = useState<Meta | null>(meta ?? null);
  useEffect(() => { if (!meta) fetch("/api/meta").then((r) => r.json()).then(setM).catch(() => undefined); }, [meta]);
  return (
    <header className="no-print" style={{ background: "var(--surface)", borderBottom: "1px solid var(--line)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "8px 16px", flexWrap: "wrap" }}>
        <Link href="/" style={{ color: "var(--ink)", textDecoration: "none" }}><strong style={{ fontSize: 15, color: "var(--brand)" }}>{SITE}</strong></Link>
        <nav aria-label="Primary" style={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          {NAV.map((n) => <Link key={n.href} href={n.href} aria-current={current === n.href ? "page" : undefined} className="btn ghost sm" style={current === n.href ? { color: "var(--brand)", fontWeight: 700, borderBottom: "2px solid var(--brand)", borderRadius: 0 } : undefined}>{n.label}</Link>)}
        </nav>
        <span style={{ marginLeft: "auto", display: "flex", gap: 10, alignItems: "center" }}><DataDate meta={m} /><ThemeToggle /></span>
      </div>
    </header>
  );
}

export function Page({ title, current, children, wide }: { title: string; current: string; children: React.ReactNode; wide?: boolean }) {
  return (
    <>
      <SiteHeader current={current} />
      <main id="main" style={{ maxWidth: wide ? 1500 : 980, margin: "0 auto", padding: "20px 16px 60px" }}>
        <h1 style={{ fontSize: 22, marginBottom: 12 }}>{title}</h1>
        {children}
      </main>
    </>
  );
}
