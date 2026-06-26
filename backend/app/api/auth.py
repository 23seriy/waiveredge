"""Yahoo OAuth 2.0 authentication endpoints.

Flow:
1. Frontend calls GET /api/auth/yahoo → redirect to Yahoo consent screen.
2. Yahoo redirects back to GET /api/auth/yahoo/callback?code=... .
3. We exchange the code for tokens, upsert a user + league_connection,
   and redirect back to the frontend with the connection_id.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..config import safe_redirect_url, settings
from ..data.yahoo import GAME_KEY, YahooFantasyClient, authorization_url, exchange_code
from ..db import get_db
from ..models import LeagueConnection, User

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Supported sports — active status reflects whether the season is currently running.
# Update these seasonally (or drive from a config/DB later).
SPORTS = [
    {"key": "nba", "name": "NBA Basketball", "icon": "\U0001f3c0", "active": False, "note": "Offseason — returns Oct 2026"},
    {"key": "mlb", "name": "MLB Baseball",  "icon": "\u26be",     "active": True,  "note": "In-season"},
]


@router.get("/sports")
def list_sports() -> list[dict]:
    """Available sports and their active status."""
    return SPORTS


@router.get("/yahoo")
def yahoo_login(sport: str = ""):
    """Redirect the user to Yahoo's OAuth consent page."""
    if not settings.yahoo_client_id:
        raise HTTPException(status_code=503, detail="Yahoo OAuth is not configured.")
    # Pass the sport as OAuth state so the callback knows which game key to use.
    return RedirectResponse(authorization_url(state=sport or GAME_KEY))


@router.get("/yahoo/callback")
def yahoo_callback(code: str = Query(...), state: str = Query(""), db: Session = Depends(get_db)):
    """Handle Yahoo's OAuth callback — exchange code, create connection."""
    try:
        tokens = exchange_code(code)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {exc}") from exc

    # state carries the sport game key from the login redirect.
    game_key = state if state in ("nba", "mlb", "nfl", "nhl", "wnba") else GAME_KEY
    yc = YahooFantasyClient(tokens)
    leagues = yc.user_leagues(game_key=game_key)
    if not leagues:
        return RedirectResponse(safe_redirect_url(f"{settings.frontend_url}/{game_key}/connect?error=no_leagues"))

    # For v1 we auto-pick the first NBA league.
    league = leagues[0]
    team_key = yc.my_team_key(league["league_key"])
    league_settings = yc.league_settings(league["league_key"])
    final_tokens = yc.current_tokens

    # Upsert user (placeholder email until we decode Yahoo's id_token).
    email = f"yahoo-{league['league_key']}@waiveredge.local"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email)
        db.add(user)
        db.flush()

    # Upsert league connection.
    conn = (
        db.query(LeagueConnection)
        .filter(LeagueConnection.user_id == user.id,
                LeagueConnection.league_id == league["league_key"])
        .first()
    )
    if conn:
        conn.oauth_tokens = final_tokens
        conn.team_key = team_key
        conn.scoring_json = {
            "scoring_type": league_settings.get("scoring_type", ""),
            "categories": league_settings.get("categories", []),
        }
    else:
        conn = LeagueConnection(
            user_id=user.id,
            platform="yahoo",
            league_id=league["league_key"],
            team_key=team_key,
            scoring_json={
                "scoring_type": league_settings.get("scoring_type", ""),
                "categories": league_settings.get("categories", []),
            },
            oauth_tokens=final_tokens,
        )
        db.add(conn)
    db.flush()
    connection_id = conn.id
    db.commit()

    return RedirectResponse(safe_redirect_url(f"{settings.frontend_url}/{game_key}/league/{connection_id}"))
