-- Injury alerts table — stores detected injury changes and the resulting
-- pickup opportunity for each user's connected league.
CREATE TABLE IF NOT EXISTS injury_alerts (
    id            SERIAL PRIMARY KEY,
    connection_id INTEGER NOT NULL REFERENCES league_connections(id),
    sport         VARCHAR(8) NOT NULL DEFAULT 'nba',
    injured_player_name VARCHAR(128) NOT NULL,
    injured_player_id   INTEGER,
    injury_status       VARCHAR(32) NOT NULL,        -- Out, Doubtful, Questionable, etc.
    injury_note         VARCHAR(256),
    pickup_player_name  VARCHAR(128),                 -- who benefits from the injury
    pickup_player_id    INTEGER,
    pickup_marginal     NUMERIC(8,2),                 -- projected value gained
    pickup_rationale    TEXT,
    is_read       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_alerts_conn ON injury_alerts(connection_id);
CREATE INDEX IF NOT EXISTS ix_alerts_created ON injury_alerts(created_at DESC);

-- User notification preferences
ALTER TABLE users ADD COLUMN IF NOT EXISTS alert_email BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS alert_push BOOLEAN NOT NULL DEFAULT TRUE;
