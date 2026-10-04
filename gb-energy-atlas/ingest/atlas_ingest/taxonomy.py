"""Map each source's vocabulary onto the platform taxonomy. Source wording is stored alongside, never replaced."""
from __future__ import annotations

from .units import clean_text

# ---------------------------------------------------------------------------
# REPD technology -> technology code
# ---------------------------------------------------------------------------
REPD_TECH = {
    "solar photovoltaics": "solar_pv",
    "wind onshore": "wind_onshore",
    "wind offshore": "wind_offshore",
    "battery": "bess",
    "anaerobic digestion": "anaerobic_digestion",
    "landfill gas": "landfill_gas",
    "biomass (dedicated)": "biomass",
    "biomass (co-firing)": "biomass",
    "efw incineration": "energy_from_waste",
    "small hydro": "hydro",
    "large hydro": "hydro",
    "advanced conversion technologies": "advanced_conversion",
    "hydrogen": "hydrogen",
    "fuel cell (hydrogen)": "hydrogen",
    "tidal stream": "tidal_stream",
    "tidal lagoon": "tidal_range",
    "pumped storage hydroelectricity": "pumped_hydro",
    "sewage sludge digestion": "sewage_gas",
    "shoreline wave": "wave",
    "geothermal": "geothermal",
    "hot dry rocks (hdr)": "geothermal",
    "liquid air energy storage": "ldes",
    "compressed air energy storage": "caes",
    "flywheels": "other_storage",
    "air source heat pumps": "other_low_carbon",
    "unknown": "unknown",
}

# REPD "Development Status (short)" -> status code
REPD_STATUS = {
    "operational": "operational",
    "under construction": "under_construction",
    "awaiting construction": "awaiting_construction",
    "application submitted": "planning_submitted",
    "application refused": "refused",
    "application withdrawn": "withdrawn",
    "appeal refused": "refused",
    "appeal withdrawn": "withdrawn",
    "appeal lodged": "planning",
    "planning permission expired": "expired",
    "abandoned": "cancelled",
    "decommissioned": "decommissioned",
    "revised": "superseded",
    # 'No Application Required' says nothing about construction stage – not inferred.
    "no application required": "unknown",
}

# NESO TEC / Embedded "Project Status"
NESO_STATUS = {
    "built": "operational",
    "under construction/commissioning": "under_construction",
    "consents approved": "consented",
    "awaiting consents": "planning",
    "scoping": "scoping",
}

# DNO ECR "Connection Status"
ECR_STATUS = {
    "connected": "operational",
    "accepted to connect": "connection_agreed",
    "accepted to connect ": "connection_agreed",
}

# Crown Estate "Inf_Status" (values observed in the 4 Oct 2026 extract). 'Government Support on Offer' is deliberately
# left unmapped (-> unknown): it states a support stage, not a development stage.
TCE_STATUS = {
    "active/in operation": "operational",
    "under construction": "under_construction",
    "consented": "consented",
    "in planning": "planning",
    "pre-planning application": "pre_planning",
}

# NESO "Plant Type" tokens
NESO_PLANT = {
    "wind onshore": ("wind_onshore", "gen"),
    "wind offshore": ("wind_offshore", "gen"),
    "pv array (photo voltaic/solar)": ("solar_pv", "gen"),
    "energy storage system": ("bess", "storage"),
    "hydro": ("hydro", "gen"),
    "pump storage": ("pumped_hydro", "storage"),
    "biomass": ("biomass", "gen"),
    "tidal": ("tidal_stream", "gen"),
    "wave": ("wave", "gen"),
    "waste": ("energy_from_waste", "other"),
    # Not renewable / not generation: retained in the norm layer, not promoted.
    "ccgt (combined cycle gas turbine)": (None, "excluded:fossil_gas"),
    "ocgt (open cycle gas turbine)": (None, "excluded:fossil_gas"),
    "gas reciprocating": (None, "excluded:fossil_gas"),
    "chp (combined heat and power)": (None, "excluded:chp_fuel_unspecified"),
    "thermal": (None, "excluded:thermal_fuel_unspecified"),
    "nuclear": (None, "excluded:nuclear"),
    "demand": (None, "excluded:demand"),
    "reactive compensation": (None, "excluded:reactive_compensation"),
}

# DNO ECR "Energy Conversion Technology" + "Energy Source"
ECR_TECH = {
    "photovoltaic": "solar_pv",
    "solar": "solar_pv",
    "storage - electrochemical (batteries)": "bess",
    "onshore wind turbines": "wind_onshore",
    "wind": "wind_onshore",
    "offshore wind turbines": "wind_offshore",
    "hydro - run of river": "hydro",
    "hydro - reservoir (not pumped)": "hydro",
    "hydro - other": "hydro",
    "hydro - pumped storage": "pumped_hydro",
    "water (flowing water or head of water)": "hydro",
    "tidal": "tidal_stream",
    "wave": "wave",
    "geothermal": "geothermal",
    "storage - other": "other_storage",
    "storage - flywheel": "other_storage",
    "storage - compressed air": "caes",
    "storage - hydrogen": "hydrogen",
}
ECR_SOURCE_HINT = {  # used only when technology column is generic ('Engine', 'Steam turbine', 'Other')
    "biofuel - landfill gas": "landfill_gas",
    "biofuel - sewage gas": "sewage_gas",
    "biofuel - biogas from anaerobic digestion (excluding landfill & sewage)": "anaerobic_digestion",
    "biomass": "biomass",
    "waste": "energy_from_waste",
}
ECR_EXCLUDED_SOURCES = {"fossil - gas", "fossil - oil", "fossil - coal", "nuclear", "fossil - other", "fossil - coal (inc. coal mine methane)"}


def map_repd_technology(raw: str | None) -> str:
    return REPD_TECH.get((clean_text(raw) or "").lower(), "unknown")


def map_repd_status(raw: str | None) -> str:
    return REPD_STATUS.get((clean_text(raw) or "").lower(), "unknown")


def hybrid_code(techs: set[str]) -> str:
    """Hybrid code from an explicit multi-technology record. Order-independent."""
    wind = any(t.startswith("wind") for t in techs)
    solar = "solar_pv" in techs
    bess = "bess" in techs
    if wind and solar and bess:
        return "hybrid_wind_solar_bess"
    if wind and solar:
        return "hybrid_wind_solar"
    if wind and bess:
        return "hybrid_wind_bess"
    if solar and bess:
        return "hybrid_solar_bess"
    return "hybrid_other"


CFD_TECH = {
    "offshore wind": "wind_offshore", "offshore wind-scotland": "wind_offshore", "offshore wind permitted reduction": "wind_offshore",
    "floating offshore wind": "wind_offshore_floating",
    "onshore wind (>5mw)": "wind_onshore", "onshore wind": "wind_onshore", "remote island wind (riw)": "wind_onshore",
    "remote island wind": "wind_onshore", "solar pv (>5mw)": "solar_pv", "solar pv": "solar_pv",
    "tidal stream": "tidal_stream", "wave": "wave", "geothermal": "geothermal",
    "advanced conversion technologies": "advanced_conversion", "anaerobic digestion (>5mw)": "anaerobic_digestion",
    "biomass conversion": "biomass", "dedicated biomass with chp": "biomass", "energy from waste with chp": "energy_from_waste",
    "landfill gas": "landfill_gas", "sewage gas": "sewage_gas", "hydro": "hydro",
}
