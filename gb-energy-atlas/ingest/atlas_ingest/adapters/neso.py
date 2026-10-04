"""NESO Transmission Entry Capacity (TEC) and Embedded registers (CKAN, twice-weekly CSV)."""
from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterator

from ..http import SourceUnavailable, get_text
from ..model import NormRecord, Reject
from ..taxonomy import NESO_PLANT, NESO_STATUS, hybrid_code
from ..textnorm import norm_name
from ..units import clean_text, parse_date, parse_number
from .base import Adapter, Resource

CKAN = "https://api.neso.energy/api/3/action/package_show?id="


class NesoRegisterAdapter(Adapter):
    def __init__(self, source_key: str, package_id: str, is_tec: bool) -> None:
        self.source_key = source_key
        self.package_id = package_id
        self.is_tec = is_tec
        self.landing = f"https://www.neso.energy/data-portal/{package_id}"
        self._licence: tuple[str | None, str | None] = (None, None)

    def discover(self) -> list[Resource]:
        body, _ = get_text(CKAN + self.package_id)
        pkg = json.loads(body).get("result") or {}
        csvs = [r for r in pkg.get("resources", []) if str(r.get("format", "")).upper() == "CSV"]
        if not csvs:
            raise SourceUnavailable(f"NESO package {self.package_id} lists no CSV resource")
        res = csvs[0]
        mod = (res.get("last_modified") or pkg.get("metadata_modified") or "")[:10]
        self._licence = (pkg.get("license_title"), pkg.get("license_url"))
        return [Resource(url=res["url"], label=res.get("name", ""), suffix=".csv",
                         publication_date=date.fromisoformat(mod) if mod else None,
                         licence_text=f"{pkg.get('license_title')} ({pkg.get('license_url')})")]

    def parse(self, path: Path, resource: Resource) -> Iterator[tuple[int, str | None, dict[str, Any]]]:
        with open(path, encoding="utf-8-sig", newline="") as f:
            for i, row in enumerate(csv.DictReader(f), start=2):
                yield i, clean_text(row.get("Project Number")), dict(row)

    def normalise(self, payload: dict[str, Any], row_number: int, resource: Resource) -> NormRecord | Reject:
        g = lambda k: clean_text(payload.get(k))  # noqa: E731
        num = g("Project Number")
        if not num:
            return Reject("missing Project Number")
        name = g("Project Name") or f"{num} (unnamed)"
        rec = NormRecord(record_key=num, name=name, name_norm=norm_name(name), record_url=self.landing)
        rec.ids["neso_project_number"] = num
        if g("Project ID"):
            rec.ids["neso_project_id"] = g("Project ID")  # type: ignore[assignment]
        rec.ids["tec" if self.is_tec else "neso_embedded"] = num

        plant = g("Plant Type") or ""
        tokens = [t.strip() for t in plant.split(";") if t.strip()]
        rec.technologies_raw = tokens
        rec.technology_raw = plant or None
        mapped = [NESO_PLANT.get(t.lower(), (None, "excluded:unmapped_plant_type")) for t in tokens]
        codes = [c for c, kind in mapped if c and not kind.startswith("excluded")]
        excl = [kind for c, kind in mapped if kind.startswith("excluded") and not kind.endswith(("demand", "reactive_compensation"))]
        if excl:
            rec.excluded_reason = "mixed_with_non_renewable_or_unclassified: " + ",".join(sorted(set(excl))) if codes else excl[0]
        elif not codes:
            rec.excluded_reason = "excluded:demand_or_reactive_only"
        if codes:
            rec.technology_code = codes[0] if len(set(codes)) == 1 else hybrid_code(set(codes))
        rec.prov("technology", "Plant Type", plant)

        status_raw = g("Project Status")
        rec.status_raw = status_raw
        rec.status_code = NESO_STATUS.get((status_raw or "").lower(), "unknown")
        rec.prov("status", "Project Status", status_raw)

        cap = parse_number(g("Cumulative Total Capacity (MW)"))
        rec.capacity_mw = cap
        rec.capacity_basis = "NESO cumulative total contracted capacity (MW); may include not-yet-connected capacity"
        rec.prov("capacity_mw", "Cumulative Total Capacity (MW)", g("Cumulative Total Capacity (MW)"), "MW")
        rec.attrs.update(
            mw_connected=parse_number(g("MW Connected")),
            mw_change=parse_number(g("MW Increase / Decrease")),
            mw_effective_from=(parse_date(g("MW Effective From")).isoformat() if parse_date(g("MW Effective From")) else None),
            stage=g("Stage"), agreement_type=g("Agreement Type"), customer_name=g("Customer Name"),
        )
        rec.host_to = g("HOST TO")
        rec.connection_site = g("Connection Site")
        rec.gate = g("Gate")
        rec.connection_status = status_raw
        eff = parse_date(g("MW Effective From"))
        if rec.status_code in ("operational",):
            rec.connection_date = None  # 'effective from' is a capacity-effective date, not a connection date
        else:
            rec.expected_operational_date = eff
        rec.owner_raw = None  # NESO 'Customer Name' is the connection-agreement counterparty (role: customer)
        rec.developer_raw = None
        # no coordinates and no country in these registers – nothing is inferred
        rec.qa_notes.append("no coordinates in source")
        return rec
