"""Build real NBA fixtures from stats.nba.com (the source balldontlie wraps).

This is the project's data layer: real players, real box scores, a real schedule
week, materialized into the JSON shapes the scoring engine reads. `build_real_fixtures`
is called both by the CLI (`scripts/dump_real_fixtures.py`) and lazily by the API the
first time it needs data, so the app always serves real NBA data.

nba_api is imported lazily inside the function so merely importing this module (or the
API serving already-materialized fixtures) does not require nba_api to be installed.

Free, works from a residential IP; datacenter IPs are blocked by stats.nba.com, which
is why a deployed product pays for a stabilized feed (balldontlie ALL-STAR) instead.
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import date as date_cls
from datetime import timedelta
from pathlib import Path

from ..scoring.projections import project_all
from ..scoring.scoring_systems import DEFAULT_POINTS_SCORING
from ..scoring.types import GameLog

DEFAULT_SEASONS = ["2025-26", "2024-25", "2023-24"]

# stats.nba.com positions are coarse (G/F/C/combo). Map to the engine's 5-position
# vocabulary so DvP buckets and roster-slot eligibility work.
POS_MAP = {
    "PG": ["PG"], "SG": ["SG"], "SF": ["SF"], "PF": ["PF"], "C": ["C"],
    "G": ["PG", "SG"], "F": ["SF", "PF"],
    "G-F": ["SG", "SF"], "F-G": ["SG", "SF"],
    "F-C": ["PF", "C"], "C-F": ["PF", "C"], "C-G": ["C", "PG"],
}


def _norm_positions(pos: object) -> list[str]:
    if not pos:
        return ["UTIL"]
    return POS_MAP.get(str(pos).strip().upper(), ["UTIL"])


def _parse_min(value: object) -> int:
    if value in (None, ""):
        return 0
    s = str(value).split(":")[0].strip()
    try:
        return int(float(s))
    except ValueError:
        return 0


def _split_matchup(matchup: str) -> tuple[str, str | None, str | None]:
    """(opponent_abbr, home_abbr, visitor_abbr) from 'OKC vs. LAL' / 'OKC @ LAL'."""
    if " vs. " in matchup:
        left, right = matchup.split(" vs. ")
        return right.strip(), left.strip(), right.strip()          # team is home
    if " @ " in matchup:
        left, right = matchup.split(" @ ")
        return right.strip(), right.strip(), left.strip()          # team is visitor
    return "", None, None


def _fetch(call, label, retries=3):
    last = None
    for attempt in range(retries):
        try:
            return call()
        except Exception as e:  # noqa: BLE001 — network flakiness
            last = e
            print(f"   ({label} attempt {attempt + 1} failed: {type(e).__name__}; retrying...)")
            time.sleep(3 * (attempt + 1))
    raise last  # type: ignore[misc]


def _fmt_nba(d: date_cls) -> str:
    """date -> MM/DD/YYYY (the format nba_api expects)."""
    return d.strftime("%m/%d/%Y")


def _pick_representative_week(team_rows: list[dict]) -> tuple[date_cls, date_cls]:
    """Choose a dense, representative MID-SEASON week from a season's team game log.

    Slides a 7-day window over the middle third of the season (which excludes the
    October ramp-up, the All-Star break, and the end-of-season resting/tanking) and
    picks the window where the most teams play — i.e. a normal, full fantasy week.
    Deterministic: same season data always yields the same week.
    """
    teams_by_date: dict[str, set] = defaultdict(set)
    for r in team_rows:
        d = str(r.get("GAME_DATE", ""))[:10]
        t = r.get("TEAM_ABBREVIATION")
        if d and t:
            teams_by_date[d].add(t)
    dates = sorted(teams_by_date)
    if not dates:
        raise RuntimeError("No game dates in the season schedule.")

    first, last = date_cls.fromisoformat(dates[0]), date_cls.fromisoformat(dates[-1])
    span = (last - first).days
    lo = first + timedelta(days=span // 3)
    hi = last - timedelta(days=span // 3)

    best = None  # (distinct_teams, team_games, -ordinal), start, end
    cur = lo
    while cur <= hi - timedelta(days=6):
        teams: set = set()
        team_games = 0
        for i in range(7):
            ds = (cur + timedelta(days=i)).isoformat()
            if ds in teams_by_date:
                teams |= teams_by_date[ds]
                team_games += len(teams_by_date[ds])
        key = (len(teams), team_games, -cur.toordinal())
        if best is None or key > best[0]:
            best = (key, cur, cur + timedelta(days=6))
        cur += timedelta(days=1)
    return best[1], best[2]


def build_real_fixtures(out_dir: Path, seasons: list[str] | None = None) -> dict:
    """Pull real NBA data and write the six fixture JSON files into ``out_dir``.

    Returns a summary dict (season, week, counts, sample_roster names).
    """
    # Lazy import: only needed when we actually fetch.
    from nba_api.stats.endpoints import leaguegamelog, playerindex
    from nba_api.stats.static import teams as static_teams

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    seasons = seasons or DEFAULT_SEASONS

    nba_teams = static_teams.get_teams()
    teams_json = [{"id": t["id"], "abbreviation": t["abbreviation"], "full_name": t["full_name"]}
                  for t in nba_teams]
    abbr_to_id = {t["abbreviation"]: t["id"] for t in nba_teams}

    # Pick the latest season that has a schedule, then auto-select a representative
    # mid-season week from it (no hardcoded dates — works for any season).
    season = None
    week_start = week_end = stats_end = None
    rows = None
    for s in seasons:
        print(f"[PULL] season {s}: fetching full schedule from stats.nba.com...")
        try:
            team_df = _fetch(lambda: leaguegamelog.LeagueGameLog(
                season=s, season_type_all_star="Regular Season",
                player_or_team_abbreviation="T", timeout=60).get_data_frames()[0],
                f"schedule {s}")
        except Exception as e:  # noqa: BLE001
            print(f"[PULL] season {s} schedule failed: {e}")
            continue
        if len(team_df) == 0:
            print(f"[PULL] season {s} empty; trying older...")
            continue

        tw_start, tw_end = _pick_representative_week(team_df.to_dict("records"))
        proj_start = tw_start - timedelta(days=14)
        week_start, week_end = tw_start.isoformat(), tw_end.isoformat()
        stats_end = (tw_start - timedelta(days=1)).isoformat()
        print(f"[PULL] season {s}: representative week {week_start}..{week_end}; "
              f"projecting from {proj_start.isoformat()}..{stats_end}")
        player_df = _fetch(lambda: leaguegamelog.LeagueGameLog(
            season=s, season_type_all_star="Regular Season",
            player_or_team_abbreviation="P",
            date_from_nullable=_fmt_nba(proj_start), date_to_nullable=_fmt_nba(tw_end),
            timeout=60).get_data_frames()[0], f"gamelog {s}")
        if len(player_df) > 0:
            season, rows = s, player_df.to_dict("records")
            break

    if not season or not rows:
        raise RuntimeError("Could not pull box scores from stats.nba.com. Re-run, or pass a season.")

    print(f"[PULL] season {season}: {len(rows)} player game-log rows.")

    pos_map: dict[int, list[str]] = {}
    name_idx: dict[int, str] = {}
    team_idx: dict[int, int] = {}
    try:
        pdf = _fetch(lambda: playerindex.PlayerIndex(
            season=season, league_id="00", timeout=60).get_data_frames()[0], "playerindex")
        for r in pdf.to_dict("records"):
            pid = r.get("PERSON_ID")
            if not pid:
                continue
            pos_map[pid] = _norm_positions(r.get("POSITION"))
            name_idx[pid] = f"{r.get('PLAYER_FIRST_NAME', '')} {r.get('PLAYER_LAST_NAME', '')}".strip()
            team_idx[pid] = r.get("TEAM_ID") or 0
        print(f"[PULL] PlayerIndex: {len(pos_map)} players with positions.")
    except Exception as e:  # noqa: BLE001
        print(f"[PULL] PlayerIndex unavailable ({e}); positions default to UTIL.")

    logs_json: list[dict] = []
    logs_by_player: dict[int, list[GameLog]] = {}
    latest_team: dict[int, tuple[str, int]] = {}
    schedule_map: dict[str, dict] = {}

    for r in rows:
        date = str(r.get("GAME_DATE", ""))[:10]
        team_id = r.get("TEAM_ID")
        matchup = str(r.get("MATCHUP", ""))
        pid = r.get("PLAYER_ID")
        gid = str(r.get("GAME_ID", ""))
        if not (team_id and pid and gid and matchup):
            continue
        opp_abbr, home_abbr, vis_abbr = _split_matchup(matchup)
        opp_id = abbr_to_id.get(opp_abbr)
        if opp_id is None:
            continue

        if week_start <= date <= week_end and gid not in schedule_map:
            home_id, vis_id = abbr_to_id.get(home_abbr or ""), abbr_to_id.get(vis_abbr or "")
            if home_id and vis_id:
                schedule_map[gid] = {"id": gid, "date": date,
                                     "home_team_id": home_id, "visitor_team_id": vis_id}

        if date <= stats_end and _parse_min(r.get("MIN")) > 0:
            primary = pos_map.get(pid, ["UTIL"])[0]
            stats = {"pts": r.get("PTS") or 0, "reb": r.get("REB") or 0, "ast": r.get("AST") or 0,
                     "stl": r.get("STL") or 0, "blk": r.get("BLK") or 0, "fg3m": r.get("FG3M") or 0,
                     "turnover": r.get("TOV") or 0,
                     # Shooting volume for FG%/FT% categories (9-cat mode).
                     "fgm": r.get("FGM") or 0, "fga": r.get("FGA") or 0,
                     "ftm": r.get("FTM") or 0, "fta": r.get("FTA") or 0}
            logs_json.append({"player_id": pid, "game_id": gid, "date": date, "team_id": team_id,
                              "opponent_id": opp_id, "position": primary, "stats": stats})
            logs_by_player.setdefault(pid, []).append(
                GameLog(pid, gid, date, team_id, opp_id, primary, stats))
            if pid not in latest_team or date > latest_team[pid][0]:
                latest_team[pid] = (date, team_id)
            if pid not in name_idx:
                name_idx[pid] = str(r.get("PLAYER_NAME", "")).strip()

    schedule_json = list(schedule_map.values())

    all_pids = set(pos_map) | set(logs_by_player)
    players_json = []
    for pid in sorted(all_pids):
        team_id = latest_team[pid][1] if pid in latest_team else team_idx.get(pid, 0)
        players_json.append({"id": pid, "name": name_idx.get(pid, f"Player {pid}"),
                             "team_id": team_id, "positions": pos_map.get(pid, ["UTIL"])})

    # A real, plausible mid-tier default roster + bounded waiver pool, so the /sample
    # endpoint returns a meaningful real list with no user input.
    projections = project_all(logs_by_player, DEFAULT_POINTS_SCORING)
    ranked = sorted((pid for pid, pr in projections.items() if pr.games_sampled >= 3),
                    key=lambda pid: projections[pid].fppg, reverse=True)
    if len(ranked) >= 60:
        roster_ids = ranked[45:55]
    else:
        mid = max(0, len(ranked) // 2 - 5)
        roster_ids = ranked[mid:mid + 10]
    roster_set = set(roster_ids)
    pos_by_id = {p["id"]: p["positions"] for p in players_json}
    name_by_id = {p["id"]: p["name"] for p in players_json}
    free_agents = [pid for pid in ranked if pid not in roster_set][:150]

    roster_json = {
        "week_start": week_start, "week_end": week_end,
        "scoring": dict(DEFAULT_POINTS_SCORING),
        "roster": [{"player_id": pid, "slot": pos_by_id.get(pid, ["UTIL"])[0]} for pid in roster_ids],
        "free_agents": free_agents, "droppable": [],
    }

    (out_dir / "teams.json").write_text(json.dumps(teams_json, indent=2))
    (out_dir / "players.json").write_text(json.dumps(players_json, indent=2))
    (out_dir / "game_logs.json").write_text(json.dumps(logs_json, indent=2))
    (out_dir / "schedule.json").write_text(json.dumps(schedule_json, indent=2))
    (out_dir / "injuries.json").write_text(json.dumps([], indent=2))
    (out_dir / "roster.json").write_text(json.dumps(roster_json, indent=2))

    return {
        "season": season, "week_start": week_start, "week_end": week_end,
        "teams": len(teams_json), "players": len(players_json),
        "logs": len(logs_json), "schedule_games": len(schedule_json),
        "sample_roster": [name_by_id.get(pid, str(pid)) for pid in roster_ids[:5]],
    }
