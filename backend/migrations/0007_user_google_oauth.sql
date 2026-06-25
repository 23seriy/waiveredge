-- Add Google OAuth columns to users table.
ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(64) UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(256);
ALTER TABLE users ADD COLUMN IF NOT EXISTS picture VARCHAR(512);

CREATE INDEX IF NOT EXISTS ix_users_google_id ON users (google_id);
