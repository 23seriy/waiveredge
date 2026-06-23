-- Add player_key column to rosters for Yahoo/ESPN transaction support.
ALTER TABLE rosters ADD COLUMN IF NOT EXISTS player_key VARCHAR(32);
