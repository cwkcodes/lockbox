"""Dixon-Coles (1997) time-decayed bivariate Poisson-style model for football scores.

log(lambda_home) = home_adv + attack[home] - defence[away]
log(mu_away)     =            attack[away] - defence[home]
with the Dixon-Coles tau correction for low-scoring dependence (rho) and
exponential time-decay weights w = exp(-xi * days_before_fit_date).

Fitting maximises the weighted log-likelihood with scipy L-BFGS; attack
ratings are soft-constrained to mean zero for identifiability.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

MAX_GOALS = 10
DEFAULT_XI = 0.0019  # per day; ~half-weight after one year, per Dixon-Coles literature


def _tau(lam, mu, x, y, rho):
    """Vectorised DC low-score correction."""
    t = np.ones_like(lam)
    t = np.where((x == 0) & (y == 0), 1 - lam * mu * rho, t)
    t = np.where((x == 0) & (y == 1), 1 + lam * rho, t)
    t = np.where((x == 1) & (y == 0), 1 + mu * rho, t)
    t = np.where((x == 1) & (y == 1), 1 - rho, t)
    return np.maximum(t, 1e-10)


@dataclass
class DixonColesModel:
    teams: list[int]
    attack: dict[int, float]
    defence: dict[int, float]
    home_adv: float
    rho: float

    def rates(self, home_id: int, away_id: int) -> tuple[float, float]:
        lam = np.exp(self.home_adv + self.attack[home_id] - self.defence[away_id])
        mu = np.exp(self.attack[away_id] - self.defence[home_id])
        return float(lam), float(mu)

    def score_matrix(self, home_id: int, away_id: int) -> np.ndarray:
        """P(home goals = i, away goals = j) for i, j in [0, MAX_GOALS]."""
        lam, mu = self.rates(home_id, away_id)
        i = np.arange(MAX_GOALS + 1)
        from scipy.stats import poisson
        p = np.outer(poisson.pmf(i, lam), poisson.pmf(i, mu))
        for x in (0, 1):
            for y in (0, 1):
                p[x, y] *= _tau(np.array(lam), np.array(mu), np.array(x), np.array(y), self.rho)
        return p / p.sum()

    def outcome_probs(self, home_id: int, away_id: int) -> np.ndarray:
        """[P(H), P(D), P(A)] — double chance, O/U and BTTS derive from score_matrix."""
        p = self.score_matrix(home_id, away_id)
        home = np.tril(p, -1).sum()
        draw = np.trace(p)
        return np.array([home, draw, 1.0 - home - draw])


def fit(matches: pd.DataFrame, fit_date: pd.Timestamp, xi: float = DEFAULT_XI) -> DixonColesModel:
    """Fit on matches strictly before fit_date. Requires columns
    date (datetime), home_team_id, away_team_id, ft_home, ft_away."""
    df = matches[matches["date"] < fit_date]
    teams = sorted(set(df["home_team_id"]) | set(df["away_team_id"]))
    idx = {t: k for k, t in enumerate(teams)}
    n = len(teams)

    h = df["home_team_id"].map(idx).to_numpy()
    a = df["away_team_id"].map(idx).to_numpy()
    gh = df["ft_home"].to_numpy(dtype=float)
    ga = df["ft_away"].to_numpy(dtype=float)
    days = (fit_date - df["date"]).dt.days.to_numpy(dtype=float)
    w = np.exp(-xi * days)

    from scipy.special import gammaln

    def nll(params):
        att, dfc = params[:n], params[n:2 * n]
        home_adv, rho = params[2 * n], params[2 * n + 1]
        log_lam = home_adv + att[h] - dfc[a]
        log_mu = att[a] - dfc[h]
        lam, mu = np.exp(log_lam), np.exp(log_mu)
        ll = (
            gh * log_lam - lam - gammaln(gh + 1)
            + ga * log_mu - mu - gammaln(ga + 1)
            + np.log(_tau(lam, mu, gh, ga, rho))
        )
        return -(w * ll).sum() + 100.0 * att.mean() ** 2  # soft mean-zero identifiability

    x0 = np.concatenate([np.zeros(2 * n), [0.25, -0.05]])
    bounds = [(-3, 3)] * (2 * n) + [(-1, 1), (-0.5, 0.5)]
    res = minimize(nll, x0, method="L-BFGS-B", bounds=bounds,
                   options={"maxiter": 400, "ftol": 1e-9})
    att, dfc = res.x[:n], res.x[n:2 * n]
    return DixonColesModel(
        teams=teams,
        attack={t: float(att[idx[t]]) for t in teams},
        defence={t: float(dfc[idx[t]]) for t in teams},
        home_adv=float(res.x[2 * n]),
        rho=float(res.x[2 * n + 1]),
    )
