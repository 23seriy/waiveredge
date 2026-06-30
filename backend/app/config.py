"""Application settings, read from the environment (12-factor)."""
from __future__ import annotations

from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_APP_SECRET = "change-me-in-production"


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

    # Optional regex for additional allowed origins (e.g. preview deploys).
    # Empty by default — with allow_credentials=True we must not trust a
    # wildcard host. Set explicitly in prod if you need preview-URL access.
    cors_origin_regex: str = ""

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

    # Deployment environment: "development" (default) | "production" | "staging".
    # Anything other than "development" requires a real app_secret.
    environment: str = "development"

    # App secret for signing session cookies (generate a random one for production).
    app_secret: str = _DEFAULT_APP_SECRET

    # OpenAI API key for LLM-generated rationales.
    openai_api_key: str = ""

    # Sentry error monitoring (https://sentry.io — free tier: 5k errors/mo)
    sentry_dsn: str = ""

    # Stripe (https://dashboard.stripe.com/apikeys)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_monthly_price_id: str = ""     # price ID for $8/mo
    stripe_pro_season_price_id: str = ""      # price ID for $39/season

    @model_validator(mode="after")
    def _require_prod_secret(self) -> "Settings":
        if self.environment != "development" and self.app_secret == _DEFAULT_APP_SECRET:
            raise ValueError(
                "APP_SECRET must be set when ENVIRONMENT is not 'development'. "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        return self


settings = Settings()


def safe_redirect_url(path: str) -> str:
    """Build a redirect URL validated against allowed origins.

    Prevents open-redirect attacks by ensuring the target host matches
    frontend_url or one of the CORS origins.
    """
    parsed = urlparse(path)
    # Relative paths are always safe.
    if not parsed.scheme and not parsed.netloc:
        return path

    allowed_origins = {settings.frontend_url.rstrip("/")}
    for origin in settings.cors_origins.split(","):
        origin = origin.strip()
        if origin:
            allowed_origins.add(origin.rstrip("/"))

    target_origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    if target_origin not in allowed_origins:
        # Fall back to frontend_url with the original path.
        return f"{settings.frontend_url.rstrip('/')}{parsed.path}"
    return path
