"""Phase 9 — conservative coupon builder.

Screens the latest batch of 1X2 predictions (the only market we hold real
bookmaker prices for in v0.1) and proposes at most one coupon:

- candidate legs need edge >= EDGE_THRESHOLD, model probability >= MIN_LEG_PROB
  (lower-variance selections), and a real price on the board;
- max one leg per match, max MAX_LEGS legs, minimum 2 — otherwise no coupon;
- combined probability is the product of leg probabilities with an explicit
  correlation caveat; EV uses the actual offered odds;
- staking guidance is flat 0.5-1% of bankroll, never increased after losses;
- everything is PAPER ONLY until the backtest gate is passed on real data.

Excluded candidates are listed with the reason, per the build plan.
"""
from __future__ import annotations

import sqlite3

import pandas as pd

from . import config
from .backtest import EDGE_THRESHOLD

MIN_LEG_PROB = 0.55
MAX_LEGS = 4
SELECTION_LABEL = {"H": "home win", "D": "draw", "A": "away win"}


def _latest_predictions(conn) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT p.match_id, p.selection, p.model_prob, p.implied_prob, p.edge,
               p.recommended_action, m.date_utc AS date,
               th.canonical_name AS home, ta.canonical_name AS away,
               (SELECT MAX(decimal_odds) FROM odds o
                WHERE o.match_id = p.match_id AND o.market='1X2'
                  AND o.is_closing=0 AND o.selection = p.selection) AS best_odds
        FROM predictions p
        JOIN matches m ON m.match_id = p.match_id
        JOIN teams th ON th.team_id = m.home_team_id
        JOIN teams ta ON ta.team_id = m.away_team_id
        WHERE p.market='1X2' AND m.status='scheduled'
          AND p.created_at = (SELECT MAX(created_at) FROM predictions)
        """,
        conn,
    )


def build(db_path=config.DB_PATH, gate_passed: bool = False) -> str | None:
    conn = sqlite3.connect(db_path)
    preds = _latest_predictions(conn)
    conn.close()
    if preds.empty:
        print("No predictions for scheduled fixtures — run predict first.")
        return None

    # Best selection per match, then screen.
    best = preds.sort_values("edge", ascending=False).groupby("match_id", as_index=False).first()
    legs, excluded = [], []
    for r in best.sort_values("model_prob", ascending=False).itertuples(index=False):
        label = f"{r.home} v {r.away}: {SELECTION_LABEL[r.selection]}"
        if pd.isna(r.best_odds):
            excluded.append((label, "no bookmaker price available"))
        elif pd.isna(r.edge) or r.edge < EDGE_THRESHOLD:
            excluded.append((label, f"edge {r.edge:+.3f} below threshold {EDGE_THRESHOLD:+.2f}"
                             if pd.notna(r.edge) else "no implied probability"))
        elif r.model_prob < MIN_LEG_PROB:
            excluded.append((label, f"model probability {r.model_prob:.3f} below {MIN_LEG_PROB} "
                             "(variance rule)"))
        elif len(legs) >= MAX_LEGS:
            excluded.append((label, f"coupon already at max {MAX_LEGS} legs"))
        else:
            legs.append(r)

    lines = ["# Coupon proposal", ""]
    if not gate_passed:
        lines.append("> **PAPER ONLY — backtest gate not passed on real data. Do not stake money.**\n")
    if len(legs) < 2:
        lines += [f"**No coupon proposed** — only {len(legs)} selection(s) cleared the screen "
                  "(minimum 2). Weak legs are never added to inflate payout.", ""]
    else:
        comb_p = float(pd.Series([l.model_prob for l in legs]).prod())
        comb_odds = float(pd.Series([l.best_odds for l in legs]).prod())
        ev = comb_p * comb_odds - 1.0
        lines += [
            "| leg | selection | model p | implied p | edge | best odds |",
            "|---|---|---|---|---|---|",
        ]
        for i, l in enumerate(legs, 1):
            lines.append(f"| {i} | {l.home} v {l.away} — {SELECTION_LABEL[l.selection]} ({l.date[:10]}) "
                         f"| {l.model_prob:.3f} | {l.implied_prob:.3f} | {l.edge:+.3f} | {l.best_odds:.2f} |")
        risk = "low-moderate" if comb_p >= 0.45 else ("moderate" if comb_p >= 0.30 else "high")
        lines += [
            "",
            f"Combined probability (independence assumed — legs on the same day/narrative are "
            f"not fully independent, treat as optimistic): **{comb_p:.3f}**",
            f"Combined offered odds: **{comb_odds:.2f}** (fair odds at model probability: {1 / comb_p:.2f})",
            f"Estimated EV per unit staked: **{ev:+.3f}** | risk level: **{risk}**",
            "",
            "Each leg is included because its modelled probability exceeds the margin-removed "
            f"market probability by at least {EDGE_THRESHOLD:.0%} and clears the {MIN_LEG_PROB} "
            "variance floor.",
            "",
            "**Staking**: flat 0.5-1% of bankroll maximum, only if the backtest gate has passed. "
            "Never increase stakes after losses. Record the coupon in betting_results whether or "
            "not it is placed.",
        ]
    if excluded:
        lines += ["", "## Considered and excluded", ""]
        lines += [f"- {label} — {reason}" for label, reason in excluded]
    lines += ["", "_Betting is high-risk and uncertain; an estimated edge is a model output, not "
              "a promise. If gambling stops being fun, stop: https://www.begambleaware.org_"]

    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = config.REPORTS_DIR / "coupon.md"
    out.write_text("\n".join(lines) + "\n")
    return str(out)


if __name__ == "__main__":
    import sys
    path = build(gate_passed="--gate-passed" in sys.argv)
    if path:
        print(f"Coupon written to {path}")
