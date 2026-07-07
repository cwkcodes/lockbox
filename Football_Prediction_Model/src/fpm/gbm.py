"""Phase 6.2 ML layer: gradient boosting on the Phase 5 rolling-form features.

sklearn's HistGradientBoostingClassifier (native NaN handling, no extra
dependency) fitted rolling-origin: for each test season, train on all matches
strictly before that season's first fixture. Stats-only — no odds features —
so its probabilities are independent of the market baseline and available at
bet time.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import features

OUTCOMES = ("H", "D", "A")
MIN_TRAIN_ROWS = 500


def gbm_probs(df: pd.DataFrame, test_mask: np.ndarray) -> np.ndarray:
    from sklearn.ensemble import HistGradientBoostingClassifier

    feats = features.build(df)
    # All-NaN or constant columns (e.g. xG when no Understat data is loaded)
    # crash HistGradientBoosting's binning; they carry nothing anyway.
    x = feats.loc[:, feats.nunique(dropna=True) > 1].to_numpy(dtype=float)
    y = df["result"].map({o: k for k, o in enumerate(OUTCOMES)}).to_numpy()
    season = df["season"].to_numpy()
    out = np.full((len(df), 3), np.nan)
    for s in sorted(pd.unique(season[test_mask])):
        train = (season < s) & ~pd.isna(df["result"]).to_numpy()
        if train.sum() < MIN_TRAIN_ROWS:
            continue
        score = test_mask & (season == s)
        # Heavily regularised: with ~20 noisy form features and a few
        # thousand rows, anything bigger is overconfident (worse than a
        # uniform prior at default settings). The early-stopping split is a
        # random subset of pre-season training rows, never test data.
        clf = HistGradientBoostingClassifier(
            max_iter=400, learning_rate=0.03, max_leaf_nodes=7,
            min_samples_leaf=50, l2_regularization=10.0,
            early_stopping=True, validation_fraction=0.15, n_iter_no_change=20,
            random_state=0,
        ).fit(x[train], y[train])
        proba = clf.predict_proba(x[score])
        for k, cls in enumerate(clf.classes_):
            out[np.where(score)[0], cls] = proba[:, k]
    return out
