"""Recommendation service.

Builds the ranked waiver action list from a set of fixtures (dicts in the
balldontlie shapes). The API uses this against sample data today; once ingestion
is wired up, the same function consumes rows loaded from Postgres.
"""
from __future__ import annotations

import json
import unicodedata
from dataclasses import asdict
from pathlib import Path

from .scoring.categories import rank_category_adds
from .scoring.engine import games_in_window, project_value, rank_waiver_adds
from .scoring.matchups import compute_dvp
from .scoring.projections import project_all
from .scoring.scoring_systems import DEFAULT_POINTS_SCORING, league_from_config
from .scoring.types import GameLog, Injury, Player, Projection, ScheduledGame

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample_data"


FIXTURE_FILES = ("teams", "players", "game_logs", "schedule", "injuries", "roster")


def load_fixtures() -> dict:
    """Load the real NBA fixtures, materializing them from stats.nba.com if absent.

    The app always serves real data. On first use (or after the files are cleared)
    this fetches a fresh dataset via app.data.nba_fixtures; subsequent calls read the
    cached JSON. Refresh anytime with `python scripts/dump_real_fixtures.py`.
    """
    if not (SAMPLE_DIR / "roster.json").exists():
        from .data.nba_fixtures import build_real_fixtures

        build_real_fixtures(SAMPLE_DIR)
    return {name: json.loads((SAMPLE_DIR / f"{name}.json").read_text())
            for name in FIXTURE_FILES}


def build_recommendations(fx: dict) -> list[dict]:
    cfg = fx["roster"]
    league = league_from_config({"mode": cfg.get("mode", "points"),
                                 "weights": cfg.get("scoring"),
                                 "categories": cfg.get("categories")})
    window = (cfg["week_start"], cfg["week_end"])
    # Points weights drive fppg + the DvP matchup buckets; per-game projections
    # (used by category mode) are computed regardless of the weights.
    weights = league.weights if league.mode == "points" else DEFAULT_POINTS_SCORING

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
) -> dict:
    """Run the engine against a user-typed roster, using real NBA data for everything else.

    Free agents = every known player not on the roster. Unrecognized names are
    reported back so the frontend can flag them. ``fixtures`` may be injected (tests);
    it defaults to the real dataset.
    """
    fx = fixtures if fixtures is not None else load_fixtures()
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
        "recommendations": build_recommendations(fx) if roster_entries else [],
        "unresolved": unresolved,
        "resolved_count": len(roster_entries),
    }


def sample_recommendations(scoring_mode: str = "points") -> dict:
    fx = load_fixtures()
    if scoring_mode == "categories":
        fx["roster"]["mode"] = "categories"
    return {
        "week": {"start": fx["roster"]["week_start"], "end": fx["roster"]["week_end"]},
        "scoring_mode": scoring_mode,
        "recommendations": build_recommendations(fx),
    }


def top_streamers(top_n: int = 30) -> dict:
    """Top streaming pickups this week ranked by absolute projected value.

    No roster required — this is the public, free, SEO-friendly page content.
    Returns the schedule density grid (games per team) and the ranked player list.
    """
    fx = load_fixtures()
    cfg = fx["roster"]
    window = (cfg["week_start"], cfg["week_end"])

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

    projections = project_all(logs_by_player)
    dvp = compute_dvp(all_logs)

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
