"""End-to-end pipeline self-test on synthetic data.

Generates several seasons of fake fixtures in football-data.co.uk CSV format
(Poisson goals from latent team strengths; bookmaker odds = true probabilities
+ noise + 5% margin), then runs load -> backtest against a temp database.

This validates the code path only. It says nothing about real-world edge —
in synthetic data the 'bookmaker' knows the true model, as in reality.
"""
from __future__ import annotations

import shutil
import sqlite3

import numpy as np
import pandas as pd

from . import config, backtest, load

RNG = np.random.default_rng(7)
TEAM_NAMES = [f"Team {chr(65 + i)}" for i in range(20)]


def _season_fixtures(start_year: int) -> pd.DataFrame:
    strengths = {t: RNG.normal(0, 0.35) for t in TEAM_NAMES}
    rows = []
    pairs = [(h, a) for h in TEAM_NAMES for a in TEAM_NAMES if h != a]
    RNG.shuffle(pairs)
    date = pd.Timestamp(f"{start_year}-08-09")
    for k, (h, a) in enumerate(pairs):
        if k and k % 10 == 0:
            date += pd.Timedelta(days=7)
        lam = np.exp(0.20 + strengths[h] - strengths[a] + np.log(1.35))
        mu = np.exp(strengths[a] - strengths[h] + np.log(1.15))
        gh, ga = RNG.poisson(lam), RNG.poisson(mu)
        i = np.arange(11)
        from scipy.stats import poisson
        p = np.outer(poisson.pmf(i, lam), poisson.pmf(i, mu))
        truth = np.array([np.tril(p, -1).sum(), np.trace(p), np.triu(p, 1).sum()])
        noisy = np.clip(truth + RNG.normal(0, 0.02, 3), 0.02, None)
        book = noisy / noisy.sum() * 1.05  # 5% overround
        oh, od, oa = (1.0 / book).round(2)
        rows.append({
            "Div": "E0", "Date": date.strftime("%d/%m/%Y"),
            "HomeTeam": h, "AwayTeam": a, "FTHG": gh, "FTAG": ga,
            "FTR": "H" if gh > ga else ("A" if ga > gh else "D"),
            "HTHG": min(gh, 1), "HTAG": min(ga, 1), "HTR": "D",
            "HS": gh + RNG.integers(5, 15), "AS": ga + RNG.integers(4, 12),
            "HST": gh + RNG.integers(1, 6), "AST": ga + RNG.integers(1, 5),
            "HC": RNG.integers(2, 10), "AC": RNG.integers(2, 9),
            "HF": RNG.integers(6, 14), "AF": RNG.integers(6, 14),
            "HY": RNG.integers(0, 4), "AY": RNG.integers(0, 4), "HR": 0, "AR": 0,
            "B365H": oh, "B365D": od, "B365A": oa,
            "AvgH": oh, "AvgD": od, "AvgA": oa,
            "PSCH": oh, "PSCD": od, "PSCA": oa,
        })
    return pd.DataFrame(rows)


def run() -> None:
    tmp = config.DATA_DIR / "selftest"
    shutil.rmtree(tmp, ignore_errors=True)
    (tmp / "raw").mkdir(parents=True)
    db = tmp / "football.sqlite"

    # Point the pipeline at the sandbox dirs for the duration of the test.
    real_raw, real_db = config.RAW_DIR, config.DB_PATH
    config.RAW_DIR, config.DB_PATH = tmp / "raw", db
    try:
        for code in config.season_codes()[:6]:
            year = 2000 + int(code[:2])
            _season_fixtures(year).to_csv(config.RAW_DIR / f"E0_{code}.csv", index=False)
        n = load.load_all(db)
        assert n == 6 * 380, f"expected {6 * 380} matches, loaded {n}"

        conn = sqlite3.connect(db)
        odds_n = conn.execute("SELECT COUNT(*) FROM odds").fetchone()[0]
        teams_n = conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
        conn.close()
        assert teams_n == 20 and odds_n > 0

        report = backtest.run(db, warmup_seasons=3)
        print(f"\nSelf-test PASSED: {n} matches, {teams_n} teams, {odds_n} odds rows")
        print(f"Report: {report}")
        print("\n" + open(report).read())
    finally:
        config.RAW_DIR, config.DB_PATH = real_raw, real_db


if __name__ == "__main__":
    run()
