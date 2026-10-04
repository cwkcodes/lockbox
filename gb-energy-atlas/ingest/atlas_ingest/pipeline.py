"""Download → store raw → validate → normalise → detect changes. Canonical building is a separate step."""
from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from psycopg.types.json import Jsonb

from . import PARSER_VERSION
from .adapters.base import Adapter, Resource
from .http import Fetched, ManualReviewRequired, SourceRestricted, SourceUnavailable, get, robots_overridden
from .model import NORM_COLUMNS, NormRecord, Reject
from .textnorm import norm_name

log = logging.getLogger("atlas.pipeline")

_JSON_COLS = {"ids", "attrs", "fields"}
_INSERT_COLS = NORM_COLUMNS + ["geom"]
_INSERT_SQL = (
    "INSERT INTO norm.source_record (snapshot_id, source_key, row_number, "
    + ", ".join(_INSERT_COLS)
    + ") VALUES (%(snapshot_id)s, %(source_key)s, %(row_number)s, "
    + ", ".join(f"%({c})s" for c in NORM_COLUMNS)
    + ", CASE WHEN %(geom_wkt)s::text IS NOT NULL THEN ST_GeomFromText(%(geom_wkt)s::text, 4326) "
    "WHEN %(lat)s::float8 IS NOT NULL AND %(lon)s::float8 IS NOT NULL THEN ST_SetSRID(ST_MakePoint(%(lon)s::float8, %(lat)s::float8), 4326) END)"
)


def _params(rec: NormRecord, snapshot_id: int, source_key: str, row_number: int) -> dict[str, Any]:
    p: dict[str, Any] = {c: getattr(rec, c) for c in NORM_COLUMNS}
    for c in _JSON_COLS:
        p[c] = Jsonb(p[c])
    p.update(snapshot_id=snapshot_id, source_key=source_key, row_number=row_number, geom_wkt=rec.geom_wkt)
    return p


def _finish_run(conn, run_id: int, outcome: str, message: str, **counts) -> None:
    conn.execute(
        "UPDATE ops.ingestion_run SET finished_at = now(), outcome=%s, message=%s, snapshot_id=%s, rows_read=%s, rows_ok=%s, rows_rejected=%s WHERE run_id=%s",
        (outcome, message[:2000], counts.get("snapshot_id"), counts.get("rows_read"), counts.get("rows_ok"), counts.get("rows_rejected"), run_id),
    )


def _registry_status(conn, source_key: str, status: str, note: str | None = None, **extra) -> None:
    sets = ["access_status=%s", "last_checked_at=now()"]
    vals: list[Any] = [status]
    if note is not None:
        sets.append("access_notes=%s")
        vals.append(note)
    for k, v in extra.items():
        sets.append(f"{k}=%s")
        vals.append(v)
    vals.append(source_key)
    conn.execute(f"UPDATE ops.source_registry SET {', '.join(sets)} WHERE source_key=%s", vals)


def run_source(conn, adapter: Adapter, *, force: bool = False, supplied: "Supplied | None" = None) -> dict[str, Any]:
    """Run one source. `supplied` = a file a person downloaded via the publisher's own download button
    (used when automated access is not permitted); it is recorded as manually supplied."""
    sk = adapter.source_key
    run_id = conn.execute("INSERT INTO ops.ingestion_run (source_key) VALUES (%s) RETURNING run_id", (sk,)).fetchone()["run_id"]
    conn.commit()
    result: dict[str, Any] = {"source": sk, "outcome": None, "rows_ok": 0, "rows_rejected": 0, "message": ""}
    try:
        if supplied is not None:
            resources = [Resource(url=supplied.source_url, label=supplied.label, publication_date=supplied.publication_date,
                                  suffix=supplied.path.suffix, licence_text=supplied.licence_text)]
        else:
            resources = adapter.discover()
    except SourceUnavailable as exc:
        return _terminal(conn, run_id, sk, "source_unavailable", str(exc), result)
    except SourceRestricted as exc:
        return _terminal(conn, run_id, sk, "restricted", str(exc), result)
    except ManualReviewRequired as exc:
        return _terminal(conn, run_id, sk, "manual_review_required", str(exc), result)

    total_ok = total_rej = 0
    unchanged = 0
    last_snapshot = None
    pub_date: dt.date | None = None
    for res in resources:
        try:
            if supplied is not None:
                fetched = _adopt_supplied(supplied, sk)
            else:
                fetched = get(res.url, source_key=sk, label=res.label or sk, headers=res.headers, suffix=res.suffix)
        except SourceRestricted as exc:
            return _terminal(conn, run_id, sk, "restricted", str(exc), result)
        except SourceUnavailable as exc:
            return _terminal(conn, run_id, sk, "source_unavailable", str(exc), result)
        except ManualReviewRequired as exc:
            return _terminal(conn, run_id, sk, "manual_review_required", str(exc), result)

        existing = conn.execute(
            "SELECT snapshot_id FROM raw.snapshot WHERE source_key=%s AND resource_label=%s AND sha256=%s",
            (sk, res.label, fetched.sha256),
        ).fetchone()
        if existing and not force:
            unchanged += 1
            last_snapshot = existing["snapshot_id"]
            pub_date = res.publication_date or pub_date
            continue

        raw_rows = list(adapter.parse(fetched.path, res))
        if not raw_rows:
            fetched.path.unlink(missing_ok=True)
            return _terminal(conn, run_id, sk, "restricted",
                             f"{res.url} returned no data rows (header-only/empty export – the portal likely requires an API key)", result)

        # Diff against the most recent *different* edition (a forced re-import of identical bytes has nothing to diff).
        prev = conn.execute(
            "SELECT snapshot_id FROM raw.snapshot WHERE source_key=%s AND resource_label=%s AND sha256 <> %s "
            "ORDER BY retrieved_at DESC LIMIT 1",
            (sk, res.label, fetched.sha256),
        ).fetchone()
        if existing and force:
            conn.execute("DELETE FROM raw.snapshot WHERE snapshot_id=%s", (existing["snapshot_id"],))
        conn.execute("UPDATE raw.snapshot SET is_current=false WHERE source_key=%s AND resource_label=%s", (sk, res.label))
        snap = conn.execute(
            "INSERT INTO raw.snapshot (source_key, resource_label, publication_date, source_url, http_status, content_type, etag, sha256, "
            "byte_size, local_path, licence_snapshot, parser_version, notes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING snapshot_id",
            (sk, res.label, res.publication_date, res.url, fetched.status, fetched.content_type, fetched.etag, fetched.sha256,
             fetched.size, str(fetched.path), res.licence_text, PARSER_VERSION,
             _snapshot_note(fetched, res, supplied)),
        ).fetchone()["snapshot_id"]

        ok = rej = 0
        with conn.cursor() as cur:
            raw_batch, norm_batch, rej_batch = [], [], []
            for row_number, record_key, payload in raw_rows:
                raw_batch.append((snap, row_number, record_key, Jsonb(payload)))
                bad = adapter.validate_structure(payload)
                if bad:
                    rej_batch.append((snap, row_number, bad, Jsonb(payload)))
                    continue
                out = adapter.normalise(payload, row_number, res)
                if isinstance(out, Reject):
                    rej_batch.append((snap, row_number, out.reason, Jsonb(payload)))
                    continue
                if out.name and not out.name_norm:
                    out.name_norm = norm_name(out.name)
                norm_batch.append(_params(out, snap, sk, row_number))
            cur.executemany("INSERT INTO raw.record (snapshot_id, row_number, record_key, payload) VALUES (%s,%s,%s,%s)", raw_batch)
            if rej_batch:
                cur.executemany("INSERT INTO raw.reject (snapshot_id, row_number, reason, payload) VALUES (%s,%s,%s,%s)", rej_batch)
            cur.executemany(_INSERT_SQL, norm_batch)
            ok, rej = len(norm_batch), len(rej_batch)
        conn.execute("UPDATE raw.snapshot SET row_count=%s, rejected_count=%s WHERE snapshot_id=%s", (len(raw_rows), rej, snap))
        if prev:
            from .change_detect import detect
            detect(conn, sk, prev["snapshot_id"], snap)
        extra = adapter.registry_update(res)
        if extra:
            sets = ", ".join(f"{k}=%s" for k in extra)
            conn.execute(f"UPDATE ops.source_registry SET {sets} WHERE source_key=%s", [*extra.values(), sk])
        conn.commit()
        total_ok += ok
        total_rej += rej
        last_snapshot = snap
        pub_date = res.publication_date or pub_date
        log.info("%s [%s]: %s rows ok, %s quarantined", sk, res.label, ok, rej)

    outcome = "unchanged" if unchanged == len(resources) and not total_ok else "success"
    if outcome == "success" or unchanged:
        counts = conn.execute(
            "SELECT coalesce(sum(row_count - rejected_count),0)::int AS ok, coalesce(sum(rejected_count),0)::int AS rej "
            "FROM raw.snapshot WHERE source_key=%s AND is_current", (sk,)).fetchone()
        _registry_status(conn, sk, "current", None, latest_publication_date=pub_date,
                         records_imported=counts["ok"], records_rejected=counts["rej"])
    _finish_run(conn, run_id, outcome, f"{total_ok} rows normalised, {total_rej} quarantined, {unchanged} resource(s) unchanged",
                snapshot_id=last_snapshot, rows_read=total_ok + total_rej, rows_ok=total_ok, rows_rejected=total_rej)
    conn.commit()
    result.update(outcome=outcome, rows_ok=total_ok, rows_rejected=total_rej)
    return result


def _terminal(conn, run_id: int, sk: str, outcome: str, message: str, result: dict) -> dict:
    status = {"source_unavailable": "source_unavailable", "restricted": "restricted", "manual_review_required": "manual_review_required"}[outcome]
    _registry_status(conn, sk, status, message[:1000])
    _finish_run(conn, run_id, outcome, message)
    conn.commit()
    result.update(outcome=outcome, message=message)
    log.warning("%s: %s – %s", sk, outcome, message)
    return result


@dataclass
class Supplied:
    path: Path
    source_url: str
    retrieved_on: dt.date
    publication_date: dt.date | None = None
    label: str = ""
    licence_text: str | None = None


def _adopt_supplied(sup: Supplied, source_key: str) -> Fetched:
    """Copy an operator-supplied file into the raw cache and hash it."""
    import hashlib
    import shutil
    from . import config
    out_dir = config.DATA_DIR / source_key
    out_dir.mkdir(parents=True, exist_ok=True)
    data = sup.path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    dest = out_dir / f"supplied_{digest[:12]}{sup.path.suffix}"
    if not dest.exists():
        shutil.copyfile(sup.path, dest)
    return Fetched(dest, sup.source_url, digest, len(data), 200, None, None, None)


def _snapshot_note(fetched: Fetched, res: Resource, supplied: "Supplied | None") -> str | None:
    notes = []
    if supplied is not None:
        notes.append(f"MANUALLY SUPPLIED by operator (retrieved {supplied.retrieved_on.isoformat()} from {supplied.source_url}); "
                     "not fetched by automation")
    elif robots_overridden(res.url):
        notes.append("robots.txt override by operator for this host (ATLAS_ROBOTS_OVERRIDE) – operator accepted responsibility for terms of use")
    if fetched.last_modified:
        notes.append(f"Last-Modified: {fetched.last_modified}")
    return "; ".join(notes) or None
