# Deployment

## Topology

`browser ─▶ reverse proxy (TLS) ─▶ web (Next.js, port 3000) ─▶ PostgreSQL/PostGIS ◀─ worker / ingest (Python)`

The web app needs read access to the `atlas`, `ops` and `norm`/`raw` schemas and write access to `ops.user_reports`,
`ops.audit_log`, `ops.manual_*`, `ops.job_requests` and (admin edits) `atlas.*`. For a hardened deployment create a
dedicated role for the web app with exactly those grants; the compose file uses one role for simplicity.

## Option A – Docker Compose

> The Dockerfiles and compose file were written alongside the app but **have not been built** in the authoring environment
> (no Docker daemon). The same steps were run by hand there: `npm ci && npm run build`, then the standalone server
> (`node .next/standalone/server.js`) served pages, static assets, tiles and API against the loaded database; `docker compose config` validates.

```bash
cp .env.example .env            # set POSTGRES_PASSWORD, ADMIN_TOKEN (long random), ATLAS_CONTACT
docker compose up -d db
docker compose --profile tools run --rm migrate
docker compose --profile tools run --rm ingest ingest repd crown_estate_wind_sites cfd_results ons_lad
docker compose --profile tools run --rm ingest build
docker compose up -d web worker
```

## Option B – bare metal

1. PostgreSQL 16 + PostGIS 3.4; create the database and a role; `python scripts/migrate.py`.
2. `pip install ./ingest`; set `DATABASE_URL`, `ATLAS_CONTACT`; run `scripts/rebuild_all.sh` for the first load.
3. `cd web && npm ci && npm run build`, then run `node .next/standalone/server.js` (copy `.next/static` and `public` into
   `.next/standalone/` first, as the Dockerfile does) with `DATABASE_URL`, `ADMIN_TOKEN`, `PORT`, `HOSTNAME`.
4. Run `atlas-ingest worker` under a process manager so admin-requested ingests/builds are executed.

## Environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `DATABASE_URL` | web, ingest | PostgreSQL connection string |
| `ADMIN_TOKEN` | web | secret for `/admin` and `/api/admin/*`; admin is **disabled** in production while unset or `change-me` |
| `TCE_EXPORT_REVIEWED` | web | `true` only after you have reviewed The Crown Estate's GIS licence; otherwise Crown Estate geometry/fields are excluded from exports |
| `OGR2OGR_PATH` | web | enables GeoPackage export (GDAL `ogr2ogr`) |
| `ATLAS_CONTACT` | ingest | e-mail placed in the User-Agent of every download |
| `ATLAS_DATA_DIR` | ingest | on-disk cache of raw downloads (default `data/raw`) – back it up with the database |
| `ATLAS_MIN_REQUEST_INTERVAL`, `ATLAS_REQUEST_TIMEOUT` | ingest | politeness (default 1 s per host) and timeout |
| `ATLAS_RESPECT_ROBOTS` | ingest | `1` (default). Do not disable |
| `ATLAS_ROBOTS_OVERRIDE` | ingest | comma-separated hosts you have the publisher's permission to fetch despite `robots.txt` (logged on every snapshot) |
| `OVERPASS_URL` | ingest | an Overpass endpoint you may use; empty = OSM adapter reports `source_unavailable` |
| `ODS_API_KEY_UKPN` / `_ENWL` / `_SPEN` | ingest | Opendatasoft keys issued to you by those DNOs |

## Update schedule

Run `ingest` + `build` from cron/systemd timers. Cadences below come from the sources' own stated frequencies; the pipeline
hashes each download, so a run that finds nothing new records `unchanged` and changes nothing.

| Source | Publisher cadence | Suggested schedule |
|---|---|---|
| `repd` | quarterly (GOV.UK) | weekly check |
| `cfd_results` | per allocation round | monthly check |
| `crown_estate_wind_sites` | irregular | monthly check |
| `ons_lad` | annual | quarterly check |
| NESO TEC / Embedded (when enabled) | twice weekly | twice weekly – but see "Blocked sources" |
| DNO ECRs (when enabled) | monthly | monthly |

```cron
17 3 * * 1  cd /srv/atlas && docker compose --profile tools run --rm ingest ingest repd crown_estate_wind_sites cfd_results ons_lad && docker compose --profile tools run --rm ingest build
```

Run `build` after any ingest that loaded new rows; it refreshes the read model, QA flags and research queue. A second
edition of a source produces entries in `ops.change_log` (new/removed projects, status, capacity, date, developer, connection changes).

## Blocked sources (robots.txt, 403, keys)

Sources the publisher disallows for automated access are recorded as **manual review required**; nothing is fetched. To load one:

1. Open the dataset page in a browser and use the publisher's own download button (check the licence on that page).
2. `atlas-ingest ingest neso_tec --file ~/Downloads/tec-register.csv --source-url https://www.neso.energy/… --retrieved-on 2026-10-04 --publication-date 2026-10-01`
   (compose: put the file in `./manual/` and use `--file /manual/tec-register.csv`). The snapshot is annotated *MANUALLY SUPPLIED*.
3. `atlas-ingest build`.

If the publisher has **given you permission** to fetch automatically, set `ATLAS_ROBOTS_OVERRIDE=<host>`; each snapshot fetched
that way is annotated. For DNO portals that require a key, set the matching `ODS_API_KEY_*`.
DNO and NESO licences differ: they are read from dataset metadata at snapshot time; sources whose licence is unverified keep
`export_policy='exclude'` (they appear on the map but are left out of downloads) until you review them and update the registry.

## Operations

* **Backups:** `pg_dump -Fc atlas` plus the raw cache volume (`ATLAS_DATA_DIR`). The raw layer is the source of truth; `norm`
  and `atlas` can be rebuilt from it (`atlas-ingest build`).
* **Reverse proxy:** terminate TLS; forward `X-Forwarded-For` (used to rate-limit corrections). Cookies are `Secure` in production.
* **Admin access:** one shared token (no per-user accounts) – rotate it if anyone leaves; audit entries record actor `admin`.
* **Basemaps:** the default *Light/Dark* use CARTO styles/fonts, *Topographic* OpenTopoMap and *Satellite* Esri imagery – third-party
  services with their own attribution and terms (some restrict commercial or heavy use). Review them for your use or replace the
  entries in `web/src/lib/mapStyle.ts`; the *Plain* basemap is self-hosted from ONS boundaries and needs no external service.
* **Monitoring:** `/api/data-sources` and the Data page show each source's status, last check and last run message;
  `ops.ingestion_run` holds every run; the admin console lists QA flags, duplicate candidates and user reports.
