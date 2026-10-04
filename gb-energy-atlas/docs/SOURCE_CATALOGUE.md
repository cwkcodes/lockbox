# Source catalogue

Research date: **4 October 2026**. Every row below was probed live from the build
environment on that date (HTTP status, file headers, row counts, licence text).
Nothing here is recalled from memory: where a source could not be reached the
reason is stated and the corresponding adapter reports `source_unavailable`
rather than substituting data.

Authority tiers follow the platform hierarchy (see the Methodology page of the application and `docs/ARCHITECTURE.md`):
A statutory/regulator/network/official dataset · B developer/operator/manufacturer primary ·
C reputable industry or recognised open data · D secondary media · E community maintained.

## 1. Sources loaded in the current database

Counts and dates below are read from `raw.snapshot` / `ops.source_registry`, not from memory.

| Key | Source | Tier | Format / endpoint (verified) | Rows loaded | Update freq. | Licence |
|---|---|---|---|---|---|---|
| `repd` | DESNZ Renewable Energy Planning Database, **Q2 2026** edition (GOV.UK publication date 3 Aug 2026; file `Last-Modified` 31 Jul 2026) | A | CSV (cp1252, 53 columns) on `assets.publishing.service.gov.uk`, discovered via the GOV.UK content API for the `renewable-energy-planning-database-quarterly-extract` publication (the former `…-monthly-extract` path now redirects there) | 14,657 (0 quarantined; 533 Northern Ireland rows retained but flagged out of scope) | Quarterly | Open Government Licence v3.0 |
| `cfd_results` | DESNZ CfD allocation-round "successful applicants" workbooks: **AR5** (Sep 2023), **AR6** (Sep 2024), **AR7** (Jan 2026), **AR7a** (Feb 2026) | A | XLSX on `assets.publishing.service.gov.uk`, discovered via the GOV.UK content API. AR3/AR4 are not published as XLSX workbooks and are therefore not loaded. | 427 (95 + 131 + 12 + 189) | Per allocation round | Open Government Licence v3.0 |
| `crown_estate_wind_sites` | The Crown Estate – Wind Site Agreements (England, Wales & NI), updated 29 Sep 2026 | A | ArcGIS FeatureServer `WindSite_EngWalNI_TheCrownEstate` (polygons, WGS84) | 72 lease polygons | Irregular | **The Crown Estate Open Data Licence (GIS) v1.1** – see §3 |
| `ons_lad` | ONS Local Authority Districts Dec 2025 (BGC) – context layer used only to *derive* local authority by point-in-polygon | A | ArcGIS FeatureServer (`services1.arcgis.com/ESMARspQHYMw9BZ9`) | 361 GB/NI districts | Annual | Open Government Licence v3.0 |

Everything else in the registry is **not loaded**. §2 lists each one with the reason.

## 2. Sources investigated but **not** loaded (and why)

### 2a. Reachable by API, but the publisher's `robots.txt` disallows automated access

The HTTP client checks `robots.txt` before every fetch and refuses. These sources are recorded as `manual_review_required`
with the exact refusal message. **No data from them is in the database.**

| Source | Endpoint investigated | Rows seen in a research-phase probe |
|---|---|---|
| NESO Transmission Entry Capacity (TEC) Register (`neso_tec`) | `api.neso.energy` CKAN | 2,196 |
| NESO Embedded Register (`neso_embedded`) | `api.neso.energy` CKAN | 560 |
| Northern Powergrid ECR ≥1 MW / <1 MW (`npg_ecr_1mw`, `npg_ecr_lt1mw`) | `northernpowergrid.opendatasoft.com` | 931 / 1,847 |
| SP Energy Networks ECR 50 kW–1 MW / >1 MW (`spen_ecr_50kw`, `spen_ecr_1mw`) | `spenergynetworks.opendatasoft.com` | 2,662 / – |
| National Grid Electricity Distribution ECR (`nged_ecr`) | `connecteddata.nationalgrid.co.uk` CKAN | 7,211 (Aug 2026 edition) |
| UKPN ECR ≥1 MW / <1 MW, ENWL ECR ≥1 MW / <1 MW | `*.opendatasoft.com` | – (records API answered `ForbiddenAccess`; CSV export header-only without a key) |

The "rows seen" figures come from short profiling probes made while researching the sources, **before** the compliance check was
built into the HTTP client. They exist only to document each dataset's shape (and the hazards in §4); none of those rows were
stored in the database, and the adapters now refuse to repeat the fetch.

**How an operator can load them legitimately** (see `docs/DEPLOYMENT.md`): download the file with the publisher's own download
button and run `atlas-ingest ingest <source> --file <path> --source-url <page URL>`; the snapshot is recorded as *manually
supplied* with the retrieval date. Alternatively, an operator who has obtained the publisher's permission can set
`ATLAS_ROBOTS_OVERRIDE=<host>`; the override is logged on every snapshot it produces.

### 2b. Blocked, restricted or not machine-readable

| Source | What was found | Status |
|---|---|---|
| SSEN Distribution ECR | `data.ssen.co.uk`, `data-api.ssen.co.uk` and the CKAN backend all return **HTTP 403** (Cloudflare/nginx) to programmatic requests. The dataset exists (`embedded_capacity_register`, monthly, parts for ≥1 MW and 50 kW–1 MW). | `restricted` – access blocked. Not circumvented. |
| Ofgem Renewable Electricity Register (RO / REGO / FIT) | `dataportal.ofgem.gov.uk`, `renewablesandchp.ofgem.gov.uk`, `dp.ofgem.gov.uk`, `data.ofgem.gov.uk` are denied by the egress gateway. The public `www.ofgem.gov.uk` RO page offers only a RoC totals workbook; station-level RER reports are distributed via SharePoint on request. | `source_unavailable`. RO/REGO/FIT fields therefore come only from REPD columns (RO banding, FiT tariff) and are labelled as such. |
| Energy Consents Unit (Scotland) `energyconsents.scot` | HTML ASP.NET application, no bulk export or API discovered. | `manual_review_required` – link-out only; REPD supplies the S36 flag via *Planning Authority = Scottish Government (S36)*. |
| Planning Inspectorate NSIP register | robots.txt sets a 10 s crawl delay and lists AI crawlers (including Claude user-agents) as disallowed. | `manual_review_required`. Not scraped. |
| Welsh Government DNS / SIP (`gov.wales`, `dnh.gov.wales`) | 403 / unreachable from the build environment. | `source_unavailable`. |
| LCCC CfD contract portal | `lowcarboncontracts.uk` returns 403. | `restricted`. Strike prices come only from the GOV.UK round-results workbooks; no indexation or termination data. |
| Crown Estate Scotland open data | ArcGIS hub search returned HTTP 401 for anonymous access. | `restricted`. Scottish offshore leases are therefore absent. |
| OpenStreetMap turbines/solar/BESS | `overpass-api.de` and mirrors blocked from the build environment; one mirror returned an Overpass runtime error; the OSM-France UK extract is `Disallow: /*.pbf$`. | `source_unavailable`. The Overpass client is implemented with a configurable endpoint (`OVERPASS_URL`); individual-turbine rows are only created from a source that actually provides them. **As a result no individual turbine position is in the database.** |

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
| SPEN 50 kW–1 MW | many rows are **column-shifted** (`country` contains postcode districts, `x_eastings_1_km` contains `Scotland`) | rows matching the one known shifted-column signature exactly are realigned and noted; any other malformed row is quarantined to `raw.reject` with a reason and never guessed |
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
