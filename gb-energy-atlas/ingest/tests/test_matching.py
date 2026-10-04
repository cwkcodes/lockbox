from atlas_ingest.matching import Cand, name_similarity, score, tech_keys
from atlas_ingest.crs import gridref_to_bng


def C(**kw):
    kw.setdefault("techs", tech_keys(["wind_onshore"]))
    return Cand(key=kw.pop("key", "x"), **kw)


def test_same_site_same_name_links():
    a = C(name="Achairn Wind Farm", capacity_mw=18, e=330000, n=950000, accuracy="site_reference", year=2012)
    b = C(name="Achairn Windfarm", capacity_mw=18.0, e=330100, n=950050, accuracy="site_reference", year=2012)
    r = score(a, b)
    assert r.decision == "link" and r.total > 0.9


def test_name_alone_never_links():
    # identical names, but nothing else known -> not enough evidence to link
    a = C(name="Hill Top Wind Farm")
    b = C(name="Hill Top Wind Farm")
    assert score(a, b).decision != "link"


def test_same_name_far_apart_and_different_capacity_not_linked():
    a = C(name="Glen Wind Farm", capacity_mw=50, e=300000, n=800000, accuracy="site_reference")
    b = C(name="Glen Wind Farm", capacity_mw=5, e=500000, n=300000, accuracy="site_reference")
    assert score(a, b).decision != "link"


def test_phase_trap_extension_not_auto_linked():
    a = C(name="Whitelee Wind Farm", capacity_mw=322, e=256800, n=645435, accuracy="site_reference")
    b = C(name="Whitelee Wind Farm Extension", capacity_mw=217, e=256900, n=645500, accuracy="site_reference")
    r = score(a, b)
    assert r.phase_conflict and r.decision != "link"


def test_subset_names_are_not_identical():
    s, _ = name_similarity("Glen", "Glen Kinglass")
    assert s is not None and s < 0.9


def test_technology_veto():
    a = C(name="Meadow Farm", techs=tech_keys(["solar_pv"]), capacity_mw=10, e=1, n=1, accuracy="site_reference")
    b = C(name="Meadow Farm", techs=tech_keys(["bess"]), capacity_mw=10, e=1, n=1, accuracy="site_reference")
    assert score(a, b).decision == "reject"


def test_hybrid_matches_component_technology():
    ecr = C(name="Broadway House", techs=tech_keys(["hybrid_solar_bess"]), capacity_mw=59.8, cap_by_tech={"solar": 9.9, "bess": 49.9},
            e=425975, n=581272, accuracy="site_reference")
    repd = C(name="Broadway House PV", techs=tech_keys(["solar_pv"]), capacity_mw=9.9, e=425990, n=581260, accuracy="site_reference")
    assert score(repd, ecr).decision == "link"


def test_planning_reference_is_hard_evidence():
    a = C(name="Mill Farm Solar", techs=tech_keys(["solar_pv"]), planning_refs=frozenset({"20/01234/FUL".replace("/", "")}), capacity_mw=20)
    b = C(name="Mill Farm Solar Park", techs=tech_keys(["solar_pv"]), planning_refs=frozenset({"2001234FUL"}), capacity_mw=20)
    assert score(a, b).decision == "link"


def test_offshore_approximate_point_has_no_spatial_evidence():
    a = C(name="Hornsea Project Four", techs=tech_keys(["wind_offshore"]), capacity_mw=2400, e=626000, n=426000, accuracy="site_reference", offshore=True)
    b = C(name="Hornsea Project Four Offshore Wind Farm", techs=tech_keys(["wind_offshore"]), capacity_mw=2400, e=500000, n=400000, accuracy="approximate", offshore=True)
    r = score(a, b)
    assert r.components["spatial"] is None


def test_os_gridref_conversion_known_points():
    # TQ 30 80 is in central London: E 530000 N 180000
    assert gridref_to_bng("TQ3080") == (530000, 180000, 1000)
    # NT 730 745 -> E 373000 N 674500 (100 m)
    assert gridref_to_bng("NT730745") == (373000, 674500, 100)
    assert gridref_to_bng("garbage") is None
    assert gridref_to_bng("SU 387 148")[:2] == (438700, 114800)


def test_numbered_siblings_are_not_the_same_project():
    a = C(name="Hornsea 2 - Optimus and Breesea", techs=tech_keys(["wind_offshore"]), capacity_mw=1320, e=632326, n=457349, accuracy="site_reference")
    b = C(name="Hornsea Project Three", techs=tech_keys(["wind_offshore"]), capacity_mw=2955, e=626000, n=426000, accuracy="site_reference")
    assert score(a, b).decision != "link"


def test_east_west_siblings_not_linked():
    east = C(name="Norfolk Vanguard East", techs=tech_keys(["wind_offshore"]), capacity_mw=1380, e=708047, n=312194, accuracy="site_reference")
    west = C(name="Norfolk Vanguard West", techs=tech_keys(["wind_offshore"]), capacity_mw=1380, e=708047, n=312194, accuracy="site_reference")
    r = score(east, west)
    assert r.phase_conflict and r.decision != "link"


def test_number_words_equal_digits():
    from atlas_ingest.textnorm import variant_signature
    assert variant_signature("Hornsea Project Four Offshore Wind Farm") == variant_signature("Hornsea 4")
    assert variant_signature("Whitelee") != variant_signature("Whitelee Extension")


def test_mismatching_operator_is_not_negative_evidence():
    a = C(name="Pentland Floating Offshore Wind Farm", techs=tech_keys(["wind_offshore"]), capacity_mw=100, orgs=("Highland Wind Limited / Copenhagen Infrastructure Partners / Eurus Energy",), offshore=True)
    b = C(name="Pentland Floating Offshore Wind Farm", techs=tech_keys(["wind_offshore"]), capacity_mw=92.5, orgs=("HIGHLAND WIND LIMITED",), offshore=True)
    r = score(a, b)
    assert r.components["org"] == 1.0 and r.decision == "link"
    c = C(name="Pentland Floating Offshore Wind Farm", techs=tech_keys(["wind_offshore"]), capacity_mw=92.5, orgs=("Some Other Company Ltd",), offshore=True)
    assert score(a, c).components["org"] is None  # no penalty


def test_point_inside_lease_polygon_is_strong_spatial_evidence():
    from shapely.geometry import box
    lease = C(name="Walney 2", techs=tech_keys(["wind_offshore"]), e=300000, n=500000, accuracy="approximate", offshore=True, poly=box(295000, 495000, 305000, 505000))
    inside = C(name="Walney 2", techs=tech_keys(["wind_offshore"]), capacity_mw=184, e=301000, n=502000, accuracy="site_reference", offshore=True)
    far = C(name="Walney 2", techs=tech_keys(["wind_offshore"]), capacity_mw=184, e=380000, n=560000, accuracy="site_reference", offshore=True)
    assert score(lease, inside).components["spatial"] == 1.0 and score(lease, inside).decision == "link"
    assert score(lease, far).components["spatial"] is None  # offshore: distance is not evidence against


def test_sibling_lease_is_not_linked_by_containment_alone():
    from shapely.geometry import box
    lease = C(name="Walney 2", techs=tech_keys(["wind_offshore"]), e=300000, n=500000, accuracy="approximate", offshore=True, poly=box(295000, 495000, 305000, 505000))
    sibling = C(name="Walney 1", techs=tech_keys(["wind_offshore"]), capacity_mw=184, e=301000, n=502000, accuracy="site_reference", offshore=True)
    assert score(lease, sibling).decision != "link"


def test_parenthetical_aliases_do_not_create_variants():
    from atlas_ingest.textnorm import variant_signature, core_name
    assert variant_signature("Dogger Bank C (was Teesside A)") == variant_signature("Dogger Bank C")
    assert core_name("Hornsea 1 (East)") == core_name("Hornsea 1")
    assert variant_signature("Dogger Bank A") != variant_signature("Dogger Bank C (was Teesside A)")
