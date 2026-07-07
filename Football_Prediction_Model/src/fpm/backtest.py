"""Chronological backtest: Dixon-Coles vs Elo-logistic vs margin-removed market odds.

Protocol (no random splits, no leakage):
- Matches sorted by date. The first `warmup_seasons` seasons are never scored.
- Dixon-Coles is refitted every `refit_days` using only matches before the
  refit date; each match is predicted with the most recent model fitted
  strictly before its date.
- The Elo baseline attaches pre-match ratings sequentially, then a multinomial
  logistic (elo_diff -> H/D/A) is fitted, for each test season, on matches
  before that season only.
- The market baseline uses closing odds where present, else pre-match odds,
  margin-removed proportionally.

Outputs per model: log loss, Brier score, accuracy, calibration table; plus a
flat-stake value simulation of Dixon-Coles vs the market (paper only).
"""
from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

from . import config, dixon_coles, elo
from .market import implied_probs

OUTCOMES = ("H", "D", "A")
EDGE_THRESHOLD = 0.04  # model prob must exceed implied by 4pp to flag value
MAX_ODDS = 6.0         # skip long shots in the value sim: variance, and edge is likely model error


def load_matches(db_path=config.DB_PATH) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        """
        SELECT m.match_id, m.season, m.date_utc AS date, m.home_team_id, m.away_team_id,
               m.ft_home, m.ft_away, m.result,
               oc.h AS close_h, oc.d AS close_d, oc.a AS close_a,
               op.h AS pre_h,   op.d AS pre_d,   op.a AS pre_a
        FROM matches m
        LEFT JOIN (
            SELECT match_id,
                   MAX(CASE selection WHEN 'H' THEN decimal_odds END) h,
                   MAX(CASE selection WHEN 'D' THEN decimal_odds END) d,
                   MAX(CASE selection WHEN 'A' THEN decimal_odds END) a
            FROM odds WHERE market='1X2' AND is_closing=1 AND bookmaker IN ('Pinnacle','market_avg')
            GROUP BY match_id
        ) oc ON oc.match_id = m.match_id
        LEFT JOIN (
            SELECT match_id,
                   MAX(CASE selection WHEN 'H' THEN decimal_odds END) h,
                   MAX(CASE selection WHEN 'D' THEN decimal_odds END) d,
                   MAX(CASE selection WHEN 'A' THEN decimal_odds END) a
            FROM odds WHERE market='1X2' AND is_closing=0 AND bookmaker IN ('market_avg','Pinnacle')
            GROUP BY match_id
        ) op ON op.match_id = m.match_id
        WHERE m.status = 'played'
        ORDER BY m.date_utc, m.match_id
        """,
        conn,
    )
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    return df


def market_probs(df: pd.DataFrame) -> np.ndarray:
    out = np.full((len(df), 3), np.nan)
    for i, r in enumerate(df.itertuples(index=False)):
        trio = (r.close_h, r.close_d, r.close_a) if pd.notna(r.close_h) else (r.pre_h, r.pre_d, r.pre_a)
        if pd.notna(trio[0]):
            out[i] = implied_probs(*trio)
    return out


def dc_probs(df: pd.DataFrame, test_mask: np.ndarray, refit_days: int = 30) -> np.ndarray:
    out = np.full((len(df), 3), np.nan)
    model, model_date = None, None
    for i in np.where(test_mask)[0]:
        date = df["date"].iloc[i]
        if model is None or (date - model_date).days >= refit_days:
            model, model_date = dixon_coles.fit(df, fit_date=date), date
        h, a = df["home_team_id"].iloc[i], df["away_team_id"].iloc[i]
        if h in model.attack and a in model.attack:
            out[i] = model.outcome_probs(h, a)
    return out


def elo_probs(df: pd.DataFrame, test_mask: np.ndarray) -> np.ndarray:
    from sklearn.linear_model import LogisticRegression

    rated = elo.compute_elo(df)
    y = rated["result"].map({o: k for k, o in enumerate(OUTCOMES)}).to_numpy()
    x = rated[["elo_diff"]].to_numpy()
    out = np.full((len(df), 3), np.nan)
    for season in rated.loc[test_mask, "season"].unique():
        train = (rated["season"] < season).to_numpy()
        score = (rated["season"] == season).to_numpy() & test_mask
        clf = LogisticRegression(max_iter=1000).fit(x[train], y[train])
        proba = clf.predict_proba(x[score])
        for k, cls in enumerate(clf.classes_):
            out[np.where(score)[0], cls] = proba[:, k]
    return out


def metrics(probs: np.ndarray, results: pd.Series, mask: np.ndarray) -> dict:
    m = mask & ~np.isnan(probs).any(axis=1)
    y = results[m].map({o: k for k, o in enumerate(OUTCOMES)}).to_numpy()
    p = np.clip(probs[m], 1e-12, 1)
    onehot = np.eye(3)[y]
    return {
        "n": int(m.sum()),
        "log_loss": float(-np.log(p[np.arange(len(y)), y]).mean()),
        "brier": float(((p - onehot) ** 2).sum(axis=1).mean()),
        "accuracy": float((p.argmax(axis=1) == y).mean()),
    }


def calibration_table(probs: np.ndarray, results: pd.Series, mask: np.ndarray, bins: int = 10) -> pd.DataFrame:
    m = mask & ~np.isnan(probs).any(axis=1)
    p_home = probs[m][:, 0]
    won = (results[m] == "H").to_numpy(dtype=float)
    cut = pd.cut(p_home, np.linspace(0, 1, bins + 1), include_lowest=True)
    return pd.DataFrame({"bin": cut, "pred": p_home, "actual": won}).groupby(
        "bin", observed=True).agg(n=("actual", "size"), mean_pred=("pred", "mean"),
                                  actual_rate=("actual", "mean")).reset_index()


def value_simulation(df: pd.DataFrame, model_p: np.ndarray, market_p: np.ndarray,
                     mask: np.ndarray) -> dict:
    """Flat 1-unit paper stake on any outcome where model - market >= EDGE_THRESHOLD,
    settled at closing (or pre-match) odds. Diagnostic only, not a betting record."""
    odds_cols = {"H": ("close_h", "pre_h"), "D": ("close_d", "pre_d"), "A": ("close_a", "pre_a")}
    pnl, results = [], df["result"]
    ok = mask & ~np.isnan(model_p).any(axis=1) & ~np.isnan(market_p).any(axis=1)
    for i in np.where(ok)[0]:
        for k, sel in enumerate(OUTCOMES):
            edge = model_p[i, k] - market_p[i, k]
            close, pre = odds_cols[sel]
            odds = df[close].iloc[i] if pd.notna(df[close].iloc[i]) else df[pre].iloc[i]
            if edge >= EDGE_THRESHOLD and odds <= MAX_ODDS:
                pnl.append(odds - 1.0 if results.iloc[i] == sel else -1.0)
    pnl = np.array(pnl)
    if len(pnl) == 0:
        return {"bets": 0}
    equity = pnl.cumsum()
    return {
        "bets": int(len(pnl)),
        "hit_rate": float((pnl > 0).mean()),
        "roi": float(pnl.mean()),
        "max_drawdown": float((np.maximum.accumulate(equity) - equity).max()),
    }


def run(db_path=config.DB_PATH, warmup_seasons: int = 3) -> str:
    df = load_matches(db_path)
    seasons = sorted(df["season"].unique())
    if len(seasons) <= warmup_seasons:
        raise SystemExit(f"Need more than {warmup_seasons} seasons; have {len(seasons)}")
    test_mask = df["season"].isin(seasons[warmup_seasons:]).to_numpy()

    mkt = market_probs(df)
    dc = dc_probs(df, test_mask)
    el = elo_probs(df, test_mask)

    common = test_mask & ~np.isnan(mkt).any(axis=1) & ~np.isnan(dc).any(axis=1) & ~np.isnan(el).any(axis=1)
    lines = [
        "# Backtest report",
        f"Matches: {len(df)} | seasons: {seasons[0]}..{seasons[-1]} | "
        f"test seasons: {', '.join(seasons[warmup_seasons:])} | scored matches: {int(common.sum())}",
        "",
        "| model | n | log loss | Brier | accuracy |",
        "|---|---|---|---|---|",
    ]
    for name, p in (("market (margin-removed)", mkt), ("Dixon-Coles", dc), ("Elo + logistic", el)):
        s = metrics(p, df["result"], common)
        lines.append(f"| {name} | {s['n']} | {s['log_loss']:.4f} | {s['brier']:.4f} | {s['accuracy']:.3f} |")

    lines += ["", "## Dixon-Coles calibration (P(home win) deciles)", "",
              "| bin | n | mean predicted | actual rate |", "|---|---|---|---|"]
    for r in calibration_table(dc, df["result"], common).itertuples(index=False):
        lines.append(f"| {r.bin} | {r.n} | {r.mean_pred:.3f} | {r.actual_rate:.3f} |")

    sim = value_simulation(df, dc, mkt, common)
    lines += ["", "## Flat-stake value simulation (Dixon-Coles vs market, paper only)", ""]
    if sim["bets"] == 0:
        lines.append("No selections cleared the edge threshold.")
    else:
        lines.append(
            f"Bets: {sim['bets']} | hit rate: {sim['hit_rate']:.3f} | "
            f"ROI/bet: {sim['roi']:+.4f} units | max drawdown: {sim['max_drawdown']:.1f} units"
        )
    lines += ["", "_Simulation at historical closing odds; past ROI does not predict future returns. "
              "Recommendations stay 'watch only' unless calibration holds and ROI/CLV is positive "
              "on the untouched test window._"]

    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = config.REPORTS_DIR / "backtest_report.md"
    out.write_text("\n".join(lines) + "\n")
    return str(out)


if __name__ == "__main__":
    print(f"Report written to {run()}")
