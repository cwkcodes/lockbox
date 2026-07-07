-- Football prediction model — core schema (SQLite dialect, portable to Postgres)
-- All timestamps stored as ISO-8601 UTC strings unless suffixed _local.

CREATE TABLE competitions (
    competition_id   TEXT PRIMARY KEY,          -- e.g. 'ENG-PL'
    name             TEXT NOT NULL,
    country          TEXT,
    tier             INTEGER,
    is_cup           INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE teams (
    team_id          INTEGER PRIMARY KEY,
    canonical_name   TEXT NOT NULL UNIQUE,
    country          TEXT,
    stadium          TEXT,
    latitude         REAL,
    longitude        REAL,
    elevation_m      REAL
);

-- Per-source raw-name resolution. New raw names must be added here explicitly.
CREATE TABLE name_map (
    source           TEXT NOT NULL,             -- 'football-data', 'fbref', 'clubelo', ...
    entity_type      TEXT NOT NULL,             -- 'team' | 'player' | 'competition'
    raw_name         TEXT NOT NULL,
    canonical_id     INTEGER NOT NULL,
    PRIMARY KEY (source, entity_type, raw_name)
);

CREATE TABLE players (
    player_id        INTEGER PRIMARY KEY,
    canonical_name   TEXT NOT NULL,
    date_of_birth    TEXT,
    nationality      TEXT,
    primary_position TEXT,                      -- GK/DF/MF/FW
    preferred_foot   TEXT
);

CREATE TABLE matches (
    match_id         INTEGER PRIMARY KEY,
    competition_id   TEXT NOT NULL REFERENCES competitions(competition_id),
    season           TEXT NOT NULL,             -- '2024-25'
    matchday         INTEGER,
    date_utc         TEXT NOT NULL,
    kickoff_local    TEXT,
    home_team_id     INTEGER NOT NULL REFERENCES teams(team_id),
    away_team_id     INTEGER NOT NULL REFERENCES teams(team_id),
    venue            TEXT,
    neutral_venue    INTEGER NOT NULL DEFAULT 0,
    status           TEXT NOT NULL DEFAULT 'scheduled',  -- scheduled/played/postponed/abandoned
    ft_home          INTEGER,
    ft_away          INTEGER,
    ht_home          INTEGER,
    ht_away          INTEGER,
    result           TEXT,                      -- 'H'/'D'/'A'
    total_goals      INTEGER,
    btts             INTEGER,
    derby_flag       INTEGER NOT NULL DEFAULT 0,
    importance       TEXT,                      -- free-text/enum: title race, relegation, dead rubber...
    UNIQUE (competition_id, season, date_utc, home_team_id, away_team_id)
);

CREATE TABLE team_match_stats (
    match_id         INTEGER NOT NULL REFERENCES matches(match_id),
    team_id          INTEGER NOT NULL REFERENCES teams(team_id),
    is_home          INTEGER NOT NULL,
    goals            INTEGER,
    shots            INTEGER,
    shots_on_target  INTEGER,
    corners          INTEGER,
    fouls            INTEGER,
    yellow_cards     INTEGER,
    red_cards        INTEGER,
    possession_pct   REAL,
    pass_accuracy    REAL,
    xg               REAL,
    xga              REAL,
    big_chances      INTEGER,
    formation        TEXT,
    PRIMARY KEY (match_id, team_id)
);

CREATE TABLE player_match_stats (
    match_id         INTEGER NOT NULL REFERENCES matches(match_id),
    player_id        INTEGER NOT NULL REFERENCES players(player_id),
    team_id          INTEGER NOT NULL REFERENCES teams(team_id),
    started          INTEGER NOT NULL,
    minutes          INTEGER NOT NULL,
    position_played  TEXT,
    goals            INTEGER DEFAULT 0,
    assists          INTEGER DEFAULT 0,
    shots            INTEGER,
    shots_on_target  INTEGER,
    xg               REAL,
    xa               REAL,
    key_passes       INTEGER,
    touches          INTEGER,
    tackles_interceptions INTEGER,
    fouls            INTEGER,
    yellow_card      INTEGER DEFAULT 0,
    red_card         INTEGER DEFAULT 0,
    penalty_attempted INTEGER DEFAULT 0,
    PRIMARY KEY (match_id, player_id)
);

CREATE TABLE odds (
    odds_id          INTEGER PRIMARY KEY,
    match_id         INTEGER NOT NULL REFERENCES matches(match_id),
    bookmaker        TEXT NOT NULL,             -- 'B365', 'Pinnacle', 'market_avg', ...
    snapshot_time    TEXT,                      -- NULL for football-data.co.uk single snapshot
    is_closing       INTEGER NOT NULL DEFAULT 0,
    market           TEXT NOT NULL,             -- '1X2', 'OU2.5', 'BTTS', 'AHC', 'anytime_scorer'
    selection        TEXT NOT NULL,             -- 'H'/'D'/'A'/'over'/'under'/'yes'/player name
    decimal_odds     REAL NOT NULL
);
CREATE INDEX idx_odds_match ON odds(match_id, market);

CREATE TABLE weather (
    match_id         INTEGER NOT NULL REFERENCES matches(match_id),
    source           TEXT NOT NULL,             -- 'archive' | 'forecast'
    retrieved_at     TEXT NOT NULL,
    temp_c           REAL,
    feels_like_c     REAL,
    wind_kph         REAL,
    gust_kph         REAL,
    rain_mm          REAL,
    snow_mm          REAL,
    humidity_pct     REAL,
    pressure_hpa     REAL,
    weather_code     INTEGER,
    flag_extreme_wind INTEGER DEFAULT 0,
    flag_heavy_rain  INTEGER DEFAULT 0,
    flag_cold        INTEGER DEFAULT 0,
    flag_hot         INTEGER DEFAULT 0,
    PRIMARY KEY (match_id, source)
);

CREATE TABLE injuries (
    injury_id        INTEGER PRIMARY KEY,
    player_id        INTEGER NOT NULL REFERENCES players(player_id),
    team_id          INTEGER NOT NULL REFERENCES teams(team_id),
    injury_type      TEXT,                      -- 'hamstring', 'suspension', 'illness', ...
    source           TEXT NOT NULL,
    reported_date    TEXT,
    start_date       TEXT,
    expected_return  TEXT,
    actual_return    TEXT,
    matches_missed   INTEGER
);

CREATE TABLE news (
    news_id          INTEGER PRIMARY KEY,
    published_date   TEXT NOT NULL,
    team_id          INTEGER REFERENCES teams(team_id),
    player_id        INTEGER REFERENCES players(player_id),
    category         TEXT NOT NULL,             -- injury/suspension/rotation/manager/tactics/other
    summary          TEXT NOT NULL,
    source_name      TEXT NOT NULL,
    url              TEXT,
    credibility      INTEGER NOT NULL CHECK (credibility BETWEEN 1 AND 5),
    verified         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE predictions (
    prediction_id    INTEGER PRIMARY KEY,
    match_id         INTEGER NOT NULL REFERENCES matches(match_id),
    model_version    TEXT NOT NULL,
    created_at       TEXT NOT NULL,             -- must be < match kick-off; enforced in code
    market           TEXT NOT NULL,
    selection        TEXT NOT NULL,
    model_prob       REAL NOT NULL,
    implied_prob     REAL,                      -- margin-removed
    edge             REAL,                      -- model_prob - implied_prob
    confidence       TEXT,                      -- low/medium/high
    recommended_action TEXT,                    -- bet/avoid/watch_only/wait_for_lineups
    rationale        TEXT
);

CREATE TABLE betting_results (
    bet_id           INTEGER PRIMARY KEY,
    coupon_id        TEXT,                      -- groups legs of one coupon
    prediction_id    INTEGER REFERENCES predictions(prediction_id),
    placed_at        TEXT,
    is_paper         INTEGER NOT NULL DEFAULT 1,
    stake            REAL,
    odds_taken       REAL,
    closing_odds     REAL,
    outcome          TEXT,                      -- won/lost/void/pending
    pnl              REAL,
    bankroll_after   REAL,
    clv              REAL,                      -- closing-line value
    notes            TEXT
);
