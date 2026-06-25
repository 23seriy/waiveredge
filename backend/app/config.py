"""Application settings, read from the environment (12-factor)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres connection string.
    database_url: str = "postgresql+psycopg2://waiveredge:waiveredge@localhost:5432/waiveredge"

    # balldontlie API. Stats + injuries require at least the ALL-STAR tier ($9.99/mo).
    balldontlie_api_key: str = ""
    balldontlie_base_url: str = "https://api.balldontlie.io"

    # Current NBA season (start year) used for ingestion queries.
    season: int = 2025

    cors_origins: str = "http://localhost:3000,https://localhost:3000"

    # Frontend URL for OAuth/billing redirects.
    frontend_url: str = "http://localhost:3000"

    # Yahoo OAuth 2.0 (register at https://developer.yahoo.com/apps/)
    yahoo_client_id: str = ""
    yahoo_client_secret: str = ""
    yahoo_redirect_uri: str = "http://localhost:8000/api/auth/yahoo/callback"
    yahoo_game_key: str = "nba"  # nba | mlb | nfl | nhl — switch for offseason testing

    # Google OAuth 2.0 (https://console.cloud.google.com/apis/credentials)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"

    # App secret for signing session cookies (generate a random one for production).
    app_secret: str = "change-me-in-production"

    # OpenAI API key for LLM-generated rationales.
    openai_api_key: str = ""

    # Sentry error monitoring (https://sentry.io — free tier: 5k errors/mo)
    sentry_dsn: str = ""

    # Stripe (https://dashboard.stripe.com/apikeys)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_monthly_price_id: str = ""     # price ID for $8/mo
    stripe_pro_season_price_id: str = ""      # price ID for $39/season


settings = Settings()
