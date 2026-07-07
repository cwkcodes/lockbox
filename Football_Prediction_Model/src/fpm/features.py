"""Phase 5 (v0.1 subset): leak-free pre-match rolling form features.

Everything is computed from information strictly before kick-off: rolling
means use shift(1) within each team's date-ordered match log, so a match never
contributes to its own features. Missing history (season starts, promoted
teams with no prior rows) stays NaN — the GBM handles NaN natively, nothing is
imputed.

Feature set per match: home-minus-away differences of rolling means (points,
goals for/against, shots, shots on target, corners, all for and against) over
the last 5 and 10 matches, venue-specific (home-at-home vs away-at-away)
points and goal difference over the last 5, rest days each side, and the
pre-match Elo difference.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import elo

WINDOWS = (5, 10)
VENUE_WINDOW = 5
FORM_COLS = ("points", "gf", "ga", "sf", "sa", "stf", "sta", "cf", "ca")


def team_log(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (match, team), date-ordered: goals/shots/SoT/corners for and against."""
    sides = []
    for is_home, us, them in ((1, "home", "away"), (0, "away", "home")):
        sides.append(pd.DataFrame({
            "match_id": df["match_id"],
            "date": df["date"],
            "team": df[f"{us}_team_id"],
            "is_home": is_home,
            "gf": df[f"ft_{us}"], "ga": df[f"ft_{them}"],
            "sf": df[f"{us}_shots"], "sa": df[f"{them}_shots"],
            "stf": df[f"{us}_sot"], "sta": df[f"{them}_sot"],
            "cf": df[f"{us}_corners"], "ca": df[f"{them}_corners"],
        }))
    log = pd.concat(sides, ignore_index=True).sort_values(["date", "match_id"], kind="stable")
    log["points"] = np.where(log["gf"] > log["ga"], 3.0, np.where(log["gf"] == log["ga"], 1.0, 0.0))
    return log.reset_index(drop=True)


def _rolling_before(grouped, col: str, window: int) -> pd.Series:
    return grouped[col].transform(lambda s: s.shift(1).rolling(window, min_periods=window).mean())


def build(df: pd.DataFrame) -> pd.DataFrame:
    """Feature matrix aligned to df's rows (df must be date-sorted, as loaded)."""
    log = team_log(df)
    by_team = log.groupby("team", sort=False)
    feats = pd.DataFrame(index=log.index)
    feats["rest_days"] = (log["date"] - by_team["date"].shift(1)).dt.days
    for w in WINDOWS:
        for col in FORM_COLS:
            feats[f"{col}_{w}"] = _rolling_before(by_team, col, w)
    # Venue-specific recent form: the home side's last home matches vs the
    # away side's last away matches.
    by_venue = log.groupby(["team", "is_home"], sort=False)
    for col in ("points", "gf", "ga"):
        feats[f"{col}_venue"] = _rolling_before(by_venue, col, VENUE_WINDOW)

    feats["match_id"] = log["match_id"]
    feats["is_home"] = log["is_home"]
    home = feats[feats["is_home"] == 1].set_index("match_id")
    away = feats[feats["is_home"] == 0].set_index("match_id")

    out = pd.DataFrame(index=df["match_id"])
    for c in feats.columns.drop(["match_id", "is_home"]):
        out[f"d_{c}"] = home[c] - away[c]
    out["rest_home"] = home["rest_days"]
    out["rest_away"] = away["rest_days"]
    out["elo_diff"] = elo.compute_elo(df)["elo_diff"].to_numpy()
    return out.reset_index(drop=True)
