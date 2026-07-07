"""Sequential Elo ratings computed from results only (leak-free by construction).

Ratings are updated match by match in date order; the rating pair attached to a
match is always the PRE-match rating. The Elo->1X2 mapping is fitted separately
(multinomial logistic on Elo difference) on training data only, in backtest.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BASE_RATING = 1500.0
K = 20.0
HOME_ADV = 60.0  # Elo points added to the home side inside the expected-score formula


def margin_multiplier(goal_diff: int) -> float:
    return 1.0 if abs(goal_diff) <= 1 else 1.0 + 0.5 * (abs(goal_diff) - 1)


def compute_elo(matches: pd.DataFrame) -> pd.DataFrame:
    """matches: date-sorted DataFrame with home_team_id, away_team_id, ft_home, ft_away.

    Returns a copy with elo_home, elo_away, elo_diff (all pre-match).
    """
    ratings: dict[int, float] = {}
    eh, ea = np.empty(len(matches)), np.empty(len(matches))
    for i, r in enumerate(matches.itertuples(index=False)):
        rh = ratings.get(r.home_team_id, BASE_RATING)
        ra = ratings.get(r.away_team_id, BASE_RATING)
        eh[i], ea[i] = rh, ra
        exp_home = 1.0 / (1.0 + 10 ** (-(rh + HOME_ADV - ra) / 400.0))
        score_home = 0.5 if r.ft_home == r.ft_away else float(r.ft_home > r.ft_away)
        delta = K * margin_multiplier(r.ft_home - r.ft_away) * (score_home - exp_home)
        ratings[r.home_team_id] = rh + delta
        ratings[r.away_team_id] = ra - delta
    out = matches.copy()
    out["elo_home"], out["elo_away"] = eh, ea
    out["elo_diff"] = eh - ea
    return out
