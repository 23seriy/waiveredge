"""ESPN Fantasy league connection endpoints.

ESPN uses cookie-based auth (espn_s2 + SWID) instead of OAuth.
The user provides their league ID + cookies, and we fetch their roster.

Flow:
1. POST /api/espn/connect — create connection with league_id + cookies
2. POST /api/leagues/{id}/sync — same sync endpoint as Yahoo (sport-aware)
3. GET /api/leagues/{id}/recs — same recs endpoint
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..data.espn import ESPNFantasyClient
from ..db import get_db
from ..models import LeagueConnection, RosterEntry, User
from ..recommendations import load_fixtures, resolve_names

router = APIRouter(prefix="/api/espn", tags=["espn"])


class ESPNConnectRequest(BaseModel):
    league_id: int = Field(..., description="ESPN league ID (from the URL)")
    season: int = Field(default=2026, description="Season year")
    sport: str = Field(default="mlb", description="Sport key (nba, mlb)")
    team_id: int | None = Field(default=None, description="Your team ID in the league (pick from /api/espn/teams)")
    espn_s2: str = Field(default="", description="espn_s2 cookie (for private leagues)")
    swid: str = Field(default="", description="SWID cookie (for private leagues)")


@router.get("/teams")
def espn_teams(league_id: int, season: int = 2026, sport: str = "mlb") -> list[dict]:
    """List all teams in an ESPN league (no auth needed for public leagues)."""
    client = ESPNFantasyClient(sport=sport)
    try:
        return client.teams(league_id, season)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            sport_name = sport.upper()
            raise HTTPException(
                status_code=404,
                detail=f"ESPN league {league_id} not found for {sport_name} ({season}). "
                       f"Make sure this is a {sport_name} league ID, not from another sport.",
            ) from exc
        raise HTTPException(status_code=400, detail=f"Could not fetch ESPN league: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not fetch ESPN league: {exc}") from exc


@router.post("/connect")
def espn_connect(req: ESPNConnectRequest, db: Session = Depends(get_db)) -> dict:
    """Connect an ESPN Fantasy league."""
    client = ESPNFantasyClient(sport=req.sport, espn_s2=req.espn_s2, swid=req.swid)

    # Verify the league exists by fetching settings.
    try:
        settings = client.settings(req.league_id, req.season)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            sport_name = req.sport.upper()
            raise HTTPException(
                status_code=404,
                detail=f"ESPN league {req.league_id} not found for {sport_name} ({req.season}). "
                       f"Make sure this is a {sport_name} league ID, not from another sport.",
            ) from exc
        raise HTTPException(status_code=400, detail=f"Could not fetch ESPN league: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not fetch ESPN league: {exc}") from exc

    # Find the user's team: explicit team_id > cookie-based detection.
    team_id = req.team_id
    if team_id is None:
        team_id = client.my_team_id(req.league_id, req.season)

    # Fetch roster if we found the team.
    roster_data = []
    if team_id is not None:
        roster_data = client.roster(req.league_id, req.season, team_id)

    # Fetch free agents.
    fas = client.free_agents(req.league_id, req.season, count=200)

    # Resolve names against our fixtures.
    sport = req.sport
    fx = load_fixtures(sport)
    roster_names = [p["name"] for p in roster_data]
    resolved_ids, unresolved = resolve_names(roster_names, fx["players"])
    fa_names = [p["name"] for p in fas]
    fa_ids, _ = resolve_names(fa_names, fx["players"])

    # Upsert user.
    email = f"espn-{req.league_id}@waiveredge.local"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email)
        db.add(user)
        db.flush()

    # Upsert league connection.
    espn_league_key = f"espn-{req.sport}-{req.league_id}"
    conn = (
        db.query(LeagueConnection)
        .filter(LeagueConnection.user_id == user.id,
                LeagueConnection.league_id == espn_league_key)
        .first()
    )
    scoring_data = {
        "scoring_type": settings.get("scoring_type", ""),
        "weights": settings.get("weights", {}),
        "free_agent_ids": fa_ids,
    }
    oauth_tokens = {
        "espn_s2": req.espn_s2,
        "swid": req.swid,
        "espn_league_id": req.league_id,
        "espn_team_id": team_id,
        "season": req.season,
    }

    if conn:
        conn.scoring_json = scoring_data
        conn.oauth_tokens = oauth_tokens
        conn.team_key = str(team_id) if team_id else None
    else:
        conn = LeagueConnection(
            user_id=user.id,
            platform="espn",
            league_id=espn_league_key,
            team_key=str(team_id) if team_id else None,
            scoring_json=scoring_data,
            oauth_tokens=oauth_tokens,
        )
        db.add(conn)
    db.flush()

    # Store roster entries.
    db.query(RosterEntry).filter(RosterEntry.connection_id == conn.id).delete()
    players_by_id = {p["id"]: p for p in fx["players"]}
    for pid in resolved_ids:
        p = players_by_id.get(pid, {})
        slot = p.get("positions", ["UTIL"])[0] or "UTIL"
        db.add(RosterEntry(connection_id=conn.id, player_id=pid, slot=slot, droppable=True))
    db.commit()

    return {
        "connection_id": conn.id,
        "league_id": espn_league_key,
        "team_id": team_id,
        "synced": len(resolved_ids),
        "unresolved": unresolved,
        "free_agents_found": len(fa_ids),
    }
