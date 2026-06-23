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

# Yahoo game key. "nba" for production; switch to "mlb"/"nfl"/"nhl" to test
# during the NBA offseason. Configurable via YAHOO_GAME_KEY env var.
GAME_KEY = getattr(settings, "yahoo_game_key", "nba") or "nba"


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
        self.my_team_key_cached: str | None = None

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

    def _post_xml(self, path: str, xml_body: str) -> httpx.Response:
        """POST an XML payload to the Yahoo Fantasy API."""
        url = f"{FANTASY_BASE}/{path}"
        resp = httpx.post(
            url,
            content=xml_body.encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/xml",
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp

    # ---- High-level queries ------------------------------------------------

    def user_leagues(self, game_key: str | None = None) -> list[dict]:
        """Return the user's fantasy leagues for the current season."""
        gk = game_key or GAME_KEY
        data = self._get(f"users;use_login=1/games;game_keys={gk}/leagues")
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
        """Find the authenticated user's team key in a league.

        Uses the user's own teams endpoint (which reliably includes
        is_owned_by_current_login) rather than the league's teams endpoint
        (which omits it). Matches by league_key prefix in the team_key.
        """
        data = self._get("users;use_login=1/teams")
        try:
            teams = data["fantasy_content"]["users"]["0"]["user"][1]["teams"]
            for i in range(teams["count"]):
                inner = teams[str(i)]["team"][0]
                key = None
                for item in inner:
                    if isinstance(item, dict) and "team_key" in item:
                        key = item["team_key"]
                # team_key format: "469.l.233345.t.4" — starts with league_key
                if key and key.startswith(league_key + ".t."):
                    return key
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

    def free_agents(self, league_key: str, max_players: int = 500) -> list[dict]:
        """Fetch available free agents in the league (paginated, up to max_players)."""
        result: list[dict] = []
        start = 0
        page_size = 250  # Yahoo max per request
        while start < max_players:
            batch_size = min(page_size, max_players - start)
            try:
                data = self._get(
                    f"league/{league_key}/players;status=A;start={start};count={batch_size}")
                players = data["fantasy_content"]["league"][1]["players"]
                if not isinstance(players, dict):
                    break
                count = players.get("count", 0)
                if count == 0:
                    break
                for i in range(count):
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
                    if name:
                        result.append({"name": name, "position": position, "player_key": player_key})
                if count < batch_size:
                    break  # No more pages
                start += count
            except (KeyError, IndexError, TypeError):
                break
        return result

    # ---- Transactions ------------------------------------------------------

    def add_drop_player(
        self,
        league_key: str,
        team_key: str,
        add_player_key: str,
        drop_player_key: str | None = None,
    ) -> dict:
        """Submit an add (or add/drop) transaction to Yahoo.

        Returns {"success": True, ...} on success, or raises
        httpx.HTTPStatusError on failure (e.g. player on waivers).
        """
        if drop_player_key:
            xml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                "<fantasy_content>"
                "<transaction>"
                "<type>add/drop</type>"
                "<players>"
                f"<player><player_key>{add_player_key}</player_key>"
                "<transaction_data><type>add</type>"
                f"<destination_team_key>{team_key}</destination_team_key>"
                "</transaction_data></player>"
                f"<player><player_key>{drop_player_key}</player_key>"
                "<transaction_data><type>drop</type>"
                f"<source_team_key>{team_key}</source_team_key>"
                "</transaction_data></player>"
                "</players>"
                "</transaction>"
                "</fantasy_content>"
            )
        else:
            xml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                "<fantasy_content>"
                "<transaction>"
                "<type>add</type>"
                "<players>"
                f"<player><player_key>{add_player_key}</player_key>"
                "<transaction_data><type>add</type>"
                f"<destination_team_key>{team_key}</destination_team_key>"
                "</transaction_data></player>"
                "</players>"
                "</transaction>"
                "</fantasy_content>"
            )
        resp = self._post_xml(f"league/{league_key}/transactions", xml)
        return {"success": True, "status_code": resp.status_code, "body": resp.text[:500]}
