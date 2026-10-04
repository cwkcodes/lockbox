"""Distribution Network Operator Embedded Capacity Registers (Opendatasoft exports + NGED CKAN)."""
from __future__ import annotations

import csv
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Iterator

from .. import config, crs
from ..http import SourceRestricted, SourceUnavailable, get_text
from ..model import NormRecord, Reject
from ..taxonomy import ECR_EXCLUDED_SOURCES, ECR_SOURCE_HINT, ECR_STATUS, ECR_TECH, hybrid_code
from ..textnorm import norm_name
from ..units import clean_text, parse_date, parse_number
from .base import Adapter, Resource

GB_COUNTRIES = {"england", "scotland", "wales", "united kingdom"}
GENERIC_TECH = {
    "engine (combustion / reciprocating)", "steam turbine (thermal power plant)", "gas turbine (ocgt)",
    "steam-gas turbine (ccgt)", "other", "steam turbine", "engine",
}


def _k(h: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", h.lower()).strip("_")


def slot_technology(source_raw: str | None, tech_raw: str | None) -> tuple[str | None, str | None]:
    """(technology_code, excluded_reason). Never guesses from capacity."""
    t = (tech_raw or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    s = re.sub(r"\s+", " ", (source_raw or "").strip().lower())
    if s in ECR_EXCLUDED_SOURCES or s.startswith("fossil"):
        return None, f"excluded:{s}"
    if s == "nuclear":
        return None, "excluded:nuclear"
    if t in ECR_TECH:
        return ECR_TECH[t], None
    if s in ECR_SOURCE_HINT:
        return ECR_SOURCE_HINT[s], None
    if s.startswith("biofuel"):
        if "landfill" in s:
            return "landfill_gas", None
        if "sewage" in s:
            return "sewage_gas", None
        if "anaerobic" in s or "biogas" in s:
            return "anaerobic_digestion", None
        return "biomass", None
    if s == "wind":
        return "wind_onshore", None
    if s == "solar":
        return "solar_pv", None
    if s.startswith("water") or s.startswith("hydro"):
        return "hydro", None
    if s.startswith("stored energy"):
        return "bess" if "batter" in t else "other_storage", None
    if t in GENERIC_TECH or not t:
        return "unknown", None
    return "unknown", None


class EcrAdapter(Adapter):
    """Generic ECR parser. `variant` fixes dataset id/host/unit conventions."""

    def __init__(self, source_key: str, *, dno: str, dno_label: str, host: str, dataset_id: str, band: str,
                 landing: str, fetch_mode: str = "ods") -> None:
        self.source_key = source_key
        self.dno, self.dno_label, self.host, self.dataset_id, self.band = dno, dno_label, host, dataset_id, band
        self.landing = landing
        self.fetch_mode = fetch_mode
        self._licence: tuple[str | None, str | None] = (None, None)
        self._pub: date | None = None

    # ---- discovery ------------------------------------------------------
    def discover(self) -> list[Resource]:
        if self.fetch_mode == "ckan":
            return self._discover_ckan()
        key = config.ods_api_key(self.dno)
        headers = {"Authorization": f"Apikey {key}"} if key else None
        base = f"https://{self.host}/api/explore/v2.1/catalog/datasets/{self.dataset_id}"
        body, _ = get_text(base, headers=headers)
        meta = json.loads(body).get("metas", {}).get("default", {})
        lic, lic_url = meta.get("license"), meta.get("license_url")
        self._licence = (lic, lic_url)
        mod = (meta.get("data_processed") or meta.get("modified") or "")[:10]
        self._pub = date.fromisoformat(mod) if mod else None
        return [Resource(url=f"{base}/exports/csv?delimiter=%2C&lang=en", label=self.dataset_id, suffix=".csv",
                         publication_date=self._pub, headers=headers,
                         licence_text=f"{lic} ({lic_url})" if lic else None,
                         meta={"records_count": meta.get("records_count")})]

    def _discover_ckan(self) -> list[Resource]:
        body, _ = get_text(f"https://{self.host}/api/3/action/package_show?id={self.dataset_id}")
        pkg = json.loads(body).get("result") or {}
        csvs = [r for r in pkg.get("resources", []) if str(r.get("url", "")).lower().endswith(".csv")]
        if not csvs:
            raise SourceUnavailable(f"{self.dataset_id}: no CSV resource listed")
        # newest by name/url (monthly files are named e.g. nged_ecr_aug_2026.csv); CKAN lists newest first
        res = csvs[0]
        mod = (pkg.get("metadata_modified") or "")[:10]
        self._licence = (pkg.get("license_title") or None, pkg.get("license_url") or None)
        return [Resource(url=res["url"], label=res.get("name", ""), suffix=".csv",
                         publication_date=date.fromisoformat(mod) if mod else None,
                         licence_text=self._licence[0] or "Licence not stated in CKAN metadata")]

    def registry_update(self, resource: Resource) -> dict[str, Any]:
        out: dict[str, Any] = {}
        lic, url = self._licence
        if lic:  # only overwrite the registry when the publisher's own metadata stated a licence this run
            out["licence_name"] = lic
            if url:
                out["licence_url"] = url
        return out

    # ---- parsing --------------------------------------------------------
    def parse(self, path: Path, resource: Resource) -> Iterator[tuple[int, str | None, dict[str, Any]]]:
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp1252")
        reader = csv.DictReader(text.splitlines(), delimiter=",")
        for i, row in enumerate(reader, start=2):
            if not any((v or "").strip() for v in row.values()):
                continue
            key = clean_text(row.get("ecrid") or row.get("unique_id") or row.get("site_id") or row.get("reference"))
            yield i, key, dict(row)

    # ---- structural validation + deterministic realignment (SPEN) ---------
    def _row(self, payload: dict[str, Any]) -> tuple[dict[str, str], str | None, bool]:
        """Return (keyed row, rejection reason, repaired?)."""
        row = {_k(k): (v or "") for k, v in payload.items()}
        country = (clean_text(row.get("country")) or "").lower()
        status = (clean_text(row.get("connection_status")) or "").lower()
        status_ok = status in ECR_STATUS
        if country in GB_COUNTRIES | {"northern ireland"} and status_ok:
            return row, None, False
        # Known SPEN defect: a postcode district sits in `country` and every later value is one column to the right.
        cols = list(payload.keys())
        if "country" in row and "x_eastings_1_km" in row:
            x_val = (clean_text(row.get("x_eastings_1_km")) or "").lower()
            tail_is_date = parse_date(row.get("unique_id")) is not None
            if country not in GB_COUNTRIES and x_val in GB_COUNTRIES and tail_is_date:
                i = cols.index("country")
                vals = [payload[c] or "" for c in cols]
                shifted = vals[:i] + vals[i + 1:] + [""]
                fixed = {_k(c): v for c, v in zip(cols, shifted)}
                fstatus = (clean_text(fixed.get("connection_status")) or "").lower()
                fcountry = (clean_text(fixed.get("country")) or "").lower()
                if fcountry in GB_COUNTRIES and fstatus in ECR_STATUS:
                    fixed["_postcode_district_from_shift"] = vals[i]
                    return fixed, None, True
        return row, f"structurally invalid row (country='{row.get('country')}', connection_status='{row.get('connection_status')}')", False

    def validate_structure(self, payload: dict[str, Any]) -> str | None:
        _, reason, _ = self._row(payload)
        return reason

    # ---- normalisation --------------------------------------------------
    def normalise(self, payload: dict[str, Any], row_number: int, resource: Resource) -> NormRecord | Reject:
        row, reason, repaired = self._row(payload)
        if reason:
            return Reject(reason)
        g = lambda k: clean_text(row.get(k))  # noqa: E731

        def first(*pats: str) -> str | None:
            for k in row:
                if any(re.fullmatch(p, k) for p in pats):
                    v = clean_text(row[k])
                    if v is not None:
                        return v
            return None

        ref = g("ecrid") or g("unique_id") or g("site_id") or g("reference")
        key = f"{self.source_key}:{ref}" if ref and not (repaired and not g("ecrid")) else f"{self.source_key}:row{row_number}"
        if repaired and g("reference"):
            key = f"{self.source_key}:ref{g('reference')}:row{row_number}"
        rec = NormRecord(record_key=key, record_url=self.landing)
        rec.dno = self.dno_label
        rec.ids["ecr"] = key
        if g("ecrid"):
            rec.ids["ecr_id"] = g("ecrid")  # type: ignore[assignment]
        if repaired:
            rec.qa_notes.append("source row was column-shifted (+1 from 'country'); realigned deterministically, original in raw layer")
            rec.attrs["repaired_column_shift"] = True
            rec.attrs["postcode_district"] = clean_text(row.get("_postcode_district_from_shift"))

        # --- energy-source slots -------------------------------------------------
        comps = []
        for n in "123":
            src, tech = g(f"energy_source_{n}"), first(rf"energy_conversion_technology_{n}")
            cap_key = next((k for k in row if re.fullmatch(rf"energy_source_.*{n}_(?:registered|reg)_capacity_(mw|kw)", k)), None)
            if not (src or tech):
                continue
            unit = "kw" if cap_key and cap_key.endswith("_kw") else "mw"
            raw_cap = row.get(cap_key, "") if cap_key else ""
            cap = parse_number(raw_cap)
            cap_mw = None if cap is None else cap * (1e-3 if unit == "kw" else 1.0)
            st_key = next((k for k in row if re.fullmatch(rf"storage_capacity_{n}_(mwh|kwh)", k)), None)
            st_unit = "kwh" if st_key and st_key.endswith("kwh") else "mwh"
            st = parse_number(row.get(st_key, "")) if st_key else None
            dur = parse_number(row.get(f"storage_duration_{n}_hours", ""))
            code, excl = slot_technology(src, tech)
            comps.append({"slot": int(n), "energy_source": src, "technology_raw": tech, "technology_code": code,
                          "excluded": excl, "mw": cap_mw, "raw_capacity": clean_text(raw_cap), "raw_unit": unit,
                          "storage_mwh": None if st is None else st * (1e-3 if st_unit == "kwh" else 1.0),
                          "duration_h": dur})
        rec.attrs["components"] = comps
        if not comps:
            return Reject("no energy source/technology slot populated")
        rec.technologies_raw = [f"{c['energy_source'] or ''} / {c['technology_raw'] or ''}".strip(" /") for c in comps]
        rec.technology_raw = "; ".join(rec.technologies_raw)
        excl = [c["excluded"] for c in comps if c["excluded"]]
        codes = [c["technology_code"] for c in comps if c["technology_code"] and not c["excluded"]]
        if excl:
            rec.excluded_reason = excl[0] if not codes else "mixed_with_non_renewable: " + ",".join(sorted(set(excl)))
        known = [c for c in codes if c != "unknown"]
        use = known or codes
        if use:
            rec.technology_code = use[0] if len(set(use)) == 1 else hybrid_code(set(use))
        rec.prov("technology", "energy_source_1 / energy_conversion_technology_1", rec.technology_raw)
        rec.chp_enabled = any((clean_text(row.get(k)) or "").lower() in ("yes", "y") for k in row if k.startswith("chp_cogeneration"))

        # --- status & capacities ----------------------------------------------------
        status_raw = g("connection_status")
        rec.connection_status = status_raw
        rec.status_raw = status_raw
        rec.status_code = ECR_STATUS.get((status_raw or "").lower(), "unknown")
        rec.prov("status", "connection_status", status_raw)

        def capk(prefix_alt: tuple[str, ...], unit_suffix: str) -> float | None:
            for k in row:
                if any(k.startswith(p) for p in prefix_alt) and re.search(rf"(^|_){unit_suffix}$", k) and "mva" not in k and "kva" not in k:
                    v = parse_number(row[k])
                    if v is not None:
                        return v * (1e-3 if unit_suffix == "kw" else 1.0)
            return None

        unit_sfx = "kw" if any(re.search(r"_kw$", k) for k in row) else "mw"
        connected_cap = capk(("already_connected_registered_capacity",), unit_sfx)
        accepted_cap = capk(("accepted_to_connect_registered_capacity",), unit_sfx)
        max_export = capk(("maximum_export_capacity", "connected_maximum_export_capacity", "already_connected_maximum_export_capacity"), unit_sfx)
        max_import = capk(("maximum_import_capacity", "connected_maximum_import_capacity", "already_connected_maximum_import_capacity"), unit_sfx)
        comp_total = sum(c["mw"] for c in comps if c["mw"] is not None) if any(c["mw"] is not None for c in comps) else None
        rec.capacity_mw = connected_cap if rec.status_code == "operational" and connected_cap is not None else (
            accepted_cap if rec.status_code != "operational" and accepted_cap is not None else comp_total)
        rec.capacity_basis = "ECR registered capacity (MW)"
        rec.export_capacity_mw = max_export
        rec.import_capacity_mw = max_import
        rec.prov("capacity_mw", "already_connected/accepted_to_connect_registered_capacity", rec.capacity_mw, "MW")
        bess = [c for c in comps if c["technology_code"] == "bess"]
        mwh = [c["storage_mwh"] for c in bess if c["storage_mwh"] is not None]
        rec.storage_mwh = sum(mwh) if mwh else None
        durs = [c["duration_h"] for c in bess if c["duration_h"] is not None]
        rec.storage_duration_h = durs[0] if len(durs) == 1 else None

        # --- dates -----------------------------------------------------------------
        rec.connection_date = parse_date(g("date_connected"))
        rec.attrs["date_accepted"] = (parse_date(g("date_accepted")).isoformat() if parse_date(g("date_accepted")) else None)
        rec.expected_operational_date = parse_date(g("target_energisation_date"))
        rec.record_updated = parse_date(g("last_updated"))
        rec.operational_date = rec.connection_date if rec.status_code == "operational" else None

        # --- network ---------------------------------------------------------------
        rec.connection_site = first(r"primary")
        rec.attrs.update(grid_supply_point=g("grid_supply_point"), bulk_supply_point=g("bulk_supply_point"),
                         primary_substation=g("primary"), licence_area=g("licence_area"),
                         flexible_connection=first(r"flexible_connection.*"),
                         in_connection_queue=first(r"in_a_connection_queue.*"))
        v = parse_number(first(r"point_of_connection_poc_voltage_kv", r"point_of_connection_poc_voltage_kv_?"))
        rec.connection_voltage_kv = v if v and v > 0 else None
        rec.prov("connection_voltage_kv", "point_of_connection_poc_voltage_kv", rec.connection_voltage_kv, "kV")

        # --- location & privacy ----------------------------------------------------
        rec.country = (g("country") or "").title() or None
        if (rec.country or "").lower() == "united kingdom":
            rec.country = None  # not a usable country (NGED publishes this for every row)
        rec.county = g("county")
        rec.attrs["town_city"] = first(r"town_city")
        rec.attrs["source_local_authority"] = g("local_authority")
        rec.local_authority = g("local_authority")
        small = (self.band in ("lt1mw", "50kw_1mw")) or (rec.capacity_mw is not None and rec.capacity_mw < 1.0)
        rec.privacy_class = "sub_1mw_masked" if small else "public"
        # Name / address: kept in the internal layer for matching, never for masked rows in the public layer.
        cust, site = g("customer_name"), g("customer_site")
        rec.attrs["customer_name"] = cust
        rec.attrs["customer_site"] = site
        rec.attrs["postcode"] = g("postcode")
        label = site or cust
        rec.name = label or f"{self.dno_label} ECR record {ref or row_number}"
        rec.name_norm = norm_name(rec.name)
        if not small:
            rec.postcode_public = g("postcode")
        rec.owner_raw = None

        e = parse_number(first(r"location.*eastings.*", r"x_eastings_1_km"))
        n = parse_number(first(r"location.*northings.*", r"y_northings_1_km"))
        lon_v, lat_v = parse_number(g("lon")), parse_number(g("lat"))
        gp = g("geopoint")
        if gp and lat_v is None:
            try:
                lat_v, lon_v = (float(x) for x in gp.split(","))
            except ValueError:
                pass
        grid_1km = any(k.startswith("x_eastings_1_km") for k in row)
        placed = False
        if e is not None and n is not None and crs.bng_numeric_ok(e, n):
            la, lo = crs.bng_to_wgs84(e, n)
            if crs.lat_lon_plausible_uk(la, lo):
                if grid_1km:
                    rec.coord_accuracy, rec.coord_note = "grid_1km", "published at 1 km resolution by the DNO"
                elif small:
                    e, n = crs.snap_to_grid(e, n, 1000)
                    la, lo = crs.bng_to_wgs84(e, n)
                    rec.coord_accuracy, rec.coord_note = "grid_1km", "privacy-masked: rounded to the centre of a 1 km grid square (sub-1 MW ECR record)"
                else:
                    rec.coord_accuracy, rec.coord_note = "site_reference", "DNO-published site coordinates ('where data is held')"
                rec.bng_e, rec.bng_n, rec.lat, rec.lon = e, n, la, lo
                placed = True
        if not placed and lat_v is not None and lon_v is not None and crs.lat_lon_plausible_uk(lat_v, lon_v):
            if small:
                e2, n2 = crs.wgs84_to_bng(lat_v, lon_v)
                e2, n2 = crs.snap_to_grid(e2, n2, 1000)
                la, lo = crs.bng_to_wgs84(e2, n2)
                rec.bng_e, rec.bng_n, rec.lat, rec.lon = e2, n2, la, lo
                rec.coord_accuracy, rec.coord_note = "grid_1km", "privacy-masked: rounded to the centre of a 1 km grid square (sub-1 MW ECR record)"
            else:
                rec.lat, rec.lon = lat_v, lon_v
                rec.bng_e, rec.bng_n = crs.wgs84_to_bng(lat_v, lon_v)
                rec.coord_accuracy, rec.coord_note = "site_reference", "DNO-published latitude/longitude (BNG eastings/northings missing or invalid)"
            placed = True
        if not placed:
            raw_e = first(r"location.*eastings.*", r"x_eastings_1_km")
            if raw_e is not None and e is not None and not crs.bng_numeric_ok(e, n):
                rec.qa_notes.append(f"easting/northing {e},{n} not plausible BNG metres – left unplaced")
            else:
                rec.qa_notes.append("no usable coordinates in source (redacted or not provided)")
        gb_country = (rec.country or "").lower()
        if gb_country == "northern ireland":
            rec.in_scope_gb = False
            rec.scope_note = "Northern Ireland – outside Great Britain scope"
        return rec
