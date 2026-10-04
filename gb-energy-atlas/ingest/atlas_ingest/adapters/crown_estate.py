"""The Crown Estate – Wind Site Agreements (England, Wales & NI): lease polygons via the ArcGIS FeatureServer."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from shapely.geometry import shape
from shapely.validation import make_valid

from .. import crs
from ..http import get_text
from ..model import NormRecord, Reject
from ..taxonomy import TCE_STATUS
from ..textnorm import norm_name
from ..units import clean_text, parse_number
from .base import Adapter, Resource

LAYER = "https://services2.arcgis.com/PZklK9Q45mfMFuZs/arcgis/rest/services/WindSite_EngWalNI_TheCrownEstate/FeatureServer/0"
ITEM = "https://opendata-thecrownestate.opendata.arcgis.com/datasets/22a1be6fb0c5416e9369f97743f387b1"
LICENCE = "The Crown Estate Open Data Licence (GIS) v1.1 – attribution: 'Contains data provided by The Crown Estate that is protected by copyright and database rights.'"


class CrownEstateAdapter(Adapter):
    source_key = "crown_estate_wind_sites"

    def discover(self) -> list[Resource]:
        q = f"{LAYER}/query?where=1%3D1&outFields=*&outSR=4326&f=geojson&resultRecordCount=2000"
        pub = None
        try:  # layer metadata carries the last edit time of the data (epoch ms)
            body, _ = get_text(f"{LAYER}?f=json")
            ms = (json.loads(body).get("editingInfo") or {}).get("lastEditDate")
            if ms:
                pub = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()
        except Exception:  # metadata is a nicety; the data fetch below is what matters
            pub = None
        return [Resource(url=q, label="wind_site_agreements", suffix=".geojson", licence_text=LICENCE, publication_date=pub)]

    def parse(self, path: Path, resource: Resource) -> Iterator[tuple[int, str | None, dict[str, Any]]]:
        doc = json.loads(path.read_text(encoding="utf-8"))
        for i, f in enumerate(doc.get("features", []), start=1):
            props = dict(f.get("properties") or {})
            props["_geometry"] = f.get("geometry")
            yield i, f"{props.get('OBJECTID')}:{props.get('Name_Prop')}", props

    def normalise(self, payload: dict[str, Any], row_number: int, resource: Resource) -> NormRecord | Reject:
        name = clean_text(payload.get("Name_Prop"))
        geom = payload.get("_geometry")
        if not name or not geom:
            return Reject("missing name or geometry")
        g = make_valid(shape(geom))
        if g.is_empty:
            return Reject("empty geometry")
        rec = NormRecord(record_key=f"{payload.get('OBJECTID')}:{name}", name=name, name_norm=norm_name(name), record_url=ITEM)
        rec.entity_kind = "lease"
        rec.technology_raw = "Offshore wind (Crown Estate wind site agreement)"
        rec.technology_code = "wind_offshore"
        rec.status_raw = clean_text(payload.get("Inf_Status"))
        rec.status_code = TCE_STATUS.get((rec.status_raw or "").lower(), "unknown")
        rec.prov("status", "Inf_Status", rec.status_raw)
        rec.geom_wkt = g.wkt
        rec.geom_kind = "lease_area"
        c = g.representative_point() if g.geom_type != "Point" else g
        rec.lat, rec.lon = c.y, c.x
        rec.bng_e, rec.bng_n = crs.wgs84_to_bng(c.y, c.x)
        rec.coord_accuracy = "approximate"
        rec.coord_note = "representative point inside the Crown Estate lease-agreement polygon (not a turbine position)"
        rec.site_area_ha = (parse_number(payload.get("km2")) or 0) * 100 or None
        rec.developer_raw = None
        rec.owner_raw = clean_text(payload.get("Name_Ten"))  # tenant named on the agreement
        rec.attrs.update(wind_round=clean_text(payload.get("Wind_Round")), lease_status=clean_text(payload.get("Lease_Stat")),
                         tenant=clean_text(payload.get("Name_Ten")), km2=payload.get("km2"))
        rec.attrs["is_offshore"] = True
        return rec
