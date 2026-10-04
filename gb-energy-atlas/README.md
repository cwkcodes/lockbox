# GB Renewable Energy Atlas

A source-driven, traceable geospatial database and web application for renewable-generation and energy-storage assets in
Great Britain (England, Scotland, Wales). Every material value shown is traceable to the organisation, dataset, record,
URL, publication date, retrieval date and licence it came from; conflicts between sources are kept, not silently merged.

> **Coverage statement.** This platform consolidates publicly available renewable-energy and storage information from
> government, regulator, network, planning and industry sources. Although designed to provide broad coverage, it should
> not be interpreted as a definitive register of every installation in Great Britain. Coverage and data quality vary by
> technology, project scale, geography and source.

## What is in the database today (4 October 2026 build)

| | |
|---|---|
| Canonical assets | 14,935 published (14,402 in GB scope; 533 Northern Ireland records retained but flagged out of scope) |
| Located on the map | 14,343 in-scope assets (59 have no coordinates in any loaded source and are flagged, not guessed) |
| Operational / pipeline projects (GB) | 3,013 operational (≈57 GW) · 7,896 pipeline (≈285 GW) · 3,397 refused/withdrawn/expired/superseded · 31 historic |
| Offshore lease areas | 72 Crown Estate wind-site polygons (England & Wales): 50 stand-alone lease areas, 22 attached to matched projects |
| Provenance | 110,338 field-level observations with raw column/value, source record and preferred-value reasoning |
| Relationships | 2,378 phase / extension / repower / supersedes links |
| Organisations | 6,796 canonical organisations with aliases |

**Loaded sources:** DESNZ REPD (Q2 2026, 14,657 rows), DESNZ CfD allocation results AR5–AR7a (427 rows),
The Crown Estate wind-site agreements (72 polygons), ONS Local Authority Districts (361, used only to derive local authority).

**Not loaded – and why** (full detail in [`docs/SOURCE_CATALOGUE.md`](docs/SOURCE_CATALOGUE.md)):

* NESO TEC / Embedded registers and the DNO Embedded Capacity Registers (Northern Powergrid, SP Energy Networks, NGED, UKPN,
  ENWL): the publishers' `robots.txt` disallows automated access, so the client refuses. They are recorded as *manual review
  required*. An operator can load them with a manually downloaded file (`--file`) – see [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).
* SSEN ECR, Ofgem station-level registers, Welsh DNS/SIP, LCCC, Crown Estate Scotland, OpenStreetMap/Overpass: blocked,
  restricted or unavailable from the build environment (HTTP 403/401, gateway denial). Not circumvented.
* Planning portals (Scottish ECU, Planning Inspectorate): no machine-readable bulk route found / crawling disallowed. Link-out only.

**Consequences the interface states plainly:** there are **no individual turbine positions** (the only candidate source,
OpenStreetMap, was unreachable); there is **no station-level RO/REGO/FIT data** beyond what REPD carries; turbine
manufacturer/model, hub height, rotor diameter, ownership and BESS MWh are mostly *Unknown* – they sit in a research queue
(3,124 items) rather than being guessed. Change detection works and is tested, but only one edition of each source has been loaded, so the change log is empty.

## Repository layout

```
db/migrations/      PostgreSQL 16 + PostGIS schema: raw → norm → atlas (canonical) → ops
ingest/             Python package atlas_ingest: adapters, pipeline, entity resolution, QA, change detection, CLI
scripts/            migrate.py, rebuild_all.sh
web/                Next.js 16 / React 19 / TypeScript app: map (MapLibre GL + PostGIS vector tiles), API, pages
docs/               SOURCE_CATALOGUE.md, ARCHITECTURE.md, DEVELOPER.md, DEPLOYMENT.md
docker-compose.yml  db + web + worker (+ one-off migrate / ingest tools)
```

## Quick start (local development)

Requires PostgreSQL 16 with PostGIS 3.4, Python ≥ 3.11, Node ≥ 22.

```bash
createdb atlas   # role atlas / password atlas_dev by default – see .env.example for DATABASE_URL
python -m venv .venv && source .venv/bin/activate && pip install -e "ingest[dev]"
export ATLAS_CONTACT=you@example.org          # sent in the User-Agent of every download
scripts/rebuild_all.sh                         # migrate, ingest every permitted source, build the canonical layer
cd web && npm ci && cp ../.env.example .env.local && npm run dev    # http://localhost:3000
```

Tests: `cd ingest && pytest` · `cd web && npm test` · `cd web && npm run test:e2e` (needs the app running and the database loaded).
Details: [`docs/DEVELOPER.md`](docs/DEVELOPER.md). Deployment: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).
Design: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Principles that are enforced in code, not just policy

* Raw source files and rows are never modified or deleted; the normalised and canonical layers are rebuildable from them.
* No fuzzy-name-only merges: a link needs a score ≥ 0.80 **and** hard evidence (spatial/planning/identifier); siblings
  ("East"/"West", "Phase 2", "Extension", digits, compass words) are never merged; borderline pairs go to a review queue.
* A project centroid is never turned into a turbine coordinate; turbines live in their own table and only appear with a
  verified coordinate class.
* Calculated values are labelled with their expression; MW, MWh, MWp/MWac, installed vs contracted vs registered capacity
  are separate fields.
* Sources whose licence has not been cleared for redistribution (e.g. Crown Estate GIS until `TCE_EXPORT_REVIEWED=true`)
  are excluded from exports, with the reason stated in the export. Exports always carry publisher + dataset + licence attribution.
* Sub-1 MW ECR records never expose customer names, addresses or postcodes; positions are 1 km grid centres.
* Corrections from users require an evidence URL and go to a review queue; nothing is auto-published. Admin edits are audited.

## Known limitations (also shown in the app)

* Admin access is a single shared `ADMIN_TOKEN` (no per-user accounts); audit entries record the actor as `admin`. Saved
  views are stored in the visitor's browser, not on the server.
* Default basemaps (CARTO, OpenTopoMap, Esri) are third-party tile services; check their terms before commercial deployment
  or substitute your own. A self-hosted *Plain* basemap (ONS outlines) works offline.
* Docker images are provided but were not built in the authoring environment (no Docker daemon); the app was built
  (`next build`) and run in standalone mode, and the Python suite was run against PostGIS 16.
* The material in `docs/SOURCE_CATALOGUE.md` reflects what was reachable on 4 October 2026; re-probe before relying on it.
