"""Chronological backtest: Dixon-Coles, Elo-logistic and their stacked ensemble
vs margin-removed market odds.

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
- The ensemble stacks {market, Dixon-Coles, Elo} log-probabilities with a
  multinomial logistic fitted, per test season, on earlier test seasons only.

Outputs per model: log loss, Brier score, accuracy, calibration table; plus a
flat-stake value simulation (paper only) priced both at closing and at
pre-match odds, the latter with closing-line value (CLV), and an explicit
verdict against the BUILD_PLAN Phase 7 promotion gate.
"""
from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

from . import config, dixon_coles, elo, ensemble
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


def market_probs(df: pd.DataFrame, prefer_closing: bool = True) -> np.ndarray:
    """Margin-removed 1X2 probabilities. prefer_closing=True (evaluation
    baseline) falls back to pre-match odds; prefer_closing=False uses
    pre-match odds only — the information actually available at bet time."""
    out = np.full((len(df), 3), np.nan)
    for i, r in enumerate(df.itertuples(index=False)):
        if prefer_closing:
            trio = (r.close_h, r.close_d, r.close_a) if pd.notna(r.close_h) else (r.pre_h, r.pre_d, r.pre_a)
        else:
            trio = (r.pre_h, r.pre_d, r.pre_a)
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


DOUBLE_CHANCE = {"1X": (0, 1), "X2": (1, 2), "12": (0, 2)}


def double_chance_metrics(probs: np.ndarray, results: pd.Series, mask: np.ndarray) -> dict[str, float]:
    """Binary Brier score per double-chance selection, probabilities derived from 1X2."""
    m = mask & ~np.isnan(probs).any(axis=1)
    y = results[m].map({o: k for k, o in enumerate(OUTCOMES)}).to_numpy()
    out = {}
    for name, (i, j) in DOUBLE_CHANCE.items():
        p = probs[m][:, i] + probs[m][:, j]
        hit = ((y == i) | (y == j)).astype(float)
        out[name] = float(((p - hit) ** 2).mean())
    return out


def value_simulation(df: pd.DataFrame, model_p: np.ndarray, mask: np.ndarray,
                     at_close: bool = True) -> dict:
    """Flat 1-unit paper stake on any outcome where model - implied >= EDGE_THRESHOLD.
    Diagnostic only, not a betting record.

    at_close=True: flag and settle at closing odds (pre-match fallback) — the
    plan's headline ROI. at_close=False: flag and settle at pre-match odds
    only, recording per-bet CLV = bet_odds / closing_odds - 1 where closing
    odds exist (did the line move our way before kickoff?).
    """
    odds_cols = {"H": ("close_h", "pre_h"), "D": ("close_d", "pre_d"), "A": ("close_a", "pre_a")}
    pnl, clv, results = [], [], df["result"]
    ok = mask & ~np.isnan(model_p).any(axis=1)
    for i in np.where(ok)[0]:
        if at_close:
            trio = [df[c].iloc[i] if pd.notna(df[c].iloc[i]) else df[p].iloc[i]
                    for c, p in odds_cols.values()]
        else:
            trio = [df[p].iloc[i] for _, p in odds_cols.values()]
        if any(pd.isna(v) for v in trio):
            continue
        market = implied_probs(*trio)
        for k, sel in enumerate(OUTCOMES):
            edge = model_p[i, k] - market[k]
            odds = trio[k]
            if edge >= EDGE_THRESHOLD and odds <= MAX_ODDS:
                pnl.append(odds - 1.0 if results.iloc[i] == sel else -1.0)
                close = df[odds_cols[sel][0]].iloc[i]
                if not at_close and pd.notna(close):
                    clv.append(odds / close - 1.0)
    pnl = np.array(pnl)
    if len(pnl) == 0:
        return {"bets": 0}
    equity = pnl.cumsum()
    out = {
        "bets": int(len(pnl)),
        "hit_rate": float((pnl > 0).mean()),
        "roi": float(pnl.mean()),
        "max_drawdown": float((np.maximum.accumulate(equity) - equity).max()),
    }
    if clv:
        clv = np.array(clv)
        out["clv_mean"] = float(clv.mean())
        out["clv_pos"] = float((clv > 0).mean())
        out["clv_n"] = int(len(clv))
    return out


def logloss_diff_vs_market(model_p: np.ndarray, market_p: np.ndarray,
                           results: pd.Series, mask: np.ndarray) -> dict:
    """Paired per-match log-loss difference (model - market): mean and its SE.
    Negative mean = model better; 'within noise' = |mean| < 2*SE when positive."""
    m = mask & ~np.isnan(model_p).any(axis=1) & ~np.isnan(market_p).any(axis=1)
    y = results[m].map({o: k for k, o in enumerate(OUTCOMES)}).to_numpy()
    rows = np.arange(len(y))
    lm = -np.log(np.clip(model_p[m], 1e-12, 1)[rows, y])
    lk = -np.log(np.clip(market_p[m], 1e-12, 1)[rows, y])
    d = lm - lk
    return {"n": int(len(d)), "mean": float(d.mean()),
            "se": float(d.std(ddof=1) / np.sqrt(len(d)))}


def calibration_error(probs: np.ndarray, results: pd.Series, mask: np.ndarray) -> float:
    """Weighted mean |predicted - actual| over the P(home) decile bins."""
    tab = calibration_table(probs, results, mask)
    return float((tab["n"] * (tab["mean_pred"] - tab["actual_rate"]).abs()).sum() / tab["n"].sum())


def run(db_path=config.DB_PATH, warmup_seasons: int = 3) -> str:
    df = load_matches(db_path)
    seasons = sorted(df["season"].unique())
    if len(seasons) <= warmup_seasons:
        raise SystemExit(f"Need more than {warmup_seasons} seasons; have {len(seasons)}")
    test_mask = df["season"].isin(seasons[warmup_seasons:]).to_numpy()

    mkt = market_probs(df)
    dc = dc_probs(df, test_mask)
    el = elo_probs(df, test_mask)
    # Two stacks: `ens` sees the closing-preferred market feature and is only
    # compared against the closing line (log loss / calibration); `ens_pre`
    # sees pre-match odds only, so it can honestly flag bets before the close.
    ens = ensemble.stack_probs(df, [mkt, dc, el], test_mask)
    ens_pre = ensemble.stack_probs(df, [market_probs(df, prefer_closing=False), dc, el], test_mask)

    common = test_mask & ~np.isnan(mkt).any(axis=1) & ~np.isnan(dc).any(axis=1) & ~np.isnan(el).any(axis=1)
    ens_mask = common & ~np.isnan(ens).any(axis=1)
    ens_pre_mask = common & ~np.isnan(ens_pre).any(axis=1)
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

    lines += ["", "## Double chance (derived from 1X2) — binary Brier score", "",
              "| model | 1X | X2 | 12 |", "|---|---|---|---|"]
    for name, p in (("market (margin-removed)", mkt), ("Dixon-Coles", dc)):
        s = double_chance_metrics(p, df["result"], common)
        lines.append(f"| {name} | {s['1X']:.4f} | {s['X2']:.4f} | {s['12']:.4f} |")

    lines += ["", "## Ensemble (Phase 6.3: logistic stacking of market + Dixon-Coles + Elo)", "",
              f"Stacker fitted per season on earlier test seasons only; "
              f"scored matches: {int(ens_mask.sum())} (earliest test season unscored — no training data).", ""]
    if ens_mask.any():
        lines += ["| model | n | log loss | Brier | accuracy |", "|---|---|---|---|---|"]
        for name, p in (("market (margin-removed)", mkt), ("Dixon-Coles", dc),
                        ("Elo + logistic", el), ("ensemble", ens)):
            s = metrics(p, df["result"], ens_mask)
            lines.append(f"| {name} | {s['n']} | {s['log_loss']:.4f} | {s['brier']:.4f} | {s['accuracy']:.3f} |")

    lines += ["", "## Calibration (P(home win) deciles)", ""]
    for name, p, m in (("Dixon-Coles", dc, common), ("ensemble", ens, ens_mask)):
        if not m.any():
            continue
        lines += [f"### {name}", "", "| bin | n | mean predicted | actual rate |", "|---|---|---|---|"]
        for r in calibration_table(p, df["result"], m).itertuples(index=False):
            lines.append(f"| {r.bin} | {r.n} | {r.mean_pred:.3f} | {r.actual_rate:.3f} |")
        lines.append("")

    lines += ["## Flat-stake value simulation (paper only)", "",
              "| model | priced at | bets | hit rate | ROI/bet | max drawdown | mean CLV | CLV>0 |",
              "|---|---|---|---|---|---|---|---|"]
    sims = {}
    for name, p, m, at_close in (("Dixon-Coles", dc, common, True),
                                 ("Dixon-Coles", dc, common, False),
                                 ("ensemble", ens, ens_mask, True),
                                 ("ensemble (pre-match features)", ens_pre, ens_pre_mask, False)):
        label = "closing" if at_close else "pre-match"
        s = sims[name, label] = value_simulation(df, p, m, at_close=at_close)
        if s["bets"] == 0:
            lines.append(f"| {name} | {label} | 0 | — | — | — | — | — |")
            continue
        clv = f"{s['clv_mean']:+.4f}" if "clv_mean" in s else "—"
        pos = f"{s['clv_pos']:.3f}" if "clv_pos" in s else "—"
        lines.append(
            f"| {name} | {label} | {s['bets']} | {s['hit_rate']:.3f} | {s['roi']:+.4f} | "
            f"{s['max_drawdown']:.1f} | {clv} | {pos} |")
    lines += ["", "_CLV = bet odds / closing odds − 1 on bets flagged and priced at pre-match odds: "
              "positive means the closing line moved towards our selection. Simulation at historical "
              "odds; past ROI does not predict future returns._"]

    # Promotion gate (BUILD_PLAN Phase 7): (a) calibrated, (b) log loss within
    # noise of or better than the market, (c) positive CLV on flagged bets.
    lines += ["", "## Gate verdict — promotion rule (BUILD_PLAN Phase 7)", ""]
    if not ens_mask.any():
        lines += ["Ensemble unscored (not enough test seasons); gate cannot be evaluated.",
                  "", "**Verdict: GATE NOT PASSED — predictions and coupons stay watch-only / paper-only.**"]
    else:
        ece = calibration_error(ens, df["result"], ens_mask)
        pass_a = ece <= 0.025
        dll = logloss_diff_vs_market(ens, mkt, df["result"], ens_mask)
        pass_b = dll["mean"] <= 0 or dll["mean"] < 2 * dll["se"]
        sim_pre = sims.get(("ensemble (pre-match features)", "pre-match"), {"bets": 0})
        pass_c = sim_pre.get("clv_mean", float("-inf")) > 0 and sim_pre["bets"] > 0
        clv_txt = (f"mean CLV {sim_pre['clv_mean']:+.4f} over {sim_pre.get('clv_n', 0)} bets"
                   if "clv_mean" in sim_pre else "no flagged pre-match bets with closing odds")
        lines += [
            "Candidate model: ensemble (market + Dixon-Coles + Elo stack).",
            "",
            f"- (a) calibrated: weighted decile calibration error {ece:.4f} "
            f"(threshold 0.025) — {'PASS' if pass_a else 'FAIL'}",
            f"- (b) log loss vs market: {dll['mean']:+.4f} ± {2 * dll['se']:.4f} (2·SE) per match — "
            f"{'PASS' if pass_b else 'FAIL'}",
            f"- (c) positive CLV on flagged bets: {clv_txt} — {'PASS' if pass_c else 'FAIL'}",
            "",
            ("**Verdict: GATE PASSED on this window. Re-check after every retrain; "
             "recommendations remain paper-traded for one full cycle before any stake.**"
             if pass_a and pass_b and pass_c else
             "**Verdict: GATE NOT PASSED — predictions and coupons stay watch-only / paper-only.**"),
        ]

    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = config.REPORTS_DIR / "backtest_report.md"
    out.write_text("\n".join(lines) + "\n")
    return str(out)


if __name__ == "__main__":
    print(f"Report written to {run()}")
