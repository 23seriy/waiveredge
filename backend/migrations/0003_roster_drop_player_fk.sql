-- Drop player_id FK on rosters table — roster entries can reference players
-- from any sport's fixture data, not just the DB players table.
ALTER TABLE rosters DROP CONSTRAINT IF EXISTS rosters_player_id_fkey;
CREATE INDEX IF NOT EXISTS ix_roster_player ON rosters(player_id);
