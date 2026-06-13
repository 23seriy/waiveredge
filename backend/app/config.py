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

    cors_origins: str = "http://localhost:3000"


settings = Settings()
