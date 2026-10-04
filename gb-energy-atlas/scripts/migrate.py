#!/usr/bin/env python3
"""Apply db/migrations/*.sql in order, once each. Usage: python scripts/migrate.py [--reset]"""
import os
import pathlib
import sys

import psycopg

ROOT = pathlib.Path(__file__).resolve().parent.parent
MIGRATIONS = ROOT / "db" / "migrations"
DSN = os.environ.get("DATABASE_URL", "postgresql://atlas:atlas_dev@127.0.0.1:5432/atlas")


def main() -> int:
    reset = "--reset" in sys.argv
    with psycopg.connect(DSN, autocommit=True) as conn:
        if reset:
            for schema in ("atlas", "norm", "raw", "ops"):
                conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
            conn.execute("DROP SCHEMA IF EXISTS meta CASCADE")
            print("reset: dropped atlas/norm/raw/ops")
        conn.execute("CREATE SCHEMA IF NOT EXISTS meta")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS meta.schema_migrations (name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        applied = {r[0] for r in conn.execute("SELECT name FROM meta.schema_migrations")}
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.name in applied:
                print(f"skip   {path.name}")
                continue
            print(f"apply  {path.name}")
            with conn.transaction():
                conn.execute(path.read_text())
                conn.execute("INSERT INTO meta.schema_migrations (name) VALUES (%s)", (path.name,))
    print("migrations complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
