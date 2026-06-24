-- Persistent fixture cache: survives container restarts and deploys.
-- Stores the same JSON fixture files (teams, players, game_logs, etc.)
-- keyed by sport + file_name, with an updated_at timestamp for staleness.

CREATE TABLE IF NOT EXISTS fixture_cache (
    sport       VARCHAR(16)  NOT NULL,
    file_name   VARCHAR(32)  NOT NULL,
    data        JSONB        NOT NULL DEFAULT '[]'::jsonb,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (sport, file_name)
);

CREATE INDEX IF NOT EXISTS idx_fixture_cache_updated
    ON fixture_cache (sport, updated_at);
