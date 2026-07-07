# Football Prediction Model

A data-driven workflow for predicting football match outcomes, likely scorers and low-stake, probability-screened betting coupon selections.

**This project does not and cannot guarantee betting profit.** Its purpose is better decision-making through data, probability, back-testing and disciplined risk management. No bet is ever certain, losses must never be chased, and a selection is only flagged when the modelled probability materially exceeds the bookmaker's margin-adjusted implied probability. If gambling stops being fun, stop — support at https://www.begambleaware.org.

## Contents

| Path | What it is |
|---|---|
| [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) | Phase 1 audit of free/freemium data sources: what each provides, cost, legality/practicality of automated access, and what role it plays in the model |
| [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) | The full 9-phase build plan: collection, schema, cleaning, feature engineering, model design (Elo / Poisson / Dixon–Coles / gradient boosting / ensemble + scorer model), back-testing gates, prediction workflow and coupon rules |
| [`schema/schema.sql`](schema/schema.sql) | Database DDL (SQLite dialect): matches, teams, players, per-match stats, odds, weather, injuries, news, predictions, betting_results |
| [`src/fpm/`](src/fpm/) | v0.1 pipeline: ingest (football-data.co.uk CSVs), SQLite loader, Elo + Dixon–Coles + market baselines, chronological backtest with calibration and flat-stake value simulation |

## Running v0.1

Scope (chosen 2026-07-07): **English Premier League, seasons 2014-15 → present, 1X2 + double chance markets.**

```bash
pip install -r requirements.txt
cd src
python -m fpm selftest    # end-to-end check on synthetic data (no network needed)
python -m fpm ingest      # download EPL season CSVs from football-data.co.uk
python -m fpm load        # normalise into data/football.sqlite
python -m fpm backtest    # chronological backtest -> reports/backtest_report.md

python -m fpm fixtures upcoming.csv   # add scheduled fixtures + current 1X2 odds (CSV: Date,HomeTeam,AwayTeam,B365H,B365D,B365A)
python -m fpm predict     # prediction cards (1X2, double chance, O/U 2.5, BTTS) -> reports/predictions.md
python -m fpm coupon      # conservative coupon screen -> reports/coupon.md
```

`predict` and `coupon` are gated: recommendations stay **watch only / paper only** until you pass `--gate-passed`, which should only happen after a real-data backtest report shows calibration and positive value performance on unseen seasons.

`ingest` needs open internet access to `www.football-data.co.uk` — sandboxed environments with restricted network policies can run only `selftest`. The self-test validates the code path, not betting edge: its "value" numbers come from synthetic data and mean nothing about real markets.

## Roadmap

- **v0.1** — one league: Football-Data.co.uk + ClubElo + Open-Meteo backfill, Dixon–Coles/Elo/market baselines, chronological backtest with calibration and closing-line-value reporting. Output is "watch only" until the backtest gate passes.
- **v0.2** — FBref/Understat player layer, availability features, anytime-scorer model.
- **v0.3** — odds snapshots for upcoming fixtures, value screening, conservative coupon builder with flat staking (max 0.5–1% of bankroll) and full paper-trading log.

## Standing rules

Time-ordered validation only; no future information in historical features; bookmaker margin always removed before edge calculation; missing data declared, never imputed silently; injuries and news always cited, never invented; every prediction and paper bet recorded for audit.
