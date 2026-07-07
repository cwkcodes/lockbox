"""Phase 6.3 stacking: multinomial logistic blend of base-model 1X2 probabilities.

Features are the log-probabilities of each base model (market, Dixon-Coles,
Elo). For each test season the stacker is fitted only on earlier test seasons'
out-of-sample base predictions — every base probability was itself produced
using only pre-match information, and the blend weights never see the season
being scored. The earliest test season has no stacking training data and is
left unscored (NaN) for the ensemble.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MIN_TRAIN_ROWS = 300  # roughly one season of usable matches

OUTCOMES = ("H", "D", "A")


def _features(base_probs: list[np.ndarray]) -> np.ndarray:
    return np.hstack([np.log(np.clip(p, 1e-9, 1.0)) for p in base_probs])


def stack_probs(df: pd.DataFrame, base_probs: list[np.ndarray], test_mask: np.ndarray) -> np.ndarray:
    """Rolling-origin stacked probabilities; NaN where unscored.

    df needs 'season' (sortable chronologically) and 'result' columns; each
    array in base_probs is (n, 3) H/D/A with NaN where that model is silent.
    """
    from sklearn.linear_model import LogisticRegression

    x = _features(base_probs)
    ok = test_mask & ~np.isnan(x).any(axis=1)
    y = df["result"].map({o: k for k, o in enumerate(OUTCOMES)}).to_numpy()
    season = df["season"].to_numpy()
    out = np.full((len(df), 3), np.nan)
    for s in sorted(pd.unique(season[ok])):
        train = ok & (season < s)
        if train.sum() < MIN_TRAIN_ROWS:
            continue
        score = ok & (season == s)
        clf = LogisticRegression(max_iter=2000).fit(x[train], y[train])
        proba = clf.predict_proba(x[score])
        for k, cls in enumerate(clf.classes_):
            out[np.where(score)[0], cls] = proba[:, k]
    return out
