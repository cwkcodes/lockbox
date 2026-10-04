"""Number/unit/date parsing. Original values are always retained by callers; these only normalise."""
from __future__ import annotations

import re
from datetime import date, datetime

NULL_TOKENS = {
    "", "n/a", "na", "nan", "null", "none", "-", "--", "tbc", "tbd", "?",
    "data not available", "data not applicable", "not available", "not applicable", "--redacted--", "redacted",
}


def clean_text(value) -> str | None:
    """Strip, collapse internal whitespace, map sentinel strings to None."""
    if value is None:
        return None
    s = re.sub(r"\s+", " ", str(value)).strip()
    if s.lower() in NULL_TOKENS:
        return None
    return s


def parse_number(value) -> float | None:
    """Parse '1,234.5', ' 12 ', '12.0' → float. Returns None for blanks/sentinels/non-numeric."""
    s = clean_text(value)
    if s is None:
        return None
    s = s.replace(",", "").replace("£", "")
    if not re.fullmatch(r"[-+]?\d+(\.\d+)?([eE][-+]?\d+)?", s):
        return None
    return float(s)


_TO_MW = {"kw": 1e-3, "mw": 1.0, "gw": 1e3, "w": 1e-6}
_TO_MWH = {"kwh": 1e-3, "mwh": 1.0, "gwh": 1e3, "twh": 1e6}
_TO_M = {"m": 1.0, "km": 1000.0, "mm": 1e-3}
_TO_HA = {"m2": 1e-4, "sqm": 1e-4, "ha": 1.0, "km2": 100.0}


def power_to_mw(value, unit: str) -> float | None:
    n = parse_number(value)
    if n is None:
        return None
    return n * _TO_MW[unit.strip().lower()]


def energy_to_mwh(value, unit: str) -> float | None:
    n = parse_number(value)
    if n is None:
        return None
    return n * _TO_MWH[unit.strip().lower()]


def length_to_m(value, unit: str) -> float | None:
    n = parse_number(value)
    return None if n is None else n * _TO_M[unit.strip().lower()]


def area_to_ha(value, unit: str) -> float | None:
    n = parse_number(value)
    return None if n is None else n * _TO_HA[unit.strip().lower()]


def parse_date(value) -> date | None:
    """Accepts dd/mm/yyyy, yyyy-mm-dd, yyyy-mm-ddTHH:MM:SS, dd-Mon-yyyy. Excel 1900 artefacts → None."""
    s = clean_text(value)
    if s is None:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%d-%b-%Y", "%d/%m/%y"):
        try:
            d = datetime.strptime(s[:26] if ("T" in s or " " in s) else s, fmt).date()
        except ValueError:
            continue
        if d.year <= 1900:  # Excel serial-date artefact (e.g. 02/01/1900): never a real project date
            return None
        return d
    return None


def duration_hours(power_mw: float | None, energy_mwh: float | None) -> float | None:
    """Duration (h) = energy (MWh) / power (MW). Only when both are known and power > 0."""
    if power_mw is None or energy_mwh is None or power_mw <= 0:
        return None
    return round(energy_mwh / power_mw, 3)
