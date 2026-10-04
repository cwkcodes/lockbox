"""Completeness review (cross-checks between the loaded sources), rendered as Markdown.

It only reports what the loaded data can support: a cross-check against a source that has not been loaded is listed as
"cannot be performed", never silently skipped or filled in."""
from __future__ import annotations

import datetime as dt

_SQL_SOURCES = """
SELECT g.source_key, g.organisation, g.dataset, g.access_status,
       (SELECT count(*) FROM norm.source_record r JOIN raw.snapshot s USING (snapshot_id)
         WHERE r.source_key = g.source_key AND s.is_current) AS records,
       (SELECT count(DISTINCT l.source_record_id) FROM atlas.asset_source_links l JOIN norm.source_record r USING (source_record_id)
         JOIN atlas.assets a USING (asset_id) WHERE r.source_key = g.source_key AND a.is_published AND l.link_type <> 'primary') AS linked,
       (SELECT count(DISTINCT l.source_record_id) FROM atlas.asset_source_links l JOIN norm.source_record r USING (source_record_id)
         JOIN atlas.assets a USING (asset_id) WHERE r.source_key = g.source_key AND a.is_published AND l.link_type = 'primary') AS own_assets
FROM ops.source_registry g WHERE g.active ORDER BY g.tier, g.source_key"""

_SQL_UNMATCHED = """
SELECT a.asset_id, a.canonical_name, a.technology_code, a.status_code, a.installed_capacity_mw AS mw, r.source_key, a.country
FROM atlas.assets a
JOIN atlas.asset_source_links l ON l.asset_id = a.asset_id AND l.link_type = 'primary'
JOIN norm.source_record r ON r.source_record_id = l.source_record_id
WHERE a.is_published AND a.in_scope_gb AND r.source_key <> 'repd' AND a.asset_kind = 'project'
  AND NOT EXISTS (SELECT 1 FROM atlas.asset_source_links x JOIN norm.source_record rx USING (source_record_id)
                  WHERE x.asset_id = a.asset_id AND rx.source_key = 'repd')
ORDER BY a.installed_capacity_mw DESC NULLS LAST, a.asset_id LIMIT %s"""

_SQL_LEASES = """
SELECT a.asset_id, a.canonical_name, a.status_code,
       b.asset_id || ' ' || b.canonical_name || ' (REPD ' || b.repd_ref || ', ' || coalesce(b.installed_capacity_mw::text, '?') || ' MW, '
         || coalesce(round(ST_Distance(a.geom::geography, b.geom::geography) / 1000)::text || ' km away', 'no coordinates') || ')' AS lead
FROM atlas.assets a
LEFT JOIN LATERAL (
    SELECT x.* FROM atlas.assets x
    WHERE x.is_published AND x.asset_kind = 'project' AND x.repd_ref IS NOT NULL AND x.technology_code LIKE 'wind_offshore%%'
      AND (x.name_norm ILIKE a.name_norm || '%%' OR similarity(x.name_norm, a.name_norm) > 0.45)
    ORDER BY similarity(x.name_norm, a.name_norm) DESC LIMIT 1) b ON true
WHERE a.is_published AND a.asset_kind = 'lease_area' ORDER BY a.canonical_name LIMIT %s"""

_SQL_DUPES = """
SELECT m.asset_b AS asset_id, a.canonical_name, a.technology_code, a.installed_capacity_mw AS mw, max(m.score) AS best_score, count(*) AS candidates
FROM ops.match_candidates m JOIN atlas.assets a ON a.asset_id = m.asset_b
WHERE m.decision = 'pending' AND a.is_published
GROUP BY 1, 2, 3, 4 ORDER BY coalesce(a.installed_capacity_mw, 0) DESC, best_score DESC LIMIT %s"""

_SQL_CAPACITY = """
SELECT a.asset_id, a.canonical_name, (f.detail->>'installed_mw')::numeric AS installed_mw, f.detail->>'other_field' AS other_field,
       (f.detail->>'other_mw')::numeric AS other_mw, f.detail->>'other_source' AS other_source
FROM atlas.data_quality_flags f JOIN atlas.assets a USING (asset_id)
WHERE f.flag_code = 'capacity_discrepancy' AND f.resolved_at IS NULL
ORDER BY abs((f.detail->>'installed_mw')::numeric - (f.detail->>'other_mw')::numeric) DESC LIMIT %s"""


def _table(rows: list[dict], cols: list[tuple[str, str]]) -> str:
    if not rows:
        return "_None found in the loaded data._\n"
    head = "| " + " | ".join(h for h, _ in cols) + " |\n|" + "---|" * len(cols) + "\n"
    body = "".join("| " + " | ".join("" if r[k] is None else str(r[k]) for _, k in cols) + " |\n" for r in rows)
    return head + body


def completeness_review(conn, top: int = 25) -> str:
    out = [f"# Completeness review\n\nGenerated {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC from the loaded data. "
           "Findings are **leads for investigation**, not conclusions: an unmatched record may be a different project, a naming "
           "difference or genuinely missing from the other source.\n"]

    srcs = conn.execute(_SQL_SOURCES).fetchall()
    out.append("## 1. Source coverage and cross-checks\n")
    out.append(_table([{**s, "state": s["access_status"]} for s in srcs if s["records"] or s["access_status"] != "current"],
                      [("Source", "source_key"), ("State", "state"), ("Records loaded", "records"), ("Linked to another source's asset", "linked"),
                       ("Created its own asset", "own_assets")]))
    missing = [s["source_key"] for s in srcs if not s["records"]]
    if missing:
        out.append("\n**Cross-checks that cannot be performed because the source is not loaded:** "
                   + ", ".join(f"`{m}`" for m in missing)
                   + ". In particular: REPD ↔ ECR/TEC comparisons (projects missing from either), Ofgem ↔ REPD, and planning-register ↔ REPD "
                     "need those sources (see `docs/SOURCE_CATALOGUE.md` §2 for why and how to load them).\n")

    out.append("\n## 2. Projects found only outside REPD (potential gaps in REPD, or unmatched records)\n")
    out.append("Largest first. CfD awards that never reached REPD are expected for early-stage projects; large operational ones deserve a manual check.\n\n")
    out.append(_table(conn.execute(_SQL_UNMATCHED, (top,)).fetchall(),
                      [("Asset", "asset_id"), ("Name", "canonical_name"), ("Technology", "technology_code"), ("Status", "status_code"), ("MW", "mw"), ("Source", "source_key"), ("Country", "country")]))

    out.append("\n## 3. Offshore lease areas not linked to a REPD project\n")
    out.append("A lease is linked only with hard evidence (the REPD point inside the polygon, or an identifier). Where the closest-named REPD project "
               "is shown as a lead it was **not** linked – e.g. its point lies far outside the polygon, or the names differ by a phase letter – "
               "and needs human review.\n\n")
    out.append(_table(conn.execute(_SQL_LEASES, (top,)).fetchall(), [("Asset", "asset_id"), ("Lease area", "canonical_name"), ("Status", "status_code"), ("Closest-named REPD project (lead, not linked)", "lead")]))

    out.append("\n## 4. Potential duplicates awaiting review (not linked automatically)\n")
    out.append("Largest capacity first. Pairs with a high name score but no spatial/planning/identifier evidence are held for review, never merged.\n\n")
    out.append(_table(conn.execute(_SQL_DUPES, (top,)).fetchall(),
                      [("Asset", "asset_id"), ("Name", "canonical_name"), ("Technology", "technology_code"), ("MW", "mw"), ("Best score", "best_score"), ("Candidates", "candidates")]))

    out.append("\n## 5. Largest capacity discrepancies between quantities (installed vs contracted/registered)\n")
    out.append("These are different quantities and can legitimately differ; large gaps are listed first for investigation.\n\n")
    out.append(_table(conn.execute(_SQL_CAPACITY, (top,)).fetchall(),
                      [("Asset", "asset_id"), ("Name", "canonical_name"), ("Installed MW", "installed_mw"), ("Other quantity", "other_field"), ("Other MW", "other_mw"), ("Source", "other_source")]))

    tot = conn.execute("""SELECT count(*) FILTER (WHERE geom IS NULL) AS unplaced, count(*) AS n FROM atlas.assets WHERE is_published AND in_scope_gb""").fetchone()
    out.append(f"\n## 6. Location coverage\n\n{tot['unplaced']} of {tot['n']} in-scope assets have no coordinates in any loaded source (flagged `missing_coordinates`).\n")
    return "".join(out)
