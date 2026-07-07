"""Phase 8 — prediction cards for upcoming (scheduled) fixtures.

Fits Dixon-Coles on all played matches, then for every scheduled fixture in the
database produces 1X2, double-chance, over/under 2.5 and BTTS probabilities,
compares 1X2 against margin-removed bookmaker odds where available, writes rows
to the predictions table and renders a markdown card per match.

Recommended actions are gated: until the backtest gate has been passed on real
(non-synthetic) unseen data, everything is capped at 'watch_only'. Pass
gate_passed=True (CLI: --gate-passed) only after reviewing a real backtest
report that shows calibration and positive value performance.

Upcoming fixtures enter the DB via load_fixtures_csv: a CSV with columns
Date (dd/mm/yyyy), HomeTeam, AwayTeam and optionally B365H/B365D/B365A (or
AvgH/AvgD/AvgA) current odds, using football-data.co.uk team spellings.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import config, dixon_coles
from .backtest import EDGE_THRESHOLD, OUTCOMES, load_matches
from .market import implied_probs

MODEL_VERSION = "dc-v0.1"


def load_fixtures_csv(path, db_path=config.DB_PATH) -> int:
    """Insert scheduled fixtures (and any provided 1X2 odds) from a CSV."""
    from .load import _team_id, parse_dates

    df = pd.read_csv(path)
    df["date"] = parse_dates(df["Date"])
    conn = sqlite3.connect(db_path)
    cache: dict = {}
    n = 0
    for _, r in df.iterrows():
        home_id = _team_id(conn, r["HomeTeam"], cache)
        away_id = _team_id(conn, r["AwayTeam"], cache)
        season = _season_of(r["date"])
        cur = conn.execute(
            "INSERT OR IGNORE INTO matches (competition_id, season, date_utc, home_team_id, "
            "away_team_id, status) VALUES (?, ?, ?, ?, ?, 'scheduled')",
            (config.COMPETITION_ID, season, r["date"].strftime("%Y-%m-%d"), home_id, away_id),
        )
        if cur.rowcount == 0:
            continue
        n += 1
        for book, cols in (("B365", ("B365H", "B365D", "B365A")), ("market_avg", ("AvgH", "AvgD", "AvgA"))):
            vals = [pd.to_numeric(r.get(c), errors="coerce") for c in cols]
            if any(pd.isna(v) or v <= 1.0 for v in vals):
                continue
            for sel, odd in zip(OUTCOMES, vals):
                conn.execute(
                    "INSERT INTO odds (match_id, bookmaker, is_closing, market, selection, decimal_odds) "
                    "VALUES (?, ?, 0, '1X2', ?, ?)", (cur.lastrowid, book, sel, float(odd)),
                )
    conn.commit()
    conn.close()
    return n


def _season_of(date: pd.Timestamp) -> str:
    start = date.year if date.month >= 7 else date.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def _team_names(conn) -> dict[int, str]:
    return dict(conn.execute("SELECT team_id, canonical_name FROM teams").fetchall())


def _scheduled(conn) -> pd.DataFrame:
    df = pd.read_sql_query(
        """
        SELECT m.match_id, m.date_utc AS date, m.home_team_id, m.away_team_id,
               o.h AS odds_h, o.d AS odds_d, o.a AS odds_a
        FROM matches m
        LEFT JOIN (
            SELECT match_id,
                   MAX(CASE selection WHEN 'H' THEN decimal_odds END) h,
                   MAX(CASE selection WHEN 'D' THEN decimal_odds END) d,
                   MAX(CASE selection WHEN 'A' THEN decimal_odds END) a
            FROM odds WHERE market='1X2' AND is_closing=0 GROUP BY match_id
        ) o ON o.match_id = m.match_id
        WHERE m.status='scheduled' ORDER BY m.date_utc
        """,
        conn,
    )
    df["date"] = pd.to_datetime(df["date"])
    return df


def run(db_path=config.DB_PATH, gate_passed: bool = False) -> str | None:
    played = load_matches(db_path)
    conn = sqlite3.connect(db_path)
    fixtures = _scheduled(conn)
    if fixtures.empty:
        conn.close()
        print("No scheduled fixtures in the database (see load_fixtures_csv).")
        return None
    names = _team_names(conn)
    model = dixon_coles.fit(played, fit_date=fixtures["date"].min())
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cards = ["# Prediction cards", f"Model: {MODEL_VERSION} (Dixon-Coles) | generated {created_at}",
             "" if gate_passed else
             "\n> **Backtest gate NOT passed** — all recommendations capped at *watch only*. "
             "No real-money action is suggested.\n"]
    for r in fixtures.itertuples(index=False):
        if r.home_team_id not in model.attack or r.away_team_id not in model.attack:
            cards.append(f"## {names[r.home_team_id]} v {names[r.away_team_id]} — insufficient history, skipped\n")
            continue
        p = model.outcome_probs(r.home_team_id, r.away_team_id)
        sm = model.score_matrix(r.home_team_id, r.away_team_id)
        over25 = 1.0 - sum(sm[i, j] for i in range(3) for j in range(3 - i))
        btts = 1.0 - sm[0, :].sum() - sm[:, 0].sum() + sm[0, 0]
        flat = [((i, j), sm[i, j]) for i in range(sm.shape[0]) for j in range(sm.shape[1])]
        top_scores = sorted(flat, key=lambda t: -t[1])[:3]

        has_odds = pd.notna(r.odds_h)
        implied = implied_probs(r.odds_h, r.odds_d, r.odds_a) if has_odds else None
        edges = p - implied if has_odds else None
        best = int(np.argmax(edges)) if has_odds else None
        if not gate_passed:
            action = "watch_only"
        elif not has_odds:
            action = "wait_for_lineups"
        elif edges[best] >= EDGE_THRESHOLD:
            action = f"bet ({OUTCOMES[best]})"
        elif edges.max() < -EDGE_THRESHOLD:
            action = "avoid"
        else:
            action = "watch_only"

        home, away = names[r.home_team_id], names[r.away_team_id]
        cards += [
            f"## {home} v {away} — {r.date.date()}",
            "",
            "| market | model | implied (margin-removed) | edge |",
            "|---|---|---|---|",
        ]
        for k, label in enumerate(("Home win", "Draw", "Away win")):
            imp = f"{implied[k]:.3f}" if has_odds else "n/a"
            edg = f"{edges[k]:+.3f}" if has_odds else "n/a"
            cards.append(f"| {label} | {p[k]:.3f} | {imp} | {edg} |")
        cards += [
            f"| Double chance 1X | {p[0] + p[1]:.3f} | — | — |",
            f"| Double chance X2 | {p[1] + p[2]:.3f} | — | — |",
            f"| Double chance 12 | {p[0] + p[2]:.3f} | — | — |",
            f"| Over 2.5 goals | {over25:.3f} | — | — |",
            f"| BTTS yes | {btts:.3f} | — | — |",
            "",
            "Most likely scores: " + ", ".join(f"{i}-{j} ({q:.1%})" for (i, j), q in top_scores),
            f"Recommended action: **{action}**",
            "",
        ]
        for market, sel, mp in (
            [("1X2", OUTCOMES[k], p[k]) for k in range(3)]
            + [("DC", "1X", p[0] + p[1]), ("DC", "X2", p[1] + p[2]), ("DC", "12", p[0] + p[2]),
               ("OU2.5", "over", over25), ("BTTS", "yes", btts)]
        ):
            k = OUTCOMES.index(sel) if market == "1X2" else None
            conn.execute(
                "INSERT INTO predictions (match_id, model_version, created_at, market, selection, "
                "model_prob, implied_prob, edge, confidence, recommended_action) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (r.match_id, MODEL_VERSION, created_at, market, sel, float(mp),
                 float(implied[k]) if has_odds and k is not None else None,
                 float(edges[k]) if has_odds and k is not None else None,
                 "medium" if has_odds else "low", action),
            )
    conn.commit()
    conn.close()

    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = config.REPORTS_DIR / "predictions.md"
    out.write_text("\n".join(cards) + "\n")
    return str(out)


if __name__ == "__main__":
    import sys
    path = run(gate_passed="--gate-passed" in sys.argv)
    if path:
        print(f"Cards written to {path}")
