"""The normalised source-record shape shared by every adapter (mirrors norm.source_record)."""
from __future__ import annotations

from dataclasses import dataclass, field, fields as dc_fields
from datetime import date
from typing import Any


@dataclass
class Reject:
    reason: str


@dataclass
class NormRecord:
    record_key: str
    name: str | None = None
    name_norm: str | None = None
    alt_names: list[str] = field(default_factory=list)
    record_url: str | None = None
    entity_kind: str = "project"
    technology_code: str | None = None
    technology_raw: str | None = None
    technologies_raw: list[str] = field(default_factory=list)
    status_code: str | None = None
    status_raw: str | None = None
    capacity_mw: float | None = None
    capacity_basis: str | None = None
    export_capacity_mw: float | None = None
    import_capacity_mw: float | None = None
    storage_mwh: float | None = None
    storage_duration_h: float | None = None
    turbine_count: int | None = None
    turbine_rated_mw: float | None = None
    turbine_height_m: float | None = None
    site_area_ha: float | None = None
    bng_e: float | None = None
    bng_n: float | None = None
    lat: float | None = None
    lon: float | None = None
    geom_wkt: str | None = None            # non-point geometry, WGS84 WKT
    geom_kind: str | None = None
    coord_accuracy: str = "none"
    coord_note: str | None = None
    country: str | None = None
    region: str | None = None
    county: str | None = None
    local_authority: str | None = None
    planning_authority: str | None = None
    postcode_public: str | None = None
    operator_raw: str | None = None
    developer_raw: str | None = None
    owner_raw: str | None = None
    planning_ref: str | None = None
    appeal_ref: str | None = None
    sos_ref: str | None = None
    dno: str | None = None
    host_to: str | None = None
    connection_site: str | None = None
    connection_voltage_kv: float | None = None
    connection_status: str | None = None
    connection_date: date | None = None
    gate: str | None = None
    cfd_round: str | None = None
    cfd_capacity_mw: float | None = None
    strike_price: float | None = None
    ro_banding: float | None = None
    fit_tariff: float | None = None
    chp_enabled: bool | None = None
    mounting_type: str | None = None
    storage_type: str | None = None
    record_updated: date | None = None
    application_date: date | None = None
    consent_date: date | None = None
    construction_date: date | None = None
    operational_date: date | None = None
    expected_operational_date: date | None = None
    decommissioned_date: date | None = None
    in_scope_gb: bool = True
    scope_note: str | None = None
    privacy_class: str = "public"
    ids: dict[str, str] = field(default_factory=dict)
    attrs: dict[str, Any] = field(default_factory=dict)
    fields: dict[str, dict[str, Any]] = field(default_factory=dict)
    qa_notes: list[str] = field(default_factory=list)
    excluded_reason: str | None = None

    def prov(self, field_name: str, column: str, raw: Any, unit: str | None = None) -> None:
        """Record which raw column/value a normalised field came from."""
        if raw is None or str(raw).strip() == "":
            return
        entry: dict[str, Any] = {"col": column, "raw": str(raw).strip()}
        if unit:
            entry["unit"] = unit
        self.fields[field_name] = entry


NORM_COLUMNS = [f.name for f in dc_fields(NormRecord) if f.name not in {"geom_wkt"}]
