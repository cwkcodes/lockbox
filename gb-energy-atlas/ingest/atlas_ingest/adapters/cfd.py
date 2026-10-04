"""DESNZ Contracts for Difference allocation-round results (GOV.UK 'successful applicants' workbooks)."""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

import openpyxl

from .. import crs
from ..http import SourceUnavailable, get_text
from ..model import NormRecord, Reject
from ..taxonomy import CFD_TECH
from ..textnorm import norm_name
from ..units import clean_text, parse_date, parse_number
from .base import Adapter, Resource

PAGES = [
    "contracts-for-difference-cfd-allocation-round-5-results",
    "contracts-for-difference-cfd-allocation-round-6-results",
    "contracts-for-difference-cfd-allocation-round-7-results",
]
API = "https://www.gov.uk/api/content/government/publications/"
GB = {"england", "scotland", "wales"}


def _hk(h: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(h or "").lower()).strip()


def _round_label(title: str, url: str) -> str:
    t = title.lower()
    m = re.search(r"allocation round (\d+)(a?)", t)
    return f"AR{m.group(1)}{m.group(2)}" if m else re.sub(r"\W+", "_", url.rsplit("/", 1)[-1])[:30]


class CfdAdapter(Adapter):
    source_key = "cfd_results"

    def discover(self) -> list[Resource]:
        out: list[Resource] = []
        for page in PAGES:
            body, _ = get_text(API + page)
            doc = json.loads(body)
            pub = (doc.get("public_updated_at") or "")[:10]
            for a in doc.get("details", {}).get("attachments", []):
                url = str(a.get("url", ""))
                if url.lower().endswith(".xlsx"):
                    out.append(Resource(url=url, label=_round_label(a.get("title", ""), url), suffix=".xlsx",
                                        publication_date=date.fromisoformat(pub) if pub else None,
                                        meta={"page": f"https://www.gov.uk/government/publications/{page}", "title": a.get("title")}))
        if not out:
            raise SourceUnavailable("no CfD results workbooks found on GOV.UK")
        return out

    def parse(self, path: Path, resource: Resource) -> Iterator[tuple[int, str | None, dict[str, Any]]]:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        for ws in wb.worksheets:
            rows = list(ws.iter_rows(values_only=True))
            hdr_i = next((i for i, r in enumerate(rows) if r and any(_hk(c) == "project name" for c in r)), None)
            if hdr_i is None:
                continue
            title_text = " | ".join(str(c) for r in rows[:hdr_i] for c in r if c)
            hdr = [(_hk(c), c) for c in rows[hdr_i]]
            for j, r in enumerate(rows[hdr_i + 1:], start=hdr_i + 2):
                if not r or not any(r):
                    continue
                payload = {str(orig).strip(): (v.isoformat() if isinstance(v, (datetime, date)) else v)
                           for (k, orig), v in zip(hdr, r) if orig is not None}
                name = clean_text(payload.get("Project Name"))
                if not name:
                    continue
                payload["_sheet"] = ws.title
                payload["_title_text"] = title_text
                yield j, f"{resource.label}|{norm_name(name)}|{norm_name(str(payload.get('Name of CfD Unit (Phase 1)') or ''))}", payload

    def normalise(self, payload: dict[str, Any], row_number: int, resource: Resource) -> NormRecord | Reject:
        P = {_hk(k): v for k, v in payload.items()}

        def pick(*names: str) -> Any:
            for n in names:
                for k, v in P.items():
                    if k == n or k.startswith(n):
                        return v
            return None

        name = clean_text(P.get("project name"))
        if not name:
            return Reject("no project name")
        tech_raw = clean_text(pick("technology type"))
        size = parse_number(pick("size mw"))
        if size is None:
            return Reject("no size (MW)")
        rec = NormRecord(record_key=f"{resource.label}|{norm_name(name)}|{norm_name(str(P.get('name of cfd unit phase 1') or ''))}",
                         name=name, name_norm=norm_name(name), record_url=resource.meta.get("page") or resource.url)
        rec.technology_raw = tech_raw
        rec.technology_code = CFD_TECH.get((tech_raw or "").lower(), "unknown")
        rec.status_raw = f"CfD allocation round {resource.label} – successful applicant"
        rec.status_code = "cfd_awarded"
        rec.capacity_mw = size
        rec.cfd_capacity_mw = size
        rec.capacity_basis = "CfD contracted capacity (MW) from allocation round results"
        rec.cfd_round = resource.label
        rec.prov("cfd_capacity_mw", "Size (MW)", size, "MW")
        # strike price: AR6/AR7 sheets state 2012 prices in the title or headers; AR7 also gives 2024 prices
        p12 = parse_number(pick("strike price mwh 2012 prices", "strike price mwh 2012", "strike price mwh"))
        p24 = parse_number(pick("strike price mwh 2024 prices", "strike price mwh 2024"))
        rec.strike_price = p12
        rec.attrs["strike_price_2024"] = p24
        title = str(payload.get("_title_text") or "")
        rec.attrs["price_basis_note"] = ("2012 prices (stated in workbook)" if "2012" in title or any("2012" in k for k in P) else
                                         "price base not stated in this workbook; see GOV.UK results document")
        rec.prov("strike_price", "Strike Price (£/MWh)", p12, "£/MWh")
        rec.attrs.update(applicant=clean_text(pick("applicant")), cfd_unit=clean_text(pick("name of cfd unit")),
                         delivery_year=clean_text(pick("delivery year")), pot=clean_text(pick("pot")),
                         phases=clean_text(pick("no of phases")), region_raw=clean_text(pick("region", "country region", "county region")),
                         workbook_sheet=payload.get("_sheet"), source_row=row_number)
        rec.expected_operational_date = parse_date(pick("target commissioning date"))
        reg = (rec.attrs.get("region_raw") or "")
        for c in re.split(r"[,/]", reg):
            if c.strip().lower() in GB:
                rec.country = c.strip().title()
                break
        # location: lat/long text (3 d.p.) preferred, else OS grid reference (100 m)
        ll_txt = str(pick("northerly extreme", "notherly extreme", "project location northerly") or "")
        nums = re.findall(r"-?\d+\.\d+|-?\d+", ll_txt)
        gref = clean_text(pick("project location os reference", "project location"))
        lat = lon = None
        if len(nums) >= 2:
            lat, lon = float(nums[0]), float(nums[1])
            if "northerly extreme" in " ".join(P) or "notherly extreme" in " ".join(P):
                note = "AR7 'Northerly extreme' point of phase 1 (not a centroid) – position is indicative only"
            else:
                note = "CfD results workbook latitude/longitude (3 d.p.)"
        offshore = (rec.technology_code or "").startswith("wind_offshore")
        if (lat is None or not crs.lat_lon_plausible_uk(lat, lon or 0)) and gref:
            g = crs.gridref_to_bng(gref)
            if g and offshore:
                # Verified against the 4 Oct 2026 workbooks: every AR5/AR6 offshore 'Project Location' OS reference lies on land
                # (grid connection / landfall), so it is NOT a project position. Kept in attrs, not used as a location.
                e, n, res = g
                rec.attrs["onshore_reference_bng"] = [e + res / 2, n + res / 2]
                rec.coord_note = f"offshore project: OS reference {gref} is an onshore point (not the array position) – left unplaced"
                lat = lon = None
            elif g:
                e, n, res = g
                lat, lon = crs.bng_to_wgs84(e + res / 2, n + res / 2)
                rec.bng_e, rec.bng_n = e + res / 2, n + res / 2
                note = f"CfD results workbook OS grid reference {gref} ({res} m resolution), centre of square"
            else:
                lat = lon = None
        if lat is not None and lon is not None and crs.lat_lon_plausible_uk(lat, lon):
            rec.lat, rec.lon = lat, lon
            if rec.bng_e is None:
                rec.bng_e, rec.bng_n = crs.wgs84_to_bng(lat, lon)
            rec.coord_accuracy, rec.coord_note = "approximate", note
        rec.attrs["os_grid_reference"] = gref
        return rec
