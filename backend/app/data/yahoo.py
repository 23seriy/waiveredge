"""Yahoo Fantasy Sports API client.

Handles OAuth 2.0 token exchange/refresh and fetches league data (roster,
scoring settings, free agents) from the Yahoo Fantasy v2 API.

Yahoo Fantasy responses are XML by default; we request JSON via ``format=json``.
The JSON shapes are nested and a bit inconsistent — the helpers here normalize
them into the flat shapes the scoring engine consumes.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from ..config import settings

AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
FANTASY_BASE = "https://fantasysports.yahooapis.com/fantasy/v2"

# Yahoo game key for NBA. Changes each season; "nba" is the alias.
NBA_GAME_KEY = "nba"


def authorization_url(state: str = "") -> str:
    """Build the Yahoo OAuth authorize redirect URL."""
    params = {
        "client_id": settings.yahoo_client_id,
        "redirect_uri": settings.yahoo_redirect_uri,
        "response_type": "code",
        "language": "en-us",
    }
    if state:
        params["state"] = state
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{AUTH_URL}?{qs}"


def exchange_code(code: str) -> dict:
    """Exchange an authorization code for access + refresh tokens."""
    resp = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.yahoo_redirect_uri,
        },
        auth=(settings.yahoo_client_id, settings.yahoo_client_secret),
        timeout=15,
    )
    resp.raise_for_status()
    return _normalize_tokens(resp.json())


def refresh_tokens(refresh_token: str) -> dict:
    """Use a refresh token to get a new access token."""
    resp = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        auth=(settings.yahoo_client_id, settings.yahoo_client_secret),
        timeout=15,
    )
    resp.raise_for_status()
    return _normalize_tokens(resp.json())


def _normalize_tokens(data: dict) -> dict:
    expires_in = data.get("expires_in", 3600)
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
        "token_type": data.get("token_type", "bearer"),
        "expires_in": expires_in,
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat(),
    }


class YahooFantasyClient:
    """Authenticated Yahoo Fantasy API client.

    Automatically refreshes tokens when expired. Pass the stored oauth_tokens
    dict from league_connections; the caller should persist the updated tokens
    if ``tokens_refreshed`` is True after any call.
    """

    def __init__(self, tokens: dict):
        self._tokens = dict(tokens)
        self.tokens_refreshed = False

    @property
    def access_token(self) -> str:
        expires_at = self._tokens.get("expires_at", "")
        if expires_at:
            exp = datetime.fromisoformat(expires_at)
            if datetime.now(timezone.utc) >= exp - timedelta(minutes=2):
                self._refresh()
        return self._tokens["access_token"]

    @property
    def current_tokens(self) -> dict:
        return dict(self._tokens)

    def _refresh(self) -> None:
        new = refresh_tokens(self._tokens["refresh_token"])
        self._tokens.update(new)
        self.tokens_refreshed = True

    def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{FANTASY_BASE}/{path}"
        p = dict(params or {})
        p["format"] = "json"
        resp = httpx.get(
            url, params=p,
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    # ---- High-level queries ------------------------------------------------

    def user_leagues(self) -> list[dict]:
        """Return the user's NBA fantasy leagues for the current season."""
        data = self._get(f"users;use_login=1/games;game_keys={NBA_GAME_KEY}/leagues")
        try:
            games = data["fantasy_content"]["users"]["0"]["user"][1]["games"]
            leagues_node = games["0"]["game"][1]["leagues"]
            count = leagues_node["count"]
            return [
                {
                    "league_key": leagues_node[str(i)]["league"][0]["league_key"],
                    "name": leagues_node[str(i)]["league"][0]["name"],
                    "num_teams": leagues_node[str(i)]["league"][0].get("num_teams", 0),
                    "scoring_type": leagues_node[str(i)]["league"][0].get("scoring_type", ""),
                }
                for i in range(count)
            ]
        except (KeyError, IndexError, TypeError):
            return []

    def league_settings(self, league_key: str) -> dict:
        """Fetch league scoring settings (stat categories + modifiers)."""
        data = self._get(f"league/{league_key}/settings")
        try:
            settings_node = data["fantasy_content"]["league"][1]["settings"][0]
            stat_mods = {
                str(s["stat"]["stat_id"]): float(s["stat"].get("value", 0))
                for s in settings_node.get("stat_modifiers", {}).get("stats", [])
            }
            categories = [
                {
                    "stat_id": str(s["stat"]["stat_id"]),
                    "name": s["stat"].get("name", ""),
                    "display_name": s["stat"].get("display_name", ""),
                    "enabled": s["stat"].get("enabled") == "1",
                    "modifier": stat_mods.get(str(s["stat"]["stat_id"]), 0),
                }
                for s in settings_node.get("stat_categories", {}).get("stats", [])
            ]
            return {
                "league_key": league_key,
                "scoring_type": data["fantasy_content"]["league"][0].get("scoring_type", ""),
                "categories": categories,
            }
        except (KeyError, IndexError, TypeError):
            return {"league_key": league_key, "scoring_type": "", "categories": []}

    def my_team_key(self, league_key: str) -> str | None:
        """Find the authenticated user's team key in a league."""
        data = self._get(f"league/{league_key}/teams")
        try:
            teams = data["fantasy_content"]["league"][1]["teams"]
            for i in range(teams["count"]):
                team = teams[str(i)]["team"][0]
                for item in team:
                    if isinstance(item, dict) and item.get("is_owned_by_current_login") == "1":
                        for k in team:
                            if isinstance(k, dict) and "team_key" in k:
                                return k["team_key"]
            return None
        except (KeyError, IndexError, TypeError):
            return None

    def roster(self, team_key: str) -> list[dict]:
        """Fetch the authenticated user's roster."""
        data = self._get(f"team/{team_key}/roster/players")
        try:
            players = data["fantasy_content"]["team"][1]["roster"]["0"]["players"]
            result = []
            for i in range(players["count"]):
                p_data = players[str(i)]["player"][0]
                name, position, player_key = "", "", ""
                for item in p_data:
                    if isinstance(item, dict):
                        if "name" in item:
                            name = item["name"].get("full", "")
                        if "display_position" in item:
                            position = item["display_position"]
                        if "player_key" in item:
                            player_key = item["player_key"]
                slot = ""
                player_info = players[str(i)]["player"]
                if len(player_info) > 1:
                    pos_node = player_info[1].get("selected_position", [{}])
                    if isinstance(pos_node, list) and pos_node and isinstance(pos_node[0], dict):
                        slot = pos_node[0].get("position", "")
                result.append({"player_key": player_key, "name": name, "position": position, "slot": slot})
            return result
        except (KeyError, IndexError, TypeError):
            return []

    def free_agents(self, league_key: str, count: int = 50) -> list[dict]:
        """Top available free agents in the league."""
        data = self._get(f"league/{league_key}/players;status=FA;count={count}")
        try:
            players = data["fantasy_content"]["league"][1]["players"]
            result = []
            for i in range(players["count"]):
                p_data = players[str(i)]["player"][0]
                name, position = "", ""
                for item in p_data:
                    if isinstance(item, dict):
                        if "name" in item:
                            name = item["name"].get("full", "")
                        if "display_position" in item:
                            position = item["display_position"]
                result.append({"name": name, "position": position})
            return result
        except (KeyError, IndexError, TypeError):
            return []
