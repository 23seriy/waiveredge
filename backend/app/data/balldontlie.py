"""Thin balldontlie API client.

Base URL: https://api.balldontlie.io  (auth via `Authorization: <API_KEY>` header)

Tiers (req/min): Free 5  |  ALL-STAR 60 ($9.99)  |  GOAT 600 ($39.99)
  - /v1/teams, /v1/players, /v1/games  -> Free
  - /v1/stats, /v1/player_injuries      -> ALL-STAR
  - /v1/season_averages/{category}      -> GOAT

Cursor pagination via `cursor` + `per_page` (max 100); responses carry
`meta.next_cursor`.
"""
from __future__ import annotations

import time
from typing import Any

import httpx

from ..config import settings


class BalldontlieError(RuntimeError):
    pass


class BalldontlieClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 min_interval: float = 0.2):
        self.api_key = api_key if api_key is not None else settings.balldontlie_api_key
        self.base_url = (base_url or settings.balldontlie_base_url).rstrip("/")
        self._min_interval = min_interval  # crude rate-limit guard between calls
        self._last_call = 0.0
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": self.api_key} if self.api_key else {},
            timeout=30.0,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "BalldontlieClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.monotonic()

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        if not self.api_key:
            raise BalldontlieError(
                "No BALLDONTLIE_API_KEY set. Get a key at https://app.balldontlie.io "
                "(stats/injuries need the ALL-STAR tier)."
            )
        self._throttle()
        resp = self._client.get(path, params=params or {})
        if resp.status_code == 401:
            raise BalldontlieError("401 Unauthorized — check BALLDONTLIE_API_KEY.")
        if resp.status_code == 429:
            raise BalldontlieError("429 Rate limited — slow down or upgrade tier.")
        resp.raise_for_status()
        return resp.json()

    def _paginate(self, path: str, params: dict[str, Any] | None = None,
                  per_page: int = 100, max_pages: int = 100) -> list[dict]:
        params = dict(params or {})
        params["per_page"] = per_page
        out: list[dict] = []
        cursor: Any = None
        for _ in range(max_pages):
            if cursor is not None:
                params["cursor"] = cursor
            payload = self._get(path, params)
            out.extend(payload.get("data", []))
            cursor = payload.get("meta", {}).get("next_cursor")
            if not cursor:
                break
        return out

    # -- endpoints ------------------------------------------------------------
    def teams(self) -> list[dict]:
        return self._paginate("/v1/teams")

    def players(self, team_ids: list[int] | None = None) -> list[dict]:
        params: dict[str, Any] = {}
        if team_ids:
            params["team_ids[]"] = team_ids
        return self._paginate("/v1/players", params)

    def games(self, start_date: str, end_date: str,
              seasons: list[int] | None = None) -> list[dict]:
        params: dict[str, Any] = {"start_date": start_date, "end_date": end_date}
        if seasons:
            params["seasons[]"] = seasons
        return self._paginate("/v1/games", params)

    def stats(self, start_date: str, end_date: str,
              seasons: list[int] | None = None) -> list[dict]:
        """Per-game player box scores. Requires ALL-STAR tier."""
        params: dict[str, Any] = {"start_date": start_date, "end_date": end_date}
        if seasons:
            params["seasons[]"] = seasons
        return self._paginate("/v1/stats", params)

    def player_injuries(self, team_ids: list[int] | None = None) -> list[dict]:
        """Active injuries. Requires ALL-STAR tier."""
        params: dict[str, Any] = {}
        if team_ids:
            params["team_ids[]"] = team_ids
        return self._paginate("/v1/player_injuries", params)
