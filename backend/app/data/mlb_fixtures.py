"""Build real MLB fixtures from statsapi.mlb.com (free, no auth).

Produces the same fixture shapes the scoring engine consumes — teams, players,
game_logs, schedule, injuries, roster — but with baseball stats. Lazily
materialized on first request, same pattern as nba_fixtures.py.

The MLB Stats API is public, well-documented, and works from any IP (no
datacenter blocking like stats.nba.com).
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import date as date_cls
from datetime import timedelta
from pathlib import Path

import httpx

MLB_BASE = "https://statsapi.mlb.com/api/v1"
SPORT_ID = 1  # MLB

# Map MLB API position abbreviations to our canonical MLB positions.
POS_MAP = {
    "P": "SP", "SP": "SP", "RP": "RP", "CL": "RP",
    "C": "C", "1B": "1B", "2B": "2B", "SS": "SS", "3B": "3B",
    "LF": "OF", "CF": "OF", "RF": "OF", "OF": "OF",
    "DH": "DH", "PH": "DH", "PR": "DH",
    "TWP": "DH", "UT": "DH",
}


def _get(path: str, params: dict | None = None) -> dict:
    """GET from the MLB Stats API with basic retry."""
    url = f"{MLB_BASE}/{path}"
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
        return ["DH"]
    return [POS_MAP.get(pos_abbr.strip().upper(), "DH")]


def _select_week(season: int) -> tuple[str, str]:
    """Pick a representative mid-season week (densest week in the middle third).

    MLB regular season is roughly April–September. We pick from the middle third
    (late May – late July) to avoid opening-week weirdness and September callups.
    """
    data = _get("schedule", {
        "sportId": SPORT_ID, "season": season, "gameType": "R",
        "startDate": f"{season}-04-01", "endDate": f"{season}-09-30",
    })
    dates = data.get("dates", [])
    if not dates:
        return (f"{season}-06-16", f"{season}-06-22")

    # Middle third
    n = len(dates)
    mid_dates = dates[n // 3: 2 * n // 3]
    if not mid_dates:
        mid_dates = dates

    # Find the densest 7-day window
    best_start = 0
    best_count = 0
    for i in range(len(mid_dates)):
        start_date = mid_dates[i]["date"]
        end_date = (date_cls.fromisoformat(start_date) + timedelta(days=6)).isoformat()
        count = sum(
            len(d.get("games", []))
            for d in mid_dates[i:]
            if d["date"] <= end_date
        )
        if count > best_count:
            best_count = count
            best_start = i

    start = mid_dates[best_start]["date"]
    end = (date_cls.fromisoformat(start) + timedelta(days=6)).isoformat()
    return (start, end)


def build_real_fixtures(output_dir: Path, season: int | None = None) -> None:
    """Fetch real MLB data and write fixture JSONs to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine season
    today = date_cls.today()
    if season is None:
        season = today.year

    print(f"[MLB] Fetching teams for {season}...")
    teams_data = _get("teams", {"sportId": SPORT_ID, "season": season})
    teams = [
        {"id": t["id"], "abbreviation": t["abbreviation"], "full_name": t["name"]}
        for t in teams_data.get("teams", [])
    ]
    teams_by_id = {t["id"]: t for t in teams}

    # Select the scoring week
    week_start, week_end = _select_week(season)
    print(f"[MLB] Selected week: {week_start} → {week_end}")

    # Schedule for the week
    sched_data = _get("schedule", {
        "sportId": SPORT_ID, "startDate": week_start, "endDate": week_end, "gameType": "R",
    })
    schedule = []
    for day in sched_data.get("dates", []):
        for g in day.get("games", []):
            away_id = g["teams"]["away"]["team"]["id"]
            home_id = g["teams"]["home"]["team"]["id"]
            schedule.append({
                "id": g["gamePk"],
                "date": day["date"],
                "home_team_id": home_id,
                "visitor_team_id": away_id,
            })
    print(f"[MLB] {len(schedule)} games in the week")

    # Collect active rosters for all teams
    print("[MLB] Fetching rosters...")
    players = []
    seen_ids: set[int] = set()
    for team in teams:
        try:
            roster_data = _get(f"teams/{team['id']}/roster", {
                "rosterType": "active", "season": season,
            })
            for entry in roster_data.get("roster", []):
                pid = entry["person"]["id"]
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)
                pos = entry.get("position", {}).get("abbreviation", "")
                players.append({
                    "id": pid,
                    "name": entry["person"]["fullName"],
                    "team_id": team["id"],
                    "positions": _norm_pos(pos),
                })
            time.sleep(0.2)  # Be polite to the API
        except Exception as e:
            print(f"  Warning: failed to get roster for {team['abbreviation']}: {e}")

    print(f"[MLB] {len(players)} players")

    # Fetch game logs for a recent window (last 30 days before the week)
    log_end = date_cls.fromisoformat(week_start) - timedelta(days=1)
    log_start = log_end - timedelta(days=30)
    print(f"[MLB] Fetching game logs ({log_start} → {log_end})...")

    game_logs = []
    batch_size = 50
    for i in range(0, len(players), batch_size):
        batch = players[i:i + batch_size]
        for p in batch:
            try:
                # Determine stat group based on position
                is_pitcher = p["positions"][0] in ("SP", "RP")
                group = "pitching" if is_pitcher else "hitting"
                data = _get(f"people/{p['id']}/stats", {
                    "stats": "gameLog", "group": group, "season": season,
                })
                for stat_block in data.get("stats", []):
                    for split in stat_block.get("splits", []):
                        game_date = split.get("date", "")
                        if not (log_start.isoformat() <= game_date <= log_end.isoformat()):
                            continue
                        st = split.get("stat", {})
                        opp = split.get("opponent", {})
                        team_info = split.get("team", {})

                        if is_pitcher:
                            stats = {
                                "ip": float(st.get("inningsPitched", 0) or 0),
                                "k_pitching": int(st.get("strikeOuts", 0) or 0),
                                "w": 1 if st.get("wins", 0) else 0,
                                "sv": 1 if st.get("saves", 0) else 0,
                                "er": int(st.get("earnedRuns", 0) or 0),
                                "ha": int(st.get("hits", 0) or 0),
                                "bba": int(st.get("baseOnBalls", 0) or 0),
                                "h": 0, "r": 0, "hr": 0, "rbi": 0, "sb": 0,
                                "bb": 0, "k_hitting": 0, "ab": 0,
                            }
                        else:
                            stats = {
                                "h": int(st.get("hits", 0) or 0),
                                "r": int(st.get("runs", 0) or 0),
                                "hr": int(st.get("homeRuns", 0) or 0),
                                "rbi": int(st.get("rbi", 0) or 0),
                                "sb": int(st.get("stolenBases", 0) or 0),
                                "bb": int(st.get("baseOnBalls", 0) or 0),
                                "k_hitting": int(st.get("strikeOuts", 0) or 0),
                                "ab": int(st.get("atBats", 0) or 0),
                                "ip": 0, "k_pitching": 0, "w": 0, "sv": 0,
                                "er": 0, "ha": 0, "bba": 0,
                            }

                        game_logs.append({
                            "player_id": p["id"],
                            "game_id": split.get("game", {}).get("gamePk", 0),
                            "date": game_date,
                            "team_id": team_info.get("id", p["team_id"]),
                            "opponent_id": opp.get("id", 0),
                            "position": p["positions"][0],
                            "stats": stats,
                        })
            except Exception:
                pass  # Skip players whose logs fail
        time.sleep(0.3)
        if (i + batch_size) % 200 == 0:
            print(f"  ... {i + batch_size}/{len(players)} players processed")

    print(f"[MLB] {len(game_logs)} game log rows")

    # Build a default roster (top players by game log count as a proxy)
    log_counts = defaultdict(int)
    for lg in game_logs:
        log_counts[lg["player_id"]] += 1
    top_players = sorted(log_counts.keys(), key=lambda pid: log_counts[pid], reverse=True)

    # Pick a 12-player default roster from different teams
    roster_ids: list[int] = []
    roster_teams: set[int] = set()
    players_by_id = {p["id"]: p for p in players}
    for pid in top_players:
        p = players_by_id.get(pid)
        if p and p["team_id"] not in roster_teams and len(roster_ids) < 12:
            roster_ids.append(pid)
            roster_teams.add(p["team_id"])

    free_agents = [p["id"] for p in players if p["id"] not in set(roster_ids)]

    roster = {
        "week_start": week_start,
        "week_end": week_end,
        "scoring": None,  # Use sport defaults
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
    (output_dir / "injuries.json").write_text(json.dumps([]))  # No injury feed yet
    (output_dir / "roster.json").write_text(json.dumps(roster, indent=2))

    print(f"[MLB] Fixtures written to {output_dir}")
    print(f"  teams={len(teams)} players={len(players)} logs={len(game_logs)} "
          f"schedule={len(schedule)} roster={len(roster_ids)}")
