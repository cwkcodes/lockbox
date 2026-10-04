"""Automated QA. Each rule is set-based SQL that raises a data_quality_flag; flags a human has resolved/dismissed stay resolved."""
from __future__ import annotations

RULES: list[tuple[str, str, str, str]] = [
    # (flag_code, severity, message, SELECT asset_id, detail FROM ...)
    ("missing_coordinates", "warning", "No coordinates available from any source",
     "SELECT asset_id, '{}'::jsonb FROM atlas.assets WHERE is_published AND in_scope_gb AND geom IS NULL"),
    ("approximate_coordinates", "info", "Location is approximate (coarse grid, lease-area point or similar)",
     "SELECT asset_id, jsonb_build_object('accuracy', coordinate_accuracy) FROM atlas.assets WHERE is_published AND geom IS NOT NULL AND coordinate_accuracy IN ('approximate','grid_1km','postcode_centroid')"),
    ("status_conflict", "warning", "Sources report materially different development stages",
     """SELECT p.asset_id, jsonb_build_object('observations', jsonb_agg(jsonb_build_object('status', p.value_text, 'source', p.source_key)))
        FROM atlas.field_provenance p JOIN atlas.status s ON s.code = p.value_text
        WHERE p.field_name = 'status' AND s.stage_group <> 'unknown' AND p.value_text NOT IN ('cfd_awarded','unknown')
        GROUP BY p.asset_id HAVING count(DISTINCT s.stage_group) > 1"""),
    ("capacity_discrepancy", "info", "Preferred installed capacity differs by >15% from a registered/contracted capacity (different quantities; may be legitimate)",
     """SELECT i.asset_id, jsonb_build_object('installed_mw', i.value_num, 'other_field', o.field_name, 'other_mw', o.value_num, 'other_source', o.source_key)
        FROM atlas.field_provenance i JOIN atlas.field_provenance o ON o.asset_id = i.asset_id AND o.field_name IN ('registered_capacity_mw','cfd_capacity_mw')
        WHERE i.field_name = 'installed_capacity_mw' AND i.is_preferred AND i.value_num > 0 AND o.value_num > 0
          AND abs(i.value_num - o.value_num) / greatest(i.value_num, o.value_num) > 0.15"""),
    ("duplicate_candidate", "warning", "A similar record was found but not linked automatically – review required",
     "SELECT DISTINCT asset_b, jsonb_build_object('best_score', max(score)) FROM ops.match_candidates WHERE decision='pending' AND asset_b IS NOT NULL GROUP BY asset_b"),
    ("potential_repower_duplicate", "info", "Name/proximity heuristics suggest this record repowers, extends or is a phase of another asset – verify the hierarchy",
     "SELECT from_asset_id, jsonb_build_object('relation', relation, 'other', to_asset_id) FROM atlas.asset_relationships WHERE basis LIKE 'heuristic%%'"),
    ("turbine_count_conflict", "warning", "Sources report different turbine counts",
     "SELECT asset_id, '{}'::jsonb FROM atlas.field_provenance WHERE field_name='turbine_count' GROUP BY asset_id HAVING count(DISTINCT value_num) > 1"),
    ("model_not_verified", "info", "Turbine model not publicly verified for this operational/under-construction wind project",
     """SELECT a.asset_id, '{}'::jsonb FROM atlas.assets a JOIN atlas.wind_details w USING (asset_id)
        WHERE a.is_published AND a.status_code IN ('operational','partially_operational','under_construction') AND w.turbine_model IS NULL"""),
    ("planning_reference_missing", "info", "Pipeline project has a planning authority but no planning reference",
     """SELECT a.asset_id, '{}'::jsonb FROM atlas.assets a JOIN atlas.status s ON s.code = a.status_code
        WHERE a.is_published AND s.stage_group = 'pipeline' AND a.status_code <> 'cfd_awarded' AND a.planning_authority IS NOT NULL AND a.planning_reference IS NULL"""),
    ("old_source", "info", "Most recent source update for this record is more than 3 years old",
     """SELECT a.asset_id, jsonb_build_object('source_record_last_updated', a.source_updated) FROM atlas.assets a JOIN atlas.status s ON s.code = a.status_code
        WHERE a.is_published AND s.stage_group IN ('operational','pipeline') AND a.source_updated IS NOT NULL AND a.source_updated < current_date - interval '3 years'"""),
    ("capacity_arithmetic_mismatch", "warning", "turbine count × reported turbine rating differs from installed capacity by >15% (mixed fleets or data error)",
     """SELECT a.asset_id, jsonb_build_object('turbines', w.turbine_count_reported, 'turbine_mw', w.turbine_rated_mw_reported, 'capacity_mw', a.installed_capacity_mw,
               'implied_mw', w.turbine_count_reported * w.turbine_rated_mw_reported)
        FROM atlas.assets a JOIN atlas.wind_details w USING (asset_id)
        WHERE a.is_published AND w.turbine_count_reported > 0 AND w.turbine_rated_mw_reported > 0 AND a.installed_capacity_mw > 0
          AND abs(w.turbine_count_reported * w.turbine_rated_mw_reported - a.installed_capacity_mw) / a.installed_capacity_mw > 0.15"""),
    ("unknown_operator", "info", "Operational asset with no operator recorded",
     """SELECT a.asset_id, '{}'::jsonb FROM atlas.assets a WHERE a.is_published AND a.status_code IN ('operational','partially_operational')
        AND NOT EXISTS (SELECT 1 FROM atlas.asset_organisations o WHERE o.asset_id = a.asset_id AND o.role = 'operator')"""),
    ("unknown_owner", "info", "Operational asset with no owner recorded (no loaded source states ownership)",
     """SELECT a.asset_id, '{}'::jsonb FROM atlas.assets a WHERE a.is_published AND a.status_code IN ('operational','partially_operational')
        AND NOT EXISTS (SELECT 1 FROM atlas.asset_organisations o WHERE o.asset_id = a.asset_id AND o.role = 'owner')"""),
    ("coordinate_not_on_land", "warning", "Onshore technology but the coordinates are not on GB land (offshore, estuary, Isle of Man/Channel Islands, or a mis-keyed grid reference)",
     """SELECT a.asset_id, jsonb_build_object('lat', a.lat, 'lon', a.lon) FROM atlas.assets a
        WHERE a.is_published AND a.geom IS NOT NULL AND NOT a.is_offshore AND a.technology_code NOT IN ('tidal_stream','tidal_range','wave')
          AND NOT EXISTS (SELECT 1 FROM atlas.admin_areas l WHERE l.layer='lad' AND ST_Intersects(l.geom, a.geom))
          AND NOT EXISTS (SELECT 1 FROM atlas.admin_areas l WHERE l.layer='lad' AND ST_DWithin(l.geom, a.geom, 0.05) AND ST_DWithin(l.geom::geography, a.geom::geography, 1500))"""),
    ("coordinate_country_mismatch", "error", "Stated country disagrees with the country containing the coordinates",
     """SELECT a.asset_id, jsonb_build_object('stated_country', a.country, 'coordinates_in', l.country) FROM atlas.assets a
        JOIN atlas.admin_areas l ON l.layer='lad' AND ST_Intersects(l.geom, a.geom)
        WHERE a.is_published AND a.geom IS NOT NULL AND NOT a.is_offshore AND a.country IN ('England','Scotland','Wales') AND l.country IS NOT NULL AND l.country <> a.country
          AND NOT EXISTS (SELECT 1 FROM atlas.admin_areas l2 WHERE l2.layer='lad' AND l2.country = a.country AND ST_DWithin(l2.geom, a.geom, 0.01))"""),
    ("capacity_unit_suspect", "warning", "Capacity is implausibly large for this technology – check MW vs kW (or MWh) confusion",
     """SELECT asset_id, jsonb_build_object('capacity_mw', installed_capacity_mw, 'technology', technology_code) FROM atlas.assets
        WHERE is_published AND installed_capacity_mw IS NOT NULL AND (
              (technology_code = 'wind_onshore' AND installed_capacity_mw > 1000) OR (technology_code = 'solar_pv' AND installed_capacity_mw > 1500)
           OR (technology_code = 'bess' AND installed_capacity_mw > 2500) OR (technology_code IN ('hydro','anaerobic_digestion','biomass','landfill_gas') AND installed_capacity_mw > 2000))"""),
    ("identical_coordinates", "info", "Several unrelated projects share exactly the same coordinates (REPD often uses one reference point per site/zone); unless intentionally co-located, positions are not independent",
     """SELECT a.asset_id, jsonb_build_object('count', c.n) FROM atlas.assets a
        JOIN (SELECT bng_e, bng_n, count(*) n FROM atlas.assets WHERE is_published AND bng_e IS NOT NULL GROUP BY 1,2 HAVING count(*) >= 3) c USING (bng_e, bng_n)
        WHERE a.is_published AND NOT EXISTS (SELECT 1 FROM atlas.asset_relationships r WHERE r.from_asset_id = a.asset_id OR r.to_asset_id = a.asset_id)"""),
    ("date_order_inconsistent", "warning", "Operational/construction date precedes the planning application date",
     """SELECT o.asset_id, jsonb_build_object('operational', o.event_date, 'application', p.event_date)
        FROM atlas.asset_history o JOIN atlas.asset_history p ON p.asset_id = o.asset_id AND p.event_type = 'planning_submitted'
        WHERE o.event_type IN ('operational','construction_started') AND o.event_date < p.event_date"""),
    ("operational_in_future", "warning", "Status is operational but the commissioning date is in the future",
     "SELECT asset_id, jsonb_build_object('date', commissioning_date) FROM atlas.assets WHERE is_published AND status_code='operational' AND commissioning_date > current_date"),
    ("bess_duration_inconsistent", "warning", "Published storage duration disagrees with MWh ÷ MW by >15%",
     """SELECT asset_id, jsonb_build_object('power_mw', power_mw, 'energy_mwh', energy_mwh, 'duration_h', duration_h_published) FROM atlas.storage_systems
        WHERE power_mw > 0 AND energy_mwh > 0 AND duration_h_published > 0 AND abs(energy_mwh / power_mw - duration_h_published) / duration_h_published > 0.15"""),
    ("tip_height_inconsistent", "info", "Tip height is inconsistent with hub height + rotor radius",
     """SELECT a.asset_id, jsonb_build_object('hub', w.hub_height_m, 'rotor', w.rotor_diameter_m, 'tip', w.installed_tip_height_m) FROM atlas.assets a JOIN atlas.wind_details w USING (asset_id)
        WHERE w.hub_height_m > 0 AND w.rotor_diameter_m > 0 AND w.installed_tip_height_m > 0
          AND abs(w.installed_tip_height_m - (w.hub_height_m + w.rotor_diameter_m / 2)) / w.installed_tip_height_m > 0.10"""),
    ("unknown_technology", "warning", "Technology could not be classified from the source wording",
     "SELECT asset_id, '{}'::jsonb FROM atlas.assets WHERE is_published AND technology_code = 'unknown'"),
]


def run(conn) -> dict[str, int]:
    conn.execute("DELETE FROM atlas.data_quality_flags WHERE resolved_at IS NULL")
    counts: dict[str, int] = {}
    for code, sev, msg, sql in RULES:
        res = conn.execute(
            f"""INSERT INTO atlas.data_quality_flags (asset_id, flag_code, severity, message, detail)
                SELECT q.asset_id, %s, %s, %s, q.detail FROM ({sql.replace('SELECT', 'SELECT', 1)}) AS q(asset_id, detail)
                WHERE q.asset_id IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM atlas.data_quality_flags f WHERE f.asset_id = q.asset_id AND f.flag_code = %s AND f.resolved_at IS NOT NULL)""",
            (code, sev, msg, code))
        counts[code] = res.rowcount
    conn.commit()
    return counts


def research_queue(conn) -> int:
    """Queue enrichment tasks for high-value missing fields, prioritised as in the specification (operational wind first)."""
    conn.execute("DELETE FROM ops.research_queue WHERE status = 'open'")
    sql = """
    INSERT INTO ops.research_queue (asset_id, missing_field, priority, suggested_sources)
    SELECT a.asset_id, q.field, q.base + CASE WHEN s.stage_group='operational' THEN 0 WHEN s.stage_group='pipeline' THEN 5 ELSE 40 END,
           q.sources
    FROM atlas.assets a
    JOIN atlas.status s ON s.code = a.status_code
    LEFT JOIN atlas.wind_details w USING (asset_id)
    LEFT JOIN atlas.storage_systems st USING (asset_id)
    LEFT JOIN atlas.solar_details so USING (asset_id)
    CROSS JOIN LATERAL (VALUES
        ('turbine_model',  (CASE WHEN a.is_offshore THEN 50 ELSE 10 END), ARRAY['planning decision notice / EIA','developer project page','operator page'],
            (a.technology_code LIKE 'wind%%' AND w.turbine_model IS NULL AND a.status_code IN ('operational','partially_operational','under_construction','awaiting_construction','consented'))),
        ('turbine_count',  12, ARRAY['planning application','developer project page'],
            (a.technology_code LIKE 'wind%%' AND w.turbine_count_reported IS NULL AND a.status_code IN ('operational','partially_operational','under_construction'))),
        ('turbine_positions', 15, ARRAY['planning site layout / EIA figures','OpenStreetMap (supplementary)'],
            (a.technology_code LIKE 'wind%%' AND NOT a.is_offshore AND a.status_code IN ('operational','partially_operational'))),
        ('mwp_dc_and_mw_ac', 20, ARRAY['planning statement','developer project page'],
            (a.technology_code = 'solar_pv' AND so.asset_id IS NOT NULL AND a.status_code IN ('operational','partially_operational') AND coalesce(a.installed_capacity_mw,0) >= 5)),
        ('storage_mwh',    30, ARRAY['planning statement','developer project page','DNO ECR'],
            (a.technology_code = 'bess' AND a.storage_capacity_mwh IS NULL AND a.status_code IN ('operational','partially_operational','under_construction') AND coalesce(a.installed_capacity_mw,0) >= 5)),
        ('planning_reference', 70, ARRAY['local planning authority portal','Energy Consents Unit'],
            (s.stage_group IN ('operational','pipeline') AND a.planning_reference IS NULL AND coalesce(a.installed_capacity_mw,0) >= 5 AND a.status_code <> 'cfd_awarded'))
    ) AS q(field, base, sources, cond)
    WHERE a.is_published AND a.in_scope_gb AND q.cond
    ON CONFLICT (asset_id, missing_field) DO NOTHING"""
    n = conn.execute(sql).rowcount
    conn.commit()
    return n


def refresh_views(conn) -> None:
    conn.execute("REFRESH MATERIALIZED VIEW atlas.asset_flat")
    conn.commit()
