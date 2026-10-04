#!/usr/bin/env bash
# Reset the database, ingest every source that is allowed to run, then build the canonical layer.
# Usage: scripts/rebuild_all.sh [--keep]   (--keep = do not drop the schema first)
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true
export ATLAS_CONTACT="${ATLAS_CONTACT:-set-ATLAS_CONTACT}"
[[ "${1:-}" == "--keep" ]] || python scripts/migrate.py --reset
[[ "${1:-}" == "--keep" ]] && python scripts/migrate.py
python -m atlas_ingest.cli ingest repd crown_estate_wind_sites cfd_results ons_lad
# Sources that need an operator decision (robots.txt / API key / manual file) are reported, never faked:
python -m atlas_ingest.cli ingest neso_tec neso_embedded npg_ecr_1mw npg_ecr_lt1mw spen_ecr_50kw spen_ecr_1mw nged_ecr \
    ukpn_ecr_1mw ukpn_ecr_lt1mw enwl_ecr_1mw enwl_ecr_lt1mw osm_overpass 2>&1 | grep -E "^\{" || true
python -m atlas_ingest.cli ingest ssen_ecr ofgem_rer scottish_energy_consents pins_nsip welsh_infrastructure lccc_cfd crown_estate_scotland 2>&1 | grep -E "^\{" || true
python -m atlas_ingest.cli build
