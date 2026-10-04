"""Compare a freshly imported snapshot with the previous one and log what changed (new/removed/status/capacity/...)."""
from __future__ import annotations

_FIELDS = [
    ("status_raw", "status_change"),
    ("capacity_mw", "capacity_change"),
    ("operational_date", "date_change"),
    ("consent_date", "date_change"),
    ("expected_operational_date", "date_change"),
    ("operator_raw", "developer_change"),
    ("developer_raw", "developer_change"),
    ("owner_raw", "developer_change"),
    ("connection_status", "connection_change"),
    ("connection_site", "connection_change"),
]


def _load(conn, snapshot_id: int) -> dict[str, dict]:
    cols = ", ".join(["record_key", "name"] + [f for f, _ in _FIELDS])
    out: dict[str, dict] = {}
    for r in conn.execute(f"SELECT {cols} FROM norm.source_record WHERE snapshot_id=%s ORDER BY row_number", (snapshot_id,)):
        out.setdefault(r["record_key"], r)
    return out


def detect(conn, source_key: str, old_snapshot: int, new_snapshot: int) -> int:
    old, new = _load(conn, old_snapshot), _load(conn, new_snapshot)
    rows = []
    for k, n in new.items():
        if k not in old:
            rows.append((source_key, old_snapshot, new_snapshot, k, n["name"], "new_project", None, None, None))
            continue
        o = old[k]
        for f, kind in _FIELDS:
            a, b = o[f], n[f]
            if a != b:
                rows.append((source_key, old_snapshot, new_snapshot, k, n["name"], kind, f, None if a is None else str(a), None if b is None else str(b)))
    for k, o in old.items():
        if k not in new:
            rows.append((source_key, old_snapshot, new_snapshot, k, o["name"], "removed_project", None, None, None))
    if rows:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO ops.change_log (source_key, from_snapshot_id, to_snapshot_id, record_key, record_name, change_type, field_name, old_value, new_value) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", rows)
    return len(rows)
