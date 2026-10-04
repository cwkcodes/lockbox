"""Information completeness (availability, NOT truth confidence) and the confidence rating rules."""
from __future__ import annotations

from typing import Any

# field -> predicate on the asset context dict
COMMON = ["name", "status", "capacity", "coordinates", "country", "local_authority", "operator_or_developer", "owner",
          "planning_reference", "planning_authority", "grid_operator", "commissioning_date"]
BY_FAMILY = {
    "wind": ["turbine_count", "turbine_manufacturer", "turbine_model", "hub_height_m", "rotor_diameter_m", "tip_height_m", "individual_turbine_positions"],
    "solar": ["mwp_dc", "mw_ac", "export_capacity", "site_area_ha", "module_manufacturer", "inverter_manufacturer", "mounting_type"],
    "storage": ["storage_mwh", "duration_h", "chemistry", "system_manufacturer", "pcs_manufacturer", "integrator", "export_capacity"],
    "hydro": ["head_m", "unit_count", "turbine_type", "classification"],
    "bioenergy": ["feedstock", "thermal_mw", "engine_manufacturer", "chp"],
}


def expected_fields(family: str) -> list[str]:
    return COMMON + BY_FAMILY.get(family, [])


def completeness(ctx: dict[str, Any]) -> tuple[float, list[str]]:
    exp = expected_fields(ctx["family"])
    missing = [f for f in exp if not ctx.get(f)]
    return round(100.0 * (len(exp) - len(missing)) / len(exp), 1), missing


def confidence(ctx: dict[str, Any]) -> str:
    """verified  – manually/research verified OR >=2 independent tier-A sources agree on location, capacity and status
       high      – tier-A source with coordinates, capacity and status AND at least one corroborating source or document
       medium    – a single tier-A source with the core fields (name, status, capacity, coordinates)
       low       – core fields missing, location only approximate, or unresolved material conflict"""
    if ctx.get("manually_verified"):
        return "verified"
    core = ctx.get("has_core_fields")
    n_a = ctx.get("tier_a_sources", 0)
    if ctx.get("material_conflict") or not core:
        return "low"
    if n_a >= 2 and ctx.get("sources_agree"):
        return "verified" if n_a >= 3 else "high"
    if n_a >= 2 or ctx.get("tier_b_sources", 0) >= 1:
        return "high"
    if ctx.get("coordinate_accuracy") in ("approximate", "none"):
        return "low"
    return "medium"
