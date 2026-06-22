"""Build real WNBA fixtures from ESPN's public core API (free, no auth).

Produces the same fixture shapes the scoring engine consumes — teams, players,
game_logs, schedule, injuries, roster — with basketball stats. Lazily
materialized on first request, same pattern as mlb_fixtures.py.

ESPN's core API is public and well-documented.
Base: https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import date as date_cls
from datetime import timedelta
from pathlib import Path

import httpx

ESPN_CORE = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba"
ESPN_WEB = "https://site.web.api.espn.com/apis/common/v3/sports/basketball/wnba"

# WNBA position mapping
POS_MAP = {
    "PG": "G", "SG": "G", "G": "G",
    "SF": "F", "PF": "F", "F": "F",
    "C": "C",
}


def _get(url: str, params: dict | None = None) -> dict:
    """GET with retry."""
    for attempt in range(3):
        try:
            resp = httpx.get(url, params=params or {}, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, httpx.TimeoutException):
            if attempt == 2:
                raise
            time.sleep(1)
    return {}


def _norm_pos(pos_abbr: str | None) -> list[str]:
    if not pos_abbr:
        return ["G"]
    return [POS_MAP.get(pos_abbr.strip().upper(), "G")]


def _select_week(season: int) -> tuple[str, str]:
    """Select the current real-world week (Monday–Sunday).

    WNBA season typically runs May–October.
    """
    today = date_cls.today()
    season_start = date_cls(season, 5, 1)
    season_end = date_cls(season, 10, 31)

    if season_start <= today <= season_end:
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        return (monday.isoformat(), sunday.isoformat())

    # Offseason fallback — mid-July
    return (f"{season}-07-14", f"{season}-07-20")


def build_real_fixtures(output_dir: Path, season: int | None = None) -> None:
    """Fetch real WNBA data and write fixture JSONs to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    today = date_cls.today()
    if season is None:
        season = today.year

    # 1. Fetch teams
    print(f"[WNBA] Fetching teams for {season}...")
    data = _get(f"{ESPN_CORE}/teams", {"limit": 50})
    teams = []
    for t in data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", []):
        team = t.get("team", {})
        teams.append({
            "id": int(team["id"]),
            "abbreviation": team.get("abbreviation", ""),
            "full_name": team.get("displayName", ""),
        })
    print(f"[WNBA] {len(teams)} teams")

    # 2. Select the scoring week
    week_start, week_end = _select_week(season)
    print(f"[WNBA] Selected week: {week_start} → {week_end}")

    # 3. Fetch schedule for the week
    schedule = []
    ws = date_cls.fromisoformat(week_start)
    we = date_cls.fromisoformat(week_end)
    d = ws
    while d <= we:
        try:
            sched = _get(f"{ESPN_CORE}/scoreboard", {"dates": d.strftime("%Y%m%d")})
            for event in sched.get("events", []):
                comps = event.get("competitions", [{}])
                if not comps:
                    continue
                comp = comps[0]
                home_id = None
                away_id = None
                for c in comp.get("competitors", []):
                    tid = int(c.get("id", 0))
                    if c.get("homeAway") == "home":
                        home_id = tid
                    else:
                        away_id = tid
                if home_id and away_id:
                    schedule.append({
                        "id": int(event.get("id", 0)),
                        "date": d.isoformat(),
                        "home_team_id": home_id,
                        "visitor_team_id": away_id,
                    })
            time.sleep(0.1)
        except Exception as e:
            print(f"  Warning: schedule fetch failed for {d}: {e}")
        d += timedelta(days=1)
    print(f"[WNBA] {len(schedule)} games in the week")

    # 4. Fetch rosters for each team
    print("[WNBA] Fetching rosters...")
    players = []
    seen_ids: set[int] = set()
    for team in teams:
        try:
            roster_data = _get(f"{ESPN_CORE}/teams/{team['id']}/roster", {"season": season})
            for group in roster_data.get("athletes", []):
                for athlete in group.get("items", []):
                    pid = int(athlete.get("id", 0))
                    if pid in seen_ids:
                        continue
                    seen_ids.add(pid)
                    pos = athlete.get("position", {}).get("abbreviation", "G")
                    players.append({
                        "id": pid,
                        "name": athlete.get("displayName", athlete.get("fullName", "")),
                        "team_id": team["id"],
                        "positions": _norm_pos(pos),
                    })
            time.sleep(0.1)
        except Exception as e:
            print(f"  Warning: roster failed for {team['abbreviation']}: {e}")
    print(f"[WNBA] {len(players)} players")

    # 5. Fetch game logs for a recent window (last 30 days)
    log_end = date_cls.fromisoformat(week_start) - timedelta(days=1)
    log_start = log_end - timedelta(days=30)
    print(f"[WNBA] Fetching game logs ({log_start} → {log_end})...")

    # Fetch completed games in that window
    game_ids: list[int] = []
    d = log_start
    while d <= log_end:
        try:
            sched = _get(f"{ESPN_CORE}/scoreboard", {"dates": d.strftime("%Y%m%d")})
            for event in sched.get("events", []):
                status = event.get("status", {}).get("type", {}).get("state", "")
                if status == "post":
                    game_ids.append(int(event["id"]))
            time.sleep(0.05)
        except Exception:
            pass
        d += timedelta(days=1)
    print(f"[WNBA] {len(game_ids)} completed games to process")

    # Fetch box scores
    game_logs = []
    players_by_id = {p["id"]: p for p in players}
    for i, gid in enumerate(game_ids):
        try:
            boxscore = _get(f"{ESPN_CORE}/summary", {"event": gid})
            game_date = boxscore.get("header", {}).get("competitions", [{}])[0].get("date", "")[:10]
            for team_box in boxscore.get("boxscore", {}).get("players", []):
                team_id = int(team_box.get("team", {}).get("id", 0))
                # Find opponent
                comps = boxscore.get("header", {}).get("competitions", [{}])[0].get("competitors", [])
                opp_id = 0
                for c in comps:
                    cid = int(c.get("id", 0))
                    if cid != team_id:
                        opp_id = cid
                        break

                for stat_group in team_box.get("statistics", []):
                    for athlete_entry in stat_group.get("athletes", []):
                        athlete = athlete_entry.get("athlete", {})
                        pid = int(athlete.get("id", 0))
                        stats_list = athlete_entry.get("stats", [])
                        if not stats_list or len(stats_list) < 13:
                            continue
                        # ESPN basketball box score stat order:
                        # 0=MIN, 1=FG, 2=3PT, 3=FT, 4=OREB, 5=DREB, 6=REB,
                        # 7=AST, 8=STL, 9=BLK, 10=TO, 11=PF, 12=PTS
                        try:
                            fg_parts = stats_list[1].split("-")
                            fg3_parts = stats_list[2].split("-")
                            ft_parts = stats_list[3].split("-")

                            stats = {
                                "pts": int(stats_list[12]),
                                "reb": int(stats_list[6]),
                                "ast": int(stats_list[7]),
                                "stl": int(stats_list[8]),
                                "blk": int(stats_list[9]),
                                "fg3m": int(fg3_parts[0]),
                                "turnover": int(stats_list[10]),
                                "fgm": int(fg_parts[0]),
                                "fga": int(fg_parts[1]) if len(fg_parts) > 1 else 0,
                                "ftm": int(ft_parts[0]),
                                "fta": int(ft_parts[1]) if len(ft_parts) > 1 else 0,
                            }
                            pos = players_by_id.get(pid, {}).get("positions", ["G"])[0]
                            game_logs.append({
                                "player_id": pid,
                                "game_id": gid,
                                "date": game_date,
                                "team_id": team_id,
                                "opponent_id": opp_id,
                                "position": pos,
                                "stats": stats,
                            })
                        except (ValueError, IndexError):
                            continue
            time.sleep(0.15)
        except Exception:
            pass
        if (i + 1) % 20 == 0:
            print(f"  ... {i + 1}/{len(game_ids)} games processed")

    print(f"[WNBA] {len(game_logs)} game log rows")

    # 6. Build a default roster (top players by game log count)
    log_counts: dict[int, int] = defaultdict(int)
    for lg in game_logs:
        log_counts[lg["player_id"]] += 1
    top_players = sorted(log_counts.keys(), key=lambda pid: log_counts[pid], reverse=True)

    roster_ids: list[int] = []
    roster_teams: set[int] = set()
    for pid in top_players:
        p = players_by_id.get(pid)
        if p and p["team_id"] not in roster_teams and len(roster_ids) < 10:
            roster_ids.append(pid)
            roster_teams.add(p["team_id"])

    free_agents = [p["id"] for p in players if p["id"] not in set(roster_ids)]

    roster = {
        "week_start": week_start,
        "week_end": week_end,
        "scoring": None,
        "mode": "points",
        "roster": [{"player_id": pid, "slot": players_by_id[pid]["positions"][0]} for pid in roster_ids],
        "free_agents": free_agents,
        "droppable": roster_ids,
    }

    # Write fixtures
    (output_dir / "teams.json").write_text(json.dumps(teams, indent=2))
    (output_dir / "players.json").write_text(json.dumps(players, indent=2))
    (output_dir / "game_logs.json").write_text(json.dumps(game_logs, indent=2))
    (output_dir / "schedule.json").write_text(json.dumps(schedule, indent=2))
    (output_dir / "injuries.json").write_text(json.dumps([]))
    (output_dir / "roster.json").write_text(json.dumps(roster, indent=2))

    print(f"[WNBA] Fixtures written to {output_dir}")
    print(f"  teams={len(teams)} players={len(players)} logs={len(game_logs)} "
          f"schedule={len(schedule)} roster={len(roster_ids)}")
