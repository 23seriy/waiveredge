-- WaiverEdge initial schema (Postgres). Mirrors app/models.py.
-- Apply with: psql "$DATABASE_URL" -f migrations/0001_init.sql
-- (Swap for Alembic once the schema starts evolving.)

CREATE TABLE IF NOT EXISTS teams (
    id           INTEGER PRIMARY KEY,            -- balldontlie team id
    abbreviation VARCHAR(8)  NOT NULL,
    full_name    VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS players (
    id                INTEGER PRIMARY KEY,        -- balldontlie player id
    name              VARCHAR(128) NOT NULL,
    team_id           INTEGER REFERENCES teams(id),
    positions         TEXT[] NOT NULL DEFAULT '{}',
    primary_position  VARCHAR(4)
);
CREATE INDEX IF NOT EXISTS ix_players_name ON players(name);
CREATE INDEX IF NOT EXISTS ix_players_team ON players(team_id);

CREATE TABLE IF NOT EXISTS games (
    id              INTEGER PRIMARY KEY,
    date            DATE NOT NULL,
    season          INTEGER,
    home_team_id    INTEGER NOT NULL REFERENCES teams(id),
    visitor_team_id INTEGER NOT NULL REFERENCES teams(id),
    status          VARCHAR(32)
);
CREATE INDEX IF NOT EXISTS ix_games_date ON games(date);
CREATE INDEX IF NOT EXISTS ix_games_season ON games(season);

CREATE TABLE IF NOT EXISTS player_game_logs (
    id          SERIAL PRIMARY KEY,
    player_id   INTEGER NOT NULL REFERENCES players(id),
    game_id     INTEGER NOT NULL REFERENCES games(id),
    date        DATE NOT NULL,
    team_id     INTEGER NOT NULL,
    opponent_id INTEGER NOT NULL,
    position    VARCHAR(4) NOT NULL,
    minutes     INTEGER,
    pts         INTEGER NOT NULL DEFAULT 0,
    reb         INTEGER NOT NULL DEFAULT 0,
    ast         INTEGER NOT NULL DEFAULT 0,
    stl         INTEGER NOT NULL DEFAULT 0,
    blk         INTEGER NOT NULL DEFAULT 0,
    fg3m        INTEGER NOT NULL DEFAULT 0,
    turnover    INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT uq_player_game UNIQUE (player_id, game_id)
);
CREATE INDEX IF NOT EXISTS ix_logs_player ON player_game_logs(player_id);
CREATE INDEX IF NOT EXISTS ix_logs_opp_pos ON player_game_logs(opponent_id, position);

CREATE TABLE IF NOT EXISTS team_dvp (
    team_id      INTEGER NOT NULL REFERENCES teams(id),
    position     VARCHAR(4) NOT NULL,
    window_label VARCHAR(32) NOT NULL DEFAULT 'season',
    fpts_allowed NUMERIC(6,2) NOT NULL DEFAULT 0,
    multiplier   NUMERIC(5,3) NOT NULL DEFAULT 1.0,
    sample       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (team_id, position, window_label)
);

CREATE TABLE IF NOT EXISTS injuries (
    player_id  INTEGER PRIMARY KEY REFERENCES players(id),
    status     VARCHAR(32) NOT NULL,
    note       VARCHAR(256),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    id                      SERIAL PRIMARY KEY,
    email                   VARCHAR(256) UNIQUE NOT NULL,
    tier                    VARCHAR(16) NOT NULL DEFAULT 'free',
    stripe_customer_id      VARCHAR(64),
    stripe_subscription_id  VARCHAR(64),
    alert_email             BOOLEAN NOT NULL DEFAULT TRUE,
    alert_push              BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS league_connections (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    platform     VARCHAR(16) NOT NULL,           -- yahoo | espn | manual
    league_id    VARCHAR(64),
    team_key     VARCHAR(64),
    scoring_json JSONB NOT NULL DEFAULT '{}',
    oauth_tokens JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_conn_user ON league_connections(user_id);

CREATE TABLE IF NOT EXISTS rosters (
    id            SERIAL PRIMARY KEY,
    connection_id INTEGER NOT NULL REFERENCES league_connections(id),
    player_id     INTEGER NOT NULL,
    slot          VARCHAR(8) NOT NULL,
    droppable     BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS ix_roster_conn ON rosters(connection_id);
CREATE INDEX IF NOT EXISTS ix_roster_player ON rosters(player_id);

CREATE TABLE IF NOT EXISTS injury_alerts (
    id                   SERIAL PRIMARY KEY,
    connection_id        INTEGER NOT NULL REFERENCES league_connections(id),
    sport                VARCHAR(8) NOT NULL DEFAULT 'nba',
    injured_player_name  VARCHAR(128) NOT NULL,
    injured_player_id    INTEGER,
    injury_status        VARCHAR(32) NOT NULL,
    injury_note          VARCHAR(256),
    pickup_player_name   VARCHAR(128),
    pickup_player_id     INTEGER,
    pickup_marginal      NUMERIC(8,2),
    pickup_rationale     VARCHAR(512),
    is_read              BOOLEAN NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_alert_conn ON injury_alerts(connection_id);
