"""League connection + per-user recommendation endpoints.

Once a user has connected their Yahoo league via OAuth, these endpoints:
- GET /api/leagues/{id}         — connection info + roster
- POST /api/leagues/{id}/sync   — refresh roster from Yahoo
- GET /api/leagues/{id}/recs    — personalized recommendations
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..data.yahoo import YahooFantasyClient
from ..db import get_db
from ..models import LeagueConnection, RosterEntry
from ..recommendations import build_recommendations, load_fixtures, resolve_names

router = APIRouter(prefix="/api/leagues", tags=["leagues"])


def _get_connection(connection_id: int, db: Session) -> LeagueConnection:
    conn = db.query(LeagueConnection).filter(LeagueConnection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="League connection not found.")
    return conn


@router.get("/{connection_id}")
def get_league(connection_id: int, db: Session = Depends(get_db)) -> dict:
    """Return league connection info and the stored roster."""
    conn = _get_connection(connection_id, db)
    roster = db.query(RosterEntry).filter(RosterEntry.connection_id == conn.id).all()
    return {
        "id": conn.id,
        "platform": conn.platform,
        "league_id": conn.league_id,
        "team_key": conn.team_key,
        "scoring": conn.scoring_json,
        "roster": [
            {"player_id": r.player_id, "slot": r.slot, "droppable": r.droppable}
            for r in roster
        ],
    }


@router.post("/{connection_id}/sync")
def sync_roster(connection_id: int, db: Session = Depends(get_db)) -> dict:
    """Refresh the roster from Yahoo and persist it."""
    conn = _get_connection(connection_id, db)
    if conn.platform != "yahoo" or not conn.team_key:
        raise HTTPException(status_code=400, detail="Cannot sync: not a Yahoo connection or missing team_key.")
    if not conn.oauth_tokens:
        raise HTTPException(status_code=400, detail="No OAuth tokens on this connection.")

    yc = YahooFantasyClient(conn.oauth_tokens)
    yahoo_roster = yc.roster(conn.team_key)
    if yc.tokens_refreshed:
        conn.oauth_tokens = yc.current_tokens
        db.commit()

    if not yahoo_roster:
        raise HTTPException(status_code=502, detail="Yahoo returned an empty roster.")

    fx = load_fixtures()
    names = [p["name"] for p in yahoo_roster]
    resolved_ids, unresolved = resolve_names(names, fx["players"])

    db.query(RosterEntry).filter(RosterEntry.connection_id == conn.id).delete()
    yahoo_by_name = {p["name"]: p for p in yahoo_roster}
    players_by_id = {p["id"]: p for p in fx["players"]}
    for pid in resolved_ids:
        p = players_by_id.get(pid, {})
        yahoo_p = yahoo_by_name.get(p.get("name", ""), {})
        slot = yahoo_p.get("slot", p.get("positions", ["UTIL"])[0])
        db.add(RosterEntry(connection_id=conn.id, player_id=pid, slot=slot, droppable=True))
    db.commit()

    return {"synced": len(resolved_ids), "unresolved": unresolved, "roster_size": len(resolved_ids)}


@router.get("/{connection_id}/recs")
def league_recommendations(connection_id: int, db: Session = Depends(get_db)) -> dict:
    """Personalized recommendations for a connected league."""
    conn = _get_connection(connection_id, db)
    roster_entries = db.query(RosterEntry).filter(RosterEntry.connection_id == conn.id).all()
    if not roster_entries:
        raise HTTPException(status_code=400, detail="No roster stored. Call POST /sync first.")

    fx = load_fixtures()
    cfg = fx["roster"]

    roster_ids = {r.player_id for r in roster_entries}
    free_agents = [p["id"] for p in fx["players"] if p["id"] not in roster_ids]
    droppable = [r.player_id for r in roster_entries if r.droppable]

    scoring = conn.scoring_json or {}
    scoring_type = scoring.get("scoring_type", "")
    mode = "categories" if scoring_type in ("head", "roto") else "points"

    fx["roster"] = {
        "week_start": cfg["week_start"],
        "week_end": cfg["week_end"],
        "scoring": cfg.get("scoring"),
        "mode": mode,
        "categories": None,
        "roster": [{"player_id": r.player_id, "slot": r.slot} for r in roster_entries],
        "free_agents": free_agents,
        "droppable": droppable,
    }

    return {
        "connection_id": conn.id,
        "league_id": conn.league_id,
        "week": {"start": cfg["week_start"], "end": cfg["week_end"]},
        "scoring_mode": mode,
        "recommendations": build_recommendations(fx),
    }
