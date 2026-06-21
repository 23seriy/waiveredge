"""Recommendation service.

Builds the ranked waiver action list from a set of fixtures (dicts in the
balldontlie shapes). The API uses this against sample data today; once ingestion
is wired up, the same function consumes rows loaded from Postgres.
"""
from __future__ import annotations

import json
import threading
import time as _time
import unicodedata
from dataclasses import asdict
from pathlib import Path

from .scoring.categories import rank_category_adds
from .scoring.engine import games_in_window, project_value, rank_waiver_adds
from .scoring.matchups import compute_dvp
from .scoring.projections import project_all
from .scoring.scoring_systems import league_from_sport_config
from .sports import get_sport
from .scoring.types import GameLog, Injury, Player, Projection, ScheduledGame

DATA_DIR = Path(__file__).resolve().parents[1]

SPORT_DIRS: dict[str, Path] = {
    "nba": DATA_DIR / "sample_data_nba",
    "mlb": DATA_DIR / "sample_data_mlb",
}

FIXTURE_FILES = ("teams", "players", "game_logs", "schedule", "injuries", "roster")

# Max age before fixtures are considered stale and need rebuild (24 hours).
CACHE_MAX_AGE_SECONDS = 24 * 60 * 60

# In-memory build state tracking (per sport).
_build_locks: dict[str, threading.Lock] = {}
_build_status: dict[str, dict] = {}


def _get_lock(sport: str) -> threading.Lock:
    if sport not in _build_locks:
        _build_locks[sport] = threading.Lock()
    return _build_locks[sport]


def fixture_build_status(sport: str) -> dict:
    """Return the current build status for a sport's fixtures."""
    data_dir = SPORT_DIRS.get(sport, SPORT_DIRS["nba"])
    roster_file = data_dir / "roster.json"
    has_data = roster_file.exists()
    age_seconds = (_time.time() - roster_file.stat().st_mtime) if has_data else None
    is_stale = age_seconds is not None and age_seconds > CACHE_MAX_AGE_SECONDS
    status = _build_status.get(sport, {})
    return {
        "sport": sport,
        "has_data": has_data,
        "is_stale": is_stale,
        "age_seconds": round(age_seconds) if age_seconds is not None else None,
        "building": status.get("building", False),
        "progress": status.get("progress", ""),
    }


def _is_fresh(sport: str) -> bool:
    """Check if fixtures exist and are younger than CACHE_MAX_AGE_SECONDS."""
    data_dir = SPORT_DIRS.get(sport, SPORT_DIRS["nba"])
    roster_file = data_dir / "roster.json"
    if not roster_file.exists():
        return False
    age = _time.time() - roster_file.stat().st_mtime
    return age < CACHE_MAX_AGE_SECONDS


def _build_fixtures_background(sport: str) -> None:
    """Build fixtures in a background thread."""
    lock = _get_lock(sport)
    if not lock.acquire(blocking=False):
        return  # Another build is already running
    try:
        _build_status[sport] = {"building": True, "progress": "Starting..."}
        data_dir = SPORT_DIRS.get(sport, SPORT_DIRS["nba"])
        if sport == "mlb":
            from .data.mlb_fixtures import build_real_fixtures
            build_real_fixtures(data_dir)
        else:
            from .data.nba_fixtures import build_real_fixtures
            build_real_fixtures(data_dir)
        _build_status[sport] = {"building": False, "progress": "Complete"}
    except Exception as e:
        _build_status[sport] = {"building": False, "progress": f"Error: {e}"}
    finally:
        lock.release()


def ensure_fixtures(sport: str) -> bool:
    """Ensure fixtures exist. If missing/stale, start a background build.

    Returns True if fixtures are ready to serve, False if building.
    """
    if _is_fresh(sport):
        return True
    # Check if already building.
    status = _build_status.get(sport, {})
    if status.get("building"):
        return False
    # Start background build.
    thread = threading.Thread(target=_build_fixtures_background, args=(sport,), daemon=True)
    thread.start()
    # If fixtures exist (just stale), serve them while rebuilding.
    data_dir = SPORT_DIRS.get(sport, SPORT_DIRS["nba"])
    return (data_dir / "roster.json").exists()


def load_fixtures(sport: str = "nba") -> dict:
    """Load real fixtures for a sport.

    If fixtures are missing, blocks until built (first use only).
    If stale, serves cached data and rebuilds in background.
    """
    data_dir = SPORT_DIRS.get(sport, SPORT_DIRS["nba"])
    roster_file = data_dir / "roster.json"

    if roster_file.exists():
        # Serve cached data. Trigger background rebuild if stale.
        if not _is_fresh(sport):
            status = _build_status.get(sport, {})
            if not status.get("building"):
                thread = threading.Thread(target=_build_fixtures_background, args=(sport,), daemon=True)
                thread.start()
        return {name: json.loads((data_dir / f"{name}.json").read_text())
                for name in FIXTURE_FILES}

    # No fixtures at all — must build (blocking for first use).
    _build_fixtures_background(sport)
    if not roster_file.exists():
        raise RuntimeError(f"Failed to build {sport} fixtures")
    return {name: json.loads((data_dir / f"{name}.json").read_text())
            for name in FIXTURE_FILES}


def build_recommendations(fx: dict, sport: str = "nba") -> list[dict]:
    cfg = fx["roster"]
    sport_cfg = get_sport(sport)
    league = league_from_sport_config({"mode": cfg.get("mode", "points"),
                                       "weights": cfg.get("scoring"),
                                       "categories": cfg.get("categories")}, sport_cfg)
    window = (cfg["week_start"], cfg["week_end"])
    # Points weights drive fppg + the DvP matchup buckets; per-game projections
    # (used by category mode) are computed regardless of the weights.
    default_weights = dict(sport_cfg.default_points_scoring)
    weights = league.weights if league.mode == "points" else default_weights

    players = {p["id"]: Player(p["id"], p["name"], p["team_id"], p["positions"])
               for p in fx["players"]}
    all_logs = [GameLog(**lg) for lg in fx["game_logs"]]
    logs_by_player: dict[int, list[GameLog]] = {}
    for lg in all_logs:
        logs_by_player.setdefault(lg.player_id, []).append(lg)
    schedule = [ScheduledGame(**g) for g in fx["schedule"]]
    injuries = {i["player_id"]: Injury(**i) for i in fx["injuries"]}

    players_by_team: dict[int, list[Player]] = {}
    for p in players.values():
        players_by_team.setdefault(p.team_id, []).append(p)

    projections = project_all(logs_by_player, weights)
    dvp = compute_dvp(all_logs, weights)

    roster = [players[r["player_id"]] for r in cfg["roster"]]
    free_agents = [players[pid] for pid in cfg["free_agents"]]
    droppable = set(cfg["droppable"])

    if league.mode == "categories":
        recs = rank_category_adds(roster, free_agents, droppable, projections, schedule,
                                  window, dvp, injuries, players_by_team, league.categories)
    else:
        recs = rank_waiver_adds(roster, free_agents, droppable, projections, schedule,
                                window, dvp, injuries, players_by_team)
    return [asdict(r) for r in recs]


def _normalize_name(name: str) -> str:
    """Casefold + fold accents + strip punctuation/whitespace for tolerant matching.

    Diacritics are folded (Jokić -> jokic, Dončić -> doncic) so a user typing plain
    ASCII matches the accented names real NBA data uses.
    """
    decomposed = unicodedata.normalize("NFKD", name)
    out = []
    for ch in decomposed.casefold():
        if unicodedata.combining(ch):
            continue  # drop accent marks left by NFKD decomposition
        if ch.isalnum():
            out.append(ch)
        elif ch.isspace():
            out.append(" ")
        # punctuation (., ', -) is dropped
    return " ".join("".join(out).split())


def resolve_names(names: list[str], players: list[dict]) -> tuple[list[int], list[str]]:
    """Map user-typed names to player ids. Returns (resolved_ids, unresolved_names).

    Tolerant of case, surrounding whitespace, and punctuation differences
    ("D'Angelo Russell" vs "dangelo russell"). Duplicates in input are deduped
    in the output ids while preserving first-seen order.
    """
    index: dict[str, int] = {_normalize_name(p["name"]): p["id"] for p in players}
    resolved: list[int] = []
    unresolved: list[str] = []
    seen: set[int] = set()
    for raw in names:
        key = _normalize_name(raw)
        if not key:
            continue
        pid = index.get(key)
        if pid is None:
            unresolved.append(raw.strip())
        elif pid not in seen:
            resolved.append(pid)
            seen.add(pid)
    return resolved, unresolved


def manual_recommendations(
    roster_names: list[str],
    droppable_names: list[str] | None = None,
    fixtures: dict | None = None,
    scoring_mode: str = "points",
    categories: list[str] | None = None,
    sport: str = "nba",
) -> dict:
    """Run the engine against a user-typed roster, using real data for everything else.

    Free agents = every known player not on the roster. Unrecognized names are
    reported back so the frontend can flag them. ``fixtures`` may be injected (tests);
    it defaults to the real dataset.
    """
    fx = fixtures if fixtures is not None else load_fixtures(sport)
    league = fx["roster"]
    roster_ids, unresolved = resolve_names(roster_names, fx["players"])
    drop_ids, drop_unresolved = resolve_names(droppable_names or [], fx["players"])
    unresolved.extend(drop_unresolved)

    roster_id_set = set(roster_ids)
    free_agents = [p["id"] for p in fx["players"] if p["id"] not in roster_id_set]

    players_by_id = {p["id"]: p for p in fx["players"]}
    roster_entries = [
        {"player_id": pid, "slot": players_by_id[pid]["positions"][0]}
        for pid in roster_ids
    ]

    fx["roster"] = {
        "week_start": league["week_start"],
        "week_end": league["week_end"],
        "scoring": league["scoring"],
        "mode": scoring_mode,
        "categories": categories,
        "roster": roster_entries,
        "free_agents": free_agents,
        "droppable": [pid for pid in drop_ids if pid in roster_id_set],
    }

    return {
        "week": {"start": league["week_start"], "end": league["week_end"]},
        "scoring_mode": scoring_mode,
        "recommendations": build_recommendations(fx, sport) if roster_entries else [],
        "unresolved": unresolved,
        "resolved_count": len(roster_entries),
    }


def sample_recommendations(scoring_mode: str = "points", sport: str = "nba") -> dict:
    fx = load_fixtures(sport)
    if scoring_mode == "categories":
        fx["roster"]["mode"] = "categories"
    return {
        "week": {"start": fx["roster"]["week_start"], "end": fx["roster"]["week_end"]},
        "scoring_mode": scoring_mode,
        "recommendations": build_recommendations(fx, sport),
    }


def top_streamers(top_n: int = 30, sport: str = "nba") -> dict:
    """Top streaming pickups this week ranked by absolute projected value.

    No roster required — this is the public, free, SEO-friendly page content.
    Returns the schedule density grid (games per team) and the ranked player list.
    """
    fx = load_fixtures(sport)
    cfg = fx["roster"]
    window = (cfg["week_start"], cfg["week_end"])
    sport_cfg = get_sport(sport)
    weights = dict(sport_cfg.default_points_scoring)

    players = {p["id"]: Player(p["id"], p["name"], p["team_id"], p["positions"])
               for p in fx["players"]}
    all_logs = [GameLog(**lg) for lg in fx["game_logs"]]
    logs_by_player: dict[int, list[GameLog]] = {}
    for lg in all_logs:
        logs_by_player.setdefault(lg.player_id, []).append(lg)
    schedule = [ScheduledGame(**g) for g in fx["schedule"]]
    injuries = {i["player_id"]: Injury(**i) for i in fx["injuries"]}

    players_by_team: dict[int, list[Player]] = {}
    for p in players.values():
        players_by_team.setdefault(p.team_id, []).append(p)

    projections = project_all(logs_by_player, weights)
    dvp = compute_dvp(all_logs, weights)

    # Build team lookup and schedule density grid.
    teams_by_id = {t["id"]: t for t in fx["teams"]}
    team_games: dict[int, list[dict]] = {}
    for tid in teams_by_id:
        games = games_in_window(tid, schedule, window[0], window[1])
        team_games[tid] = [
            {"date": g.date, "opponent": teams_by_id.get(g.opponent_of(tid), {}).get("abbreviation", "?")}
            for g in games
        ]
    schedule_grid = [
        {"team_id": tid, "abbreviation": teams_by_id[tid]["abbreviation"],
         "team_name": teams_by_id[tid].get("full_name", teams_by_id[tid]["abbreviation"]),
         "games": len(gs), "matchups": gs}
        for tid, gs in sorted(team_games.items(), key=lambda kv: len(kv[1]), reverse=True)
    ]

    # Rank all players by absolute projected value.
    ranked: list[dict] = []
    for p in players.values():
        proj = projections.get(p.id, Projection(p.id, 0.0, 0, {}))
        if proj.games_sampled < 3 or proj.fppg < 10:
            continue
        vr = project_value(p, proj, schedule, window, dvp, injuries, players_by_team)
        if vr.n_games == 0:
            continue
        ranked.append({
            "player_id": p.id,
            "name": p.name,
            "position": "/".join(p.positions),
            "team": teams_by_id.get(p.team_id, {}).get("abbreviation", "?"),
            "team_id": p.team_id,
            "team_name": teams_by_id.get(p.team_id, {}).get("full_name", "?"),
            "n_games": vr.n_games,
            "soft_matchups": vr.soft_matchups,
            "fppg": proj.fppg,
            "projected_total": vr.value,
            "matchups": [
                {"opponent": teams_by_id.get(c.opponent_id, {}).get("abbreviation", "?"),
                 "mult": round(c.matchup_mult, 2)}
                for c in vr.contributions
            ],
        })
    ranked.sort(key=lambda r: r["projected_total"], reverse=True)

    return {
        "week": {"start": cfg["week_start"], "end": cfg["week_end"]},
        "schedule_grid": schedule_grid,
        "streamers": ranked[:top_n],
    }
