"""WaiverEdge API.

`/api/recommendations/sample` runs the real scoring engine over bundled fixtures,
so the API returns meaningful output with no database and no API key — handy for
frontend development. The DB-backed, per-user endpoint arrives once Yahoo OAuth
import + ingestion are wired up (see app/data/ingest.py).
"""
from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .api.auth import router as auth_router
from .api.billing import router as billing_router
from .api.leagues import router as leagues_router
from .config import settings
from .recommendations import manual_recommendations, sample_recommendations, top_streamers
from .scoring.scoring_systems import CATEGORY_META, NINE_CAT
from .sports import SPORTS, get_sport


class ManualRosterRequest(BaseModel):
    roster: list[str] = Field(..., min_length=1, max_length=30,
                              description="Player names on the user's roster.")
    droppable: list[str] = Field(default_factory=list, max_length=30,
                                 description="Optional subset of roster the user is willing to drop. "
                                             "Empty = the engine picks the weakest position match.")
    scoring_mode: Literal["points", "categories"] = Field(
        default="points",
        description="'points' for weighted-sum scoring, 'categories' for 9-cat z-score ranking.")
    categories: list[str] = Field(
        default_factory=lambda: list(NINE_CAT),
        description="Active categories for category mode (ignored in points mode). "
                    "Defaults to the standard 9-cat set.")
    sport: str = Field(default="nba", description="Sport key (nba, mlb).")

app = FastAPI(title="WaiverEdge API", version="0.1.0")
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(leagues_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/sports")
def list_sports() -> list[dict]:
    """Available sports with their configuration and status."""
    return [
        {"key": s.key, "name": s.name, "icon": s.icon, "active": s.active,
         "has_data": s.has_data, "positions": s.positions, "note": s.note}
        for s in SPORTS.values()
    ]


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "waiveredge", "has_api_key": bool(settings.balldontlie_api_key)}


@app.get("/api/recommendations/sample")
def recommendations_sample(mode: Literal["points", "categories"] = "points", sport: str = "nba") -> dict:
    """Ranked waiver adds for the sample roster (runs the live scoring engine)."""
    sc = get_sport(sport)
    if not sc.has_data:
        raise HTTPException(status_code=501, detail=f"{sc.name} data pipeline not yet available.")
    return sample_recommendations(scoring_mode=mode)


@app.post("/api/recommendations/manual")
def recommendations_manual(req: ManualRosterRequest) -> dict:
    """Ranked waiver adds for a user-typed roster (bridge to per-user before OAuth)."""
    sc = get_sport(req.sport)
    if not sc.has_data:
        raise HTTPException(status_code=501, detail=f"{sc.name} data pipeline not yet available.")
    cat_meta = sc.category_meta
    cats = [c for c in req.categories if c in cat_meta] if req.scoring_mode == "categories" else None
    result = manual_recommendations(req.roster, req.droppable, scoring_mode=req.scoring_mode, categories=cats)
    if result["resolved_count"] == 0:
        raise HTTPException(
            status_code=400,
            detail={"message": "No roster names matched the known player pool.",
                    "unresolved": result["unresolved"]},
        )
    return result


@app.get("/api/streamers")
def streamers(top: int = 30, sport: str = "nba") -> dict:
    """Top streaming pickups this week + schedule density grid. No auth required."""
    sc = get_sport(sport)
    if not sc.has_data:
        raise HTTPException(status_code=501, detail=f"{sc.name} data pipeline not yet available.")
    return {**top_streamers(top_n=min(top, 50)), "sport": sport}


# TODO: @app.get("/api/recommendations/{connection_id}") — DB-backed, per-user.
#   1. load the user's roster + league scoring from rosters/league_connections
#   2. load projections + DvP from player_game_logs / team_dvp (computed nightly)
#   3. determine the league's free-agent pool (Yahoo/ESPN API) and run the engine
