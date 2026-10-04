"""Entity-resolution scoring (pure functions – no database).

Weights follow the specification's illustrative split and are re-normalised over the components that are
actually available for a pair (a missing coordinate does not count as a mismatch, but it also cannot count
as evidence). Safeguards that the score alone cannot provide:

* a name match NEVER links two records on its own (hard-evidence gate);
* a phase / extension / repower marker mismatch blocks automatic linking;
* incompatible technologies are a veto;
* ambiguous best matches go to review, not to a coin-flip.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from .textnorm import core_name, norm_name, norm_org, variant_signature

WEIGHTS = {"name": 0.25, "spatial": 0.25, "tech": 0.10, "capacity": 0.15, "org": 0.10, "planning": 0.10, "date": 0.05}
LINK_THRESHOLD = 0.80
REVIEW_THRESHOLD = 0.55
MIN_EVIDENCE = 0.40  # sum of weights of available components required to score at all

# coordinate tolerance (metres) by accuracy class: full spatial score within it
TOLERANCE_M = {"exact_published": 100, "site_reference": 300, "postcode_centroid": 800, "grid_1km": 1000,
               "approximate": 5000, "open_source_mapped": 150, "digitised_from_drawing": 100}

_TECH_KEY = {
    "wind_onshore": "wind", "wind_offshore": "wind", "wind_offshore_fixed": "wind", "wind_offshore_floating": "wind",
    "solar_pv": "solar", "bess": "bess", "other_storage": "bess", "flow_battery": "bess",
    "hydro": "hydro", "pumped_hydro": "pumped", "tidal_stream": "tidal", "tidal_range": "tidal", "wave": "wave",
    "anaerobic_digestion": "bio", "biomass": "bio", "landfill_gas": "bio", "sewage_gas": "bio", "renewable_chp": "bio",
    "energy_from_waste": "efw", "advanced_conversion": "act", "hydrogen": "h2", "geothermal": "geo",
    "ldes": "ldes", "caes": "ldes",
}
_HYBRID = {
    "hybrid_wind_bess": {"wind", "bess"}, "hybrid_solar_bess": {"solar", "bess"}, "hybrid_wind_solar": {"wind", "solar"},
    "hybrid_wind_solar_bess": {"wind", "solar", "bess"},
}


def tech_keys(codes) -> frozenset[str]:
    out: set[str] = set()
    for c in codes or ():
        if c in _HYBRID:
            out |= _HYBRID[c]
        elif c in _TECH_KEY:
            out.add(_TECH_KEY[c])
        elif c:
            out.add(c)
    return frozenset(out)


@dataclass
class Cand:
    key: str
    name: str | None = None
    techs: frozenset[str] = frozenset()           # technology keys (see tech_keys)
    capacity_mw: float | None = None
    cap_by_tech: dict[str, float] = field(default_factory=dict)
    e: float | None = None
    n: float | None = None
    accuracy: str = "none"
    offshore: bool = False
    orgs: tuple[str, ...] = ()
    planning_refs: frozenset[str] = frozenset()
    year: int | None = None
    country: str | None = None
    poly: object | None = None        # shapely geometry in BNG metres (lease areas etc.)


@dataclass
class MatchResult:
    total: float
    components: dict[str, float | None]
    coverage: float
    decision: str                 # link | review | reject
    reasons: list[str]
    phase_conflict: bool = False


def norm_ref(s: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def name_similarity(a: str | None, b: str | None) -> tuple[float | None, bool]:
    """(similarity 0..1 or None, variant_conflict). Uses token_sort_ratio – NOT token_set_ratio, whose subset rule
    would call 'Glen' and 'Glen Kinglass' identical."""
    if not a or not b:
        return None, False
    ca, cb = core_name(a), core_name(b)
    if len(ca) >= 3 and len(cb) >= 3:
        s = max(fuzz.token_sort_ratio(ca, cb), fuzz.ratio(ca, cb)) / 100.0
    else:
        s = 0.8 * fuzz.token_sort_ratio(norm_name(a), norm_name(b)) / 100.0
    conflict = variant_signature(a) != variant_signature(b)
    if conflict:
        s = min(s, 0.6)
    return s, conflict


def distance_m(a: Cand, b: Cand) -> float | None:
    if None in (a.e, a.n, b.e, b.n):
        return None
    return math.hypot(a.e - b.e, a.n - b.n)  # type: ignore[operator]


def _poly_point_score(poly_c: Cand, pt_c: Cand) -> float | None:
    from shapely.geometry import Point
    if pt_c.e is None or pt_c.n is None or pt_c.accuracy == "none":
        return None
    d = poly_c.poly.distance(Point(pt_c.e, pt_c.n))  # type: ignore[union-attr]
    if d == 0:
        return 1.0  # the point lies inside the polygon
    if d <= 1500:
        return 0.9
    if poly_c.offshore or pt_c.offshore:
        return None  # REPD's offshore reference point is often an onshore/landfall point: far away is not evidence against
    if d <= 8000:
        return max(0.0, 0.9 * (1 - (d - 1500) / 6500))
    return 0.0


def spatial_score(a: Cand, b: Cand) -> float | None:
    if a.poly is not None or b.poly is not None:
        if a.poly is not None and b.poly is not None:
            return None
        return _poly_point_score(a, b) if a.poly is not None else _poly_point_score(b, a)
    d = distance_m(a, b)
    if d is None or a.accuracy == "none" or b.accuracy == "none":
        return None
    if a.offshore and b.offshore and "approximate" in (a.accuracy, b.accuracy):
        return None  # offshore array vs a representative point: distance carries no evidence
    r = max(TOLERANCE_M.get(a.accuracy, 500), TOLERANCE_M.get(b.accuracy, 500))
    if d <= r:
        return 1.0
    far = 3 * r + 500
    return max(0.0, 1.0 - (d - r) / (far - r))


def capacity_score(a: Cand, b: Cand, tech_key: str | None = None) -> float | None:
    ca = a.cap_by_tech.get(tech_key) if tech_key and tech_key in a.cap_by_tech else a.capacity_mw
    cb = b.cap_by_tech.get(tech_key) if tech_key and tech_key in b.cap_by_tech else b.capacity_mw
    if not ca or not cb or ca <= 0 or cb <= 0:
        return None
    r = min(ca, cb) / max(ca, cb)
    return 1.0 if r >= 0.95 else 0.85 if r >= 0.85 else 0.6 if r >= 0.7 else 0.3 if r >= 0.5 else 0.0


def _org_parts(values) -> list[str]:
    out: list[str] = []
    for v in values:
        for part in re.split(r"\s*(?:/|;|&|\band\b)\s*", v or "", flags=re.I):
            k = norm_org(part)
            if len(k) >= 3:
                out.append(k)
    return out


def org_score(a: Cand, b: Cand) -> float | None:
    """Positive evidence only: SPVs get renamed and operators change, so a mismatch says nothing."""
    A, B = _org_parts(a.orgs), _org_parts(b.orgs)
    if not A or not B:
        return None
    best = max(fuzz.token_sort_ratio(x, y) for x in A for y in B)
    return 1.0 if best >= 90 else 0.6 if best >= 78 else None


def planning_score(a: Cand, b: Cand) -> float | None:
    if not a.planning_refs or not b.planning_refs:
        return None
    return 1.0 if any(len(r) >= 5 and r in b.planning_refs for r in a.planning_refs) else 0.0


def date_score(a: Cand, b: Cand) -> float | None:
    """Positive evidence only (commissioning/target dates legitimately differ between sources)."""
    if a.year is None or b.year is None:
        return None
    d = abs(a.year - b.year)
    return 1.0 if d == 0 else 0.6 if d == 1 else None


def tech_score(a: Cand, b: Cand) -> tuple[float | None, str | None]:
    if not a.techs or not b.techs or "unknown" in a.techs or "unknown" in b.techs:
        return None, None
    common = a.techs & b.techs
    if common:
        return 1.0, sorted(common)[0]
    return 0.0, None


def score(a: Cand, b: Cand) -> MatchResult:
    reasons: list[str] = []
    t, tkey = tech_score(a, b)
    name, phase_conflict = name_similarity(a.name, b.name)
    comps: dict[str, float | None] = {
        "name": name, "spatial": spatial_score(a, b), "tech": t,
        "capacity": capacity_score(a, b, tkey), "org": org_score(a, b),
        "planning": planning_score(a, b), "date": date_score(a, b),
    }
    avail = {k: v for k, v in comps.items() if v is not None}
    coverage = sum(WEIGHTS[k] for k in avail)
    total = sum(WEIGHTS[k] * v for k, v in avail.items()) / coverage if coverage else 0.0
    if t == 0.0:
        return MatchResult(total, comps, coverage, "reject", ["technology incompatible (veto)"], phase_conflict)
    if coverage < MIN_EVIDENCE:
        return MatchResult(total, comps, coverage, "reject", [f"insufficient evidence (coverage {coverage:.2f})"], phase_conflict)

    sp, cap, nm, pl = comps["spatial"], comps["capacity"], comps["name"], comps["planning"]
    hard = False
    if pl == 1.0:
        hard = True
        reasons.append("planning reference identical")
    if sp is not None and sp >= 0.8 and (nm is None or nm >= 0.5) and (cap is None or cap >= 0.6):
        hard = True
        reasons.append("co-located, consistent name/capacity")
    if nm is not None and nm >= 0.92 and cap is not None and cap >= 0.85 and (sp is None or sp >= 0.5):
        hard = True
        reasons.append("near-identical name AND matching capacity")
    if phase_conflict:
        reasons.append("phase/extension marker differs – never auto-linked")
    if total >= LINK_THRESHOLD and hard and not phase_conflict:
        return MatchResult(total, comps, coverage, "link", reasons, phase_conflict)
    if total >= REVIEW_THRESHOLD:
        if not hard:
            reasons.append("no hard evidence beyond similarity")
        return MatchResult(total, comps, coverage, "review", reasons, phase_conflict)
    return MatchResult(total, comps, coverage, "reject", reasons or ["below review threshold"], phase_conflict)
