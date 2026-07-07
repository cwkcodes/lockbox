"""Download football-data.co.uk season CSVs into data/raw/, never modifying them.

Files are published explicitly for download; still, be polite: one request per
file, a real User-Agent, and skip files already on disk unless refresh=True
(current season only, since past seasons are immutable).
"""
from __future__ import annotations

import sys
import time

import requests

from . import config


def raw_path(season: str, league: str = config.LEAGUE_CODE):
    return config.RAW_DIR / f"{league}_{season}.csv"


def download_season(season: str, league: str = config.LEAGUE_CODE, refresh: bool = False) -> bool:
    """Fetch one season CSV. Returns True if a file is present afterwards."""
    dest = raw_path(season, league)
    if dest.exists() and not refresh:
        return True
    url = config.CSV_URL_TEMPLATE.format(season=season, league=league)
    resp = requests.get(url, timeout=30, headers={"User-Agent": "fpm-research/0.1 (personal, non-commercial)"})
    if resp.status_code != 200 or not resp.content.strip():
        print(f"  ! {url} -> HTTP {resp.status_code}, skipped", file=sys.stderr)
        return dest.exists()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    return True


def download_all(refresh_latest: bool = True) -> list[str]:
    """Download every configured season; returns season codes with data on disk."""
    codes = config.season_codes()
    have = []
    for i, code in enumerate(codes):
        is_latest = code == codes[-1]
        ok = download_season(code, refresh=refresh_latest and is_latest)
        if ok:
            have.append(code)
        time.sleep(1.0)
    return have


if __name__ == "__main__":
    got = download_all()
    print(f"Seasons on disk: {', '.join(got)}")
