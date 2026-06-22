"""ESPN Fantasy Sports API client.

ESPN's Fantasy API is undocumented but well-reverse-engineered. Private leagues
require two browser cookies (espn_s2 + SWID); public leagues need no auth.

Base URL: https://lm-api-reads.fantasy.espn.com/apis/v3/games/{gameCode}/
Game codes: fba (basketball), flb (baseball), fhl (hockey), ffl (football), wfba (WNBA)
"""
from __future__ import annotations

from typing import Any

import httpx

ESPN_BASE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games"

GAME_CODES = {
    "nba": "fba",
    "mlb": "flb",
    "nfl": "ffl",
    "nhl": "fhl",
    "wnba": "wfba",
}

# ESPN stat ID → our fixture stat keys (basketball)
ESPN_NBA_STAT_MAP: dict[int, str] = {
    0: "pts", 1: "blk", 2: "stl", 3: "ast", 6: "reb",
    11: "turnover", 17: "fg3m", 13: "fgm", 14: "fga", 15: "ftm", 16: "fta",
}

# ESPN stat ID → our fixture stat keys (WNBA basketball — same IDs as NBA)
ESPN_WNBA_STAT_MAP: dict[int, str] = {
    0: "pts", 1: "blk", 2: "stl", 3: "ast", 6: "reb",
    11: "turnover", 17: "fg3m", 13: "fgm", 14: "fga", 15: "ftm", 16: "fta",
}

# ESPN stat ID → our fixture stat keys (baseball)
# Verified against real player data (Juan Soto, etc.)
# Hitting: 0=AB, 1=H, 5=HR, 6=RBI, 7=R, 10=BB, 11=HBP, 20=SB, 27=K
# Pitching: 34=W, 37=SV(blown), 39=HA, 45=ER, 48=K, 53=QS, 54=blown saves
ESPN_MLB_STAT_MAP: dict[int, str] = {
    # Hitting
    0: "ab", 1: "h", 5: "hr", 6: "rbi", 7: "r",
    8: "h",   # total bases → approximate as hits for scoring
    10: "bb", 20: "sb", 21: "r",   # 21=runs (duplicate stat id in some leagues)
    23: "sb", 27: "k_hitting",
    # Pitching
    34: "w", 37: "er",  # 37=ER (not saves)
    39: "ha", 45: "er",
    48: "k_pitching", 53: "ip",   # 53=quality starts → approximate as IP
    57: "sv",
    60: "ip",
}


class ESPNFantasyClient:
    """ESPN Fantasy API client. Supports public and private leagues."""

    def __init__(self, sport: str = "nba", espn_s2: str = "", swid: str = ""):
        self.sport = sport
        self.game_code = GAME_CODES.get(sport, "fba")
        self._cookies: dict[str, str] = {}
        if espn_s2:
            self._cookies["espn_s2"] = espn_s2
        if swid:
            self._cookies["SWID"] = swid

    def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{ESPN_BASE}/{self.game_code}/{path}"
        resp = httpx.get(url, params=params or {}, cookies=self._cookies, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def league_data(self, league_id: int, season: int, views: list[str] | None = None) -> dict:
        """Fetch league data with optional views."""
        params: dict[str, Any] = {}
        if views:
            params["view"] = views  # httpx handles list params
        return self._get(f"seasons/{season}/segments/0/leagues/{league_id}", params)

    def settings(self, league_id: int, season: int) -> dict:
        """Fetch league scoring settings."""
        data = self.league_data(league_id, season, views=["mSettings"])
        raw_settings = data.get("settings", {})
        scoring = raw_settings.get("scoringSettings", {})
        scoring_items = scoring.get("scoringItems", [])

        stat_map = (
            ESPN_MLB_STAT_MAP if self.sport == "mlb"
            else ESPN_WNBA_STAT_MAP if self.sport == "wnba"
            else ESPN_NBA_STAT_MAP
        )
        weights: dict[str, float] = {}
        for item in scoring_items:
            stat_id = item.get("statId")
            points = item.get("pointsOverrides", {}).get(str(stat_id), item.get("points", 0))
            our_key = stat_map.get(stat_id)
            if our_key and points:
                weights[our_key] = weights.get(our_key, 0) + float(points)

        scoring_type = raw_settings.get("scoringType", "")
        return {
            "scoring_type": scoring_type,
            "weights": weights,
            "roster_slots": raw_settings.get("rosterSettings", {}).get("lineupSlotCounts", {}),
        }

    def teams(self, league_id: int, season: int) -> list[dict]:
        """Fetch all teams in the league with roster previews for identification."""
        data = self.league_data(league_id, season, views=["mTeam", "mRoster"])
        result = []
        for t in data.get("teams", []):
            name = f"{t.get('location', '')} {t.get('nickname', '')}".strip()
            abbrev = t.get("abbrev", "")
            if not name:
                name = f"Team {t['id']}" + (f" ({abbrev})" if abbrev else "")
            # Include top roster players for identification.
            entries = t.get("roster", {}).get("entries", [])
            top_players = [
                e.get("playerPoolEntry", {}).get("player", {}).get("fullName", "")
                for e in entries[:4]
            ]
            result.append({
                "id": t.get("id"),
                "name": name,
                "abbrev": abbrev,
                "top_players": [p for p in top_players if p],
            })
        return result

    def roster(self, league_id: int, season: int, team_id: int) -> list[dict]:
        """Fetch a specific team's roster."""
        data = self.league_data(league_id, season, views=["mRoster"])
        for team in data.get("teams", []):
            if team.get("id") != team_id:
                continue
            entries = team.get("roster", {}).get("entries", [])
            result = []
            for entry in entries:
                player = entry.get("playerPoolEntry", {}).get("player", {})
                result.append({
                    "espn_id": player.get("id"),
                    "name": player.get("fullName", ""),
                    "position": player.get("defaultPositionId", 0),
                    "slot": entry.get("lineupSlotId", 0),
                })
            return result
        return []

    def free_agents(self, league_id: int, season: int, count: int = 200) -> list[dict]:
        """Fetch available free agents."""
        params: dict[str, Any] = {
            "view": "kona_player_info",
            "scoringPeriodId": 0,  # current period
        }
        # ESPN uses X-Fantasy-Filter header for FA filtering
        headers = {
            "X-Fantasy-Filter": '{"players":{"filterStatus":{"value":["FREEAGENT","WAIVERS"]},'
                                f'"limit":{count},"sortPercOwned":{{"sortPriority":1,"sortAsc":false}}}}}}'
        }
        try:
            url = f"{ESPN_BASE}/{self.game_code}/seasons/{season}/segments/0/leagues/{league_id}"
            resp = httpx.get(
                url, params=params, cookies=self._cookies,
                headers=headers, timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            players = data.get("players", [])
            return [
                {
                    "espn_id": p.get("id"),
                    "name": p.get("player", {}).get("fullName", ""),
                    "position": p.get("player", {}).get("defaultPositionId", 0),
                }
                for p in players
                if p.get("status") in ("FREEAGENT", "WAIVERS")
            ]
        except Exception:
            return []

    def my_team_id(self, league_id: int, season: int) -> int | None:
        """Find the authenticated user's team ID (requires cookies)."""
        if not self._cookies:
            return None
        data = self.league_data(league_id, season, views=["mTeam"])
        swid = self._cookies.get("SWID", "").strip("{}")
        for team in data.get("teams", []):
            owners = team.get("owners", [])
            for owner in owners:
                if owner and swid and owner.strip("{}") == swid:
                    return team["id"]
        return None
