"""Ingestion job — pulls from balldontlie into Postgres (or into JSON fixtures).

Two entry points:
  * `ingest_all(db)`  — upsert teams/players/games/logs/injuries into the DB. This
    is what a nightly scheduled worker calls.
  * `dump_fixtures(days)` — write the JSON fixture shapes from the live API so you
    can refresh sample_data/ with real recent data (needs an ALL-STAR key).

Both are intentionally thin and idempotent. The transform from balldontlie's
nested shapes to our flat rows lives in the `_to_*` helpers so it is easy to test.

NOTE: not exercised against the live API in this scaffold (no key on hand). Treat
the field mappings as the documented shapes; verify on first real run.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Game, Injury, Player, PlayerGameLog, Team
from .balldontlie import BalldontlieClient

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample_data"


def _primary_position(pos: str | None) -> str:
    if not pos:
        return "UTIL"
    # balldontlie returns e.g. "G", "F-C", "PG". Take the first token.
    token = pos.replace("-", " ").split()[0].upper()
    expand = {"G": "PG", "F": "SF"}
    return expand.get(token, token)


def _to_game_log_row(stat: dict) -> dict | None:
    """Flatten a /v1/stats row into a player_game_logs row."""
    player = stat.get("player") or {}
    team = stat.get("team") or {}
    game = stat.get("game") or {}
    if not (player.get("id") and game.get("id") and team.get("id")):
        return None
    home = game.get("home_team_id")
    visitor = game.get("visitor_team_id")
    team_id = team["id"]
    opponent_id = visitor if team_id == home else home
    pos = _primary_position(player.get("position"))
    return {
        "player_id": player["id"],
        "game_id": game["id"],
        "date": game.get("date", "")[:10],
        "team_id": team_id,
        "opponent_id": opponent_id,
        "position": pos,
        "minutes": _safe_min(stat.get("min")),
        "pts": stat.get("pts", 0) or 0,
        "reb": stat.get("reb", 0) or 0,
        "ast": stat.get("ast", 0) or 0,
        "stl": stat.get("stl", 0) or 0,
        "blk": stat.get("blk", 0) or 0,
        "fg3m": stat.get("fg3m", 0) or 0,
        "turnover": stat.get("turnover", 0) or 0,
    }


def _safe_min(value: object) -> int:
    """balldontlie 'min' can be '34' or '34:12' or None."""
    if not value:
        return 0
    s = str(value).split(":")[0]
    return int(s) if s.isdigit() else 0


def _upsert(db: Session, model, rows: list[dict], index_elements: list[str]) -> int:
    if not rows:
        return 0
    stmt = insert(model).values(rows)
    update_cols = {c.name: stmt.excluded[c.name]
                   for c in model.__table__.columns if c.name not in index_elements}
    stmt = stmt.on_conflict_do_update(index_elements=index_elements, set_=update_cols)
    db.execute(stmt)
    db.commit()
    return len(rows)


def ingest_all(db: Session, days: int = 30) -> dict[str, int]:
    """Idempotent pull of recent data into Postgres."""
    end = date.today()
    start = end - timedelta(days=days)
    counts: dict[str, int] = {}
    with BalldontlieClient() as bdl:
        counts["teams"] = _upsert(db, Team, [
            {"id": t["id"], "abbreviation": t["abbreviation"], "full_name": t["full_name"]}
            for t in bdl.teams()
        ], ["id"])

        counts["players"] = _upsert(db, Player, [
            {"id": p["id"], "name": f"{p['first_name']} {p['last_name']}",
             "team_id": (p.get("team") or {}).get("id"),
             "positions": [_primary_position(p.get("position"))],
             "primary_position": _primary_position(p.get("position"))}
            for p in bdl.players() if p.get("team")
        ], ["id"])

        counts["games"] = _upsert(db, Game, [
            {"id": g["id"], "date": g["date"][:10], "season": g.get("season"),
             "home_team_id": g["home_team"]["id"], "visitor_team_id": g["visitor_team"]["id"],
             "status": g.get("status")}
            for g in bdl.games(start.isoformat(), end.isoformat(), seasons=[settings.season])
        ], ["id"])

        log_rows = [r for r in (_to_game_log_row(s)
                    for s in bdl.stats(start.isoformat(), end.isoformat(),
                                       seasons=[settings.season])) if r]
        counts["logs"] = _upsert(db, PlayerGameLog, log_rows, ["player_id", "game_id"])

        counts["injuries"] = _upsert(db, Injury, [
            {"player_id": (i.get("player") or {}).get("id"),
             "status": i.get("status", ""), "note": i.get("description", "")}
            for i in bdl.player_injuries() if (i.get("player") or {}).get("id")
        ], ["player_id"])
    return counts


def dump_fixtures(days: int = 30) -> None:
    """Refresh sample_data/*.json from the live API (needs an ALL-STAR key)."""
    end = date.today()
    start = end - timedelta(days=days)
    with BalldontlieClient() as bdl:
        teams = [{"id": t["id"], "abbreviation": t["abbreviation"], "full_name": t["full_name"]}
                 for t in bdl.teams()]
        players = [{"id": p["id"], "name": f"{p['first_name']} {p['last_name']}",
                    "team_id": (p.get("team") or {}).get("id"),
                    "positions": [_primary_position(p.get("position"))]}
                   for p in bdl.players() if p.get("team")]
        logs = [r for r in (_to_game_log_row(s)
                for s in bdl.stats(start.isoformat(), end.isoformat(),
                                   seasons=[settings.season])) if r]
        # Reshape logs into the fixture's nested `stats` dict.
        fixture_logs = [{
            "player_id": r["player_id"], "game_id": r["game_id"], "date": r["date"],
            "team_id": r["team_id"], "opponent_id": r["opponent_id"], "position": r["position"],
            "stats": {k: r[k] for k in ("pts", "reb", "ast", "stl", "blk", "fg3m", "turnover", "minutes")},
        } for r in logs]

    (SAMPLE_DIR / "teams.json").write_text(json.dumps(teams, indent=2))
    (SAMPLE_DIR / "players.json").write_text(json.dumps(players, indent=2))
    (SAMPLE_DIR / "game_logs.json").write_text(json.dumps(fixture_logs, indent=2))
    print(f"Refreshed fixtures from live API: teams={len(teams)} players={len(players)} logs={len(fixture_logs)}")


if __name__ == "__main__":
    # Convenience: `python -m app.data.ingest` refreshes fixtures from the live API.
    dump_fixtures()
