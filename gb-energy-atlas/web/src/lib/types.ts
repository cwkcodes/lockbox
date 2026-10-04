export interface Tech { code: string; label: string; family: string; category: string; is_renewable: boolean | null; sort_order: number; colour: string; symbol: string; description: string | null }
export interface StatusDef { code: string; label: string; stage_group: string; sort_order: number; pattern: string }
export interface SourceMeta { source_key: string; organisation: string; dataset: string; tier: string; access_status: string; latest_publication_date: string | null; last_checked_at: string | null; records_imported: number | null; licence_name: string | null; attribution: string | null; export_policy: string }
export interface Meta { technologies: Tech[]; statuses: StatusDef[]; sources: SourceMeta[]; totals: { assets: number; last_verified: string | null; last_retrieved: string | null; latest_publication: string | null } }

export interface AssetRow {
  asset_id: string; canonical_name: string; aliases: string[]; technology_code: string; technology_label: string; family: string; colour: string; subtechnology: string | null;
  status_code: string; status_label: string; stage_group: string; country: string | null; region: string | null; local_authority: string | null; is_offshore: boolean;
  lat: number | null; lon: number | null; bng_e: number | null; bng_n: number | null; coordinate_accuracy: string;
  installed_capacity_mw: number | null; capacity_basis: string | null; export_capacity_mw: number | null; storage_capacity_mwh: number | null; storage_duration_h: number | null;
  turbine_count: number | null; turbine_manufacturer: string | null; turbine_model: string | null; hub_height_m: number | null; rotor_diameter_m: number | null; tip_height_m: number | null;
  individual_turbines_known: boolean; developer: string | null; owner: string | null; operator: string | null; commissioning_year: number | null; commissioning_date: string | null;
  planning_reference: string | null; planning_authority: string | null; grid_operator: string | null; dno: string | null; connection_type: string | null; connection_voltage_kv: number | null; connection_status: string | null;
  repd_ref: string | null; tec_ref: string | null; ecr_ref: string | null; cfd_ref: string | null; confidence: string; completeness_pct: number | null; last_verified: string | null;
  asset_kind: string; scale_class: string; has_conflict: boolean; has_cfd: boolean; has_ro: boolean; has_fit: boolean; repowering_status: string; co_located_storage: boolean; source_keys: string[];
}

export interface Headline { projects: number; operational_mw: number; pipeline_mw: number; storage_mw: number; storage_mwh: number; storage_with_mwh: number; turbines_reported: number; turbines_positioned: number; avg_mw: number; without_capacity: number; with_conflicts: number }
export interface Bucket { key: string | number; label?: string; colour?: string; n: number; mw: number; operational_mw?: number; turbines?: number; stage_group?: string }
export interface Stats { headline: Headline; byTechnology: Bucket[]; byStatus: Bucket[]; byCountry: Bucket[]; byDeveloper: Bucket[]; byManufacturer: Bucket[]; byYear: Bucket[]; byYearTech: { year: number; family: string; mw: number }[]; byLocalAuthority: Bucket[] }
export interface FacetOpt { value: string; label?: string; family?: string; category?: string; stage_group?: string; n: number }
export interface Facets { technology: FacetOpt[]; status: FacetOpt[]; country: FacetOpt[]; region: FacetOpt[]; localAuthority: FacetOpt[]; dno: FacetOpt[]; planningAuthority: FacetOpt[]; manufacturer: FacetOpt[]; model: FacetOpt[]; confidence: FacetOpt[]; source: FacetOpt[]; developer: FacetOpt[]; owner: FacetOpt[]; operator: FacetOpt[]; planningYears: { min: number | null; max: number | null }; commissioningYears: { min: number | null; max: number | null } }
