"""Runtime configuration (environment driven; see .env.example)."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("ATLAS_DATA_DIR", ROOT / "data" / "raw"))
DSN = os.environ.get("DATABASE_URL", "postgresql://atlas:atlas_dev@127.0.0.1:5432/atlas")

CONTACT = os.environ.get("ATLAS_CONTACT", "set ATLAS_CONTACT=you@example.org")
USER_AGENT = f"GB-Energy-Atlas/0.1 (open-data ingestion; {CONTACT})"

# Politeness: minimum seconds between requests to the same host.
MIN_REQUEST_INTERVAL = float(os.environ.get("ATLAS_MIN_REQUEST_INTERVAL", "1.0"))
REQUEST_TIMEOUT = float(os.environ.get("ATLAS_REQUEST_TIMEOUT", "180"))
RESPECT_ROBOTS = os.environ.get("ATLAS_RESPECT_ROBOTS", "1") != "0"
# Explicit operator decision, per host, to fetch from a host whose robots.txt disallows automated access
# (e.g. a portal whose open licence permits the use). Never set by default; every use is written to the
# snapshot notes. Example: ATLAS_ROBOTS_OVERRIDE=api.neso.energy
ROBOTS_OVERRIDE_HOSTS = {h.strip().lower() for h in os.environ.get("ATLAS_ROBOTS_OVERRIDE", "").split(",") if h.strip()}

OVERPASS_URL = os.environ.get("OVERPASS_URL", "")  # empty = OSM adapter reports source_unavailable

# Optional per-DNO Opendatasoft API keys (the portals gate some ECR datasets behind a key).
def ods_api_key(dno: str) -> str | None:
    return os.environ.get(f"ODS_API_KEY_{dno.upper()}") or None
