"""Normalise raw football-data.co.uk CSVs into the SQLite schema.

Only the subset of schema.sql needed for v0.1 is populated: competitions,
teams, name_map, matches, team_match_stats and odds (1X2, pre-match average
+ Bet365 + Pinnacle, and Pinnacle/market closing where present).
"""
from __future__ import annotations

import sqlite3

import pandas as pd

from . import config
from .ingest import raw_path

SCHEMA_PATH = config.PROJECT_DIR / "schema" / "schema.sql"

# (bookmaker, [H, D, A columns], is_closing)
ODDS_COLUMN_SETS = [
    ("B365", ["B365H", "B365D", "B365A"], 0),
    ("Pinnacle", ["PSH", "PSD", "PSA"], 0),
    ("market_avg", ["AvgH", "AvgD", "AvgA"], 0),
    ("market_avg", ["BbAvH", "BbAvD", "BbAvA"], 0),  # pre-2019 naming
    ("Pinnacle", ["PSCH", "PSCD", "PSCA"], 1),
    ("market_avg", ["AvgCH", "AvgCD", "AvgCA"], 1),
    ("B365", ["B365CH", "B365CD", "B365CA"], 1),
]

TEAM_STAT_COLS = {
    "shots": ("HS", "AS"),
    "shots_on_target": ("HST", "AST"),
    "corners": ("HC", "AC"),
    "fouls": ("HF", "AF"),
    "yellow_cards": ("HY", "AY"),
    "red_cards": ("HR", "AR"),
}


def parse_dates(series: pd.Series) -> pd.Series:
    d = pd.to_datetime(series, format="%d/%m/%Y", errors="coerce")
    two_digit = pd.to_datetime(series, format="%d/%m/%y", errors="coerce")
    return d.fillna(two_digit)


def init_db(db_path=config.DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_PATH.read_text())
    conn.execute(
        "INSERT OR IGNORE INTO competitions (competition_id, name, country, tier, is_cup) "
        "VALUES (?, ?, ?, 1, 0)",
        (config.COMPETITION_ID, "Premier League", "England"),
    )
    return conn


def _team_id(conn: sqlite3.Connection, raw_name: str, cache: dict) -> int:
    if raw_name in cache:
        return cache[raw_name]
    row = conn.execute(
        "SELECT canonical_id FROM name_map WHERE source='football-data' "
        "AND entity_type='team' AND raw_name=?",
        (raw_name,),
    ).fetchone()
    if row:
        cache[raw_name] = row[0]
        return row[0]
    cur = conn.execute(
        "INSERT INTO teams (canonical_name, country) VALUES (?, 'England')", (raw_name,)
    )
    team_id = cur.lastrowid
    conn.execute(
        "INSERT INTO name_map (source, entity_type, raw_name, canonical_id) "
        "VALUES ('football-data', 'team', ?, ?)",
        (raw_name, team_id),
    )
    cache[raw_name] = team_id
    return team_id


def load_season(conn: sqlite3.Connection, season_code: str) -> int:
    path = raw_path(season_code)
    if not path.exists():
        return 0
    df = pd.read_csv(path, encoding="latin-1")
    df = df.dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"])
    df["date"] = parse_dates(df["Date"])
    season = config.season_label(season_code)
    cache: dict = {}
    n = 0
    for _, r in df.iterrows():
        home_id = _team_id(conn, r["HomeTeam"], cache)
        away_id = _team_id(conn, r["AwayTeam"], cache)
        fthg, ftag = int(r["FTHG"]), int(r["FTAG"])
        cur = conn.execute(
            "INSERT OR IGNORE INTO matches (competition_id, season, date_utc, home_team_id, "
            "away_team_id, status, ft_home, ft_away, ht_home, ht_away, result, total_goals, btts) "
            "VALUES (?, ?, ?, ?, ?, 'played', ?, ?, ?, ?, ?, ?, ?)",
            (
                config.COMPETITION_ID, season, r["date"].strftime("%Y-%m-%d"),
                home_id, away_id, fthg, ftag,
                _int_or_none(r.get("HTHG")), _int_or_none(r.get("HTAG")),
                str(r["FTR"]), fthg + ftag, int(fthg > 0 and ftag > 0),
            ),
        )
        if cur.rowcount == 0:
            continue
        match_id = cur.lastrowid
        n += 1
        for team_id, is_home, goals, prefix_idx in ((home_id, 1, fthg, 0), (away_id, 0, ftag, 1)):
            stats = {k: _int_or_none(r.get(cols[prefix_idx])) for k, cols in TEAM_STAT_COLS.items()}
            conn.execute(
                "INSERT OR IGNORE INTO team_match_stats (match_id, team_id, is_home, goals, "
                "shots, shots_on_target, corners, fouls, yellow_cards, red_cards) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (match_id, team_id, is_home, goals, stats["shots"], stats["shots_on_target"],
                 stats["corners"], stats["fouls"], stats["yellow_cards"], stats["red_cards"]),
            )
        for bookmaker, cols, is_closing in ODDS_COLUMN_SETS:
            vals = [pd.to_numeric(r.get(c), errors="coerce") for c in cols]
            if any(pd.isna(v) or v <= 1.0 for v in vals):
                continue
            for sel, odd in zip(("H", "D", "A"), vals):
                conn.execute(
                    "INSERT INTO odds (match_id, bookmaker, is_closing, market, selection, decimal_odds) "
                    "VALUES (?, ?, ?, '1X2', ?, ?)",
                    (match_id, bookmaker, is_closing, sel, float(odd)),
                )
    conn.commit()
    return n


def _int_or_none(v):
    v = pd.to_numeric(v, errors="coerce")
    return None if pd.isna(v) else int(v)


def load_all(db_path=config.DB_PATH) -> int:
    conn = init_db(db_path)
    total = 0
    for code in config.season_codes():
        n = load_season(conn, code)
        if n:
            print(f"  {config.season_label(code)}: {n} matches loaded")
        total += n
    conn.close()
    return total


if __name__ == "__main__":
    print(f"Total matches loaded: {load_all()}")
