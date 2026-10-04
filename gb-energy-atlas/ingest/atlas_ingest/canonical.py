"""Build the canonical layer (atlas.*) from the current normalised source records.

Idempotent and rebuildable: asset_ids are stable because each asset is anchored to the identifier that first created it
(atlas.asset_anchor). Nothing is deleted from raw/norm. Every value that reaches an asset row also exists as a
field_provenance observation pointing at the source record it came from; when several sources disagree all observations
are kept, one is marked preferred with a written reason, and the disagreement stays visible.
"""
from __future__ import annotations

import datetime as dt
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from psycopg.types.json import Jsonb
from rapidfuzz import fuzz, process

from . import matching as M
from .completeness import completeness, confidence
from .orgs import OrgIndex, split_orgs
from .textnorm import core_name, norm_name, norm_org

log = logging.getLogger("atlas.canonical")

TIER_RANK = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
NONSPECIFIC_STATUS = {"unknown", "cfd_awarded"}
ACCURACY_RANK = {"exact_published": 0, "digitised_from_drawing": 1, "site_reference": 2, "open_source_mapped": 3,
                 "postcode_centroid": 4, "grid_1km": 5, "approximate": 6, "none": 9}
# order in which non-REPD sources are processed (better evidence first so later records can link to them)
SOURCE_ORDER = ["crown_estate_wind_sites", "cfd_results", "neso_tec", "neso_embedded", "nged_ecr", "npg_ecr_1mw", "npg_ecr_lt1mw",
                "ukpn_ecr_1mw", "ukpn_ecr_lt1mw", "enwl_ecr_1mw", "enwl_ecr_lt1mw", "spen_ecr_1mw", "spen_ecr_50kw", "osm_overpass"]
TO_NAMES = {"NGET": "National Grid Electricity Transmission", "SHET": "SSEN Transmission", "SPT": "SP Transmission",
            "OFTO": "Offshore transmission owner (OFTO)"}
FAMILY_STORAGE = {"bess", "pumped_hydro", "ldes", "caes", "flow_battery", "other_storage"}
REPOWER_STATUS = {"planning_submitted": "repowering_proposed", "planning": "repowering_proposed",
                  "consented": "repowering_consented", "awaiting_construction": "repowering_consented",
                  "under_construction": "repowering_under_construction"}


# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class Draft:
    asset_id: str
    anchor: tuple[str, str]
    primary: dict
    links: list[tuple[dict, str, float | None, dict | None]] = field(default_factory=list)  # (rec, type, score, components)
    cand: M.Cand | None = None

    def recs(self) -> list[dict]:
        return [r for r, *_ in self.links]


class Pool:
    """Spatial grid + name index over asset drafts (grows as new drafts are created)."""

    CELL = 5000.0

    def __init__(self) -> None:
        self.drafts: list[Draft] = []
        self.grid: dict[tuple[int, int], list[int]] = defaultdict(list)
        self.names: list[str] = []
        self.name_idx: list[int] = []

    def add(self, d: Draft) -> None:
        i = len(self.drafts)
        self.drafts.append(d)
        c = d.cand
        assert c is not None
        if c.poly is not None:
            minx, miny, maxx, maxy = c.poly.bounds  # type: ignore[union-attr]
            for cx in range(int(minx // self.CELL) - 1, int(maxx // self.CELL) + 2):
                for cy in range(int(miny // self.CELL) - 1, int(maxy // self.CELL) + 2):
                    self.grid[(cx, cy)].append(i)
        elif c.e is not None and c.n is not None and c.accuracy != "none":
            self.grid[(int(c.e // self.CELL), int(c.n // self.CELL))].append(i)
        cn = core_name(c.name)
        if len(cn) >= 3:
            self.names.append(cn)
            self.name_idx.append(i)

    def near(self, e: float, n: float, radius: float) -> set[int]:
        r = int(radius // self.CELL) + 1
        cx, cy = int(e // self.CELL), int(n // self.CELL)
        out: set[int] = set()
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                out.update(self.grid.get((cx + dx, cy + dy), ()))
        return out

    def by_name(self, name: str | None, limit: int = 6) -> set[int]:
        cn = core_name(name)
        if len(cn) < 3 or not self.names:
            return set()
        hits = process.extract(cn, self.names, scorer=fuzz.token_sort_ratio, limit=limit, score_cutoff=72)
        return {self.name_idx[h[2]] for h in hits}


# ---------------------------------------------------------------------------------------------------------------------
def _year(rec: dict) -> int | None:
    for k in ("operational_date", "connection_date", "expected_operational_date"):
        if rec.get(k):
            return rec[k].year
    return None


def _components(rec: dict) -> list[dict]:
    return list((rec.get("attrs") or {}).get("components") or [])


def to_cand(rec: dict) -> M.Cand:
    comps = _components(rec)
    codes = [c["technology_code"] for c in comps if c.get("technology_code") and not c.get("excluded")] or [rec["technology_code"]]
    cap_by: dict[str, float] = {}
    for c in comps:
        if c.get("technology_code") and c.get("mw") is not None and not c.get("excluded"):
            for k in M.tech_keys([c["technology_code"]]):
                cap_by[k] = cap_by.get(k, 0.0) + c["mw"]
    attrs = rec.get("attrs") or {}
    orgs = tuple(x for x in (rec.get("operator_raw"), rec.get("developer_raw"), rec.get("owner_raw"), attrs.get("applicant"),
                             attrs.get("tenant"), None if rec.get("privacy_class") == "sub_1mw_masked" else attrs.get("customer_name")) if x)
    refs = frozenset(M.norm_ref(x) for x in (rec.get("planning_ref"),) if x and len(M.norm_ref(x)) >= 5)
    offshore = bool(attrs.get("is_offshore")) or (rec.get("region") or "").lower() == "offshore" or str(rec["technology_code"]).startswith("wind_offshore")
    masked = rec.get("privacy_class") == "sub_1mw_masked"
    name = None if (masked and rec["source_key"] != "repd") else rec.get("name")
    poly = None
    if rec.get("geom_wkt") and rec.get("geom_kind") == "lease_area":
        from shapely import wkt as _wkt
        from shapely.ops import transform as _transform
        from .crs import _TO_BNG
        poly = _transform(lambda x, y, z=None: _TO_BNG.transform(x, y), _wkt.loads(rec["geom_wkt"]))
    cand = M.Cand(key=f"{rec['source_key']}:{rec['record_key']}", name=name, techs=M.tech_keys(codes),
                  capacity_mw=rec.get("capacity_mw"), cap_by_tech=cap_by,
                  e=float(rec["bng_e"]) if rec.get("bng_e") is not None else None,
                  n=float(rec["bng_n"]) if rec.get("bng_n") is not None else None,
                  accuracy=rec.get("coord_accuracy") or "none", offshore=offshore, orgs=orgs, planning_refs=refs,
                  year=_year(rec), country=rec.get("country"), poly=poly)
    return cand


def observed_at(rec: dict) -> dt.date:
    return rec.get("record_updated") or rec.get("publication_date") or rec["retrieved_on"]


def choose(field_name: str, obs: list[dict]) -> tuple[dict | None, str]:
    """Pick the preferred observation and say why. Order of consideration:
       manual/research evidence > source authority tier > (for location) accuracy class > recency of the source value."""
    live = [o for o in obs if o.get("value_text") is not None or o.get("value_num") is not None]
    if field_name == "status":
        specific = [o for o in live if o["value_text"] not in NONSPECIFIC_STATUS]
        live = specific or live
    if not live:
        return None, ""
    kind_rank = {"manual": 0, "research": 1, "published": 2, "calculated": 3, "derived_spatial": 4}

    def key(o: dict):
        acc = ACCURACY_RANK.get(o.get("accuracy", "none"), 9) if field_name == "location_bng" else 0
        return (kind_rank.get(o.get("value_kind", "published"), 5), TIER_RANK.get(o["tier"], 5), acc,
                -(o["observed_at"] or dt.date.min).toordinal())

    live.sort(key=key)
    best = live[0]
    if len(live) == 1:
        return best, f"Only source reporting this value: {best['source_label']}"
    why = (f"Preferred {best['source_label']} (tier {best['tier']}, value dated {best['observed_at']}) over "
           + ", ".join(f"{o['source_label']} (tier {o['tier']}, {o['observed_at']})" for o in live[1:])
           + ": highest authority, then most recent")
    if field_name == "location_bng":
        why = f"Preferred the most precise coordinate class ({best.get('accuracy')}) from {best['source_label']}; others are alternatives"
    return best, why


# ---------------------------------------------------------------------------------------------------------------------
class Builder:
    def __init__(self, conn) -> None:
        self.conn = conn
        self.drafts: dict[str, Draft] = {}
        self.pool = Pool()
        self.orgs = OrgIndex()
        self.recs: list[dict] = []
        self.rec_assets: dict[int, list[str]] = defaultdict(list)
        self.review: list[tuple] = []
        self.stats: Counter = Counter()

    # -- loading ------------------------------------------------------------------------------------------------
    def load(self) -> None:
        self.recs = list(self.conn.execute("""
            SELECT r.source_record_id, r.snapshot_id, r.source_key, r.record_key, r.record_url, r.name, r.entity_kind,
                   r.technology_code, r.technology_raw, r.technologies_raw, r.status_code, r.status_raw,
                   r.capacity_mw, r.capacity_basis, r.export_capacity_mw, r.import_capacity_mw, r.storage_mwh, r.storage_duration_h,
                   r.turbine_count, r.turbine_rated_mw, r.turbine_height_m, r.site_area_ha,
                   r.bng_e, r.bng_n, r.lat, r.lon, r.coord_accuracy, r.coord_note,
                   CASE WHEN r.geom_kind IS NOT NULL THEN ST_AsText(r.geom) END AS geom_wkt, r.geom_kind,
                   r.country, r.region, r.county, r.local_authority, r.planning_authority, r.postcode_public,
                   r.operator_raw, r.developer_raw, r.owner_raw, r.planning_ref, r.appeal_ref, r.sos_ref,
                   r.dno, r.host_to, r.connection_site, r.connection_voltage_kv, r.connection_status, r.connection_date, r.gate,
                   r.cfd_round, r.cfd_capacity_mw, r.strike_price, r.ro_banding, r.fit_tariff, r.chp_enabled, r.mounting_type, r.storage_type,
                   r.record_updated, r.application_date, r.consent_date, r.construction_date, r.operational_date,
                   r.expected_operational_date, r.in_scope_gb, r.scope_note, r.privacy_class, r.ids, r.attrs, r.fields,
                   s.publication_date, s.retrieved_at::date AS retrieved_on,
                   g.tier, g.organisation AS source_org, g.dataset AS source_dataset
            FROM norm.source_record r
            JOIN raw.snapshot s USING (snapshot_id)
            JOIN ops.source_registry g ON g.source_key = r.source_key
            WHERE s.is_current AND r.entity_kind IN ('project','lease') AND r.excluded_reason IS NULL AND r.technology_code IS NOT NULL
            ORDER BY r.source_key, r.row_number"""))
        from decimal import Decimal
        for r in self.recs:
            for k, v in list(r.items()):
                if isinstance(v, Decimal):
                    r[k] = float(v)
            r["source_label"] = f"{r['source_org']} – {r['source_dataset']} ({r['publication_date'] or r['retrieved_on']})"
        log.info("loaded %d current normalised records", len(self.recs))

    # -- assignment: REPD backbone, then scored linking of everything else --------------------------------------
    def assign(self) -> None:
        anchors = {(a["anchor_scheme"], a["anchor_value"]): a["asset_id"] for a in self.conn.execute("SELECT * FROM atlas.asset_anchor")}

        def new_id() -> str:
            return self.conn.execute("SELECT 'GBA-' || lpad(nextval('atlas.asset_seq')::text, 7, '0') AS id").fetchone()["id"]

        def make(rec: dict) -> Draft:
            scheme = rec["source_key"]
            aid = anchors.get((scheme, rec["record_key"])) or new_id()
            d = Draft(aid, (scheme, rec["record_key"]), rec, [(rec, "primary", None, None)], to_cand(rec))
            self.drafts[aid] = d
            self.pool.add(d)
            self.rec_assets[rec["source_record_id"]].append(aid)
            return d

        repd = [r for r in self.recs if r["source_key"] == "repd"]
        for r in repd:
            make(r)
        # durable human decisions (ops.manual_links): 'link' forces a link, 'never_link' blocks one
        self.forced: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
        self.blocked: set[tuple[str, str, str, str]] = set()
        for m in self.conn.execute("SELECT source_key, record_key, anchor_scheme, anchor_value, decision FROM ops.manual_links"):
            if m["decision"] == "link":
                self.forced[(m["source_key"], m["record_key"])].append((m["anchor_scheme"], m["anchor_value"]))
            else:
                self.blocked.add((m["source_key"], m["record_key"], m["anchor_scheme"], m["anchor_value"]))
        order = {k: i for i, k in enumerate(SOURCE_ORDER)}
        others = sorted((r for r in self.recs if r["source_key"] != "repd"), key=lambda r: (order.get(r["source_key"], 99), r["source_record_id"]))
        for r in others:
            self._link_or_create(r, make)
        log.info("assets: %d (REPD %d, linked %d, created from other sources %d, review candidates %d)",
                 len(self.drafts), len(repd), self.stats["linked"], self.stats["created"], len(self.review))

    def _link_or_create(self, rec: dict, make) -> None:
        by_anchor = {d.anchor: d for d in self.drafts.values()}
        for anchor in self.forced.get((rec["source_key"], rec["record_key"]), []):
            d = by_anchor.get(anchor)
            if d is not None:
                d.links.append((rec, "manual", None, {"reason": "linked by an administrator (ops.manual_links)"}))
                self.rec_assets[rec["source_record_id"]].append(d.asset_id)
                self.stats["linked"] += 1
                return
        cand = to_cand(rec)
        idxs: set[int] = set()
        if cand.poly is not None:
            minx, miny, maxx, maxy = cand.poly.bounds  # type: ignore[union-attr]
            for i in self.pool.near((minx + maxx) / 2, (miny + maxy) / 2, max(maxx - minx, maxy - miny) / 2 + 9000):
                idxs.add(i)
        elif cand.e is not None and cand.accuracy != "none":
            idxs |= self.pool.near(cand.e, cand.n, 9000 if cand.offshore else 6000)
        idxs |= self.pool.by_name(cand.name)
        results = []
        for i in idxs:
            d = self.pool.drafts[i]
            if (rec["source_key"], rec["record_key"], d.anchor[0], d.anchor[1]) in self.blocked:
                continue  # an administrator ruled these two are NOT the same asset
            res = M.score(d.cand, cand)  # type: ignore[arg-type]
            if res.decision != "reject":
                results.append((res, d))
        results.sort(key=lambda x: -x[0].total)
        links = [x for x in results if x[0].decision == "link"]
        # tie-break: prefer assets that are live (operational/pipeline) over refused/withdrawn/superseded duplicates
        def live(d: Draft) -> int:
            return 0 if d.primary["status_code"] not in ("withdrawn", "refused", "expired", "cancelled", "superseded") else 1
        links.sort(key=lambda x: (-round(x[0].total, 2), live(x[1])))
        if links:
            best, d = links[0]
            ambiguous = len(links) > 1 and links[1][1].asset_id != d.asset_id and abs(links[1][0].total - best.total) < 0.03 and live(links[1][1]) == live(d)
            if not ambiguous:
                d.links.append((rec, "matched", round(best.total, 3), {"components": best.components, "reasons": best.reasons}))
                self.rec_assets[rec["source_record_id"]].append(d.asset_id)
                self.stats["linked"] += 1
                return
            reason = "ambiguous: more than one equally plausible asset"
            for res, dd in links[:3]:
                self.review.append((rec["source_record_id"], dd.asset_id, round(res.total, 3), Jsonb({"components": res.components}), reason))
        else:
            for res, dd in results[:2]:
                if res.decision == "review":
                    self.review.append((rec["source_record_id"], dd.asset_id, round(res.total, 3), Jsonb({"components": res.components}),
                                        "; ".join(res.reasons) or "similar but not conclusive"))
        make(rec)
        self.stats["created"] += 1

    # -- composing one draft into rows ---------------------------------------------------------------------------
    def observations(self, d: Draft) -> dict[str, list[dict]]:
        obs: dict[str, list[dict]] = defaultdict(list)
        for rec, ltype, *_ in d.links:
            def add(f: str, text=None, num=None, unit=None, fkey: str | None = None, kind="published", **extra):
                if text is None and num is None:
                    return
                fp = (rec["fields"] or {}).get(fkey or f, {})
                obs[f].append(dict(field=f, value_text=text, value_num=num, value_unit=unit, value_kind=kind, rec=rec,
                                   source_record_id=rec["source_record_id"], source_key=rec["source_key"], tier=rec["tier"],
                                   source_label=rec["source_label"], raw_column=fp.get("col"), raw_value=fp.get("raw"),
                                   raw_unit=fp.get("unit"), observed_at=observed_at(rec), **extra))
            sk = rec["source_key"]
            # 'unknown' / 'cfd_awarded' say nothing about development stage: keep them as context, not as a competing status
            add("status_context" if rec["status_code"] in NONSPECIFIC_STATUS and sk != "repd" else "status", rec["status_code"], fkey="status", raw_status=rec["status_raw"])
            add("technology", rec["technology_code"], fkey="technology")
            if sk == "repd":
                add("installed_capacity_mw", num=rec["capacity_mw"], unit="MW", fkey="capacity_mw")
            elif sk.startswith(("neso", "nged", "npg", "spen", "ukpn", "enwl")):
                add("registered_capacity_mw", num=rec["capacity_mw"], unit="MW", fkey="capacity_mw")
            elif sk == "cfd_results":
                add("cfd_capacity_mw", num=rec["cfd_capacity_mw"], unit="MW", fkey="cfd_capacity_mw")
            cdate = rec["operational_date"] or (rec["connection_date"] if rec["status_code"] == "operational" else None)
            add("commissioning_date", cdate.isoformat() if cdate else None, fkey="operational_date")
            if rec["expected_operational_date"]:
                add("expected_commissioning_date", rec["expected_operational_date"].isoformat())
            add("turbine_count", num=rec["turbine_count"], fkey="turbine_count")
            add("turbine_rated_mw_reported", num=rec["turbine_rated_mw"], unit="MW", fkey="turbine_rated_mw")
            add("turbine_height_reported_m", num=rec["turbine_height_m"], unit="m", fkey="turbine_height_m")
            add("site_area_ha", num=rec["site_area_ha"], unit="ha", fkey="site_area_ha")
            add("storage_capacity_mwh", num=rec["storage_mwh"], unit="MWh")
            add("storage_duration_h", num=rec["storage_duration_h"], unit="h")
            add("export_capacity_mw", num=rec["export_capacity_mw"], unit="MW")
            add("import_capacity_mw", num=rec["import_capacity_mw"], unit="MW")
            add("planning_reference", rec["planning_ref"])
            add("connection_voltage_kv", num=rec["connection_voltage_kv"], unit="kV", fkey="connection_voltage_kv")
            if rec["bng_e"] is not None and rec["coord_accuracy"] != "none" and not (sk == "cfd_results" and rec["technology_code"].startswith("wind_offshore")):
                add("location_bng", f"{float(rec['bng_e']):.0f},{float(rec['bng_n']):.0f}", unit="BNG m", fkey="bng_e",
                    accuracy=rec["coord_accuracy"], lat=rec["lat"], lon=rec["lon"], bng_e=float(rec["bng_e"]), bng_n=float(rec["bng_n"]))
            if rec["operator_raw"]:
                add("operator" if rec["status_code"] in ("operational", "partially_operational", "decommissioned") else "applicant", rec["operator_raw"])
            if rec["developer_raw"]:
                add("developer", rec["developer_raw"])
        # a generic technology ('wind_offshore') alongside a more specific one ('..._floating') is refinement, not conflict
        techs = {o["value_text"] for o in obs.get("technology", [])}
        generic = {"wind_offshore": {"wind_offshore_fixed", "wind_offshore_floating"}, "unknown": techs - {"unknown"}}
        for g, specifics in generic.items():
            if g in techs and (techs & set(specifics)):
                keep, ctx = [], []
                for o in obs["technology"]:
                    (ctx if o["value_text"] == g else keep).append(o)
                obs["technology"] = keep
                for o in ctx:
                    o["field"] = "technology_context"
                obs["technology_context"] = ctx
        return obs

    # -- write ----------------------------------------------------------------------------------------------------
    def build(self) -> dict[str, int]:
        c = self.conn
        self.load_admin_areas()
        self.load()
        self.assign()
        rows = self.compose_and_write()
        self.relationships()
        self.derive_geography()
        self.apply_overrides()
        c.execute("UPDATE atlas.assets SET is_published = false WHERE asset_id <> ALL(%s)", (list(self.drafts),))
        c.commit()
        return rows

    def apply_overrides(self) -> None:
        """Re-apply audited manual edits (ops.manual_overrides) after every rebuild; they never get lost."""
        cols = {"canonical_name": "canonical_name", "status_code": "status_code", "technology_code": "technology_code", "installed_capacity_mw": "installed_capacity_mw",
                "planning_reference": "planning_reference", "planning_authority": "planning_authority", "notes": "notes"}
        prov_field = {"status_code": "status", "technology_code": "technology"}
        n = 0
        for o in self.conn.execute("SELECT * FROM ops.manual_overrides"):
            col = cols.get(o["field_name"])
            row = self.conn.execute("SELECT asset_id FROM atlas.asset_anchor WHERE anchor_scheme=%s AND anchor_value=%s", (o["anchor_scheme"], o["anchor_value"])).fetchone()
            if not col or not row:
                continue
            val = o["value_num"] if o["value_num"] is not None else o["value_text"]
            self.conn.execute(f"UPDATE atlas.assets SET {col} = %s, confidence = 'verified', updated_at = now() WHERE asset_id = %s", (val, row["asset_id"]))
            pfield = prov_field.get(o["field_name"], o["field_name"])
            # One manual observation per override (rebuilds must not pile them up), and it is the single preferred value:
            # the source observations stay visible as the alternatives it overrode.
            self.conn.execute("DELETE FROM atlas.field_provenance WHERE asset_id=%s AND field_name=%s AND value_kind='manual' AND source_key='manual'", (row["asset_id"], pfield))
            self.conn.execute("UPDATE atlas.field_provenance SET is_preferred=false, selection_reason=NULL WHERE asset_id=%s AND field_name=%s", (row["asset_id"], pfield))
            self.conn.execute("""INSERT INTO atlas.field_provenance (asset_id, entity_type, entity_id, field_name, value_text, value_num, value_kind, source_key, observed_at, is_preferred, selection_reason)
                                 VALUES (%s,'asset',%s,%s,%s,%s,'manual','manual',%s,true,%s)""",
                              (row["asset_id"], row["asset_id"], pfield, o["value_text"], o["value_num"], o["decided_at"].date(), f"Manual override: {o['reason']}"))
            n += 1
        self.conn.commit()
        self.stats["overrides"] = n

    def load_admin_areas(self) -> None:
        c = self.conn
        c.execute("DELETE FROM atlas.admin_areas WHERE layer='lad'")
        c.execute("""INSERT INTO atlas.admin_areas (layer, code, name, country, geom, source_key)
                     SELECT 'lad', r.record_key, r.name, r.country, ST_Multi(ST_CollectionExtract(ST_MakeValid(r.geom), 3)), r.source_key
                     FROM norm.source_record r JOIN raw.snapshot s USING (snapshot_id)
                     WHERE s.is_current AND r.source_key = 'ons_lad' AND r.entity_kind = 'admin_area'""")
        c.commit()

    def compose_and_write(self) -> dict[str, int]:
        c = self.conn
        # clear derived (auto) rows; keep manual/research evidence rows
        for t in ("atlas.asset_source_links", "atlas.wind_details", "atlas.solar_details", "atlas.storage_systems",
                  "atlas.hydro_details", "atlas.bioenergy_details", "atlas.grid_connections", "atlas.support_schemes",
                  "atlas.asset_phases"):
            c.execute(f"DELETE FROM {t}")
        for t in ("atlas.field_provenance", "atlas.planning_cases", "atlas.asset_history", "atlas.asset_organisations",
                  "atlas.asset_geometries", "atlas.asset_identifiers"):
            c.execute(f"DELETE FROM {t} WHERE source_record_id IS NOT NULL")
        c.execute("DELETE FROM atlas.asset_relationships WHERE source_record_id IS NOT NULL OR basis LIKE 'heuristic%%'")
        c.execute("DELETE FROM ops.match_candidates WHERE decision IN ('pending','auto_linked')")
        c.commit()

        asset_rows, prov_rows, link_rows, ident_rows, hist_rows, plan_rows, org_rows = [], [], [], [], [], [], []
        grid_rows, support_rows, geom_rows, wind_rows, solar_rows, stor_rows, hydro_rows, bio_rows = [], [], [], [], [], [], [], []
        anchor_rows = []
        lt_cache: dict[str, str] = {r["code"]: r["label"] for r in c.execute("SELECT code, label FROM atlas.technology")}
        self.stage_group = {r["code"]: r["stage_group"] for r in c.execute("SELECT code, stage_group FROM atlas.status")}
        n = 0
        for d in self.drafts.values():
            n += 1
            P = d.primary
            obs = self.observations(d)
            pref: dict[str, dict | None] = {}
            for f, lst in obs.items():
                best, why = choose(f, lst)
                pref[f] = best
                for o in lst:
                    o["is_preferred"] = o is best
                    o["selection_reason"] = why if o is best else None
            if pref.get("status") is None:
                # No source states a development stage. A CfD award is still published evidence of a project in the pipeline,
                # so show that (its label says the stage is not stated) rather than 'Unknown'.
                award = next((o for o in obs.get("status_context", []) if o["value_text"] == "cfd_awarded"), None)
                if award is not None:
                    pref["status"] = award
                    award["is_preferred"] = True
                    award["selection_reason"] = "No source states a development stage; the CfD award is the only stage evidence available"
            g = lambda f: (pref.get(f) or {}).get("value_num") if (pref.get(f) or {}).get("value_num") is not None else (pref.get(f) or {}).get("value_text")  # noqa: E731
            status = g("status") or "unknown"
            status_obs = pref.get("status")
            tech = g("technology") or P["technology_code"]
            loc = pref.get("location_bng")
            recs = d.recs()
            is_offshore = any(((r.get("attrs") or {}).get("is_offshore") or (r.get("region") or "").lower() == "offshore") for r in recs) or str(tech).startswith("wind_offshore")
            cap = g("installed_capacity_mw")
            cap_basis = None
            if cap is not None:
                cap_basis = next((o["rec"]["capacity_basis"] for o in obs["installed_capacity_mw"] if o["is_preferred"]), None)
            elif g("registered_capacity_mw") is not None:
                cap, cap_basis = g("registered_capacity_mw"), next(o["rec"]["capacity_basis"] for o in obs["registered_capacity_mw"] if o["is_preferred"])
            elif g("cfd_capacity_mw") is not None:
                cap, cap_basis = g("cfd_capacity_mw"), "CfD contracted capacity (MW) – not an installed capacity"
            masked = P["privacy_class"] == "sub_1mw_masked" and all(r["privacy_class"] == "sub_1mw_masked" for r in recs)
            names = [(r["name"], r) for r in recs if r["name"] and not (r["privacy_class"] == "sub_1mw_masked" and r["source_key"] != "repd")]
            cname = P["name"] if not (P["privacy_class"] == "sub_1mw_masked" and P["source_key"] != "repd") else None
            if not cname:
                cname = f"{lt_cache.get(tech, 'Embedded generation')} – {P['dno'] or P['source_org']} ECR record ({cap if cap is not None else '?'} MW)"
            aliases = sorted({nm for nm, r in names if norm_name(nm) != norm_name(cname)})[:12]
            country = next((r["country"] for r in [P] + recs if r.get("country")), None)
            region = next((r["region"] for r in [P] + recs if r.get("region")), None)
            hasloc = loc is not None
            small = cap is not None and cap < 1.0
            planning_ref = g("planning_reference")
            planning_auth = next((r["planning_authority"] for r in [P] + recs if r.get("planning_authority")), None)
            grid_op = next((r["dno"] for r in recs if r.get("dno")), None) or next((TO_NAMES.get(r["host_to"], r["host_to"]) for r in recs if r.get("host_to")), None)
            conn_type = ("transmission" if any((r.get("attrs") or {}).get("agreement_type") == "Direct Connection" for r in recs)
                         else "distribution" if any(r.get("dno") or (r.get("attrs") or {}).get("agreement_type") == "Embedded" or r["source_key"].endswith("ecr") or "_ecr" in r["source_key"] for r in recs) else None)
            conn_status = next((r["connection_status"] for r in recs if r.get("connection_status")), None)
            commissioning = g("commissioning_date")
            expected = g("expected_commissioning_date")
            repd_ref = next((r["ids"].get("repd") for r in recs if r["source_key"] == "repd"), None)
            tec_ref = next((r["ids"].get("tec") for r in recs if r["ids"].get("tec")), None)
            ecr_ref = next((r["ids"].get("ecr") for r in recs if r["ids"].get("ecr")), None)
            cfd_ref = next((r["cfd_round"] for r in recs if r["source_key"] == "cfd_results"), None) or next((r["cfd_round"] for r in recs if r.get("cfd_round")), None)
            # location description: only addresses published for schemes of >= 1 MW
            loc_desc = None
            if P["source_key"] == "repd" and (cap is None or cap >= 1.0):
                a = (P["attrs"] or {}).get("address")
                loc_desc = ", ".join(x for x in (a, P.get("county")) if x) or None
            elif P["source_key"] == "repd":
                loc_desc = ", ".join(x for x in (P.get("county"), P.get("region")) if x) or None
            postcode = P.get("postcode_public")
            # last verified = latest date a CURRENT source edition contained/confirmed this record (snapshot publication, else retrieval);
            # the source's own 'record last updated' date is kept separately because it can be years old.
            last_ver = max(((r["publication_date"] or r["retrieved_on"]) for r in recs), default=None)
            src_upd = max((r["record_updated"] for r in recs if r.get("record_updated")), default=None)
            tier_a = len({r["source_key"] for r in recs if r["tier"] == "A"})
            tier_b = len({r["source_key"] for r in recs if r["tier"] == "B"})
            subtech = None
            if tech == "solar_pv" and P.get("mounting_type"):
                subtech = P["mounting_type"].lower()
            fam = c_family(tech)
            # --- detail rows ---
            wd = None
            if str(tech).startswith("wind"):
                rr = next((o["rec"] for o in obs.get("turbine_count", []) if o["is_preferred"]), P)
                wd = dict(asset_id=d.asset_id, offshore=is_offshore, foundation_type="floating" if tech == "wind_offshore_floating" else ("fixed" if tech == "wind_offshore_fixed" else None),
                          offshore_round=next(((r["attrs"] or {}).get("offshore_round") for r in recs if (r["attrs"] or {}).get("offshore_round")), None),
                          turbine_count_reported=int(g("turbine_count")) if g("turbine_count") is not None else None,
                          turbine_rated_mw_reported=g("turbine_rated_mw_reported"), turbine_height_reported_m=g("turbine_height_reported_m"),
                          lease_area_km2=next((float((r["attrs"] or {}).get("km2")) for r in recs if (r["attrs"] or {}).get("km2")), None))
                wind_rows.append(wd)
            if tech == "solar_pv":
                solar_rows.append(dict(asset_id=d.asset_id, site_area_ha=g("site_area_ha"), mounting_type=P.get("mounting_type"),
                                       export_mw=g("export_capacity_mw")))
            if tech in FAMILY_STORAGE or any(c_.get("technology_code") == "bess" for r in recs for c_ in _components(r)):
                st = next((r["storage_type"] for r in recs if r.get("storage_type")), None)
                mwh, dur_pub = g("storage_capacity_mwh"), g("storage_duration_h")
                power = cap
                stor_rows.append(dict(asset_id=d.asset_id, power_mw=power, energy_mwh=mwh, duration_h_published=dur_pub,
                                      duration_h_calculated=(round(mwh / power, 3) if (mwh and power and dur_pub is None) else None),
                                      import_mw=g("import_capacity_mw"), export_mw=g("export_capacity_mw"), storage_type=st))
            if tech in ("hydro", "pumped_hydro"):
                hydro_rows.append(dict(asset_id=d.asset_id, classification="pumped_storage" if tech == "pumped_hydro" else None))
            if fam == "bioenergy":
                bio_rows.append(dict(asset_id=d.asset_id, electrical_mw=cap, chp=next((r["chp_enabled"] for r in recs if r.get("chp_enabled") is not None), None)))
            # --- completeness / confidence ---
            ctx = dict(family=fam, name=bool(cname), status=status != "unknown", capacity=cap is not None, coordinates=hasloc,
                       country=bool(country), local_authority=any(r.get("local_authority") for r in recs), operator_or_developer=any(r.get("operator_raw") or r.get("developer_raw") for r in recs),
                       owner=any(r.get("owner_raw") for r in recs), planning_reference=bool(planning_ref), planning_authority=bool(planning_auth),
                       grid_operator=bool(grid_op), commissioning_date=bool(commissioning), turbine_count=bool(wd and wd["turbine_count_reported"]),
                       storage_mwh=bool(g("storage_capacity_mwh")), duration_h=bool(g("storage_duration_h")),
                       export_capacity=g("export_capacity_mw") is not None, site_area_ha=g("site_area_ha") is not None,
                       mounting_type=bool(P.get("mounting_type")), chp=any(r.get("chp_enabled") is not None for r in recs),
                       tier_a_sources=tier_a, tier_b_sources=tier_b, coordinate_accuracy=(loc or {}).get("accuracy", "none"))
            groups = {self.stage_group.get(o["value_text"]) for o in obs.get("status", []) if o["value_text"] not in NONSPECIFIC_STATUS}
            ctx["material_conflict"] = len(groups) > 1
            ctx["sources_agree"] = not ctx["material_conflict"]
            ctx["has_core_fields"] = ctx["name"] and ctx["status"] and ctx["capacity"] and ctx["coordinates"]
            comp_pct, _missing = completeness(ctx)
            conf = confidence(ctx)
            for r in recs:
                for oname in (r.get("operator_raw"), r.get("developer_raw"), r.get("owner_raw"), (r["attrs"] or {}).get("applicant"), (r["attrs"] or {}).get("tenant"),
                              None if r["privacy_class"] == "sub_1mw_masked" else (r["attrs"] or {}).get("customer_name")):
                    for part in split_orgs(oname):
                        self.orgs.observe(part)
            search_bits = [cname, *aliases, repd_ref, planning_ref, tec_ref, ecr_ref, cfd_ref, country, region, grid_op, lt_cache.get(tech),
                           postcode.split(" ")[0] if postcode else None]
            asset_rows.append(dict(
                asset_id=d.asset_id, canonical_name=cname, name_norm=norm_name(cname), asset_kind="lease_area" if P["entity_kind"] == "lease" else "project", aliases=aliases, technology_code=tech, subtechnology=subtech,
                status_code=status, status_original=(status_obs or {}).get("raw_status") or (status_obs or {}).get("raw_value"),
                status_source_key=(status_obs or {}).get("source_key"), country=country, region=region,
                local_authority=next((r["local_authority"] for r in recs if r.get("local_authority")), None),
                local_authority_basis="as published by the source network operator" if any(r.get("local_authority") for r in recs) else None,
                location_description=loc_desc, postcode=postcode, lat=(loc or {}).get("lat"), lon=(loc or {}).get("lon"),
                bng_e=(loc or {}).get("bng_e"), bng_n=(loc or {}).get("bng_n"), coordinate_accuracy=(loc or {}).get("accuracy", "none"),
                coordinate_source_key=(loc or {}).get("source_key"), is_offshore=is_offshore, installed_capacity_mw=cap, capacity_basis=cap_basis,
                export_capacity_mw=g("export_capacity_mw"), storage_capacity_mwh=g("storage_capacity_mwh"), storage_duration_h=g("storage_duration_h"),
                storage_duration_basis="published" if g("storage_duration_h") is not None else None,
                commissioning_date=commissioning, expected_commissioning_date=expected, planning_authority=planning_auth,
                planning_reference=planning_ref, grid_operator=grid_op, connection_type=conn_type,
                connection_voltage_kv=g("connection_voltage_kv"), connection_status=conn_status, repd_ref=repd_ref, tec_ref=tec_ref,
                ecr_ref=ecr_ref, ofgem_ref=None, cfd_ref=cfd_ref, scale_class="small" if small else "utility",
                privacy_class="sub_1mw_masked" if masked else "public",
                in_scope_gb=all(r["in_scope_gb"] for r in recs if r["source_key"] == "repd") if any(r["source_key"] == "repd" for r in recs) else all(r["in_scope_gb"] for r in recs),
                scope_note=next((r["scope_note"] for r in recs if r.get("scope_note")), None),
                last_verified=last_ver, source_updated=src_upd, confidence=conf, completeness_pct=comp_pct, is_published=True,
                notes="; ".join(sorted({n for r in recs for n in (r.get("qa_notes") or [])}))[:2000] or None,
                search_doc=" ".join(str(b) for b in search_bits if b)))
            anchor_rows.append((d.anchor[0], d.anchor[1], d.asset_id))
            d.ctx = ctx  # type: ignore[attr-defined]
            d.pref = pref  # type: ignore[attr-defined]
            # provenance rows
            for f, lst in obs.items():
                for o in lst:
                    prov_rows.append((d.asset_id, "asset", d.asset_id, f, o["value_text"], o["value_num"], o["value_unit"], o["value_kind"], None,
                                      o["source_record_id"], o["source_key"], o["raw_column"], o["raw_value"], o["raw_unit"], o["observed_at"],
                                      o["is_preferred"], o["selection_reason"]))
            # calculated values are always labelled with their expression
            if wd and wd["turbine_count_reported"] and wd["turbine_rated_mw_reported"]:
                prov_rows.append((d.asset_id, "asset", d.asset_id, "implied_turbine_mean_mw", None, round(cap / wd["turbine_count_reported"], 3) if cap else None, "MW", "calculated",
                                  f"installed_capacity_mw / turbine_count = {cap} / {wd['turbine_count_reported']}", None, None, None, None, None, last_ver, False, "calculated – not a published value"))
            # links / identifiers / history / planning / org / support / grid / geometries
            for rec, ltype, score, comps in d.links:
                link_rows.append((d.asset_id, rec["source_record_id"], ltype, score, Jsonb(comps) if comps else None))
                for scheme, ident in (rec["ids"] or {}).items():
                    ident_rows.append((d.asset_id, scheme, str(ident), rec["source_record_id"]))
                sk = rec["source_key"]
                if sk == "repd":
                    for m in (rec["attrs"] or {}).get("milestones", []):
                        hist_rows.append((d.asset_id, m["date"], m["type"], m["label"], rec["source_record_id"], rec["record_url"]))
                    ref_type = "s36" if (rec["planning_authority"] or "").lower().startswith("scottish government") else "lpa"
                    ms = {m["type"]: m["date"] for m in (rec["attrs"] or {}).get("milestones", [])}
                    decision = ("Granted" if "consent_granted" in ms or "appeal_granted" in ms or "sos_granted" in ms else "Refused" if "planning_refused" in ms
                                else "Withdrawn" if "planning_withdrawn" in ms else None)
                    if rec["planning_ref"] or rec["application_date"] or decision:
                        plan_rows.append((d.asset_id, rec["planning_authority"], rec["planning_ref"], ref_type, rec["application_date"], rec["consent_date"], decision, rec["status_raw"],
                                          None, "Reference and dates as published in REPD; REPD does not link to the underlying application", rec["source_record_id"]))
                    if rec["appeal_ref"] or any(k.startswith("appeal") for k in ms):
                        plan_rows.append((d.asset_id, rec["planning_authority"], rec["appeal_ref"], "appeal", None, None, None, None, None, "Appeal as published in REPD", rec["source_record_id"]))
                    if rec["sos_ref"]:
                        plan_rows.append((d.asset_id, "Secretary of State", rec["sos_ref"], "secretary_of_state", None, None, (rec["attrs"] or {}).get("sos_intervention_type"), None, None, "As published in REPD", rec["source_record_id"]))
                    if rec["cfd_round"]:
                        support_rows.append((d.asset_id, "CfD", rec["cfd_round"], rec["cfd_capacity_mw"], rec["cfd_round"], None, None, None, None, None, "As reported by REPD", None, rec["source_record_id"]))
                    if rec["ro_banding"] is not None:
                        support_rows.append((d.asset_id, "RO", None, None, None, None, None, None, rec["ro_banding"], None, "RO banding (ROC/MWh) as reported by REPD; accreditation reference/capacity not available", None, rec["source_record_id"]))
                    if rec["fit_tariff"] is not None:
                        support_rows.append((d.asset_id, "FIT", None, None, None, None, None, None, None, rec["fit_tariff"], "FiT tariff (p/kWh) as reported by REPD", None, rec["source_record_id"]))
                    role = "operator" if rec["status_code"] in ("operational", "partially_operational", "decommissioned") else "applicant"
                    for part in split_orgs(rec["operator_raw"]):
                        org_rows.append((d.asset_id, part, role, rec["source_record_id"], rec["operator_raw"]))
                elif sk == "cfd_results":
                    a = rec["attrs"] or {}
                    dy = a.get("delivery_year")
                    support_rows.append((d.asset_id, "CfD", f"{rec['cfd_round']}: {rec['name']}", rec["cfd_capacity_mw"], rec["cfd_round"],
                                         int(dy[:4]) if dy and dy[:4].isdigit() else None, rec["strike_price"], 2012 if rec["strike_price"] is not None and "2012" in (a.get("price_basis_note") or "") else None,
                                         None, None, f"Allocation result ({rec['cfd_round']}); 2024-price strike: {a.get('strike_price_2024')}; unit: {a.get('cfd_unit')}", "Allocated", rec["source_record_id"]))
                    for part in split_orgs(a.get("applicant")):
                        org_rows.append((d.asset_id, part, "applicant", rec["source_record_id"], a.get("applicant")))
                    hist_rows.append((d.asset_id, (rec["publication_date"] or rec["retrieved_on"]).isoformat(), "cfd_allocated", f"CfD {rec['cfd_round']} results published – listed as successful applicant", rec["source_record_id"], rec["record_url"]))
                elif sk == "crown_estate_wind_sites":
                    a = rec["attrs"] or {}
                    if rec["geom_wkt"]:
                        geom_rows.append((d.asset_id, "lease_area", rec["geom_wkt"], "EPSG:4326 (as published)", "Crown Estate lease/agreement area", f"{a.get('lease_status')}", rec["source_record_id"], score))
                    for part in split_orgs(a.get("tenant")):
                        org_rows.append((d.asset_id, part, "lessee", rec["source_record_id"], a.get("tenant")))
                else:  # network registers (TEC / embedded / ECR)
                    a = rec["attrs"] or {}
                    is_tec = sk.startswith("neso")
                    cust = None if rec["privacy_class"] == "sub_1mw_masked" else a.get("customer_name")
                    for part in split_orgs(cust):
                        org_rows.append((d.asset_id, part, "customer", rec["source_record_id"], cust))
                    grid_rows.append((d.asset_id, TO_NAMES.get(rec["host_to"], rec["host_to"]) if is_tec else rec["dno"],
                                      "transmission" if (is_tec and a.get("agreement_type") == "Direct Connection") else "distribution",
                                      rec["dno"], rec["connection_site"], a.get("grid_supply_point"), a.get("bulk_supply_point"), a.get("primary_substation"),
                                      rec["connection_voltage_kv"], rec["capacity_mw"], rec["import_capacity_mw"], rec["export_capacity_mw"],
                                      rec["capacity_mw"] if sk == "neso_tec" else None, rec["connection_status"], rec["connection_date"], rec["expected_operational_date"],
                                      rec["gate"], (rec["ids"] or {}).get("ecr_id"), (rec["ids"] or {}).get("neso_project_id"), (rec["ids"] or {}).get("neso_project_number"), rec["source_record_id"]))
                    if rec["connection_date"]:
                        hist_rows.append((d.asset_id, rec["connection_date"].isoformat(), "grid_connected", "Connected to the network (as recorded by the network operator)", rec["source_record_id"], rec["record_url"]))
                    if a.get("date_accepted"):
                        hist_rows.append((d.asset_id, a["date_accepted"], "connection_accepted", "Connection offer accepted", rec["source_record_id"], rec["record_url"]))
        # --- organisations --------------------------------------------------------------------------------------
        org_ids: dict[str, int] = {}
        for key in self.orgs.keys():
            cname_, aliases_ = self.orgs.canonical(key)
            row = c.execute("INSERT INTO atlas.organisations (canonical_name, name_norm, aliases) VALUES (%s,%s,%s) "
                            "ON CONFLICT (name_norm) DO UPDATE SET canonical_name=EXCLUDED.canonical_name, aliases=EXCLUDED.aliases RETURNING org_id",
                            (cname_, key, aliases_)).fetchone()
            org_ids[key] = row["org_id"]
        final_org_rows = []
        seen = set()
        for aid, part, role, srid, raw in org_rows:
            k = norm_org(part)
            if k in org_ids and (aid, k, role) not in seen:
                seen.add((aid, k, role))
                final_org_rows.append((aid, org_ids[k], role, raw, srid))
        # --- bulk writes ------------------------------------------------------------------------------------------
        self._upsert_assets(asset_rows)
        cur = c.cursor()
        cur.executemany("INSERT INTO atlas.asset_anchor (anchor_scheme, anchor_value, asset_id) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", anchor_rows)
        cur.executemany("INSERT INTO atlas.asset_source_links (asset_id, source_record_id, link_type, match_score, match_components) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", link_rows)
        cur.executemany("INSERT INTO atlas.asset_identifiers (asset_id, scheme, identifier, source_record_id) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING", ident_rows)
        cur.executemany("INSERT INTO atlas.asset_history (asset_id, event_date, event_type, description, source_record_id, url) VALUES (%s,%s,%s,%s,%s,%s)", hist_rows)
        cur.executemany("INSERT INTO atlas.planning_cases (asset_id, authority, reference, ref_type, application_date, decision_date, decision, stage, url, notes, source_record_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", plan_rows)
        cur.executemany("INSERT INTO atlas.asset_organisations (asset_id, org_id, role, raw_name, source_record_id) VALUES (%s,%s,%s,%s,%s)", final_org_rows)
        cur.executemany("INSERT INTO atlas.support_schemes (asset_id, scheme, reference, accredited_capacity_mw, allocation_round, delivery_year, strike_price_gbp_mwh, price_base_year, banding, tariff_p_per_kwh, notes, status, source_record_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", support_rows)
        cur.executemany("INSERT INTO atlas.grid_connections (asset_id, network_operator, connection_type, dno, point_of_connection, grid_supply_point, bulk_supply_point, primary_substation, voltage_kv, registered_capacity_mw, import_mw, export_mw, tec_mw, connection_status, connection_date, effective_from, gate, ecr_id, neso_project_id, neso_project_number, source_record_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", grid_rows)
        cur.executemany("INSERT INTO atlas.asset_geometries (asset_id, geom_type, geom, original_crs, label, accuracy_class, source_record_id, match_score) VALUES (%s,%s,ST_SetSRID(ST_GeomFromText(%s),4326),%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", geom_rows)
        cur.executemany("INSERT INTO atlas.field_provenance (asset_id, entity_type, entity_id, field_name, value_text, value_num, value_unit, value_kind, calc_expression, source_record_id, source_key, raw_column, raw_value, raw_unit, observed_at, is_preferred, selection_reason) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", prov_rows)
        self._insert_dicts("atlas.wind_details", wind_rows)
        self._insert_dicts("atlas.solar_details", solar_rows)
        self._insert_dicts("atlas.storage_systems", stor_rows)
        self._insert_dicts("atlas.hydro_details", hydro_rows)
        self._insert_dicts("atlas.bioenergy_details", bio_rows)
        cur.executemany("INSERT INTO ops.match_candidates (record_a, asset_b, score, components, reason) VALUES (%s,%s,%s,%s,%s)", self.review)
        c.commit()
        return dict(assets=len(asset_rows), provenance=len(prov_rows), links=len(link_rows), review_candidates=len(self.review))

    def _upsert_assets(self, rows: list[dict]) -> None:
        if not rows:
            return
        cols = list(rows[0].keys())
        sql = (f"INSERT INTO atlas.assets ({', '.join(cols)}, geom) VALUES ({', '.join('%(' + k + ')s' for k in cols)}, "
               "CASE WHEN %(lat)s::float8 IS NOT NULL THEN ST_SetSRID(ST_MakePoint(%(lon)s::float8, %(lat)s::float8), 4326) END) "
               f"ON CONFLICT (asset_id) DO UPDATE SET {', '.join(f'{k}=EXCLUDED.{k}' for k in cols if k != 'asset_id')}, geom=EXCLUDED.geom, updated_at=now()")
        with self.conn.cursor() as cur:
            cur.executemany(sql, rows)

    def _insert_dicts(self, table: str, rows: list[dict]) -> None:
        if not rows:
            return
        cols = list(rows[0].keys())
        with self.conn.cursor() as cur:
            cur.executemany(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('%(' + k + ')s' for k in cols)}) ON CONFLICT DO NOTHING", rows)

    # -- relationships (explicit REPD links first; name+proximity heuristics are labelled as such) ----------------------
    def relationships(self) -> None:
        c = self.conn
        by_ref = {d.primary["ids"].get("repd"): d for d in self.drafts.values() if d.primary["source_key"] == "repd"}
        rel: list[tuple] = []
        for d in by_ref.values():
            a = d.primary["attrs"] or {}
            for ref_key in ("reapply_new_ref", "reapply_old_ref"):
                for ref in re.split(r"[;,/\s]+", a.get(ref_key) or ""):
                    other = by_ref.get(ref)
                    if other and other.asset_id != d.asset_id:
                        newer, older = (other, d) if ref_key == "reapply_new_ref" else (d, other)
                        rel.append((newer.asset_id, older.asset_id, "supersedes", "REPD re-application reference", d.primary["source_record_id"]))
            col = a.get("storage_colocation_ref")
            if col and by_ref.get(col) and by_ref[col].asset_id != d.asset_id:
                rel.append((d.asset_id, by_ref[col].asset_id, "co_located_with", "REPD Storage Co-location REPD Ref ID", d.primary["source_record_id"]))
        # heuristic phase / extension / repower grouping (REPD only; same technology key, <= 3 km, base has no variant marker)
        from .textnorm import variant_signature
        names = {d.asset_id: variant_signature(d.primary["name"]) for d in by_ref.values()}
        pool: dict[str, list[Draft]] = defaultdict(list)
        for d in by_ref.values():
            cn = core_name(d.primary["name"])
            if len(cn) >= 4:
                pool[cn].append(d)
        parents: dict[str, str] = {}
        repowers: dict[str, str] = {}
        for cn, grp in pool.items():
            if len(grp) < 2:
                continue
            bases = [x for x in grp if not names[x.asset_id]]
            for x in grp:
                sig = names[x.asset_id]
                if not sig or not bases:
                    continue
                cx = x.cand
                near = [b for b in bases if b.cand and cx and b.cand.e is not None and cx.e is not None and M.distance_m(b.cand, cx) is not None and M.distance_m(b.cand, cx) <= 3000 and b.cand.techs & cx.techs]  # type: ignore[operator]
                if not near:
                    continue
                base = min(near, key=lambda b: M.distance_m(b.cand, cx))  # type: ignore[arg-type]
                kind = "repowers" if ({"repower", "repowering"} & sig) else "extension_of" if "extension" in sig else "phase_of"
                rel.append((x.asset_id, base.asset_id, kind, "heuristic: shared core name + same technology + within 3 km + variant marker in name", None))
                if kind == "repowers":
                    repowers[x.asset_id] = base.asset_id
                else:
                    parents[x.asset_id] = base.asset_id
        with c.cursor() as cur:
            cur.executemany("INSERT INTO atlas.asset_relationships (from_asset_id, to_asset_id, relation, basis, source_record_id) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", rel)
            cur.execute("UPDATE atlas.assets SET parent_asset_id = NULL, repowers_asset_id = NULL, phase_label = NULL")
            for child, parent in parents.items():
                cur.execute("UPDATE atlas.assets SET parent_asset_id=%s, phase_label=%s WHERE asset_id=%s",
                            (parent, ", ".join(sorted(names[child])), child))
            for child, base in repowers.items():
                cur.execute("UPDATE atlas.assets SET repowers_asset_id=%s, status_code = coalesce((%s::jsonb ->> status_code), status_code) WHERE asset_id=%s",
                            (base, Jsonb(REPOWER_STATUS), child))
        c.commit()

    # -- derived geography (spatial join; labelled as derived) --------------------------------------------------------
    def derive_geography(self) -> None:
        c = self.conn
        c.execute("""
            UPDATE atlas.assets a SET local_authority = l.name, local_authority_basis = 'derived: ONS LAD Dec 2025 (BGC) point-in-polygon',
                   country = coalesce(a.country, l.country)
            FROM atlas.admin_areas l
            WHERE a.geom IS NOT NULL AND a.local_authority IS NULL AND NOT a.is_offshore AND l.layer = 'lad' AND ST_Intersects(l.geom, a.geom)""")
        # coastal points just outside generalised boundaries: nearest district within 1.5 km (labelled as such)
        c.execute("""
            UPDATE atlas.assets a SET
                   local_authority = (SELECT l.name FROM atlas.admin_areas l WHERE l.layer = 'lad' ORDER BY l.geom <-> a.geom LIMIT 1),
                   local_authority_basis = 'derived: nearest ONS LAD within 1.5 km (point outside generalised boundary)'
            WHERE a.geom IS NOT NULL AND a.local_authority IS NULL AND NOT a.is_offshore AND EXISTS (
                   SELECT 1 FROM atlas.admin_areas l WHERE l.layer = 'lad' AND ST_DWithin(l.geom, a.geom, 0.05)
                     AND ST_DWithin(l.geom::geography, a.geom::geography, 1500))""")
        c.commit()


def c_family(tech: str) -> str:
    if str(tech).startswith("wind"):
        return "wind"
    if tech == "solar_pv":
        return "solar"
    if tech in FAMILY_STORAGE:
        return "storage"
    if tech in ("hydro",):
        return "hydro"
    if tech in ("anaerobic_digestion", "biomass", "landfill_gas", "sewage_gas", "renewable_chp", "energy_from_waste"):
        return "bioenergy"
    return "other"
