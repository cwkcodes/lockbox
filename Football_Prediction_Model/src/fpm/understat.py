"""Understat team-level xG backfill (v0.2 data layer).

Per docs/DATA_SOURCES.md: Understat has no official API or scraping ToS —
treat as tolerated personal, non-commercial, low-volume use. This module makes
ONE request per season (the same getLeagueData JSON the league page loads),
sleeps between requests, caches to data/raw/ (gitignored — scraped data is
never committed) and skips files already on disk except the current season.

Matched xG lands in team_match_stats.xg/xga; matches that cannot be paired
(unmapped team name, date mismatch) are reported and left NULL — declared
missing, never invented.
"""
from __future__ import annotations

import datetime
import json
import sqlite3
import sys
import time

import requests

from . import config

URL_TEMPLATE = "https://understat.com/getLeagueData/EPL/{year}"
REFERER_TEMPLATE = "https://understat.com/league/EPL/{year}"
HEADERS = {
    "User-Agent": "fpm-research/0.1 (personal, non-commercial)",
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
}

# Understat title -> football-data raw name (only where they differ, for every
# club in the EPL 2014-15 onwards). Anything not resolvable is reported, not guessed.
NAME_ALIASES = {
    "Manchester United": "Man United",
    "Manchester City": "Man City",
    "Newcastle United": "Newcastle",
    "Nottingham Forest": "Nott'm Forest",
    "Queens Park Rangers": "QPR",
    "West Bromwich Albion": "West Brom",
    "Wolverhampton Wanderers": "Wolves",
}


def raw_path(year: int):
    return config.RAW_DIR / f"understat_EPL_{year}.json"


def download_season(year: int, refresh: bool = False) -> bool:
    dest = raw_path(year)
    if dest.exists() and not refresh:
        return True
    resp = requests.get(
        URL_TEMPLATE.format(year=year), timeout=30,
        headers={**HEADERS, "Referer": REFERER_TEMPLATE.format(year=year)},
    )
    if resp.status_code != 200:
        print(f"  ! understat {year} -> HTTP {resp.status_code}, skipped", file=sys.stderr)
        return dest.exists()
    try:
        payload = resp.json()
        matches = payload["dates"]
    except (ValueError, KeyError):
        print(f"  ! understat {year} -> unexpected payload, skipped", file=sys.stderr)
        return dest.exists()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(matches))
    return True


def download_all(refresh_latest: bool = True) -> list[int]:
    years = list(range(config.FIRST_SEASON_START_YEAR, config.LAST_SEASON_START_YEAR + 1))
    have = []
    for year in years:
        is_latest = year == years[-1]
        if download_season(year, refresh=refresh_latest and is_latest):
            have.append(year)
        time.sleep(1.5)
    return have


def _team_ids(conn: sqlite3.Connection) -> dict[str, int]:
    """Understat title -> canonical team_id via the football-data name_map."""
    fd_names = dict(conn.execute(
        "SELECT raw_name, canonical_id FROM name_map "
        "WHERE source='football-data' AND entity_type='team'"))
    out = {}
    for title, fd_name in NAME_ALIASES.items():
        if fd_name in fd_names:
            out[title] = fd_names[fd_name]
    for fd_name, team_id in fd_names.items():
        out.setdefault(fd_name, team_id)
    return out


def load_xg(db_path=config.DB_PATH) -> int:
    """Write xG into team_match_stats for every downloaded season. Returns
    the number of matches updated; unmatched names/fixtures are reported."""
    conn = sqlite3.connect(db_path)
    ids = _team_ids(conn)
    match_ids = {
        (date, h, a): mid
        for mid, date, h, a in conn.execute(
            "SELECT match_id, date_utc, home_team_id, away_team_id FROM matches")
    }
    updated, unmatched_names, unmatched_fixtures = 0, set(), 0
    for year in range(config.FIRST_SEASON_START_YEAR, config.LAST_SEASON_START_YEAR + 1):
        path = raw_path(year)
        if not path.exists():
            continue
        for m in json.loads(path.read_text()):
            if not m.get("isResult") or not m.get("xG") or m["xG"]["h"] is None:
                continue
            h_title, a_title = m["h"]["title"], m["a"]["title"]
            if h_title not in ids or a_title not in ids:
                unmatched_names.update(t for t in (h_title, a_title) if t not in ids)
                continue
            date = m["datetime"][:10]
            mid = match_ids.get((date, ids[h_title], ids[a_title]))
            if mid is None:
                # Fixtures with no kickoff time carry a midnight timestamp
                # dated the day AFTER the match — try the previous day.
                prev = str(datetime.date.fromisoformat(date) - datetime.timedelta(days=1))
                mid = match_ids.get((prev, ids[h_title], ids[a_title]))
            if mid is None:
                unmatched_fixtures += 1
                continue
            xg_h, xg_a = float(m["xG"]["h"]), float(m["xG"]["a"])
            conn.execute("UPDATE team_match_stats SET xg=?, xga=? WHERE match_id=? AND is_home=1",
                         (xg_h, xg_a, mid))
            conn.execute("UPDATE team_match_stats SET xg=?, xga=? WHERE match_id=? AND is_home=0",
                         (xg_a, xg_h, mid))
            updated += 1
    conn.commit()
    conn.close()
    if unmatched_names:
        print(f"  ! unmapped Understat team names (xG left NULL): {sorted(unmatched_names)}",
              file=sys.stderr)
    if unmatched_fixtures:
        print(f"  ! {unmatched_fixtures} Understat fixtures had no date/team match", file=sys.stderr)
    return updated
