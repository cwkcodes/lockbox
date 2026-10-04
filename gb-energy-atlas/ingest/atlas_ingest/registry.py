"""Source registry. Every source we investigated is listed – including those we could not ingest –
so the Data page can state exactly what is current, restricted, unavailable or needs manual review."""
from __future__ import annotations

OGL = ("Open Government Licence v3.0", "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
       "Contains public sector information licensed under the Open Government Licence v3.0.")
NESO = ("NESO Open Data Licence", "https://www.neso.energy/data-portal/neso-open-licence",
        "Supported by National Energy SO Open Data")  # exact attribution text required by the licence (read 4 Oct 2026)
TCE_ATTR = "Contains data provided by The Crown Estate that is protected by copyright and database rights."

S = []


def add(**kw):
    kw.setdefault("redistribution", "permitted")
    kw.setdefault("export_policy", "include")
    kw.setdefault("access_status", "never_run")
    if kw["source_key"].endswith(("_ecr_1mw", "_ecr_lt1mw", "_ecr_50kw", "nged_ecr")) and "licence_name" not in kw:
        # Licence text not verified from the primary source → conservative defaults (see SOURCE_CATALOGUE §3).
        kw.update(licence_name="Dataset licence not verified (see landing page)", redistribution="unknown", export_policy="exclude",
                  export_policy_reason="Licence terms for this network's ECR were not verified from the primary text; excluded from bulk export until a licence review is recorded.")
    S.append(kw)


add(source_key="repd", organisation="DESNZ", dataset="Renewable Energy Planning Database (REPD)", tier="A",
    source_type="government_dataset", format="CSV",
    landing_url="https://www.gov.uk/government/publications/renewable-energy-planning-database-quarterly-extract",
    endpoint_url="https://www.gov.uk/api/content/government/publications/renewable-energy-planning-database-quarterly-extract",
    update_frequency="Quarterly", adapter="repd", licence_name=OGL[0], licence_url=OGL[1], attribution=OGL[2],
    known_limitations="REPD tracks projects over 150 kW; the minimum threshold was 1 MW until 2021, so sub-1 MW projects that went through planning before 2021 may be absent. Absence from REPD does not mean a project does not exist. "
    "Operator field means 'operator or applicant'. Coordinates are a site reference point, not turbine positions. "
    "Offshore Wind Round contains Excel-corrupted dates in the source file (mapped to rounds, original kept). "
    "Northern Ireland rows are retained but flagged out of GB scope.")
add(source_key="neso_tec", organisation="NESO", dataset="Transmission Entry Capacity (TEC) Register", tier="A",
    source_type="network_register", format="CSV", landing_url="https://www.neso.energy/data-portal/transmission-entry-capacity-tec-register",
    endpoint_url="https://api.neso.energy/api/3/action/package_show?id=transmission-entry-capacity-tec-register",
    update_frequency="Twice weekly", adapter="neso_tec", licence_name=NESO[0], licence_url=NESO[1], attribution=NESO[2],
    known_limitations="No coordinates. Capacity is cumulative contracted TEC (may include not-yet-connected capacity), not installed capacity. "
    "Includes non-renewable plant (gas, nuclear), demand and reactive compensation which are retained in the normalised layer but not promoted.")
add(source_key="neso_embedded", organisation="NESO", dataset="Embedded Register (Scotland)", tier="A",
    source_type="network_register", format="CSV", landing_url="https://www.neso.energy/data-portal/embedded-register",
    endpoint_url="https://api.neso.energy/api/3/action/package_show?id=embedded-register",
    update_frequency="Twice weekly", adapter="neso_embedded", licence_name=NESO[0], licence_url=NESO[1], attribution=NESO[2],
    known_limitations="Scottish embedded generation only; no coordinates.")

_ECR_NOTE = ("Embedded Capacity Register: connected and accepted-to-connect generation/storage at distribution level. "
             "Capacity is registered capacity (not necessarily installed). Rows below 1 MW are privacy-masked in the public layer.")
add(source_key="npg_ecr_1mw", organisation="Northern Powergrid", dataset="Embedded Capacity Register 1MW and over", tier="A",
    source_type="network_register", format="CSV (Opendatasoft export)",
    landing_url="https://northernpowergrid.opendatasoft.com/explore/dataset/embedded-capacity-register/",
    endpoint_url="https://northernpowergrid.opendatasoft.com/api/explore/v2.1/catalog/datasets/embedded-capacity-register",
    update_frequency="Monthly", adapter="ecr_ods:npg", known_limitations=_ECR_NOTE)
add(source_key="npg_ecr_lt1mw", organisation="Northern Powergrid", dataset="Embedded Capacity Register under 1MW", tier="A",
    source_type="network_register", format="CSV (Opendatasoft export)",
    landing_url="https://northernpowergrid.opendatasoft.com/explore/dataset/embedded-capacity-register-part-2/",
    endpoint_url="https://northernpowergrid.opendatasoft.com/api/explore/v2.1/catalog/datasets/embedded-capacity-register-part-2",
    update_frequency="Monthly", adapter="ecr_ods:npg", known_limitations=_ECR_NOTE)
add(source_key="spen_ecr_50kw", organisation="SP Energy Networks", dataset="Embedded Capacity Register 50kW–1MW", tier="A",
    source_type="network_register", format="CSV (Opendatasoft export)",
    landing_url="https://spenergynetworks.opendatasoft.com/explore/dataset/embedded-capacity-register-50kv-1mw/",
    endpoint_url="https://spenergynetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets/embedded-capacity-register-50kv-1mw",
    update_frequency="Monthly", adapter="ecr_ods:spen",
    known_limitations=_ECR_NOTE + " Locations are published at 1 km grid resolution; units are kW; many rows in the source file are column-shifted and are quarantined.")
add(source_key="spen_ecr_1mw", organisation="SP Energy Networks", dataset="Embedded Capacity Register >1MW", tier="A",
    source_type="network_register", format="CSV (Opendatasoft export)",
    landing_url="https://spenergynetworks.opendatasoft.com/explore/dataset/embedded-capacity-register/",
    endpoint_url="https://spenergynetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets/embedded-capacity-register",
    update_frequency="Monthly", adapter="ecr_ods:spen", known_limitations=_ECR_NOTE + " Anonymous access returns ForbiddenAccess / header-only export; set ODS_API_KEY_SPEN.")
add(source_key="ukpn_ecr_1mw", organisation="UK Power Networks", dataset="Embedded Capacity Register 2 – 1MW and above", tier="A",
    source_type="network_register", format="CSV (Opendatasoft export)",
    landing_url="https://ukpowernetworks.opendatasoft.com/explore/dataset/ukpn-embedded-capacity-register/",
    endpoint_url="https://ukpowernetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets/ukpn-embedded-capacity-register",
    update_frequency="Monthly", adapter="ecr_ods:ukpn", known_limitations=_ECR_NOTE + " Anonymous access returns ForbiddenAccess / header-only export; set ODS_API_KEY_UKPN.")
add(source_key="ukpn_ecr_lt1mw", organisation="UK Power Networks", dataset="Embedded Capacity Register 1 – under 1MW", tier="A",
    source_type="network_register", format="CSV (Opendatasoft export)",
    landing_url="https://ukpowernetworks.opendatasoft.com/explore/dataset/ukpn-embedded-capacity-register-1-under-1mw/",
    endpoint_url="https://ukpowernetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets/ukpn-embedded-capacity-register-1-under-1mw",
    update_frequency="Monthly", adapter="ecr_ods:ukpn", known_limitations=_ECR_NOTE + " Anonymous access restricted; set ODS_API_KEY_UKPN.")
add(source_key="enwl_ecr_1mw", organisation="Electricity North West", dataset="Embedded Capacity Register 2 – 1MW & above", tier="A",
    source_type="network_register", format="CSV (Opendatasoft export)",
    landing_url="https://electricitynorthwest.opendatasoft.com/explore/dataset/enwl-embedded-capacity-register-2-1mw-and-above/",
    endpoint_url="https://electricitynorthwest.opendatasoft.com/api/explore/v2.1/catalog/datasets/enwl-embedded-capacity-register-2-1mw-and-above",
    update_frequency="Monthly", adapter="ecr_ods:enwl", known_limitations=_ECR_NOTE + " Anonymous access restricted; set ODS_API_KEY_ENWL.")
add(source_key="enwl_ecr_lt1mw", organisation="Electricity North West", dataset="Embedded Capacity Register 1 – under 1MW", tier="A",
    source_type="network_register", format="CSV (Opendatasoft export)",
    landing_url="https://electricitynorthwest.opendatasoft.com/explore/dataset/enwl-embedded-capacity-register-1-under-1mw/",
    endpoint_url="https://electricitynorthwest.opendatasoft.com/api/explore/v2.1/catalog/datasets/enwl-embedded-capacity-register-1-under-1mw",
    update_frequency="Monthly", adapter="ecr_ods:enwl", known_limitations=_ECR_NOTE + " Anonymous access restricted; set ODS_API_KEY_ENWL.")
add(source_key="nged_ecr", organisation="National Grid Electricity Distribution", dataset="Embedded Capacity Register", tier="A",
    source_type="network_register", format="CSV", landing_url="https://connecteddata.nationalgrid.co.uk/dataset/embedded-capacity-register",
    endpoint_url="https://connecteddata.nationalgrid.co.uk/api/3/action/package_show?id=embedded-capacity-register",
    update_frequency="Monthly", adapter="ecr_ckan:nged", licence_name="NGED Shared Data Licence",
    licence_url="https://connecteddata.nationalgrid.co.uk/licence", attribution="Contains data from National Grid Electricity Distribution's Embedded Capacity Register.",
    redistribution="unknown", export_policy="exclude",
    export_policy_reason="The licence page named on the dataset could not be read from the primary text (HTTP 520 on 4 Oct 2026); a secondary description says it is OGL-derived. Excluded from bulk export until the terms are verified.",
    known_limitations=_ECR_NOTE + " Some coordinates are '--REDACTED--' and some Eastings are outside the BNG grid; such rows are left unplaced.")
add(source_key="ssen_ecr", organisation="SSEN Distribution", dataset="Embedded Capacity Register", tier="A",
    source_type="network_register", format="CSV", landing_url="https://data-api.ssen.co.uk/dataset/embedded_capacity_register",
    update_frequency="Monthly", adapter="unavailable:ssen_ecr", access_status="source_unavailable",
    access_notes="data.ssen.co.uk / data-api.ssen.co.uk return HTTP 403 (Cloudflare) to programmatic requests from the build environment. Not circumvented.",
    known_limitations="Largest DNO gap for northern Scotland: SSEN-connected generation appears only where it also appears in REPD or the NESO Embedded Register.")
add(source_key="crown_estate_wind_sites", organisation="The Crown Estate", dataset="Wind Site Agreements (England, Wales & NI)", tier="A",
    source_type="open_geodata", format="ArcGIS FeatureServer (polygons)",
    landing_url="https://opendata-thecrownestate.opendata.arcgis.com/datasets/22a1be6fb0c5416e9369f97743f387b1",
    endpoint_url="https://services2.arcgis.com/PZklK9Q45mfMFuZs/arcgis/rest/services/WindSite_EngWalNI_TheCrownEstate/FeatureServer/0",
    update_frequency="Irregular", adapter="crown_estate", licence_name="The Crown Estate Open Data Licence (GIS) v1.1",
    licence_url="https://opendata-thecrownestate.opendata.arcgis.com/", attribution=TCE_ATTR, redistribution="conditional",
    commercial_use_notes="§4.3(d) no reproduction in whole/substantial part on a site providing the same or similar services as the Crown Estate portal; "
    "§4.3(e) ordinary course of business only; §4.3(f) no resale or direct commercial gain from supplying the data to a third party.",
    export_policy="exclude",
    export_policy_reason="Crown Estate GIS licence v1.1 restricts onward supply for commercial gain; geometry export is disabled until a licence review "
    "is recorded (set TCE_EXPORT_REVIEWED=true). Display on the map with mandatory attribution is unaffected.",
    known_limitations="Lease agreement polygons, not turbine layouts or consented array boundaries. England, Wales and NI only (Scotland is Crown Estate Scotland).")
add(source_key="cfd_results", organisation="DESNZ", dataset="Contracts for Difference allocation round results (successful applicants)", tier="A",
    source_type="government_dataset", format="XLSX", landing_url="https://www.gov.uk/government/collections/contracts-for-difference-cfd-allocation-round-7",
    endpoint_url="https://www.gov.uk/api/content/government/publications/", update_frequency="Per allocation round", adapter="cfd_results",
    licence_name=OGL[0], licence_url=OGL[1], attribution=OGL[2],
    known_limitations="Allocation outcomes, not the LCCC contract register: contracts may later be terminated, re-sized or re-named. Capacity is contracted capacity, not installed capacity.")
add(source_key="ons_lad", organisation="Office for National Statistics", dataset="Local Authority Districts (Dec 2025) boundaries – BGC", tier="A",
    source_type="open_geodata", format="ArcGIS FeatureServer (polygons)", landing_url="https://geoportal.statistics.gov.uk/",
    endpoint_url="https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/Local_Authority_Districts_DEC_2025_Boundaries_UK_BGC/FeatureServer/0",
    update_frequency="Annual", adapter="ons_lad", licence_name=OGL[0], licence_url=OGL[1],
    attribution="Source: Office for National Statistics licensed under the Open Government Licence v3.0. Contains OS data © Crown copyright and database right.",
    known_limitations="Context layer used to DERIVE local authority by point-in-polygon (generalised boundaries, so coastal points can be mis-assigned). Offshore assets get no local authority.")

# ---- investigated, not ingestible from the build environment ----
add(source_key="ofgem_rer", organisation="Ofgem", dataset="Renewable Electricity Register (RO / REGO / FIT public reports)", tier="A",
    source_type="regulator_register", format="portal / SharePoint", landing_url="https://www.ofgem.gov.uk/environmental-programmes/renewable-electricity-register",
    update_frequency="Twice weekly (Tue/Fri)", adapter="unavailable:ofgem_rer", access_status="manual_review_required",
    access_notes="dataportal.ofgem.gov.uk, renewablesandchp.ofgem.gov.uk, dp.ofgem.gov.uk and data.ofgem.gov.uk are denied by the egress gateway; "
    "www.ofgem.gov.uk publishes only RoC totals. Station-level RER reports are distributed via SharePoint on request (renewable.enquiry@ofgem.gov.uk).",
    known_limitations="RO/REGO/FIT accreditation (and accredited capacity, which can differ from physical capacity) is not available station-by-station; only REPD's RO banding / FiT tariff columns are shown.")
add(source_key="scottish_energy_consents", organisation="Scottish Government – Energy Consents Unit", dataset="Energy Consents applications register", tier="A",
    source_type="planning_register", format="HTML application", landing_url="https://www.energyconsents.scot/", adapter="unavailable:scottish_energy_consents",
    access_status="manual_review_required", access_notes="No bulk export or API discovered; HTML-only ASP.NET search. Link-out only.",
    known_limitations="ECU references, turbine envelopes and layouts for S36 schemes need manual or document-level extraction.")
add(source_key="pins_nsip", organisation="Planning Inspectorate", dataset="National Infrastructure Planning register (NSIP / DCO)", tier="A",
    source_type="planning_register", format="HTML", landing_url="https://national-infrastructure-consenting.planninginspectorate.gov.uk/", adapter="unavailable:pins_nsip",
    access_status="manual_review_required", access_notes="robots.txt lists AI crawlers (including Claude user-agents) as disallowed and sets a 10 s crawl delay. Not scraped.")
add(source_key="welsh_infrastructure", organisation="Welsh Government / Planning & Environment Decisions Wales", dataset="DNS and SIP registers", tier="A",
    source_type="planning_register", format="HTML", landing_url="https://www.gov.wales/significant-infrastructure-projects", adapter="unavailable:welsh_infrastructure",
    access_status="source_unavailable", access_notes="gov.wales returns HTTP 403 and dnh.gov.wales is unreachable from the build environment.")
add(source_key="lccc_cfd", organisation="Low Carbon Contracts Company", dataset="CfD contract register / data portal", tier="A",
    source_type="regulator_register", format="portal", landing_url="https://www.lowcarboncontracts.uk/", adapter="unavailable:lccc_cfd",
    access_status="source_unavailable", access_notes="lowcarboncontracts.uk returns HTTP 403 to programmatic requests. GOV.UK round results are used instead (no strike-price indexation/termination data).")
add(source_key="crown_estate_scotland", organisation="Crown Estate Scotland", dataset="Offshore wind / marine leasing spatial data", tier="A",
    source_type="open_geodata", format="ArcGIS", landing_url="https://www.crownestatescotland.com/", adapter="unavailable:crown_estate_scotland",
    access_status="restricted", access_notes="Anonymous ArcGIS hub search returned HTTP 401. Scottish offshore leases are therefore absent from the build.")
add(source_key="osm_overpass", organisation="OpenStreetMap contributors", dataset="Wind turbines / solar / BESS / substations (Overpass)", tier="E",
    source_type="open_geodata", format="Overpass JSON", landing_url="https://overpass-api.de/", adapter="osm_overpass",
    licence_name="Open Database Licence (ODbL) 1.0", licence_url="https://www.openstreetmap.org/copyright",
    attribution="© OpenStreetMap contributors (ODbL)", redistribution="conditional",
    commercial_use_notes="ODbL share-alike and attribution apply to derivative databases.", access_status="source_unavailable",
    access_notes="overpass-api.de and mirrors are blocked from the build environment; the maps.mail.ru mirror returned a runtime error; the OSM-France UK extract is disallowed by robots.txt (Disallow: /*.pbf$). Set OVERPASS_URL to an endpoint you are permitted to use.",
    known_limitations="Supplementary spatial evidence only; never overrides authoritative planning coordinates. No individual-turbine positions are present until this adapter runs.")


def seed(conn) -> None:
    cols = ["source_key", "organisation", "dataset", "landing_url", "endpoint_url", "format", "tier", "source_type",
            "update_frequency", "adapter", "licence_name", "licence_url", "attribution", "redistribution",
            "commercial_use_notes", "export_policy", "export_policy_reason", "access_status", "access_notes", "known_limitations"]
    for s in S:
        vals = [s.get(c) for c in cols]
        # access_status / access_notes describe what actually happened when the source was last run, so re-seeding
        # (which every CLI call does) must not overwrite them once the source has been run.
        updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols[1:] if c not in ("access_status", "access_notes"))
        conn.execute(
            f"INSERT INTO ops.source_registry ({', '.join(cols)}) VALUES ({', '.join(['%s']*len(cols))}) "
            f"ON CONFLICT (source_key) DO UPDATE SET {updates}, "
            f"access_notes = CASE WHEN ops.source_registry.access_status = 'never_run' OR ops.source_registry.access_notes IS NULL "
            f"THEN EXCLUDED.access_notes ELSE ops.source_registry.access_notes END, "
            f"access_status = CASE WHEN ops.source_registry.access_status = 'never_run' "
            f"THEN EXCLUDED.access_status ELSE ops.source_registry.access_status END",
            vals,
        )
