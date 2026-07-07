# Phase 1 — Data Source Audit

Last reviewed: 2026-07-07. Free tiers and terms change; re-verify before building automated collection against any source.

**Legend:** Auto = suitable for automated/repeatable collection (API or stable CSV download). Model = suitable as a modelling input.

## Core recommended stack

| # | Source | Link | Data type | Cost | Best use case | Limitations | Auto | Model |
|---|--------|------|-----------|------|---------------|-------------|------|-------|
| 1 | Football-Data.co.uk | https://www.football-data.co.uk/data.php | Historical results, HT/FT scores, shots, shots on target, corners, cards, fouls, and pre-match + closing odds (Bet365, Pinnacle, William Hill, market max/avg) as per-season CSVs for ~25 European leagues back to the 1990s | Free | **Backbone of the historical matches + odds tables.** Explicitly published for download and betting research | No player data, no lineups, no xG; some stat columns only for bigger leagues; updated ~twice weekly, not live | Yes — stable CSV URLs | Yes — primary |
| 2 | FBref (Sports Reference) | https://fbref.com | Team + player match logs: minutes, goals, assists, shooting, passing, possession, defensive actions, xG/xA (Opta-based) for major leagues | Free (ad-supported) | Player-level features (minutes trends, xG/90, shot volume) and team style stats | **Strict rate limit: ≤10 requests/min, violators blocked up to 24h** (see sports-reference.com/bot-traffic.html). No bulk download or official API. Personal/non-commercial use | Cautiously — slow, polite scraping via `soccerdata`; cache aggressively | Yes |
| 3 | Understat | https://understat.com | Match, team and player xG/xA, shot-level data for the Big-5 leagues + Russia, from 2014/15 | Free | Long xG history for team-strength features; shot-level data for scorer models | No documented API or ToS for scraping; data embedded in page JSON. Only 6 leagues. Treat as personal-use, low-volume | Cautiously — via `soccerdata`, low frequency | Yes |
| 4 | ClubElo | http://clubelo.com/API | Elo ratings for European clubs, daily history since 1939 | Free | Team strength baseline and Elo-difference features | Club level only; European leagues only; name matching needed | **Yes — official CSV API** (`api.clubelo.com/YYYY-MM-DD`, `api.clubelo.com/<Club>`) | Yes |
| 5 | Open-Meteo | https://open-meteo.com | Historical weather (ERA5, back to 1940) + forecasts by lat/lon; hourly temp, wind, gusts, rain, snow, humidity, pressure, weather code; CSV/JSON | Free for non-commercial (~10k req/day) | **All weather features**, historical and forecast, keyed to stadium coordinates and kick-off hour | Non-commercial licence on free tier; reanalysis is gridded (fine for our purpose); need our own stadium-coordinates table | **Yes — no API key required** | Yes |
| 6 | Transfermarkt | https://www.transfermarkt.com | Injuries + absence history, suspensions, squad lists, market values, arrivals/departures | Free (web) | Historical injury/absence table; squad availability features | No official API; ToS restricts systematic reuse — keep scraping minimal, low-rate, personal-use (community tools: `worldfootballR`, transfermarkt-datasets on GitHub). Injury *dates* can be imprecise | Cautiously | Yes |
| 7 | football-data.org | https://www.football-data.org | REST API: fixtures, results, standings, scorers for 12 major competitions | Freemium (free: 10 req/min, 12 comps) | **Upcoming fixture list** (kick-off times, matchday structure) to drive the prediction pipeline | Free tier: no lineups, no match stats, odds are a paid add-on; scores slightly delayed | Yes — API key | Partially (fixtures only) |
| 8 | API-Football (api-sports.io) | https://www.api-football.com | REST API: fixtures, lineups, events, player stats, **injuries**, odds, 1,100+ leagues | Freemium (free ≈100 req/day; current-season restrictions on free plan) | Injuries + predicted lineups for upcoming matches when a budget exists; widest single-API coverage | 100 req/day is tight for historical backfill; useful mostly for the *upcoming week* slice; paid tiers for serious use | Yes — API key | Yes (forward-looking) |
| 9 | The Odds API | https://the-odds-api.com | Live pre-match odds from many bookmakers, h2h/totals/BTTS markets; historical odds on paid tiers | Freemium (500 credits/mo free; cost = markets × regions per call) | Snapshot of current market prices for upcoming fixtures → implied probabilities and value edge | Free tier is small (~80–500 calls/mo depending on markets); historical odds effectively paid — use Football-Data.co.uk CSVs for historical odds instead | Yes — API key | Yes (forward-looking) |
| 10 | StatsBomb Open Data | https://github.com/statsbomb/open-data | Full event data (JSON) for selected competitions/seasons incl. lineups, shots, xG | Free (attribution licence, non-commercial) | Prototyping event-level features and scorer models; validating our xG-based features | Selected competitions only — **not** ongoing league coverage; can't drive weekly predictions | Yes — git clone | Yes (research/prototyping) |

## Secondary / situational sources

| # | Source | Link | Data type | Cost | Best use case | Limitations | Auto | Model |
|---|--------|------|-----------|------|---------------|-------------|------|-------|
| 11 | `soccerdata` Python package | https://soccerdata.readthedocs.io | Unified scrapers for FBref, Understat, ClubElo, Football-Data.co.uk, Sofascore, WhoScored, ESPN with matched IDs and built-in caching/rate-limiting | Free (MIT) | **The practical collection layer** for sources 1–4 — don't write bespoke scrapers | You remain responsible for respecting each upstream site's terms; scrapers break when sites change | Yes | n/a (tooling) |
| 12 | openfootball / football.json | https://openfootball.github.io | Public-domain fixtures/results in text/JSON for major leagues | Free (public domain) | Fixture backfill, cross-checking results | Results only — no stats, odds or players; update lag | Yes — git | Partially |
| 13 | Kaggle (e.g. European Soccer Database) | https://www.kaggle.com/datasets/hugomathien/soccer | 25k+ matches 2008–2016, players, teams, odds (SQLite) | Free (check per-dataset licence) | One-off bootstrapping and method validation | Frozen in time; unknown provenance for some sets — never the live pipeline | Yes — one-off download | For prototyping only |
| 14 | FootyStats | https://footystats.org/download-stats-csv | League/team/player CSVs + API | Freemium | Convenience CSVs if you take a cheap plan | Most useful downloads and API volume are paid; free tier thin | Paid tiers | Optional |
| 15 | StatBunker | https://www.statbunker.com | Team/player aggregates: goals, cards, assists by competition | Free (web) | Cross-checking aggregates | HTML tables only, no downloads/API; better data exists at FBref | Not practical | No — use FBref |
| 16 | FotMob | https://www.fotmob.com | Live scores, expected/confirmed lineups, injury flags, match stats | Free (app/web) | **Manual pre-match check**: confirmed XIs ~1h before kick-off, late team news | No official public API; unofficial endpoints are unsupported and may violate ToS — treat as a manual source | No (manual) | Indirectly (news inputs) |
| 17 | Sofascore | https://www.sofascore.com | Ratings, lineups, detailed match stats | Free (web) | Secondary manual check; `soccerdata` has a scraper | No official public API; ToS restricts automated reuse | Cautiously | Indirectly |
| 18 | Premier League official injuries page | https://www.premierleague.com/en/latest-player-injuries | Club-by-club injury list (EPL) | Free | Credible EPL injury baseline for upcoming fixtures | EPL only; no structured feed — manual or light scrape | Semi | Yes (news table) |
| 19 | PremierInjuries.com | https://www.premierinjuries.com/injury-table.php | EPL injury/suspension table with return estimates | Free (web) | Weekly EPL availability snapshot | EPL only; no API; verify against club sources | Semi | Yes (news table) |
| 20 | BBC Sport / Sky Sports / ESPN / club sites & pressers | e.g. https://www.bbc.com/sport/football | Team news, press-conference quotes, expected lineups, suspensions | Free | **News table** entries with citations; credibility anchors for injury/rotation flags | Unstructured text; needs manual entry or careful summarisation with citation + credibility score | No (manual/LLM-assisted) | Indirectly |

## Legality & practicality notes

- **Explicitly download-friendly:** Football-Data.co.uk (published as CSV for this exact purpose), ClubElo (CSV API), Open-Meteo (open API), StatsBomb Open Data (licence file in repo), openfootball (public domain), Kaggle (per-dataset licence).
- **Tolerated low-volume scraping, no official API:** FBref (hard 10 req/min limit — respect it or get banned), Understat, Transfermarkt, Sofascore. Personal, non-commercial, cached, rate-limited use via `soccerdata`/`worldfootballR` is the community norm; none of these grant a licence to redistribute their data. Do not republish scraped data in this repo.
- **Blocked or impractical to scrape:** OddsPortal (aggressive anti-bot, ToS prohibits it — use Football-Data.co.uk closing odds instead), WhoScored (heavy anti-bot), FotMob (no public API). Alternatives are listed in the tables above.
- **Commercial use:** if this ever becomes more than personal research, most of the above (Open-Meteo free tier, FBref, Understat, Transfermarkt) require paid/licensed alternatives (e.g. Opta, StatsBomb paid, Sportmonks, API-Football paid).

## What each core source contributes

| Model need | Primary source | Backup |
|---|---|---|
| Historical results + match stats | Football-Data.co.uk | football-data.org, openfootball |
| Historical + closing odds | Football-Data.co.uk | The Odds API (paid history) |
| Current odds for upcoming games | The Odds API | manual bookmaker check |
| Team/player xG, shots, minutes | FBref | Understat |
| Team strength rating | ClubElo | derive own Elo from results |
| Injuries/absences (historical) | Transfermarkt | API-Football |
| Injuries/team news (upcoming) | Club sites, BBC/Sky, PL injuries page, Premier Injuries | FotMob (manual), API-Football |
| Expected/confirmed lineups | FotMob/Sofascore (manual pre-KO) | API-Football |
| Weather (past + forecast) | Open-Meteo | — |
| Fixtures ahead | football-data.org | API-Football |
