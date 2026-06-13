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

from .scoring.engine import rank_waiver_adds
from .scoring.matchups import compute_dvp
from .scoring.projections import project_all
from .scoring.types import GameLog, Injury, Player, ScheduledGame

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
    scoring = fx["roster"]["scoring"]
    window = (fx["roster"]["week_start"], fx["roster"]["week_end"])

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

    projections = project_all(logs_by_player, scoring)
    dvp = compute_dvp(all_logs, scoring)

    roster = [players[r["player_id"]] for r in fx["roster"]["roster"]]
    free_agents = [players[pid] for pid in fx["roster"]["free_agents"]]
    droppable = set(fx["roster"]["droppable"])

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
        "roster": roster_entries,
        "free_agents": free_agents,
        "droppable": [pid for pid in drop_ids if pid in roster_id_set],
    }

    return {
        "week": {"start": league["week_start"], "end": league["week_end"]},
        "recommendations": build_recommendations(fx) if roster_entries else [],
        "unresolved": unresolved,
        "resolved_count": len(roster_entries),
    }


def sample_recommendations() -> dict:
    fx = load_fixtures()
    return {
        "week": {"start": fx["roster"]["week_start"], "end": fx["roster"]["week_end"]},
        "recommendations": build_recommendations(fx),
    }
