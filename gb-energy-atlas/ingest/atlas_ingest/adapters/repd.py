"""DESNZ Renewable Energy Planning Database (REPD) adapter."""
from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path
from typing import Any, Iterator

from .. import crs
from ..http import ManualReviewRequired, SourceUnavailable, get_text
from ..model import NormRecord, Reject
from ..taxonomy import map_repd_status, map_repd_technology
from ..textnorm import norm_name
from ..units import area_to_ha, clean_text, parse_date, parse_number
from .base import Adapter, Resource

LANDING = "https://www.gov.uk/government/publications/renewable-energy-planning-database-quarterly-extract"
CONTENT_API = "https://www.gov.uk/api/content/government/publications/renewable-energy-planning-database-quarterly-extract"
GB_COUNTRIES = {"england", "scotland", "wales"}

# Milestone columns -> (history event type, label)
MILESTONES = [
    ("Planning Application Submitted", "planning_submitted", "Planning application submitted"),
    ("Planning Application Withdrawn", "planning_withdrawn", "Planning application withdrawn"),
    ("Planning Permission Refused", "planning_refused", "Planning permission refused"),
    ("Appeal Lodged", "appeal_lodged", "Appeal lodged"),
    ("Appeal Withdrawn", "appeal_withdrawn", "Appeal withdrawn"),
    ("Appeal Refused", "appeal_refused", "Appeal refused"),
    ("Appeal Granted", "appeal_granted", "Appeal granted"),
    ("Planning Permission Granted", "consent_granted", "Planning permission granted"),
    ("Secretary of State - Intervened", "sos_intervened", "Secretary of State intervened"),
    ("Secretary of State - Refusal", "sos_refusal", "Secretary of State refused"),
    ("Secretary of State - Granted", "sos_granted", "Secretary of State granted"),
    ("Planning Permission Expired", "consent_expired", "Planning permission expired"),
    ("Under Construction", "construction_started", "Construction started"),
    ("Operational", "operational", "Became operational"),
]
_GRANT_COLS = ("Planning Permission Granted", "Appeal Granted", "Secretary of State - Granted")
# The source file stores 'Round 1/2/3' as Excel dates (01/01/1900 ...). Mapping is documented in METHODOLOGY.
_ROUND_ARTEFACT = {"01/01/1900": "Round 1", "02/01/1900": "Round 2", "03/01/1900": "Round 3"}
_STORAGE_TYPE = {
    "stand-alone storage": "stand_alone",
    "co-located with re": "co_located_re",
    "co-located with fossil fuel plant": "co_located_fossil",
}


def _hkey(h: str) -> str:
    return re.sub(r"\s+", " ", h).strip().lower()


class RepdAdapter(Adapter):
    source_key = "repd"

    def __init__(self) -> None:
        self._hdr: dict[str, str] = {}

    # ---- discovery -------------------------------------------------------
    def discover(self) -> list[Resource]:
        """Resolve the current CSV from the GOV.UK content API, following GOV.UK 'redirect' documents
        (the publication was renamed monthly-extract -> quarterly-extract)."""
        import json
        api = CONTENT_API
        try:
            for _ in range(4):
                body, _status = get_text(api)
                doc = json.loads(body)
                if doc.get("document_type") != "redirect":
                    break
                dest = (doc.get("redirects") or [{}])[0].get("destination")
                if not dest:
                    raise SourceUnavailable("GOV.UK redirect document without destination")
                api = "https://www.gov.uk/api/content" + dest
            atts = doc.get("details", {}).get("attachments", [])
            csvs = [a for a in atts if str(a.get("url", "")).lower().endswith(".csv")]
            if not csvs:
                raise SourceUnavailable("GOV.UK content API lists no CSV attachment for REPD")
            url = csvs[0]["url"]
            pub = (doc.get("public_updated_at") or "")[:10]
            publication = date.fromisoformat(pub) if pub else None
        except ManualReviewRequired:
            html, _ = get_text(LANDING)
            m = re.search(r'https://assets\.publishing\.service\.gov\.uk/[^"\']+REPD[^"\']*\.csv', html)
            if not m:
                raise SourceUnavailable("could not locate REPD CSV link on the GOV.UK landing page")
            url, publication = m.group(0), None
        label = re.search(r"(Q\d_\d{4})", url)
        return [Resource(url=url, label=label.group(1) if label else "", publication_date=publication, suffix=".csv")]

    # ---- parsing ---------------------------------------------------------
    def parse(self, path: Path, resource: Resource) -> Iterator[tuple[int, str | None, dict[str, Any]]]:
        # The published file is Windows-1252, not UTF-8.
        with open(path, encoding="cp1252", newline="") as f:
            reader = csv.DictReader(f)
            self._hdr = {_hkey(h): h for h in (reader.fieldnames or [])}
            for i, row in enumerate(reader, start=2):  # row 1 is the header
                yield i, clean_text(row.get(self._hdr.get("ref id", ""))), dict(row)

    def _g(self, payload: dict[str, Any], name: str) -> str | None:
        h = self._hdr.get(_hkey(name))
        return clean_text(payload.get(h)) if h else None

    def _raw(self, payload: dict[str, Any], name: str) -> str | None:
        h = self._hdr.get(_hkey(name))
        return payload.get(h) if h else None

    # ---- normalisation ---------------------------------------------------
    def normalise(self, payload: dict[str, Any], row_number: int, resource: Resource) -> NormRecord | Reject:
        g = lambda n: self._g(payload, n)  # noqa: E731
        ref = g("Ref ID")
        if not ref:
            return Reject("missing REPD Ref ID")
        name = g("Site Name") or f"REPD {ref} (unnamed)"
        rec = NormRecord(record_key=ref, name=name, name_norm=norm_name(name), record_url=LANDING)
        rec.ids["repd"] = ref
        if g("Old Ref ID"):
            rec.ids["repd_old"] = g("Old Ref ID")  # type: ignore[assignment]

        # technology + status (original wording retained)
        rec.technology_raw = g("Technology Type")
        rec.technology_code = map_repd_technology(rec.technology_raw)
        rec.prov("technology", "Technology Type", rec.technology_raw)
        short, long_ = g("Development Status (short)"), g("Development Status")
        rec.status_raw = short or long_
        rec.status_code = map_repd_status(short or long_)
        rec.attrs["development_status_long"] = long_
        rec.prov("status", "Development Status (short)", short)

        # capacity & wind/solar descriptors – reported values, not verified as-built
        cap = parse_number(g("Installed Capacity (MWelec)"))
        if cap is not None and cap < 0:
            cap = None
        rec.capacity_mw = cap
        rec.capacity_basis = "REPD installed capacity (MWelec)"
        rec.prov("capacity_mw", "Installed Capacity (MWelec)", g("Installed Capacity (MWelec)"), "MW")
        n_t = parse_number(g("No. of Turbines"))
        rec.turbine_count = int(n_t) if n_t is not None and n_t >= 0 else None
        rec.prov("turbine_count", "No. of Turbines", g("No. of Turbines"))
        rec.turbine_rated_mw = parse_number(g("Turbine Capacity (MW)"))
        rec.prov("turbine_rated_mw", "Turbine Capacity (MW)", g("Turbine Capacity (MW)"), "MW")
        rec.turbine_height_m = parse_number(g("Height of Turbines (m)"))
        rec.prov("turbine_height_m", "Height of Turbines (m)", g("Height of Turbines (m)"), "m")
        sqm = g("Solar Site Area (sqm)")
        rec.site_area_ha = area_to_ha(sqm, "m2") if sqm else None
        rec.prov("site_area_ha", "Solar Site Area (sqm)", sqm, "m2")
        rec.mounting_type = g("Mounting Type for Solar")
        rec.chp_enabled = {"yes": True, "no": False}.get((g("CHP Enabled") or "").lower())
        st = g("Storage Type")
        rec.storage_type = _STORAGE_TYPE.get((st or "").lower(), st)
        rec.attrs["storage_colocation_ref"] = g("Storage Co-location REPD Ref ID")

        # support schemes as reported by REPD
        rec.cfd_round = g("CfD Allocation Round")
        rec.cfd_capacity_mw = parse_number(g("CfD Capacity (MW)"))
        rec.ro_banding = parse_number(g("RO Banding (ROC/MWh)"))
        rec.fit_tariff = parse_number(g("FiT Tariff (p/kWh)"))

        # organisations (REPD 'Operator (or Applicant)' is ambiguous by design)
        rec.operator_raw = g("Operator (or Applicant)")
        rec.attrs["operator_field_semantics"] = "REPD 'Operator (or Applicant)': operator once operational, applicant otherwise"

        # location
        rec.country = g("Country")
        rec.region = g("Region")
        rec.county = g("County")
        rec.planning_authority = g("Planning Authority")
        rec.attrs["address"] = g("Address")
        pc = g("Post Code")
        # Postcodes are only surfaced for schemes of 1 MW or more (small schemes can be single farms/households).
        rec.attrs["postcode"] = pc
        rec.postcode_public = pc if (cap is None or cap >= 1.0) else None
        country_l = (rec.country or "").lower()
        if country_l and country_l not in GB_COUNTRIES:
            rec.in_scope_gb = False
            rec.scope_note = f"{rec.country} – outside Great Britain scope; retained for future extension"
        elif not country_l:
            rec.qa_notes.append("country not stated in source")

        e, n = parse_number(g("X-coordinate")), parse_number(g("Y-coordinate"))
        if e is not None and n is not None:
            if crs.bng_numeric_ok(e, n):
                lat, lon = crs.bng_to_wgs84(e, n)
                if crs.lat_lon_plausible_uk(lat, lon):
                    rec.bng_e, rec.bng_n, rec.lat, rec.lon = e, n, lat, lon
                    rec.coord_accuracy = "site_reference"
                    rec.coord_note = "REPD X/Y: grid reference for the site; not an individual turbine/array position"
                    if not crs.bng_in_formal_extent(e, n):
                        rec.coord_note += "; lies beyond the formal BNG extent (far-offshore site)"
                    rec.prov("bng_e", "X-coordinate", g("X-coordinate"), "m")
                    rec.prov("bng_n", "Y-coordinate", g("Y-coordinate"), "m")
                else:
                    rec.qa_notes.append(f"coordinates {e:.0f},{n:.0f} transform outside UK waters ({lat:.2f},{lon:.2f}) – not used")
            else:
                rec.qa_notes.append(f"coordinates {e},{n} are not plausible BNG metres – not used")
        # (no coordinates → left unplaced; QA flag raised later)

        # references
        rec.planning_ref = g("Planning Application Reference")
        rec.appeal_ref = g("Appeal Reference")
        rec.sos_ref = g("Secretary of State Reference")
        rec.attrs["sos_intervention_type"] = g("Type of Secretary of State Intervention")
        rec.attrs["judicial_review"] = g("Judicial Review")
        rec.attrs["heat_network_ref"] = g("Heat Network Ref")
        rec.attrs["share_community_scheme"] = g("Share Community Scheme")
        rec.attrs["reapply_new_ref"] = g("Are they re-applying (New REPD Ref)")
        rec.attrs["reapply_old_ref"] = g("Are they re-applying (Old REPD Ref)")

        # offshore wind round: Excel-date artefact in the source file
        rnd = g("Offshore Wind Round")
        if rnd:
            mapped = _ROUND_ARTEFACT.get(rnd)
            rec.attrs["offshore_round"] = mapped or rnd
            if mapped:
                rec.attrs["offshore_round_note"] = f"source value '{rnd}' is an Excel date artefact for {mapped}"

        # dates & milestones
        rec.record_updated = parse_date(g("Record Last Updated (dd/mm/yyyy)"))
        miles: list[dict[str, str]] = []
        parsed: dict[str, date] = {}
        for col, etype, label in MILESTONES:
            d = parse_date(g(col))
            if d:
                parsed[col] = d
                miles.append({"type": etype, "date": d.isoformat(), "label": label, "col": col})
        rec.attrs["milestones"] = miles
        rec.application_date = parsed.get("Planning Application Submitted")
        grants = [parsed[c] for c in _GRANT_COLS if c in parsed]
        rec.consent_date = max(grants) if grants else None
        rec.construction_date = parsed.get("Under Construction")
        rec.operational_date = parsed.get("Operational")
        rec.prov("operational_date", "Operational", g("Operational"))
        rec.prov("consent_date", "Planning Permission Granted", g("Planning Permission Granted"))

        # sanity notes (QA proper runs later)
        if rec.status_code == "operational" and not rec.operational_date:
            rec.qa_notes.append("status Operational but no operational date")
        if rec.technology_code == "unknown":
            rec.qa_notes.append(f"technology '{rec.technology_raw}' not mapped")
        return rec
