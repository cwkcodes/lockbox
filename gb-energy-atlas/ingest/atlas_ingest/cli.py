from __future__ import annotations

import argparse
import logging
import sys

from . import db, registry
from .adapters import all_adapters
from .pipeline import run_source


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="atlas-ingest")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed", help="seed/refresh the source registry")
    p = sub.add_parser("ingest", help="ingest one or more sources")
    p.add_argument("sources", nargs="*", help="source keys (default: all runnable)")
    p.add_argument("--force", action="store_true", help="re-import even if the file hash is unchanged")
    p.add_argument("--file", help="operator-supplied file (downloaded via the publisher's download button) – single source only")
    p.add_argument("--source-url", help="URL the supplied file was downloaded from (required with --file)")
    p.add_argument("--retrieved-on", help="YYYY-MM-DD the file was downloaded (default: today)")
    p.add_argument("--publication-date", help="YYYY-MM-DD publication/update date stated by the publisher")
    p.add_argument("--label", default="", help="resource label (e.g. a round or band)")
    sub.add_parser("status", help="print source registry status")
    w = sub.add_parser("worker", help="process queued admin jobs (ops.job_requests)")
    w.add_argument("--once", action="store_true")
    sub.add_parser("build", help="resolve entities into canonical assets, run QA, queue research, refresh read model")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    with db.connect() as conn:
        registry.seed(conn)
        conn.commit()
        if args.cmd == "seed":
            print(f"seeded {len(registry.S)} sources")
        elif args.cmd == "ingest":
            adapters = all_adapters()
            keys = args.sources or list(adapters)
            if args.file:
                import datetime as dt
                from pathlib import Path
                from .pipeline import Supplied
                if len(keys) != 1 or not args.source_url:
                    ap.error("--file needs exactly one source key and --source-url")
                sup = Supplied(Path(args.file), args.source_url,
                               dt.date.fromisoformat(args.retrieved_on) if args.retrieved_on else dt.date.today(),
                               dt.date.fromisoformat(args.publication_date) if args.publication_date else None, args.label)
                print(run_source(conn, adapters[keys[0]], force=args.force, supplied=sup))
                return 0
            for k in keys:
                if k not in adapters:
                    print(f"no adapter for {k}", file=sys.stderr)
                    continue
                res = run_source(conn, adapters[k], force=args.force)
                print(res)
        elif args.cmd == "worker":
            import time
            from . import canonical, qa
            while True:
                job = conn.execute("UPDATE ops.job_requests SET status='running' WHERE job_id = (SELECT job_id FROM ops.job_requests WHERE status='pending' ORDER BY job_id LIMIT 1 FOR UPDATE SKIP LOCKED) RETURNING *").fetchone()
                conn.commit()
                if job:
                    try:
                        if job["job_type"] == "ingest":
                            msg = str(run_source(conn, all_adapters()[job["source_key"]]))
                        else:
                            msg = str(canonical.Builder(conn).build()); qa.run(conn); qa.research_queue(conn); qa.refresh_views(conn)
                        conn.execute("UPDATE ops.job_requests SET status='done', finished_at=now(), message=%s WHERE job_id=%s", (msg[:1000], job["job_id"]))
                    except Exception as exc:  # noqa: BLE001 – surface any failure to the admin UI
                        conn.rollback()
                        conn.execute("UPDATE ops.job_requests SET status='failed', finished_at=now(), message=%s WHERE job_id=%s", (repr(exc)[:1000], job["job_id"]))
                    conn.commit()
                elif args.once:
                    break
                else:
                    time.sleep(10)
        elif args.cmd == "build":
            from . import canonical, qa
            out = canonical.Builder(conn).build()
            print("canonical:", out)
            print("qa flags:", qa.run(conn))
            print("research queue items:", qa.research_queue(conn))
            qa.refresh_views(conn)
            print("read model refreshed")
        elif args.cmd == "status":
            for r in conn.execute("SELECT source_key, access_status, records_imported, records_rejected, latest_publication_date FROM ops.source_registry ORDER BY source_key"):
                print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
