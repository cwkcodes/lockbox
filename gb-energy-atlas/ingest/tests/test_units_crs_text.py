import datetime as dt

import pytest

from atlas_ingest import crs, units
from atlas_ingest.taxonomy import hybrid_code, map_repd_status, map_repd_technology
from atlas_ingest.textnorm import core_name, norm_name, norm_org, variant_signature


def test_parse_number_handles_sentinels_and_formats():
    assert units.parse_number("1,234.5") == 1234.5
    assert units.parse_number(" 12 ") == 12
    for s in ["", " ", "n/a", "Data Not Available", "data not applicable", "--REDACTED--", "abc", None]:
        assert units.parse_number(s) is None


def test_unknown_is_a_real_category_not_a_null_sentinel():
    assert units.clean_text("Unknown") == "Unknown"  # REPD technology 'Unknown' must keep its wording


def test_unit_conversions_keep_power_and_energy_apart():
    assert units.power_to_mw(500, "kw") == 0.5
    assert units.power_to_mw(2, "GW") == 2000
    assert units.energy_to_mwh(1500, "kWh") == 1.5
    assert units.area_to_ha(25_000, "m2") == 2.5
    assert units.length_to_m(1.2, "km") == 1200


def test_dates_reject_excel_artefacts():
    assert units.parse_date("16/01/2026") == dt.date(2026, 1, 16)
    assert units.parse_date("2026-08-28 00:00:00") == dt.date(2026, 8, 28)
    assert units.parse_date("02/01/1900") is None  # Excel serial artefact (REPD 'Offshore Wind Round')


def test_duration_only_when_both_known():
    assert units.duration_hours(50, 100) == 2
    assert units.duration_hours(None, 100) is None
    assert units.duration_hours(0, 100) is None


def test_bng_round_trip_and_known_point():
    lat, lon = crs.bng_to_wgs84(256800, 645435)  # a site near Eaglesham Moor, Scotland
    assert 55.6 < lat < 55.75 and -4.4 < lon < -4.2
    e, n = crs.wgs84_to_bng(lat, lon)
    assert abs(e - 256800) < 1 and abs(n - 645435) < 1


def test_far_offshore_bng_is_valid_but_nonsense_is_rejected():
    assert not crs.bng_in_formal_extent(708047, 312194)  # beyond the 700 km square …
    la, lo = crs.bng_to_wgs84(708047, 312194)
    assert crs.lat_lon_plausible_uk(la, lo)  # … yet a real far-offshore UK position
    assert not crs.bng_numeric_ok(3862265, 400000)  # not metres on the grid
    la, lo = crs.bng_to_wgs84(966043, 310748)
    assert not crs.lat_lon_plausible_uk(la, lo)  # lands in the Netherlands/Germany


def test_snap_to_1km_grid_centre():
    assert crs.snap_to_grid(425975, 581272, 1000) == (425500, 581500)


def test_gridref_conversion():
    assert crs.gridref_to_bng("TQ3080") == (530000, 180000, 1000)
    assert crs.gridref_to_bng("NT730745") == (373000, 674500, 100)
    assert crs.gridref_to_bng("SU 387 148")[:2] == (438700, 114800)
    assert crs.gridref_to_bng("IO1234") is None  # no letter I in the grid alphabet


def test_name_normalisation_and_org_variants():
    assert norm_name("Aberthaw Power Station — Biomass & Co.") == "aberthaw power station biomass and co"
    assert norm_org("SSE Renewables Limited") == norm_org("sse renewables ltd.") == "sse renewables"
    assert core_name("Whitelee Wind Farm") == "whitelee"
    assert core_name("Hornsea 1 (East)") == core_name("Hornsea 1")  # parenthetical sub-area is not identity
    assert variant_signature("Norfolk Vanguard East") != variant_signature("Norfolk Vanguard West")


@pytest.mark.parametrize("raw,code", [("Wind Onshore", "wind_onshore"), ("Battery", "bess"), ("Unknown", "unknown"), ("EfW Incineration", "energy_from_waste"), ("Pumped Storage Hydroelectricity", "pumped_hydro")])
def test_repd_technology_mapping(raw, code):
    assert map_repd_technology(raw) == code


@pytest.mark.parametrize("raw,code", [("Awaiting Construction", "awaiting_construction"), ("Revised", "superseded"), ("Abandoned", "cancelled"), ("No Application Required", "unknown"), ("Appeal Lodged", "planning")])
def test_repd_status_mapping_never_invents_progress(raw, code):
    assert map_repd_status(raw) == code


def test_hybrid_only_from_explicit_components():
    assert hybrid_code({"solar_pv", "bess"}) == "hybrid_solar_bess"
    assert hybrid_code({"wind_onshore", "solar_pv", "bess"}) == "hybrid_wind_solar_bess"
    assert hybrid_code({"hydro", "bess"}) == "hybrid_other"
