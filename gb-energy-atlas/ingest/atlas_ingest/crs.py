"""Coordinate handling: British National Grid (EPSG:27700) <-> WGS84 (EPSG:4326)."""
from __future__ import annotations

from pyproj import Transformer

_TO_WGS = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
_TO_BNG = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)

# Formal extent of the BNG 700 km x 1300 km grid. Far-offshore UK sites legitimately sit just outside it
# (the projection is defined beyond the square and registers such as REPD use those values), so this is
# informational; plausibility is judged on the *transformed* position (lat_lon_plausible_uk).
BNG_MAX_E, BNG_MAX_N = 700_000, 1_300_000


def bng_numeric_ok(e: float | None, n: float | None) -> bool:
    """Cheap numeric sanity before transforming (rejects values like 3862265 that cannot be metres on the grid)."""
    return e is not None and n is not None and -300_000 <= e <= 1_500_000 and -300_000 <= n <= 1_800_000


def bng_in_formal_extent(e: float, n: float) -> bool:
    return 0 <= e <= BNG_MAX_E and 0 <= n <= BNG_MAX_N


# kept for callers that want the strict test
bng_valid = bng_in_formal_extent


def bng_to_wgs84(e: float, n: float) -> tuple[float, float]:
    """(easting, northing) → (lat, lon)."""
    lon, lat = _TO_WGS.transform(e, n)
    return lat, lon


def wgs84_to_bng(lat: float, lon: float) -> tuple[float, float]:
    """(lat, lon) → (easting, northing)."""
    e, n = _TO_BNG.transform(lon, lat)
    return e, n


def lat_lon_plausible_uk(lat: float, lon: float) -> bool:
    """Coarse sanity box covering GB, NI and UK waters (to the median line in the North Sea). Not a scope test."""
    return 49.0 <= lat <= 61.5 and -12.0 <= lon <= 3.6


def snap_to_grid(e: float, n: float, size_m: int = 1000) -> tuple[float, float]:
    """Centre of the size_m grid square containing (e, n) – used for privacy-masked locations."""
    return (e // size_m) * size_m + size_m / 2, (n // size_m) * size_m + size_m / 2


def gridref_to_bng(ref: str) -> tuple[float, float, int] | None:
    """OS grid reference ('NT730745', 'TF 889 106') -> (easting, northing, resolution_m) at the SW corner of the square.
    Returns None if malformed. Resolution is 10**(5 - digits/2)."""
    import re
    s = re.sub(r"\s+", "", ref or "").upper()
    m = re.fullmatch(r"([A-HJ-Z])([A-HJ-Z])(\d{2,10})", s)
    if not m or len(m.group(3)) % 2:
        return None
    l1, l2 = ord(m.group(1)) - 65, ord(m.group(2)) - 65
    l1 -= l1 > 7  # the grid alphabet has no 'I'
    l2 -= l2 > 7
    e100 = ((l1 - 2) % 5) * 5 + (l2 % 5)
    n100 = (19 - (l1 // 5) * 5) - (l2 // 5)
    d = m.group(3)
    h = len(d) // 2
    res = 10 ** (5 - h)
    return e100 * 100_000 + int(d[:h]) * res, n100 * 100_000 + int(d[h:]) * res, res
