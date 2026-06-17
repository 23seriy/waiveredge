-- Add Stripe billing columns to users table.
ALTER TABLE users ADD COLUMN IF NOT EXISTS tier VARCHAR(16) NOT NULL DEFAULT 'free';
ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(64);
ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(64);
