"""Shared fixtures. All data in these tests is SYNTHETIC (clearly named 'Synthetic …') and used only to exercise code paths;
it is never loaded into the production database."""
from __future__ import annotations

import csv
import os
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[2]
ADMIN_DSN = os.environ.get("TEST_ADMIN_DSN", "postgresql://atlas:atlas_dev@127.0.0.1:5432/postgres")

REPD_COLS = [
    "Old Ref ID", "Ref ID", "Record Last Updated (dd/mm/yyyy)", "Operator (or Applicant)", "Site Name", "Technology Type", "Storage Type", "Storage Co-location REPD Ref ID",
    "Installed Capacity (MWelec)", "Share Community Scheme", "CHP Enabled", "CfD Allocation Round", "RO Banding (ROC/MWh)", "FiT Tariff (p/kWh)", "CfD Capacity (MW)", "Turbine Capacity (MW)",
    "No. of Turbines", "Height of Turbines (m)", "Mounting Type for Solar", "Development Status", "Development Status (short)", "Are they re-applying (New REPD Ref)",
    "Are they re-applying (Old REPD Ref) ", "Address", "County", "Region", "Country", "Post Code", "X-coordinate", "Y-coordinate", "Planning Authority", "Planning Application Reference",
    "Appeal Reference", "Secretary of State Reference", "Type of Secretary of State Intervention", "Judicial Review", "Offshore Wind Round", "Planning Application Submitted",
    "Planning Application Withdrawn", "Planning Permission Refused", "Appeal Lodged", "Appeal Withdrawn", "Appeal Refused", "Appeal Granted", "Planning Permission  Granted",
    "Secretary of State - Intervened", "Secretary of State - Refusal", "Secretary of State - Granted", "Planning Permission Expired", "Under Construction", "Operational",
    "Heat Network Ref", "Solar Site Area (sqm)",
]


def repd_row(**kw) -> dict[str, str]:
    row = {c: "" for c in REPD_COLS}
    row.update({"Record Last Updated (dd/mm/yyyy)": "16/01/2026", "Country": "England", "Region": "North West", "Development Status": "Operational", "Development Status (short)": "Operational"})
    row.update(kw)
    return row


def write_repd(path: Path, rows: list[dict[str, str]]) -> Path:
    with open(path, "w", encoding="cp1252", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REPD_COLS)
        w.writeheader()
        w.writerows(rows)
    return path


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """A fresh PostGIS database per test, with all migrations applied. Skipped when Postgres is unavailable."""
    name = f"atlas_test_{uuid.uuid4().hex[:10]}"
    try:
        admin = psycopg.connect(ADMIN_DSN, autocommit=True)
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL/PostGIS not available for integration tests")
    admin.execute(f'CREATE DATABASE "{name}"')
    dsn = ADMIN_DSN.rsplit("/", 1)[0] + f"/{name}"
    conn = psycopg.connect(dsn, row_factory=dict_row)
    for sql in sorted((ROOT / "db" / "migrations").glob("*.sql")):
        conn.execute(sql.read_text())
    conn.commit()
    from atlas_ingest import config, registry
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "raw")
    registry.seed(conn)
    conn.commit()
    yield conn
    conn.close()
    admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    admin.close()
