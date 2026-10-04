# Developer guide

## Environment

| Tool | Version | Notes |
|---|---|---|
| PostgreSQL + PostGIS | 16 + 3.4 | extensions `postgis`, `pg_trgm`, `unaccent`, `btree_gist` (created by migration 001; needs a superuser) |
| Python | ≥ 3.11 | `pip install -e "ingest[dev]"` (psycopg 3, rapidfuzz, pyproj, shapely, openpyxl, requests) |
| Node | ≥ 22 | `cd web && npm ci` |
| Chromium | any | e2e only; the repo's Playwright config points at `/opt/pw-browsers/chromium` (override with `CHROMIUM_PATH`) |

Configuration is by environment variables – see `.env.example` (compose) and `web/.env.example`. Defaults assume a local
database `atlas` with role `atlas` / `atlas_dev`.

## Everyday commands

```bash
python scripts/migrate.py [--reset]                  # apply db/migrations/*.sql once each (reset drops atlas/norm/raw/ops)
atlas-ingest status                                  # registry: access status, rows loaded, rows quarantined
atlas-ingest ingest repd cfd_results                 # run named adapters (omit names = all runnable)
atlas-ingest ingest <src> --file f.csv --source-url https://… [--retrieved-on YYYY-MM-DD] [--publication-date …] [--label …]
atlas-ingest ingest <src> --force                    # re-import even though the file hash is unchanged
atlas-ingest build                                   # entity resolution → canonical → QA → research queue → refresh read model
atlas-ingest report [--out report.md] [--top 25]      # completeness review: unmatched records, lease/REPD leads, duplicate candidates, unperformable cross-checks
atlas-ingest worker [--once]                         # process admin-requested jobs (ops.job_requests)
scripts/rebuild_all.sh [--keep]                      # everything above, from an empty database
```

Re-running `build` is safe and cheap (~30 s for ~15k assets): asset IDs are stable, manual links/overrides are re-applied,
and nothing is downloaded.

## Tests

```bash
cd ingest && pytest                  # 65 tests: units/CRS/text, adapters (synthetic fixtures), robots/HTTP, DB integration
cd web && npm test                   # vitest: filter parsing/WHERE building, formatting & CSV safety, geodesy
cd web && npm run dev &              # or: npm run build && node .next/standalone/server.js
cd web && npm run test:e2e           # Playwright against E2E_BASE_URL (default http://localhost:3000), needs the DB loaded
```

* **Synthetic data only in tests.** Fixtures are labelled `Synthetic …` and live in throw-away databases
  (`ingest/tests/conftest.py` creates `atlas_test_<hex>` per test from `TEST_ADMIN_DSN`, applies the migrations, drops it after;
  tests skip if Postgres is unavailable). Nothing synthetic is ever loaded into the real database.
* `test_integration_pipeline.py` covers the supplied-file route, idempotent re-run, change detection, linking vs siblings,
  provenance to raw columns, status/technology context, privacy masking, stable IDs, durable manual links/overrides,
  geography derivation + QA flags, Crown-Estate polygon containment and "no turbine positions are invented".
* `e2e/consistency.spec.ts` asserts that for several filters the **list total = statistics = exported rows = features drawn
  on the map** (and that empty filters are empty everywhere). `e2e/api-safety.spec.ts` covers attribution, formula
  injection, licence exclusion, privacy, admin protection, evidence-required corrections and hostile input.
* The e2e specs use `?base=plain` (self-hosted basemap) so they do not depend on third-party tile servers.

## Adding a source

1. **Research first** (live): endpoint, format, update date, licence, robots.txt, API terms. Record it in
   `docs/SOURCE_CATALOGUE.md`.
2. Add a registry entry in `ingest/atlas_ingest/registry.py` (tier, licence, attribution, `redistribution`, `export_policy`
   – use `exclude` until redistribution is confirmed).
3. Write `adapters/<name>.py` subclassing `Adapter`: `discover()` (raise `SourceUnavailable` / `SourceRestricted` /
   `ManualReviewRequired` honestly), `parse()` (yield original strings untouched), `validate_structure()` (quarantine broken
   rows), `normalise()` → `NormRecord` with `fields[...] = {col, raw, unit}` for every mapped value. Register it in `adapters/__init__.py`.
4. Add fixtures that reproduce the real defects you found while profiling (see `tests/test_adapters.py`).
5. If the source should create/enrich assets, add it to `SOURCE_ORDER` in `canonical.py` and map its fields to
   observations in `Builder.observations()`.
6. Run `atlas-ingest ingest <source>` then `build`, and **read the resulting links** (not just counts) for false merges.

## Schema notes

* `raw.*` immutable · `norm.source_record` one shape for all sources · `atlas.*` canonical · `ops.*` operations.
* `atlas.asset_flat` (materialised view, migration 005) is the read model for tiles/list/stats/export; refresh with
  `atlas-ingest build` or `REFRESH MATERIALIZED VIEW atlas.asset_flat`. Add a column there before exposing it through
  `LIST_COLUMNS` / `filters.ts`.
* New QA rule = one tuple in `qa.RULES` (`code, severity, message, SELECT asset_id, detail …`). Remember `%%` for literal
  `%` in SQL passed through psycopg.
* Never write human decisions into canonical tables only – store them in `ops.manual_links` / `ops.manual_overrides` (keyed
  by anchors) or they are lost on the next rebuild.

## Conventions

* MW is power, MWh is energy; never store one in the other's column. Calculated values carry `value_kind='calculated'` and a `calc_expression`.
* "Unknown" / "Not publicly identified" instead of blanks that look like data. No defaults that imply a value.
* Match the surrounding code's density; comments explain *why* a data hazard is handled, not what the line does.

## Troubleshooting

* `ATLAS_CONTACT` unset → downloads use a placeholder User-Agent and publishers may refuse; set it.
* A source shows `manual_review_required` with a robots.txt message → by design; see `docs/DEPLOYMENT.md` §"Blocked sources".
* Map canvas blank in a headless browser → pass `--use-gl=swiftshader --enable-webgl --ignore-gpu-blocklist` (already in `playwright.config.ts`).
* Playwright reports `getByRole('alert')` matches two elements → Next.js adds an empty route-announcer alert; filter by text.
