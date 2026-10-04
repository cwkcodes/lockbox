"""ONS Local Authority Districts (BGC) – context layer used to *derive* local authority by point-in-polygon."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from shapely.geometry import shape
from shapely.validation import make_valid

from ..model import NormRecord, Reject
from ..textnorm import norm_name
from ..units import clean_text
from .base import Adapter, Resource

LAYER = "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/Local_Authority_Districts_DEC_2025_Boundaries_UK_BGC/FeatureServer/0"
_COUNTRY = {"E": "England", "S": "Scotland", "W": "Wales", "N": "Northern Ireland"}


class OnsLadAdapter(Adapter):
    source_key = "ons_lad"

    def discover(self) -> list[Resource]:
        q = (f"{LAYER}/query?where=1%3D1&outFields=*&outSR=4326&f=geojson&geometryPrecision=5&resultRecordCount=2000")
        return [Resource(url=q, label="lad_dec_2025_bgc", suffix=".geojson",
                         licence_text="Open Government Licence v3.0; Source: ONS; Contains OS data © Crown copyright and database right")]

    def parse(self, path: Path, resource: Resource) -> Iterator[tuple[int, str | None, dict[str, Any]]]:
        doc = json.loads(path.read_text(encoding="utf-8"))
        for i, f in enumerate(doc.get("features", []), start=1):
            props = dict(f.get("properties") or {})
            props["_geometry"] = f.get("geometry")
            code = next((props[k] for k in props if k.upper().endswith("CD") and k.upper().startswith("LAD")), None)
            yield i, clean_text(code), props

    def normalise(self, payload: dict[str, Any], row_number: int, resource: Resource) -> NormRecord | Reject:
        code = next((payload[k] for k in payload if k.upper().endswith("CD") and k.upper().startswith("LAD")), None)
        name = next((payload[k] for k in payload if k.upper().endswith("NM") and k.upper().startswith("LAD")), None)
        geom = payload.get("_geometry")
        if not (code and name and geom):
            return Reject("missing code/name/geometry")
        g = make_valid(shape(geom))
        rec = NormRecord(record_key=str(code), name=str(name), name_norm=norm_name(str(name)), entity_kind="admin_area")
        rec.geom_wkt = g.wkt
        rec.geom_kind = "lad"
        rec.country = _COUNTRY.get(str(code)[:1])
        rec.ids["lad"] = str(code)
        rec.technology_code = None
        rec.status_code = None
        return rec
