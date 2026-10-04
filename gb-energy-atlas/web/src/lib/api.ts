import { NextRequest, NextResponse } from "next/server";
import { buildWhere, parseFilters, type Filters, type Where } from "./filters";

export const json = (data: unknown, init?: ResponseInit & { cache?: string }) =>
  NextResponse.json(data, { ...init, headers: { "Cache-Control": init?.cache ?? "no-store", ...(init?.headers ?? {}) } });

export const apiError = (status: number, message: string) => NextResponse.json({ error: message }, { status });

export function filtersFrom(req: NextRequest): { filters: Filters; where: Where } {
  const filters = parseFilters(req.nextUrl.searchParams);
  return { filters, where: buildWhere(filters) };
}

export const intParam = (req: NextRequest, k: string, def: number, min: number, max: number): number => {
  const v = Number(req.nextUrl.searchParams.get(k));
  return Number.isFinite(v) && req.nextUrl.searchParams.has(k) ? Math.min(max, Math.max(min, Math.trunc(v))) : def;
};

/** Columns returned by list-style endpoints (kept in one place so table, export and API agree). */
export const LIST_COLUMNS = `
  f.asset_id, f.canonical_name, f.aliases, f.technology_code, f.technology_label, f.family, f.colour, f.subtechnology,
  f.status_code, f.status_label, f.stage_group, f.country, f.region, f.local_authority, f.is_offshore, f.lat, f.lon, f.bng_e, f.bng_n,
  f.coordinate_accuracy, f.installed_capacity_mw, f.capacity_basis, f.export_capacity_mw, f.storage_capacity_mwh, f.storage_duration_h,
  f.turbine_count, f.turbine_manufacturer, f.turbine_model, f.hub_height_m, f.rotor_diameter_m, f.tip_height_m, f.individual_turbines_known,
  f.developer, f.owner, f.operator, f.commissioning_year, f.commissioning_date, f.planning_reference, f.planning_authority,
  f.grid_operator, f.dno, f.connection_type, f.connection_voltage_kv, f.connection_status, f.repd_ref, f.tec_ref, f.ecr_ref, f.cfd_ref,
  f.confidence, f.completeness_pct, f.last_verified, f.asset_kind, f.scale_class, f.has_conflict, f.has_cfd, f.has_ro, f.has_fit,
  f.repowering_status, f.co_located_storage, f.source_keys`;

export function adminAllowed(req: NextRequest): boolean {
  const token = process.env.ADMIN_TOKEN;
  if (!token || (process.env.NODE_ENV === "production" && token === "change-me")) return false;
  const auth = req.headers.get("authorization");
  if (auth?.startsWith("Bearer ") && timingSafeEqual(auth.slice(7), token)) return true;
  const cookie = req.cookies.get("atlas_admin")?.value;
  return !!cookie && timingSafeEqual(cookie, token);
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}
