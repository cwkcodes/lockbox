"""Adapter registry: source_key -> adapter instance."""
from __future__ import annotations

from .base import Adapter


def all_adapters() -> dict[str, Adapter]:
    from .cfd import CfdAdapter
    from .crown_estate import CrownEstateAdapter
    from .ecr import EcrAdapter
    from .neso import NesoRegisterAdapter
    from .ons_lad import OnsLadAdapter
    from .osm import OsmOverpassAdapter
    from .probes import ProbeAdapter
    from .repd import RepdAdapter

    adapters: list[Adapter] = [
        RepdAdapter(),
        CrownEstateAdapter(),
        CfdAdapter(),
        OnsLadAdapter(),
        OsmOverpassAdapter(),
        ProbeAdapter("ssen_ecr", "https://data-api.ssen.co.uk/dataset/embedded_capacity_register", "SSEN ECR portal"),
        ProbeAdapter("ofgem_rer", "https://dataportal.ofgem.gov.uk/", "Ofgem RER station-level reports"),
        ProbeAdapter("scottish_energy_consents", "https://www.energyconsents.scot/Register.aspx", "ECU register is an HTML application; no bulk export"),
        ProbeAdapter("pins_nsip", "https://national-infrastructure-consenting.planninginspectorate.gov.uk/project-search", "NSIP register (robots.txt disallows AI crawlers)"),
        ProbeAdapter("welsh_infrastructure", "https://www.gov.wales/significant-infrastructure-projects", "Welsh DNS/SIP registers"),
        ProbeAdapter("lccc_cfd", "https://www.lowcarboncontracts.uk/", "LCCC CfD register"),
        ProbeAdapter("crown_estate_scotland", "https://opendata-crownestatescotland.opendata.arcgis.com/api/search/v1/collections/all/items?q=wind", "Crown Estate Scotland open data"),
        NesoRegisterAdapter("neso_tec", "transmission-entry-capacity-tec-register", True),
        NesoRegisterAdapter("neso_embedded", "embedded-register", False),
        EcrAdapter("npg_ecr_1mw", dno="npg", dno_label="Northern Powergrid", host="northernpowergrid.opendatasoft.com",
                   dataset_id="embedded-capacity-register", band="1mw",
                   landing="https://northernpowergrid.opendatasoft.com/explore/dataset/embedded-capacity-register/"),
        EcrAdapter("npg_ecr_lt1mw", dno="npg", dno_label="Northern Powergrid", host="northernpowergrid.opendatasoft.com",
                   dataset_id="embedded-capacity-register-part-2", band="lt1mw",
                   landing="https://northernpowergrid.opendatasoft.com/explore/dataset/embedded-capacity-register-part-2/"),
        EcrAdapter("spen_ecr_50kw", dno="spen", dno_label="SP Energy Networks", host="spenergynetworks.opendatasoft.com",
                   dataset_id="embedded-capacity-register-50kv-1mw", band="50kw_1mw",
                   landing="https://spenergynetworks.opendatasoft.com/explore/dataset/embedded-capacity-register-50kv-1mw/"),
        EcrAdapter("spen_ecr_1mw", dno="spen", dno_label="SP Energy Networks", host="spenergynetworks.opendatasoft.com",
                   dataset_id="embedded-capacity-register", band="1mw",
                   landing="https://spenergynetworks.opendatasoft.com/explore/dataset/embedded-capacity-register/"),
        EcrAdapter("ukpn_ecr_1mw", dno="ukpn", dno_label="UK Power Networks", host="ukpowernetworks.opendatasoft.com",
                   dataset_id="ukpn-embedded-capacity-register", band="1mw",
                   landing="https://ukpowernetworks.opendatasoft.com/explore/dataset/ukpn-embedded-capacity-register/"),
        EcrAdapter("ukpn_ecr_lt1mw", dno="ukpn", dno_label="UK Power Networks", host="ukpowernetworks.opendatasoft.com",
                   dataset_id="ukpn-embedded-capacity-register-1-under-1mw", band="lt1mw",
                   landing="https://ukpowernetworks.opendatasoft.com/explore/dataset/ukpn-embedded-capacity-register-1-under-1mw/"),
        EcrAdapter("enwl_ecr_1mw", dno="enwl", dno_label="Electricity North West", host="electricitynorthwest.opendatasoft.com",
                   dataset_id="enwl-embedded-capacity-register-2-1mw-and-above", band="1mw",
                   landing="https://electricitynorthwest.opendatasoft.com/explore/dataset/enwl-embedded-capacity-register-2-1mw-and-above/"),
        EcrAdapter("enwl_ecr_lt1mw", dno="enwl", dno_label="Electricity North West", host="electricitynorthwest.opendatasoft.com",
                   dataset_id="enwl-embedded-capacity-register-1-under-1mw", band="lt1mw",
                   landing="https://electricitynorthwest.opendatasoft.com/explore/dataset/enwl-embedded-capacity-register-1-under-1mw/"),
        EcrAdapter("nged_ecr", dno="nged", dno_label="National Grid Electricity Distribution", host="connecteddata.nationalgrid.co.uk",
                   dataset_id="embedded-capacity-register", band="mixed", fetch_mode="ckan",
                   landing="https://connecteddata.nationalgrid.co.uk/dataset/embedded-capacity-register"),
    ]
    return {a.source_key: a for a in adapters}
