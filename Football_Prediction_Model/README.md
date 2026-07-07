# Football Prediction Model

A data-driven workflow for predicting football match outcomes, likely scorers and low-stake, probability-screened betting coupon selections.

**This project does not and cannot guarantee betting profit.** Its purpose is better decision-making through data, probability, back-testing and disciplined risk management. No bet is ever certain, losses must never be chased, and a selection is only flagged when the modelled probability materially exceeds the bookmaker's margin-adjusted implied probability. If gambling stops being fun, stop — support at https://www.begambleaware.org.

## Contents

| Path | What it is |
|---|---|
| [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) | Phase 1 audit of free/freemium data sources: what each provides, cost, legality/practicality of automated access, and what role it plays in the model |
| [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) | The full 9-phase build plan: collection, schema, cleaning, feature engineering, model design (Elo / Poisson / Dixon–Coles / gradient boosting / ensemble + scorer model), back-testing gates, prediction workflow and coupon rules |
| [`schema/schema.sql`](schema/schema.sql) | Database DDL (SQLite dialect): matches, teams, players, per-match stats, odds, weather, injuries, news, predictions, betting_results |

## Roadmap

- **v0.1** — one league: Football-Data.co.uk + ClubElo + Open-Meteo backfill, Dixon–Coles/Elo/market baselines, chronological backtest with calibration and closing-line-value reporting. Output is "watch only" until the backtest gate passes.
- **v0.2** — FBref/Understat player layer, availability features, anytime-scorer model.
- **v0.3** — odds snapshots for upcoming fixtures, value screening, conservative coupon builder with flat staking (max 0.5–1% of bankroll) and full paper-trading log.

## Standing rules

Time-ordered validation only; no future information in historical features; bookmaker margin always removed before edge calculation; missing data declared, never imputed silently; injuries and news always cited, never invented; every prediction and paper bet recorded for audit.
