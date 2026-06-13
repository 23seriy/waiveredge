"""WaiverEdge API.

`/api/recommendations/sample` runs the real scoring engine over bundled fixtures,
so the API returns meaningful output with no database and no API key — handy for
frontend development. The DB-backed, per-user endpoint arrives once Yahoo OAuth
import + ingestion are wired up (see app/data/ingest.py).
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import settings
from .recommendations import manual_recommendations, sample_recommendations


class ManualRosterRequest(BaseModel):
    roster: list[str] = Field(..., min_length=1, max_length=30,
                              description="Player names on the user's roster.")
    droppable: list[str] = Field(default_factory=list, max_length=30,
                                 description="Optional subset of roster the user is willing to drop. "
                                             "Empty = the engine picks the weakest position match.")

app = FastAPI(title="WaiverEdge API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "waiveredge", "has_api_key": bool(settings.balldontlie_api_key)}


@app.get("/api/recommendations/sample")
def recommendations_sample() -> dict:
    """Ranked waiver adds for the sample roster (runs the live scoring engine)."""
    return sample_recommendations()


@app.post("/api/recommendations/manual")
def recommendations_manual(req: ManualRosterRequest) -> dict:
    """Ranked waiver adds for a user-typed roster (bridge to per-user before OAuth)."""
    result = manual_recommendations(req.roster, req.droppable)
    if result["resolved_count"] == 0:
        raise HTTPException(
            status_code=400,
            detail={"message": "No roster names matched the known player pool.",
                    "unresolved": result["unresolved"]},
        )
    return result


# TODO: @app.get("/api/recommendations/{connection_id}") — DB-backed, per-user.
#   1. load the user's roster + league scoring from rosters/league_connections
#   2. load projections + DvP from player_game_logs / team_dvp (computed nightly)
#   3. determine the league's free-agent pool (Yahoo/ESPN API) and run the engine
