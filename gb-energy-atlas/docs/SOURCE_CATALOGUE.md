# Source catalogue

Research date: **4 October 2026**. Every row below was probed live from the build
environment on that date (HTTP status, file headers, row counts, licence text).
Nothing here is recalled from memory: where a source could not be reached the
reason is stated and the corresponding adapter reports `source_unavailable`
rather than substituting data.

Authority tiers follow the platform hierarchy (see `METHODOLOGY.md`):
A statutory/regulator/network/official dataset · B developer/operator/manufacturer primary ·
C reputable industry or recognised open data · D secondary media · E community maintained.

## 1. Sources ingested in the first build

| Key | Source | Tier | Format / endpoint (verified) | Rows seen | Update freq. | Licence |
|---|---|---|---|---|---|---|
| `repd` | DESNZ Renewable Energy Planning Database, **Q2 2026** (published 6 May 2026) | A | CSV (cp1252, 53 columns) on `assets.publishing.service.gov.uk`; discovered via the GOV.UK content API (`/api/content/government/publications/renewable-energy-planning-database-monthly-extract`) | 14,657 | Quarterly publication (monthly extract page) | Open Government Licence v3.0 |
| `neso_tec` | NESO Transmission Entry Capacity (TEC) Register, 1 Oct 2026 | A | CSV via NESO CKAN API `api.neso.energy` (`transmission-entry-capacity-tec-register`) | 2,196 | Twice weekly | NESO Open Data Licence |
| `neso_embedded` | NESO Embedded Register (embedded generation in Scotland) | A | CSV via NESO CKAN (`embedded-register`) | 560 | Twice weekly | NESO Open Data Licence |
| `npg_ecr_1mw` / `npg_ecr_lt1mw` | Northern Powergrid Embedded Capacity Register (1 MW and over / under 1 MW) | A | Opendatasoft Explore v2.1 `exports/csv` | 931 / 1,847 | Monthly | See dataset metadata (recorded per snapshot) |
| `spen_ecr_50kw` | SP Energy Networks ECR 50 kW–1 MW | A | Opendatasoft `exports/csv` | 2,662 | Monthly | See dataset metadata |
| `nged_ecr` | National Grid Electricity Distribution ECR (Aug 2026) | A | CSV on `connecteddata.nationalgrid.co.uk` (CKAN) | 7,211 | Monthly | See dataset metadata |
| `crown_estate_wind_sites` | The Crown Estate – Wind Site Agreements (England, Wales & NI) | A | ArcGIS FeatureServer `WindSite_EngWalNI_TheCrownEstate` (polygons, WGS84) | 72 | Irregular | **The Crown Estate Open Data Licence (GIS) v1.1** – see §3 |
| `cfd_results` | DESNZ CfD allocation round results (AR4–AR7a, "successful applicants" XLSX) | A | XLSX on `assets.publishing.service.gov.uk`, discovered via GOV.UK content API | per round | Per allocation round | Open Government Licence v3.0 |
| `ons_lad` | ONS Local Authority Districts Dec 2025 (BGC) – context layer for *derived* local authority | A | ArcGIS FeatureServer (`services1.arcgis.com/ESMARspQHYMw9BZ9`) | ~360 GB districts | Annual | Open Government Licence v3.0 |

## 2. Sources investigated but **not** ingested (and why)

| Source | What was found | Status |
|---|---|---|
| SSEN Distribution ECR | `data.ssen.co.uk`, `data-api.ssen.co.uk` and the CKAN backend all return **HTTP 403** (Cloudflare/nginx) to programmatic requests. The dataset exists (`embedded_capacity_register`, monthly, parts for ≥1 MW and 50 kW–1 MW). | `source_unavailable` – access blocked. Not circumvented. Adapter ships and will run when an authorised key/route is configured. |
| UKPN ECR (≥1 MW; <1 MW), ENWL ECR (≥1 MW; <1 MW), SPEN ECR >1 MW | Datasets are listed (UKPN: CC BY 4.0, monthly) but the Opendatasoft records API answers `ForbiddenAccess` and the CSV export is header-only. These need an authenticated portal key. | `restricted` – adapters accept `ODS_API_KEY_<DNO>`; without a key the run is recorded as *access restricted*, never as zero rows of real data. |
| Ofgem Renewable Electricity Register (RO / REGO / FIT) | `dataportal.ofgem.gov.uk`, `renewablesandchp.ofgem.gov.uk`, `dp.ofgem.gov.uk`, `data.ofgem.gov.uk` are denied by the egress gateway (502 to CONNECT). The public `www.ofgem.gov.uk` RO page offers only a RoC totals workbook and a 2006 archive; RER reports are distributed via SharePoint on request. | `manual_review_required` – no machine-readable station-level file reachable. RO/REGO/FIT fields therefore come only from REPD columns (RO banding, FiT tariff) and are labelled as such. |
| Energy Consents Unit (Scotland) `energyconsents.scot` | HTML ASP.NET application, no robots.txt, no bulk export or API discovered. | `manual_review_required` – link-out only; REPD supplies the S36 flag via *Planning Authority = Scottish Government (S36)*. |
| Planning Inspectorate NSIP register | `national-infrastructure-consenting.planninginspectorate.gov.uk` – robots.txt sets a 10 s crawl delay and lists AI crawlers (incl. Claude user-agents) as disallowed. | Not scraped. Link-out only. |
| Welsh Government DNS / SIP (`gov.wales`, `dnh.gov.wales`) | 403 / unreachable from this environment. | `source_unavailable`. |
| LCCC CfD contract portal | `lowcarboncontracts.uk` returns 403. | Replaced by GOV.UK round-results workbooks (above); strike prices come only from those. |
| Crown Estate Scotland open data | ArcGIS hub search returned HTTP 401 for anonymous access. | `restricted`. |
| OpenStreetMap turbines/solar/BESS | `overpass-api.de` (+ lz4/z), Geofabrik: tunnel dropped by egress gateway. `overpass.kumi.systems`, `overpass.private.coffee`: unreachable. `maps.mail.ru` mirror answers but returned an Overpass **runtime error**. `download.openstreetmap.fr` UK extract is reachable but its robots.txt is `Disallow: /*.pbf$` (all agents) – **not downloaded**. | `source_unavailable`. The Overpass client is implemented with a configurable endpoint (`OVERPASS_URL`) and polite rate limiting; individual-turbine rows are only created from a source that actually provides them. |

## 3. Licence notes that change behaviour

* **REPD / CfD results / ONS** – OGL v3.0: attribution *"Contains public sector information licensed under the Open Government Licence v3.0."*
* **NESO** – NESO Open Data Licence: attribution required; redistribution permitted with attribution.
* **The Crown Estate (GIS)** – v1.1. Conditions read from the licence text on the item:
  * mandatory attribution string: *"Contains data provided by The Crown Estate that is protected by copyright and database rights."*
  * §4.3(d) not to reproduce the data in whole or in substantial part on a website concerned with providing the same or similar services as the Crown Estate's own portal;
  * §4.3(e) use only in the ordinary course of business;
  * §4.3(f) no resale / no direct commercial gain from supplying the open data to a third party.
  * **Platform policy:** polygons are displayed with the mandatory attribution; bulk **export of Crown Estate geometry is OFF by default** (`export_policy = exclude`) until the deployer completes a licence review and sets `TCE_EXPORT_REVIEWED=true`. Exports state the exclusion and the reason.
* **DNO ECRs** – licence is read from each dataset's metadata at snapshot time and stored on the snapshot.
* **Privacy** – ECR rows below 1 MW carry customer names/addresses/postcodes. They are retained in the raw layer only; the public layer shows no customer name, address or postcode, and locations are rounded to a 1 km grid.

## 4. Data-quality hazards discovered while profiling (handled in code)

| Source | Hazard | Handling |
|---|---|---|
| REPD | cp1252 encoding; whitespace-only cells used as blanks (e.g. 66 blank Storage Type) | decode cp1252, `strip()`, blank → NULL |
| REPD | *Offshore Wind Round* values are Excel-corrupted dates (`01/01/1900`, `02/01/1900`, `03/01/1900`) | mapped to Round 1/2/3 with a note; original value kept |
| REPD | Status *Revised* (826 rows) means superseded by a re-application, not a project status | status `Superseded`, `supersedes` relationship created from the re-application REF columns |
| REPD | 533 Northern Ireland rows; 36 rows with no X/Y; 15 blank capacities | NI retained and flagged out-of-scope (not deleted); missing coordinates raise a QA flag; no value is invented |
| SPEN 50 kW–1 MW | many rows are **column-shifted** (`country` contains postcode districts, `x_eastings_1_km` contains `Scotland`) | structural validator quarantines those rows to `raw.reject` with reason; they are not guessed or repaired |
| SPEN 50 kW–1 MW | coordinates are 1 km resolution, units are **kW** (not MW) | unit normalisation kW→MW with original retained; accuracy class `grid_1km` |
| NGED | 1,158 rows with `--REDACTED--` coordinates; impossible Eastings (e.g. 3862265) | rejected as coordinates (point stays unplaced); BNG-bounds validation |
| NGED | `Storage - Electrochemical  (Batteries)` (double space), `data not available` sentinels | whitespace normalisation, sentinel → NULL |
| NESO TEC/Embedded | no coordinates at all; `Plant Type` is a `;`-separated list (e.g. `Energy Storage System;Wind Onshore`) | matched to located assets or kept unplaced; hybrid classification only from an explicit multi-technology list |
| All ECRs | Customer names may identify individuals/farms | see privacy policy above |

## 5. Source discovery log – leads still to investigate

* DataMapWales / Lle (Welsh Government) mirrors of Crown Estate layers (licence differs – check before use).
* Marine Directorate (Scotland) licensing registers; MMO public register (marine licences).
* Developer project pages (ScottishPower Renewables, SSE Renewables, RWE, EDF, Vattenfall, Ørsted, Statkraft, RES, …) – research queue, not bulk ingestible.
* Manufacturer documentation (Vestas, Nordex, Enercon, Siemens Gamesa, GE Vernova …) for `turbine_models` – research queue.
* Capacity Market Register (NESO CKAN `capacity-market-register`) – additional matching evidence for BESS/hydro.
* NESO GIS boundaries (DNO licence areas, Grid Supply Points) – optional overlays (§93).
