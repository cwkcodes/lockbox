export const fmtNum = (v: number | string | null | undefined, digits = 1): string => {
  if (v === null || v === undefined || v === "") return "—";
  const n = typeof v === "string" ? Number(v) : v;
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("en-GB", { maximumFractionDigits: digits, minimumFractionDigits: 0 });
};
export const fmtMw = (v: number | string | null | undefined): string => (v === null || v === undefined ? "—" : `${fmtNum(v, Number(v) >= 100 ? 0 : 1)} MW`);
export const fmtMwh = (v: number | string | null | undefined): string => (v === null || v === undefined ? "—" : `${fmtNum(v, 1)} MWh`);
export const fmtGw = (mw: number): string => (mw >= 1000 ? `${fmtNum(mw / 1000, 2)} GW` : `${fmtNum(mw, 0)} MW`);
export const fmtDate = (v: string | Date | null | undefined): string => {
  if (!v) return "—";
  const d = typeof v === "string" ? new Date(v) : v;
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric", timeZone: "UTC" });
};
export const fmtDateShort = (v: string | Date | null | undefined): string => {
  if (!v) return "—";
  const d = typeof v === "string" ? new Date(v) : v;
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" });
};
/** Only http(s) links are ever rendered as hrefs (source URLs come from external data). */
export const safeUrl = (u: string | null | undefined): string | null => {
  if (!u) return null;
  try { const x = new URL(u); return x.protocol === "http:" || x.protocol === "https:" ? x.toString() : null; } catch { return null; }
};
export const UNKNOWN = "Unknown";
export const NOT_IDENTIFIED = "Not publicly identified";
export const csvEscape = (v: unknown): string => {
  if (v === null || v === undefined) return "";
  let s = v instanceof Date ? v.toISOString().slice(0, 10) : String(v);
  if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`; // neutralise spreadsheet formula injection from source text
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};
