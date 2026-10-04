"""OpenStreetMap (ODbL) generator/turbine adapter via an Overpass endpoint the operator is permitted to use.

Disabled unless OVERPASS_URL is set. OSM is supplementary evidence (tier E): it never overrides authoritative coordinates."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterator

from .. import config, crs
from ..http import SourceUnavailable
from ..model import NormRecord, Reject
from ..textnorm import norm_name
from ..units import clean_text, parse_number
from .base import Adapter, Resource

# Great Britain bounding box (south, west, north, east). Scope refined later by point-in-polygon.
QUERY = ('[out:json][timeout:180];(node["generator:source"="wind"](49.8,-8.7,60.9,1.9);'
         'node["power"="generator"]["generator:source"~"solar|hydro|biomass|biogas"](49.8,-8.7,60.9,1.9););out body;')


def _power_mw(v: str | None) -> float | None:
    """'2.3 MW', '2300 kW', '2.3' (OSM default unit W for bare numbers per wiki → treated as unknown, not guessed)."""
    s = clean_text(v)
    if not s:
        return None
    m = re.fullmatch(r"([\d.,]+)\s*(kw|mw|gw|w)", s.lower().replace(" ", ""))
    if not m:
        return None
    n = parse_number(m.group(1))
    return None if n is None else n * {"w": 1e-6, "kw": 1e-3, "mw": 1.0, "gw": 1e3}[m.group(2)]


def _metres(v: str | None) -> float | None:
    s = clean_text(v)
    if not s:
        return None
    m = re.fullmatch(r"([\d.]+)\s*(m)?", s.lower())
    return float(m.group(1)) if m else None


class OsmOverpassAdapter(Adapter):
    source_key = "osm_overpass"

    def discover(self) -> list[Resource]:
        if not config.OVERPASS_URL:
            raise SourceUnavailable("OVERPASS_URL not configured: no Overpass endpoint the operator is permitted to use "
                                    "(overpass-api.de and mirrors are blocked from the build environment)")
        return [Resource(url=f"{config.OVERPASS_URL}?data={QUERY}", label="gb_generators", suffix=".json",
                         licence_text="ODbL 1.0 – © OpenStreetMap contributors")]

    def parse(self, path: Path, resource: Resource) -> Iterator[tuple[int, str | None, dict[str, Any]]]:
        doc = json.loads(path.read_text(encoding="utf-8"))
        for i, el in enumerate(doc.get("elements", []), start=1):
            yield i, f"{el.get('type', 'node')}/{el.get('id')}", el

    def normalise(self, payload: dict[str, Any], row_number: int, resource: Resource) -> NormRecord | Reject:
        tags = payload.get("tags") or {}
        if payload.get("type") != "node" or "lat" not in payload:
            return Reject("not a node with coordinates")
        lat, lon = float(payload["lat"]), float(payload["lon"])
        if not crs.lat_lon_plausible_uk(lat, lon):
            return Reject("coordinates outside UK extent")
        src = (tags.get("generator:source") or "").lower()
        code = {"wind": "wind_onshore", "solar": "solar_pv", "hydro": "hydro", "biomass": "biomass", "biogas": "anaerobic_digestion"}.get(src)
        if not code:
            return Reject(f"generator:source '{src}' not in scope")
        key = f"node/{payload['id']}"
        rec = NormRecord(record_key=key, name=clean_text(tags.get("name")) or f"OSM {src} generator {payload['id']}",
                         record_url=f"https://www.openstreetmap.org/node/{payload['id']}", entity_kind="unit")
        rec.name_norm = norm_name(rec.name)
        rec.technology_code, rec.technology_raw = code, f"generator:source={src}"
        rec.lat, rec.lon = lat, lon
        rec.bng_e, rec.bng_n = crs.wgs84_to_bng(lat, lon)
        rec.coord_accuracy, rec.coord_note = "open_source_mapped", "OpenStreetMap contributors (ODbL); not an authoritative position"
        rec.capacity_mw = _power_mw(tags.get("generator:output:electricity"))
        rec.turbine_height_m = _metres(tags.get("height"))
        rec.attrs.update(manufacturer=clean_text(tags.get("manufacturer")), model=clean_text(tags.get("model")),
                         hub_height_m=_metres(tags.get("height:hub") or tags.get("hub_height")),
                         rotor_diameter_m=_metres(tags.get("rotor:diameter")), start_date=clean_text(tags.get("start_date")),
                         operator=clean_text(tags.get("operator")), osm_tags=tags)
        rec.operator_raw = rec.attrs["operator"]
        rec.status_code, rec.status_raw = "operational", "present in OSM (not a verified operational status)"
        return rec
