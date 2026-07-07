"""Bookmaker odds -> margin-removed implied probabilities."""
from __future__ import annotations

import numpy as np


def implied_probs(odds_h: float, odds_d: float, odds_a: float) -> np.ndarray:
    """Proportional (basic) margin removal: normalise inverse odds to sum to 1."""
    inv = np.array([1.0 / odds_h, 1.0 / odds_d, 1.0 / odds_a])
    return inv / inv.sum()


def overround(odds_h: float, odds_d: float, odds_a: float) -> float:
    return 1.0 / odds_h + 1.0 / odds_d + 1.0 / odds_a - 1.0
