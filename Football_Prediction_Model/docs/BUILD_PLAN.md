# Football Match & Scorer Prediction Model — Build Plan

> **Responsible gambling notice.** This project exists to improve decision-making with data, probability, validation and disciplined risk management. Betting is uncertain and high-risk; most bettors lose over time and no model output is ever a certainty. Never bet money you cannot afford to lose, never chase losses, and stop if it stops being fun. Support: BeGambleAware (UK) https://www.begambleaware.org, GamCare 0808 8020 133, or your local equivalent. A selection is only ever *flagged* when modelled probability materially exceeds the bookmaker's margin-adjusted implied probability — that is a statistical edge estimate, not a promise.

## 0. Scope and principles

- Predict: 1X2, double chance, over/under goals, BTTS, team-to-score, correct-score bands, anytime scorer (plus shots, corners, cards where data allows).
- Coupon objective: few-leg, lower-variance accumulators, flagged only when model probability − implied probability clears a threshold, staked flat at 0.5–1% of bankroll.
- Hard rules: no future data leakage; time-based validation only; bookmaker margin always removed before comparing probabilities; missing data declared, never invented; facts, assumptions and model estimates always separated; every prediction and (paper) bet logged for later audit.

## Phase 1 — Source audit

Done — see [`DATA_SOURCES.md`](DATA_SOURCES.md). Core stack: **Football-Data.co.uk** (results + odds), **FBref/Understat** (xG, player stats), **ClubElo** (ratings), **Transfermarkt** (injury history), **Open-Meteo** (weather), **football-data.org** (fixtures), **The Odds API** (current odds), plus manual news sources (club sites, BBC/Sky, FotMob) for team news.

## Phase 2 — Data collection plan

| Layer | How | Cadence |
|---|---|---|
| Historical matches + odds | Download Football-Data.co.uk season CSVs (stable URLs, e.g. `https://www.football-data.co.uk/mmz4281/2425/E0.csv`) | One-off backfill, then weekly refresh |
| Elo | `api.clubelo.com` CSV endpoints | Weekly |
| xG / player match logs | `soccerdata` package (FBref, Understat readers) with local cache, ≤1 request per 6–10s | Backfill slowly over days; then weekly delta |
| Injuries (historical) | Transfermarkt absence pages via `worldfootballR`/light scraper, cached, low-rate | Backfill once; monthly refresh |
| Weather (historical) | Open-Meteo archive API per (stadium lat/lon, kick-off hour) | Backfill once; join on new matches |
| Fixtures ahead | football-data.org API | Daily |
| Current odds | The Odds API (h2h + totals, one region to conserve credits) | 1–2 snapshots per fixture: T-48h and near kick-off |
| Team news | Manual/LLM-assisted entry from cited sources into `news` table with credibility score | Match week |
| Weather forecast | Open-Meteo forecast API | T-24h and morning of match |

Everything lands first in `data/raw/` exactly as received (plus retrieval timestamp), then is normalised into the database. Raw files are never edited.

## Phase 3 — Data schema

SQLite to start (single file, zero ops); the DDL in [`../schema/schema.sql`](../schema/schema.sql) is portable to Postgres if it outgrows that. Tables:

- **teams** — team_id, canonical_name, country, aliases (per-source names), stadium, lat, lon, elevation
- **players** — player_id, canonical_name, dob, nationality, position, foot, aliases
- **matches** — match_id, date_utc, kickoff_local, competition, season, matchday, home_team_id, away_team_id, venue, neutral_flag, ft_home, ft_away, ht_home, ht_away, result, total_goals, btts, status (played/postponed/abandoned), derby_flag, importance
- **team_match_stats** — match_id, team_id, is_home, goals, shots, shots_on_target, corners, fouls, yellows, reds, possession, pass_accuracy, xg, xga, big_chances, formation
- **player_match_stats** — match_id, player_id, team_id, started, minutes, goals, assists, shots, shots_on_target, xg, xa, key_passes, touches, tackles+interceptions, fouls, yellow, red, penalty_taken, position_played
- **odds** — match_id, bookmaker, snapshot_time, market (1X2/OU2.5/BTTS/…), selection, decimal_odds, is_closing
- **weather** — match_id, source (archive/forecast), temp_c, feels_like_c, wind_kph, gust_kph, rain_mm, snow_mm, humidity, pressure, weather_code, flags (extreme_wind, heavy_rain, cold, hot)
- **injuries** — injury_id, player_id, team_id, type, source, reported_date, start_date, expected_return, actual_return, matches_missed
- **news** — news_id, date, team_id, player_id (nullable), category (injury/suspension/rotation/manager/other), summary, source_name, url, credibility (1–5), verified_flag
- **predictions** — prediction_id, match_id, model_version, created_at (must be < kick-off), market, selection, model_prob, implied_prob, edge, confidence, recommended_action, rationale
- **betting_results** — bet_id, prediction_id/coupon_id, stake, odds_taken, closing_odds, outcome, pnl, bankroll_after, clv (closing-line value), notes

Plus small reference tables: **competitions**, **stadium_coords**, **name_map** (source name → canonical id, per source — the single most important cleaning asset).

## Phase 4 — Cleaning and joining

- **Team names:** every source spells teams differently ("Man United", "Manchester Utd", "Manchester United"). Maintain `name_map(source, raw_name, team_id)`; new unmatched names fail loudly rather than fuzzy-match silently. Seed with `soccerdata`'s cross-source ID matching, verify by eye.
- **Player names:** match on (name, team, season, DOB where available); accents/transliteration normalised (unicode NFKD); ambiguous cases flagged for manual resolution, never guessed.
- **Dates/times:** store UTC everywhere plus local kick-off; source CSVs are often local-date only — resolve against the official fixture list before joining odds/weather (a 23:00 UTC-listed match can be the wrong calendar day).
- **Competitions and seasons:** canonical codes (`ENG-PL`, season `2024-25`); cups vs league flagged.
- **Missing values:** stat columns missing for smaller leagues stay NULL with a per-column coverage report; models are trained per feature-availability tier, never on silently imputed zeros.
- **Duplicates/postponements:** unique key (season, home_team, away_team, competition) catches duplicated fixtures; postponed games keep the original row with status='postponed' and a new row when replayed; abandoned matches excluded from training.
- **Neutral venues:** flag set (cup finals etc.) → home-advantage features zeroed.
- **Promoted/relegated teams:** first ~5 matches of a promoted side carry a "low-information" flag; their priors come from Elo (which persists across divisions) rather than league-relative rolling stats.

## Phase 5 — Feature engineering

All features computed **as of the day before kick-off** (strictly pre-match information only; confirmed lineups are used only in the live pre-match workflow, never in historical training features unless we also had them pre-KO).

- Rolling team form: points, goals for/against, shots for/against, corners, cards over last 3/5/10, exponentially decayed; home-only and away-only splits.
- Rolling xG for/against (5/10), xG minus goals (finishing luck regression signal).
- Elo, Elo difference, Elo-implied win probability.
- Attack-vs-defence interaction: home attack strength × away defence weakness (league-normalised).
- Schedule: rest days each side, rest-day differential, matches in last 21 days (congestion), travel distance from stadium coordinates, competition played midweek flag.
- Availability: injury count weighted by player importance (minutes share × goal involvement share) → squad availability score; starting-XI strength = sum of expected starters' rating vs season-best XI; returned-from-injury and suspension flags.
- Weather: raw variables + flags (wind > 40 kph, rain > 5 mm/h, temp < 2°C or > 30°C) and interactions (e.g. high wind × long-ball team). Weather effects are tested, reported honestly, and dropped if they don't validate — expected effect sizes are small.
- Market: implied probabilities from best/average odds, margin-removed (proportional and Shin's method), odds movement between snapshots.
- Scorer features (per player): expected minutes (from recent starts/subs pattern + availability), npxG/90, shots/90, headers share, penalty-taker flag, set-piece roles, opponent xGA/90 and keeper form, venue split, teammate competition for shots.

## Phase 6 — Model design

Layered, so every fancy model must beat a dumber one before it's trusted:

1. **Baselines (must-beat):**
   - *Market baseline:* margin-removed closing-odds probabilities — the strongest baseline; if we can't approach it, we have no edge.
   - *Elo baseline:* logistic mapping from Elo difference → 1X2.
   - *Poisson goals model:* team attack/defence rates + home advantage → score matrix → every goals-derived market (1X2, O/U, BTTS, correct-score bands) from one coherent model.
   - *Dixon–Coles:* Poisson with low-score dependence correction and time-decay weighting — the classic football scores model and likely workhorse.
2. **ML layer:** regularised multinomial logistic regression (interpretable reference), then gradient boosting (LightGBM/XGBoost) on the Phase-5 features for 1X2 and totals; random forest as a sanity check. Bayesian hierarchical goals model (PyMC/Stan) optional later — natural fit for team strengths with shrinkage, and gives honest uncertainty.
3. **Ensemble:** logistic stacking of {market, Elo, Dixon–Coles, GBM} probabilities, weights fitted on a validation window only. Calibrate final outputs (Platt/isotonic) and verify with reliability curves.
4. **Scorer model:** P(anytime goal) ≈ 1 − exp(−E[minutes]/90 × adjusted npx G/90 − penalty share term), with opponent-defence and lineup adjustments; validated against bookmaker scorer odds where collectable.

## Phase 7 — Back-testing (gate before any betting output)

- **Splits:** strictly chronological; e.g. train 2017–2022, validate 2022–23 (tuning), test 2023–2025 untouched until final. Then rolling-origin evaluation season by season, retraining as the window advances.
- **Metrics:** log loss and Brier vs the market baseline; calibration curves per market; rank probability score for 1X2.
- **Economic simulation:** flat-stake ROI at closing odds for selections passing the edge threshold; hit rate; max drawdown; CLV (did we beat the closing line — the best single predictor of real edge); comparison vs favourites-only and bet-everything strategies; bootstrap confidence intervals on ROI (a 3-season profitable backtest can easily be variance).
- **Promotion rule:** a model version only produces recommendations if, on the untouched test window, it (a) is calibrated, (b) has log loss within noise of or better than the market, and (c) shows positive CLV on flagged bets. Otherwise output is labelled "watch only".

## Phase 8 — Upcoming match prediction workflow

Weekly run per fixture: pull fixtures → refresh Elo/form/xG → collect injuries + news (with citations and credibility scores) → weather forecast at stadium/kick-off → odds snapshot → generate features → run ensemble → produce per-match card:

match, date/time (exact, with timezone), competition, P(home/draw/away), margin-adjusted implied probabilities, edge per market, likely score bands, O/U + BTTS probabilities, likely scorers with probabilities, weather, injury/news impact, confidence rating, main reasons, red flags, and a recommended action from {bet, avoid, watch only, wait for lineups}. Facts, assumptions and model estimates labelled separately.

## Phase 9 — Coupon builder

- Candidate legs = selections with model_prob − implied_prob ≥ threshold (start ~3–4 percentage points after margin removal, tuned in backtest) **and** model confidence ≥ medium **and** no unresolved red flags (missing lineups, manager just sacked, extreme weather uncertainty).
- Prefer 2–4 legs; combined probability shown honestly (product, with a correlation warning — same-match or same-day-narrative legs are not independent); no weak legs added to inflate payout.
- Per coupon output: each leg with model vs implied probability and edge, combined probability, combined fair odds vs offered odds, EV, risk level, why each leg is in, which games were considered and excluded and why.
- Staking: flat 0.5–1% of bankroll per coupon, max; no increase after losses, ever; every coupon logged in `betting_results` whether or not it is placed (paper-trade first — minimum one full paper cycle before any real stake).

## First-version scope (v0.1)

1. One league, ~8–10 seasons of Football-Data.co.uk CSVs + ClubElo + Open-Meteo backfill.
2. SQLite schema loaded; name_map built and verified.
3. Dixon–Coles + Elo + market baselines, chronological backtest with calibration and CLV report.
4. Weekly prediction card for upcoming fixtures, "watch only" until the backtest gate passes.
5. FBref/Understat player layer and the scorer model come in v0.2, once the match-level pipeline is trusted.

## Modelling rules (standing)

No overfitting via unlimited feature/hyperparameter search on the test set; correlation ≠ causation (report effects as associations); no future data in features; no post-KO information in historical training; always compare to closing odds; always margin-adjust; missing data is declared; injuries/news are never invented and always cited with dates; weather always from stadium coordinates + kick-off time; uncertainty is quantified and stated.
