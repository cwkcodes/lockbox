"""Adapter behaviour on SYNTHETIC fixtures that reproduce the real-world defects found while profiling live data."""
import csv
import datetime as dt
import json

import pytest

from atlas_ingest.adapters.base import Resource
from atlas_ingest.adapters.cfd import CfdAdapter
from atlas_ingest.adapters.crown_estate import CrownEstateAdapter
from atlas_ingest.adapters.ecr import EcrAdapter, slot_technology
from atlas_ingest.adapters.neso import NesoRegisterAdapter
from atlas_ingest.adapters.osm import OsmOverpassAdapter, _power_mw
from atlas_ingest.adapters.repd import RepdAdapter
from atlas_ingest.model import Reject
from conftest import repd_row, write_repd

RES = Resource(url="https://example.test/file", label="fixture", publication_date=dt.date(2026, 8, 3))


def run(adapter, path, resource=RES):
    out = []
    for row_number, key, payload in adapter.parse(path, resource):
        bad = adapter.validate_structure(payload)
        out.append(Reject(bad) if bad else adapter.normalise(payload, row_number, resource))
    return out


# ---------------------------------------------------------------------------------------------------------- REPD
def test_repd_cp1252_blank_cells_round_names_and_scope(tmp_path):
    p = write_repd(tmp_path / "repd.csv", [
        repd_row(**{"Ref ID": "1", "Site Name": "Synthetic Hill Wind Farm ", "Technology Type": "Wind Onshore", "Installed Capacity (MWelec)": "18", "No. of Turbines": "6", "X-coordinate": "256800", "Y-coordinate": "645435",
                    "Country": "Scotland", "Operator (or Applicant)": "Café Energy Ltd", "Storage Type": "   ", "Operational": "01/05/2007"}),
        repd_row(**{"Ref ID": "2", "Site Name": "Synthetic Offshore Zone", "Technology Type": "Wind Offshore", "Offshore Wind Round": "02/01/1900", "Region": "Offshore", "X-coordinate": "708047", "Y-coordinate": "312194"}),
        repd_row(**{"Ref ID": "3", "Site Name": "Synthetic NI Farm", "Technology Type": "Solar Photovoltaics", "Country": "Northern Ireland", "X-coordinate": "117392", "Y-coordinate": "488885"}),
        repd_row(**{"Ref ID": "4", "Site Name": "Synthetic Bad Coords", "Technology Type": "Battery", "X-coordinate": "3862265", "Y-coordinate": "400000"}),
        repd_row(**{"Ref ID": "5", "Site Name": "Synthetic Unknown Tech", "Technology Type": "Unknown"}),
        repd_row(**{"Ref ID": "6", "Site Name": "Synthetic Superseded", "Technology Type": "Wind Onshore", "Development Status (short)": "Revised", "Development Status": "Revised", "Are they re-applying (New REPD Ref)": "1"}),
    ])
    a = RepdAdapter()
    r1, r2, r3, r4, r5, r6 = run(a, p)
    assert r1.name == "Synthetic Hill Wind Farm" and r1.operator_raw == "Café Energy Ltd"  # cp1252 decoded, whitespace trimmed
    assert r1.technology_code == "wind_onshore" and r1.capacity_mw == 18 and r1.turbine_count == 6
    assert r1.storage_type is None  # whitespace-only cell is blank, not a value
    assert r1.coord_accuracy == "site_reference" and 55.6 < r1.lat < 55.75
    assert r1.fields["capacity_mw"] == {"col": "Installed Capacity (MWelec)", "raw": "18", "unit": "MW"}  # field-level provenance
    assert r2.attrs["offshore_round"] == "Round 2" and "Excel date artefact" in r2.attrs["offshore_round_note"]
    assert r2.lat is not None and "far-offshore" in r2.coord_note  # beyond the formal BNG square but valid
    assert r3.in_scope_gb is False and "Northern Ireland" in r3.scope_note  # retained, flagged out of scope
    assert r4.lat is None and any("not plausible" in n for n in r4.qa_notes)  # rejected, never guessed
    assert r5.technology_raw == "Unknown" and r5.technology_code == "unknown"
    assert r6.status_code == "superseded" and r6.attrs["reapply_new_ref"] == "1"


def test_repd_masks_postcode_below_1mw(tmp_path):
    p = write_repd(tmp_path / "r.csv", [repd_row(**{"Ref ID": "7", "Site Name": "S small", "Technology Type": "Wind Onshore", "Installed Capacity (MWelec)": "0.4", "Post Code": "AB1 2CD"}),
                                          repd_row(**{"Ref ID": "8", "Site Name": "S large", "Technology Type": "Wind Onshore", "Installed Capacity (MWelec)": "12", "Post Code": "AB1 2CD"})])
    small, large = run(RepdAdapter(), p)
    assert small.postcode_public is None and large.postcode_public == "AB1 2CD"


# ---------------------------------------------------------------------------------------------------------- NESO
def test_neso_plant_types_hybrid_and_exclusions(tmp_path):
    p = tmp_path / "tec.csv"
    cols = ["Project Name", "Customer Name", "Connection Site", "Stage", "MW Connected", "MW Increase / Decrease", "Cumulative Total Capacity (MW)", "MW Effective From", "Project Status", "Agreement Type", "HOST TO", "Plant Type", "Project ID", "Project Number", "Gate"]
    rows = [
        ["Synthetic Wind+BESS", "ACME", "Test 132kV", "", "0.00", "138.00", "138.00", "2031-04-30", "Scoping", "Direct Connection", "SHET", "Energy Storage System;Wind Onshore", "a0l1", "PRO-1", "1"],
        ["Synthetic CCGT", "ACME", "Test", "", "10", "0", "10", "", "Built", "Embedded", "NGET", "CCGT (Combined Cycle Gas Turbine)", "a0l2", "PRO-2", ""],
        ["Synthetic Mixed", "ACME", "Test", "", "0", "5", "5", "", "Consents Approved", "Embedded", "NGET", "Energy Storage System;Nuclear", "a0l3", "PRO-3", ""],
        ["Synthetic Demand", "ACME", "Test", "", "0", "5", "5", "", "Scoping", "Embedded", "NGET", "Demand", "a0l4", "PRO-4", ""],
        ["Synthetic Solar+BESS", "ACME", "Test", "", "0", "50", "50", "", "Awaiting Consents", "Embedded", "SPT", "Energy Storage System;PV Array (Photo Voltaic/solar)", "a0l5", "PRO-5", "2"],
    ]
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(cols); w.writerows(rows)
    wind, ccgt, mixed, demand, solar = run(NesoRegisterAdapter("neso_tec", "x", True), p)
    assert wind.technology_code == "hybrid_wind_bess" and wind.excluded_reason is None and wind.status_code == "scoping" and wind.gate == "1"
    assert "no coordinates in source" in wind.qa_notes and wind.lat is None  # nothing placed without evidence
    assert ccgt.excluded_reason == "excluded:fossil_gas" and ccgt.technology_code is None
    assert mixed.excluded_reason and mixed.excluded_reason.startswith("mixed_with_non_renewable")  # BESS+nuclear must not inflate renewables
    assert demand.excluded_reason == "excluded:demand_or_reactive_only"
    assert solar.technology_code == "hybrid_solar_bess" and solar.status_code == "planning" and solar.capacity_basis.startswith("NESO cumulative")
    assert wind.ids["tec"] == "PRO-1"


# ---------------------------------------------------------------------------------------------------------- ECR
def _ecr_csv(path, cols, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(cols); w.writerows(rows)
    return path


SPEN_COLS = ["site_id", "town_city", "county", "country", "x_eastings_1_km", "y_northings_1_km", "licence_area", "energy_source_1", "energy_conversion_technology_1", "chp_cogeneration_yes_no",
             "energy_source_energy_conversion_technology_1_registered_capacity_kw", "connection_status", "already_connected_registered_capacity_kw", "maximum_export_capacity_kw", "date_connected",
             "last_updated", "unique_id"]


def test_spen_column_shift_is_realigned_only_with_exact_signature(tmp_path):
    good = ["S1", "Synthetictown", "Lanarkshire", "Scotland", "297000", "645000", "SP Distribution Ltd", "Wind", "Onshore wind turbines", "N", "500.0", "Connected", "500", "500", "2016-09-27", "2026-05-29 00:00:00", "SPEN_50kW_1"]
    i = SPEN_COLS.index("country")
    shifted = (good[:i] + ["ML11"] + good[i:])[: len(good)]  # a postcode district inserted before `country`; every later value moves right
    broken = good[:i] + ["???"] + ["not-a-country"] + good[i + 2:]  # damaged differently: must be quarantined, not repaired
    p = _ecr_csv(tmp_path / "spen.csv", SPEN_COLS, [good, shifted, broken])
    a = EcrAdapter("spen_ecr_50kw", dno="spen", dno_label="SP Energy Networks", host="x", dataset_id="x", band="50kw_1mw", landing="https://example.test")
    ok, repaired, rejected = run(a, p)
    assert ok.attrs.get("repaired_column_shift") is None
    assert repaired.attrs["repaired_column_shift"] is True and repaired.country == "Scotland" and repaired.status_code == "operational"
    assert repaired.capacity_mw == 0.5 and repaired.attrs["postcode_district"] == "ML11"  # kW → MW; shifted value preserved
    assert isinstance(rejected, Reject)


NGED_COLS = ["customer_name", "customer_site", "postcode", "country", "location(x-coordinate):_eastings_(where_data_is_held)", "location(y-coordinate):_northings_(where_data_is_held)", "licence_area", "energy_source_1",
             "Energy Conversion Technology 1", "energy_source_&_conversion_tech_1_reg_capacity_mw", "energy_source_2", "Energy Conversion Technology 2", "energy_source_&_conversion_tech_2_reg_capacity_mw",
             "storage_capacity_2(mwh)", "storage_duration_2(hours)", "connection_status", "already_connected_registered_capacity(mw)", "accepted_to_connect_registered_capacity(mw)", "lon", "lat", "local_authority", "last_updated"]


def test_nged_redacted_impossible_coords_privacy_and_hybrid(tmp_path):
    rows = [
        ["A Farm Ltd", "Worths Farm", "PE11 3EX", "United Kingdom", "521470", "316792", "NGED East Midlands", "Solar", "Photovoltaic", "0.15", "", "", "", "", "", "Connected", "0.15", "", "-0.2023", "52.7351", "South Holland", "06/08/2026"],
        ["Redacted Ltd", "Site", "", "United Kingdom", "--REDACTED--", "--REDACTED--", "NGED East Midlands", "Solar", "Photovoltaic", "2", "", "", "", "", "", "Connected", "2", "", "", "", "", "06/08/2026"],
        ["Odd Ltd", "Site", "", "United Kingdom", "3862265", "400000", "NGED", "Solar", "Photovoltaic", "3", "", "", "", "", "", "Connected", "3", "", "", "", "", "06/08/2026"],
        ["Hybrid Ltd", "Hybrid Site", "AB1 2CD", "United Kingdom", "425975", "281272", "NGED", "Solar", "Photovoltaic", "9.9", "Stored Energy (all stored energy irrespective of the original energy source)", "Storage - Electrochemical  (Batteries)", "49.9", "99.8", "2", "Accepted to connect", "", "59.8", "", "", "", "06/08/2026"],
    ]
    a = EcrAdapter("nged_ecr", dno="nged", dno_label="National Grid Electricity Distribution", host="x", dataset_id="x", band="mixed", landing="https://example.test", fetch_mode="ckan")
    small, redacted, odd, hybrid = run(a, _ecr_csv(tmp_path / "n.csv", NGED_COLS, rows))
    assert small.privacy_class == "sub_1mw_masked" and small.coord_accuracy == "grid_1km" and small.postcode_public is None  # <1 MW: masked to a 1 km square, no postcode
    assert (small.bng_e % 1000, small.bng_n % 1000) == (500, 500)
    assert redacted.lat is None and any("no usable coordinates" in n for n in redacted.qa_notes)  # '--REDACTED--' is not a location
    assert odd.lat is None and any("not plausible" in n for n in odd.qa_notes)
    assert hybrid.technology_code == "hybrid_solar_bess" and hybrid.status_code == "connection_agreed" and hybrid.privacy_class == "public"
    assert hybrid.storage_mwh == 99.8 and hybrid.storage_duration_h == 2 and hybrid.capacity_mw == 59.8
    comps = {c["technology_code"]: c["mw"] for c in hybrid.attrs["components"]}
    assert comps == {"solar_pv": 9.9, "bess": 49.9}  # component capacities kept apart (never summed into one technology)


def test_ecr_slot_technology_excludes_fossil_and_does_not_guess():
    assert slot_technology("Fossil - Gas", "Engine (combustion / reciprocating)") == (None, "excluded:fossil - gas")
    assert slot_technology("Biofuel - Landfill gas", "Engine (combustion / reciprocating)") == ("landfill_gas", None)
    assert slot_technology("Other", "Other") == ("unknown", None)


# ---------------------------------------------------------------------------------------------------------- CfD / Crown Estate / OSM
def test_cfd_workbook_leading_blank_column_offshore_osref_and_prices(tmp_path):
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(["Contracts for Difference Allocation Round 6 Results"]); ws.append(["(A) strike prices are in 2012 prices"]); ws.append([])
    ws.append([None, "Project Name", "Project Location", "Country, Region", "Applicant", "Technology Type", "Size (MW)", "Strike Price (£/MWh)", "Delivery Year ", "Target Commissioning Date", "No. of Phases", "Pot"])
    ws.append([None, "Synthetic Offshore Wind Farm", "TG210034", "England", "SYNTH OFFSHORE LTD", "Offshore Wind", 360, 54.23, "2027/28", dt.datetime(2027, 4, 1), 1, "Pot 3"])
    ws.append([None, "Synthetic Solar", "NT730745", "Scotland", "SYNTH SOLAR LTD", "Solar PV (>5MW)", 20, 50.07, "2026/27", dt.datetime(2027, 3, 1), 1, "Pot 1"])
    p = tmp_path / "cfd.xlsx"; wb.save(p)
    a = CfdAdapter()
    off, sol = run(a, p, Resource(url="https://example.test/ar6.xlsx", label="AR6", meta={"page": "https://example.test/page"}))
    assert off.technology_code == "wind_offshore" and off.lat is None and "onshore point" in off.coord_note and off.attrs["onshore_reference_bng"]  # not a project position
    assert sol.lat is not None and sol.coord_accuracy == "approximate" and sol.country == "Scotland"
    assert sol.status_code == "cfd_awarded" and sol.cfd_capacity_mw == 20 and sol.strike_price == 50.07 and "2012 prices" in sol.attrs["price_basis_note"]


def test_crown_estate_polygon_normalisation(tmp_path):
    fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"OBJECTID": 1, "Name_Prop": "Synthetic Bank", "Name_Ten": "Synthetic Offshore Ltd", "Wind_Round": "2", "Lease_Stat": "Lease - Marine", "Inf_Status": "Under Construction", "km2": 12.5},
              "geometry": {"type": "Polygon", "coordinates": [[[-3.6, 53.9], [-3.4, 53.9], [-3.4, 54.0], [-3.6, 54.0], [-3.6, 53.9]]]}}]}
    p = tmp_path / "tce.geojson"; p.write_text(json.dumps(fc))
    (r,) = run(CrownEstateAdapter(), p)
    assert r.entity_kind == "lease" and r.geom_kind == "lease_area" and r.status_code == "under_construction" and r.geom_wkt.startswith("POLYGON")
    assert r.coord_accuracy == "approximate" and "not a turbine position" in r.coord_note and r.site_area_ha == 1250


def test_osm_parsing_never_guesses_units(tmp_path):
    assert _power_mw("2.3 MW") == pytest.approx(2.3) and _power_mw("2300 kW") == pytest.approx(2.3) and _power_mw("2300") is None  # bare numbers are not guessed
    doc = {"elements": [{"type": "node", "id": 1, "lat": 55.68, "lon": -4.28, "tags": {"generator:source": "wind", "manufacturer": "Synthetic Co", "model": "SX1", "generator:output:electricity": "2.3 MW", "height:hub": "80"}},
                        {"type": "node", "id": 2, "lat": 10.0, "lon": 10.0, "tags": {"generator:source": "wind"}}]}
    p = tmp_path / "o.json"; p.write_text(json.dumps(doc))
    ok, bad = run(OsmOverpassAdapter(), p)
    assert ok.coord_accuracy == "open_source_mapped" and ok.attrs["manufacturer"] == "Synthetic Co" and ok.capacity_mw == 2.3 and ok.attrs["hub_height_m"] == 80.0
    assert isinstance(bad, Reject)
