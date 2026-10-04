"""End-to-end ingestion + canonical-build behaviour against a real PostGIS database.

Every record below is SYNTHETIC (names start 'Synthetic …'). The data exists only to exercise code paths and is
created in a throw-away database per test – it never touches the real atlas database."""
from __future__ import annotations

import datetime as dt
import json

import openpyxl
import pytest
from pyproj import Transformer

from atlas_ingest import canonical, qa
from atlas_ingest.adapters.cfd import CfdAdapter
from atlas_ingest.adapters.crown_estate import CrownEstateAdapter
from atlas_ingest.adapters.ons_lad import OnsLadAdapter
from atlas_ingest.adapters.repd import RepdAdapter
from atlas_ingest.pipeline import Supplied, run_source
from conftest import repd_row, write_repd

TODAY = dt.date(2026, 10, 4)


def ingest(db, adapter, path, *, label="", publication=None):
    sup = Supplied(path, f"https://example.test/{path.name}", TODAY, publication, label)
    return run_source(db, adapter, supplied=sup)


def build(db):
    out = canonical.Builder(db).build()
    qa.run(db)
    qa.research_queue(db)
    qa.refresh_views(db)
    return out


def asset_for(db, repd_ref):
    return db.execute("SELECT * FROM atlas.assets WHERE repd_ref=%s AND is_published", (repd_ref,)).fetchone()


# ------------------------------------------------------------------------------------------------ fixtures
VALE = dict(**{"Ref ID": "101", "Site Name": "Synthetic Vale Wind Farm", "Technology Type": "Wind Onshore", "Installed Capacity (MWelec)": "20", "No. of Turbines": "8",
               "X-coordinate": "340000", "Y-coordinate": "480000", "Operator (or Applicant)": "Vale Power Ltd", "Planning Application Reference": "20/00001/FUL", "Operational": "01/06/2015"})
VALE_EXT = dict(**{"Ref ID": "102", "Site Name": "Synthetic Vale Wind Farm Extension", "Technology Type": "Wind Onshore", "Installed Capacity (MWelec)": "6", "X-coordinate": "340300",
                   "Y-coordinate": "480200", "Development Status": "Awaiting Construction", "Development Status (short)": "Awaiting Construction"})
RIDGE_E = dict(**{"Ref ID": "103", "Site Name": "Synthetic Ridge East Wind Farm", "Technology Type": "Wind Onshore", "Installed Capacity (MWelec)": "10", "X-coordinate": "400000", "Y-coordinate": "500000"})
RIDGE_W = dict(**{"Ref ID": "104", "Site Name": "Synthetic Ridge West Wind Farm", "Technology Type": "Wind Onshore", "Installed Capacity (MWelec)": "10", "X-coordinate": "400400", "Y-coordinate": "500000"})
FEN_BESS = dict(**{"Ref ID": "105", "Site Name": "Synthetic Fen Battery", "Technology Type": "Battery", "Installed Capacity (MWelec)": "50", "X-coordinate": "530000", "Y-coordinate": "280000"})
SMALL_SOLAR = dict(**{"Ref ID": "106", "Site Name": "Synthetic Yard Solar", "Technology Type": "Solar Photovoltaics", "Installed Capacity (MWelec)": "0.4", "Post Code": "AB1 2CD",
                      "Address": "1 Synthetic Lane", "X-coordinate": "350000", "Y-coordinate": "350000"})


def repd_file(tmp_path, rows, name="repd.csv"):
    return write_repd(tmp_path / name, [repd_row(**r) for r in rows])


def cfd_file(tmp_path, rows):
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(["Contracts for Difference Allocation Round 6 Results"]); ws.append(["(A) strike prices are in 2012 prices"]); ws.append([])
    ws.append([None, "Project Name", "Project Location", "Country, Region", "Applicant", "Technology Type", "Size (MW)", "Strike Price (£/MWh)", "Delivery Year ", "Target Commissioning Date", "No. of Phases", "Pot"])
    for r in rows:
        ws.append([None, *r])
    p = tmp_path / "cfd.xlsx"; wb.save(p)
    return p


CFD_VALE = ["Synthetic Vale Wind Farm", "SD4080", "England", "VALE POWER LTD", "Onshore Wind", 26, 45.0, "2027/28", dt.datetime(2027, 4, 1), 1, "Pot 2"]
CFD_ORPHAN = ["Synthetic Orphan Solar", "NT730745", "Scotland", "ORPHAN SOLAR LTD", "Solar PV (>5MW)", 20, 50.07, "2026/27", dt.datetime(2027, 3, 1), 1, "Pot 1"]


# ------------------------------------------------------------------------------------------------ pipeline
def test_supplied_file_is_recorded_as_manual_and_rerun_is_idempotent(db, tmp_path):
    p = repd_file(tmp_path, [VALE, RIDGE_E, {"Ref ID": "107", "Site Name": "Synthetic Bad Coords", "Technology Type": "Battery", "X-coordinate": "3862265", "Y-coordinate": "400000"}])
    first = ingest(db, RepdAdapter(), p, publication=dt.date(2026, 8, 3))
    assert first["outcome"] == "success" and first["rows_ok"] == 3
    snap = db.execute("SELECT * FROM raw.snapshot WHERE source_key='repd'").fetchone()
    assert "MANUALLY SUPPLIED" in snap["notes"] and snap["publication_date"] == dt.date(2026, 8, 3) and len(snap["sha256"]) == 64
    assert db.execute("SELECT count(*) AS n FROM raw.record WHERE snapshot_id=%s", (snap["snapshot_id"],)).fetchone()["n"] == 3
    # impossible coordinates are kept (never guessed) but flagged, and the original string is preserved in raw
    bad = db.execute("SELECT lat, qa_notes FROM norm.source_record WHERE record_key='107'").fetchone()
    assert bad["lat"] is None and any("not plausible" in n for n in bad["qa_notes"])
    assert db.execute("SELECT payload->>'X-coordinate' AS x FROM raw.record WHERE record_key='107'").fetchone()["x"] == "3862265"
    reg = db.execute("SELECT access_status, records_imported FROM ops.source_registry WHERE source_key='repd'").fetchone()
    assert reg["access_status"] == "current" and reg["records_imported"] == 3

    again = ingest(db, RepdAdapter(), p)
    assert again["outcome"] == "unchanged"
    assert db.execute("SELECT count(*) AS n FROM raw.snapshot WHERE source_key='repd'").fetchone()["n"] == 1
    assert db.execute("SELECT count(*) AS n FROM norm.source_record WHERE source_key='repd'").fetchone()["n"] == 3


def test_new_edition_keeps_old_raw_and_logs_changes(db, tmp_path):
    ed1 = repd_file(tmp_path, [VALE, RIDGE_E, RIDGE_W], "ed1.csv")
    ingest(db, RepdAdapter(), ed1)
    changed = {**VALE, "Installed Capacity (MWelec)": "24", "Development Status": "Decommissioned", "Development Status (short)": "Decommissioned"}
    ed2 = repd_file(tmp_path, [changed, RIDGE_E, FEN_BESS], "ed2.csv")   # Ridge West removed, Fen added
    r = ingest(db, RepdAdapter(), ed2)
    assert r["outcome"] == "success"
    # the first edition is retained untouched; only the newest is current
    snaps = db.execute("SELECT is_current FROM raw.snapshot WHERE source_key='repd' ORDER BY snapshot_id").fetchall()
    assert [s["is_current"] for s in snaps] == [False, True]
    assert db.execute("SELECT count(*) AS n FROM raw.record").fetchone()["n"] == 6
    log = {(c["record_key"], c["change_type"], c["field_name"]): (c["old_value"], c["new_value"]) for c in db.execute("SELECT * FROM ops.change_log")}
    assert log[("101", "capacity_change", "capacity_mw")] == ("20", "24")
    assert ("101", "status_change", "status_raw") in log
    assert ("105", "new_project", None) in log and ("104", "removed_project", None) in log
    assert not any(k[0] == "103" for k in log)   # unchanged project produces no noise


# ------------------------------------------------------------------------------------------------ canonical build
@pytest.fixture()
def loaded(db, tmp_path):
    ingest(db, RepdAdapter(), repd_file(tmp_path, [VALE, VALE_EXT, RIDGE_E, RIDGE_W, FEN_BESS, SMALL_SOLAR]))
    ingest(db, CfdAdapter(), cfd_file(tmp_path, [CFD_VALE, CFD_ORPHAN]), label="AR6")
    build(db)
    return db


def test_matching_links_same_project_but_never_siblings_or_extensions(loaded):
    db = loaded
    vale = asset_for(db, "101")
    links = db.execute("SELECT r.source_key, l.link_type, l.match_score FROM atlas.asset_source_links l JOIN norm.source_record r USING (source_record_id) WHERE l.asset_id=%s",
                       (vale["asset_id"],)).fetchall()
    assert sorted(l["source_key"] for l in links) == ["cfd_results", "repd"]
    cfd_link = next(l for l in links if l["source_key"] == "cfd_results")
    assert cfd_link["link_type"] == "matched" and float(cfd_link["match_score"]) >= 0.80

    ext, east, west = asset_for(db, "102"), asset_for(db, "103"), asset_for(db, "104")
    assert len({vale["asset_id"], ext["asset_id"], east["asset_id"], west["asset_id"]}) == 4   # extension and East/West are NOT merged
    for a in (ext, east, west):
        n = db.execute("SELECT count(*) AS n FROM atlas.asset_source_links WHERE asset_id=%s", (a["asset_id"],)).fetchone()["n"]
        assert n == 1
    rel = db.execute("SELECT relation FROM atlas.asset_relationships WHERE from_asset_id=%s AND to_asset_id=%s", (ext["asset_id"], vale["asset_id"])).fetchall()
    assert [r["relation"] for r in rel] == ["extension_of"]
    # a CfD-only project gets its own asset, honestly labelled as a CfD award rather than a development status
    orphan = db.execute("SELECT * FROM atlas.assets WHERE canonical_name ILIKE 'Synthetic Orphan Solar%%'").fetchone()
    assert orphan["status_code"] == "cfd_awarded" and orphan["repd_ref"] is None and orphan["technology_code"] == "solar_pv"


def test_field_provenance_traces_values_to_raw_columns_and_keeps_context(loaded):
    db = loaded
    a = asset_for(db, "101")
    cap = db.execute("SELECT * FROM atlas.field_provenance WHERE asset_id=%s AND field_name='installed_capacity_mw'", (a["asset_id"],)).fetchall()
    assert len(cap) == 1 and cap[0]["is_preferred"] and cap[0]["source_key"] == "repd" and cap[0]["raw_column"] == "Installed Capacity (MWelec)" and cap[0]["raw_value"] == "20"
    assert cap[0]["source_record_id"] is not None and cap[0]["observed_at"] is not None and cap[0]["selection_reason"]
    # CfD capacity is a different quantity: retained as its own field, never overwriting installed capacity
    cfd = db.execute("SELECT value_num, source_key FROM atlas.field_provenance WHERE asset_id=%s AND field_name='cfd_capacity_mw'", (a["asset_id"],)).fetchall()
    assert [(float(c["value_num"]), c["source_key"]) for c in cfd] == [(26.0, "cfd_results")]
    assert float(a["installed_capacity_mw"]) == 20.0
    # "CfD awarded" says nothing about development stage, so it does not overwrite or conflict with 'operational'
    assert a["status_code"] == "operational"
    assert db.execute("SELECT count(*) AS n FROM atlas.field_conflicts WHERE asset_id=%s AND field_name='status'", (a["asset_id"],)).fetchone()["n"] == 0
    ctx = db.execute("SELECT value_text FROM atlas.field_provenance WHERE asset_id=%s AND field_name='status_context'", (a["asset_id"],)).fetchall()
    assert any("cfd_awarded" in c["value_text"] for c in ctx)
    # the more accurate REPD site reference wins over the CfD's 1 km grid square, and says why
    assert a["coordinate_source_key"] == "repd" and a["coordinate_accuracy"] == "site_reference"
    # unit/derivation: provenance values never come from nowhere
    assert db.execute("SELECT count(*) AS n FROM atlas.field_provenance WHERE value_kind='published' AND source_record_id IS NULL").fetchone()["n"] == 0


def test_capacity_difference_between_quantities_is_flagged_not_merged(loaded):
    db = loaded
    a = asset_for(db, "101")
    flags = db.execute("SELECT flag_code FROM atlas.data_quality_flags WHERE asset_id=%s", (a["asset_id"],)).fetchall()
    assert "capacity_discrepancy" in {f["flag_code"] for f in flags}    # 20 MW installed vs 26 MW contracted (>15 %)


def test_privacy_masking_below_1mw(loaded):
    db = loaded
    a = asset_for(db, "106")
    assert a["postcode"] is None and a["scale_class"] == "small"
    doc = (a["search_doc"] or "").lower()
    assert "ab1" not in doc and "synthetic lane" not in doc


def test_stable_ids_and_idempotent_rebuild(loaded):
    db = loaded
    before = {r["repd_ref"]: r["asset_id"] for r in db.execute("SELECT repd_ref, asset_id FROM atlas.assets WHERE repd_ref IS NOT NULL")}
    n_before = db.execute("SELECT count(*) AS n FROM atlas.assets WHERE is_published").fetchone()["n"]
    build(db)
    after = {r["repd_ref"]: r["asset_id"] for r in db.execute("SELECT repd_ref, asset_id FROM atlas.assets WHERE repd_ref IS NOT NULL AND is_published")}
    assert after == before   # identifiers survive a rebuild
    assert db.execute("SELECT count(*) AS n FROM atlas.assets WHERE is_published").fetchone()["n"] == n_before
    assert db.execute("SELECT count(*) AS n FROM atlas.assets").fetchone()["n"] == n_before   # nothing orphaned or duplicated


def test_manual_never_link_and_link_decisions_persist(db, tmp_path):
    ingest(db, RepdAdapter(), repd_file(tmp_path, [VALE, RIDGE_E]))
    rename = ["Synthetic Hilltop Scheme", "SD4080", "England", "OTHER LTD", "Onshore Wind", 9, 40.0, "2027/28", dt.datetime(2027, 4, 1), 1, "Pot 2"]
    ingest(db, CfdAdapter(), cfd_file(tmp_path, [CFD_VALE, rename]), label="AR6")
    build(db)
    vale = asset_for(db, "101")
    keys = {r["name"]: r["record_key"] for r in db.execute("SELECT name, record_key FROM norm.source_record WHERE source_key='cfd_results'")}
    # auto: identical name -> linked; a differently-named project at the same square is NOT linked automatically
    assert db.execute("SELECT count(*) AS n FROM atlas.asset_source_links WHERE asset_id=%s", (vale["asset_id"],)).fetchone()["n"] == 2
    hilltop = db.execute("SELECT asset_id FROM atlas.assets WHERE canonical_name ILIKE 'Synthetic Hilltop%%'").fetchone()
    assert hilltop is not None and hilltop["asset_id"] != vale["asset_id"]

    db.execute("INSERT INTO ops.manual_links (source_key, record_key, anchor_scheme, anchor_value, decision, reason, decided_by) VALUES "
               "('cfd_results',%s,'repd','101','never_link','Different projects – checked against CfD register','tester'),"
               "('cfd_results',%s,'repd','103','link','Developer confirms same scheme','tester')",
               (keys["Synthetic Vale Wind Farm"], keys["Synthetic Hilltop Scheme"]))
    db.commit()
    build(db); build(db)   # decisions are durable across repeated rebuilds
    vale = asset_for(db, "101")
    assert db.execute("SELECT count(*) AS n FROM atlas.asset_source_links WHERE asset_id=%s", (vale["asset_id"],)).fetchone()["n"] == 1
    ridge = asset_for(db, "103")
    types = [r["link_type"] for r in db.execute("SELECT link_type FROM atlas.asset_source_links WHERE asset_id=%s ORDER BY 1", (ridge["asset_id"],))]
    assert types == ["manual", "primary"]
    assert db.execute("SELECT count(*) AS n FROM atlas.assets WHERE is_published AND canonical_name ILIKE 'Synthetic Hilltop%%'").fetchone()["n"] == 0
    assert db.execute("SELECT count(*) AS n FROM atlas.assets WHERE is_published AND canonical_name ILIKE 'Synthetic Vale Wind Farm' AND repd_ref IS NULL").fetchone()["n"] == 1


def test_manual_override_survives_rebuild_with_audit_provenance(loaded):
    db = loaded
    aid = asset_for(db, "101")["asset_id"]
    db.execute("INSERT INTO ops.manual_overrides (anchor_scheme, anchor_value, field_name, value_num, reason, evidence_url, decided_by) "
               "VALUES ('repd','101','installed_capacity_mw',21,'Operator page states 21 MW','https://example.test/evidence','tester')")
    db.commit()
    for _ in range(2):
        build(db)
        a = asset_for(db, "101")
        assert a["asset_id"] == aid and float(a["installed_capacity_mw"]) == 21.0 and a["confidence"] == "verified"
        manual = db.execute("SELECT selection_reason, value_kind FROM atlas.field_provenance WHERE asset_id=%s AND field_name='installed_capacity_mw' AND value_kind='manual'", (aid,)).fetchall()
        assert len(manual) == 1 and "Operator page states 21 MW" in manual[0]["selection_reason"]
        # exactly one preferred value; the REPD figure stays visible as the alternative that was overridden
        prefs = db.execute("SELECT source_key, value_num FROM atlas.field_provenance WHERE asset_id=%s AND field_name='installed_capacity_mw' ORDER BY is_preferred DESC, source_key", (aid,)).fetchall()
        assert [(p["source_key"], float(p["value_num"])) for p in prefs] == [("manual", 21.0), ("repd", 20.0)]
        assert db.execute("SELECT count(*) AS n FROM atlas.field_provenance WHERE asset_id=%s AND field_name='installed_capacity_mw' AND is_preferred", (aid,)).fetchone()["n"] == 1
        assert db.execute("SELECT count(*) AS n FROM atlas.field_conflicts WHERE asset_id=%s AND field_name='installed_capacity_mw'", (aid,)).fetchone()["n"] == 1


# ------------------------------------------------------------------------------------------------ geography & QA
def _lad(tmp_path, code, name, bbox_lonlat):
    x0, y0, x1, y1 = bbox_lonlat
    fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"LAD25CD": code, "LAD25NM": name},
                                                       "geometry": {"type": "Polygon", "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}}]}
    p = tmp_path / f"lad_{code}.geojson"; p.write_text(json.dumps(fc))
    return p


def _lonlat(e, n):
    lon, lat = Transformer.from_crs(27700, 4326, always_xy=True).transform(e, n)
    return lon, lat


def test_local_authority_is_derived_and_qa_flags_off_land_and_country_mismatch(db, tmp_path):
    ingest(db, RepdAdapter(), repd_file(tmp_path, [VALE, RIDGE_E]))
    lon, lat = _lonlat(340000, 480000)
    # A synthetic 'Welsh' district around Vale: the record says England, so the coordinates disagree with the stated country
    ingest(db, OnsLadAdapter(), _lad(tmp_path, "W06000001", "Synthetic Principality", (lon - 0.2, lat - 0.2, lon + 0.2, lat + 0.2)), label="lad")
    build(db)
    vale, ridge = asset_for(db, "101"), asset_for(db, "103")
    assert vale["local_authority"] == "Synthetic Principality" and "point-in-polygon" in vale["local_authority_basis"]
    assert ridge["local_authority"] is None   # outside every polygon: left unknown, never guessed
    flags = {(f["asset_id"], f["flag_code"]): f for f in db.execute("SELECT * FROM atlas.data_quality_flags WHERE resolved_at IS NULL")}
    assert (vale["asset_id"], "coordinate_country_mismatch") in flags and flags[(vale["asset_id"], "coordinate_country_mismatch")]["severity"] == "error"
    assert (ridge["asset_id"], "coordinate_not_on_land") in flags
    assert (vale["asset_id"], "coordinate_not_on_land") not in flags


def test_offshore_record_links_to_crown_estate_lease_by_polygon_containment(db, tmp_path):
    lon, lat = -3.5, 53.95
    e, n = Transformer.from_crs(4326, 27700, always_xy=True).transform(lon, lat)
    off = {"Ref ID": "201", "Site Name": "Synthetic Bank Offshore Wind Farm", "Technology Type": "Wind Offshore", "Installed Capacity (MWelec)": "300",
           "X-coordinate": str(round(e)), "Y-coordinate": str(round(n)), "Region": "Offshore", "Development Status": "Under Construction", "Development Status (short)": "Under Construction"}
    ingest(db, RepdAdapter(), repd_file(tmp_path, [off]))
    fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"OBJECTID": 1, "Name_Prop": "Synthetic Bank", "Name_Ten": "Synthetic Offshore Ltd", "Wind_Round": "2",
                                                                                         "Lease_Stat": "Lease - Marine", "Inf_Status": "Under Construction", "km2": 12.5},
                                                      "geometry": {"type": "Polygon", "coordinates": [[[-3.6, 53.9], [-3.4, 53.9], [-3.4, 54.0], [-3.6, 54.0], [-3.6, 53.9]]]}}]}
    p = tmp_path / "tce.geojson"; p.write_text(json.dumps(fc))
    ingest(db, CrownEstateAdapter(), p)
    build(db)
    a = asset_for(db, "201")
    srcs = [r["source_key"] for r in db.execute("SELECT r.source_key FROM atlas.asset_source_links l JOIN norm.source_record r USING (source_record_id) WHERE l.asset_id=%s ORDER BY 1", (a["asset_id"],))]
    assert srcs == ["crown_estate_wind_sites", "repd"] and a["is_offshore"]
    # the lease polygon is attached as an area, never promoted to a turbine or project point
    geoms = db.execute("SELECT geom_type FROM atlas.asset_geometries WHERE asset_id=%s", (a["asset_id"],)).fetchall()
    assert any(g["geom_type"] == "lease_area" for g in geoms)
    assert db.execute("SELECT count(*) AS n FROM atlas.wind_turbines").fetchone()["n"] == 0


def test_no_turbine_positions_are_ever_derived_from_project_points(loaded):
    db = loaded
    assert db.execute("SELECT count(*) AS n FROM atlas.wind_turbines").fetchone()["n"] == 0
    # reported turbine count stays a reported number, not a set of invented points
    w = db.execute("SELECT turbine_count_reported FROM atlas.wind_details WHERE asset_id=%s", (asset_for(db, "101")["asset_id"],)).fetchone()
    assert w["turbine_count_reported"] == 8


def test_licence_export_policy_is_in_the_registry_and_read_model(loaded):
    db = loaded
    pol = {r["source_key"]: r["export_policy"] for r in db.execute("SELECT source_key, export_policy FROM ops.source_registry")}
    assert pol["crown_estate_wind_sites"] == "exclude" and pol["repd"] == "include"
    # the read model must carry the facts the exporter needs to apply it
    cols = {r["attname"] for r in db.execute("SELECT attname FROM pg_attribute WHERE attrelid='atlas.asset_flat'::regclass AND attnum > 0 AND NOT attisdropped")}
    assert {"asset_id", "technology_code", "status_code", "installed_capacity_mw", "geom"} <= cols
