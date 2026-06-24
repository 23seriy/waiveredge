"""Injury alert endpoints + injury monitoring logic.

The monitor detects new/changed injuries and finds the pickup opportunity
for each connected league. Alerts are stored in the DB and served via API.

Flow:
1. POST /api/alerts/scan — triggers an injury scan for a connection
   (in production, this runs on a cron schedule)
2. GET /api/alerts/{connection_id} — list alerts for a connection
3. POST /api/alerts/{alert_id}/read — mark an alert as read
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import InjuryAlert, LeagueConnection, RosterEntry
from ..recommendations import build_recommendations, load_fixtures, resolve_names
from ..scoring.engine import role_multiplier
from ..scoring.types import Injury as ScoringInjury
from ..scoring.types import Player
from .leagues import _sport_for_league

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _detect_injury_opportunities(
    sport: str,
    roster_player_ids: set[int],
    free_agent_ids: list[int],
) -> list[dict]:
    """Find players whose teammates just got injured, creating pickup opportunities.

    Returns a list of alert dicts for each detected opportunity.
    """
    fx = load_fixtures(sport)
    players_by_id = {p["id"]: Player(p["id"], p["name"], p["team_id"], p["positions"])
                     for p in fx["players"]}
    injuries = {i["player_id"]: ScoringInjury(**i) for i in fx["injuries"]}

    if not injuries:
        return []

    players_by_team: dict[int, list[Player]] = {}
    for p in players_by_id.values():
        players_by_team.setdefault(p.team_id, []).append(p)

    alerts: list[dict] = []
    fa_set = set(free_agent_ids)

    for inj_pid, injury in injuries.items():
        if injury.status.strip().lower() not in ("out", "doubtful"):
            continue
        injured = players_by_id.get(inj_pid)
        if not injured:
            continue

        # Find free-agent teammates at the same position who benefit.
        teammates = players_by_team.get(injured.team_id, [])
        for tm in teammates:
            if tm.id == inj_pid:
                continue
            if tm.id not in fa_set:
                continue
            if tm.primary != injured.primary:
                continue
            # This teammate benefits from the injury — role bump.
            mult, note = role_multiplier(tm, injuries, players_by_team)
            if mult > 1.0:
                alerts.append({
                    "injured_player_name": injured.name,
                    "injured_player_id": injured.id,
                    "injury_status": injury.status,
                    "injury_note": injury.note,
                    "pickup_player_name": tm.name,
                    "pickup_player_id": tm.id,
                    "pickup_rationale": f"{tm.name} gets elevated role — {injured.name} ({injured.primary}) {injury.status.lower()}. {note}",
                })

    return alerts


@router.post("/scan/{connection_id}")
def scan_injuries(connection_id: int, db: Session = Depends(get_db)) -> dict:
    """Scan for injury-driven pickup opportunities for a connected league."""
    conn = db.query(LeagueConnection).filter(LeagueConnection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")

    sport = _sport_for_league(conn.league_id)
    roster_entries = db.query(RosterEntry).filter(RosterEntry.connection_id == conn.id).all()
    roster_ids = {r.player_id for r in roster_entries}

    # Get free agent IDs from stored data or fall back to all non-rostered.
    scoring_data = conn.scoring_json or {}
    stored_fa_ids = scoring_data.get("free_agent_ids", [])
    if not stored_fa_ids:
        fx = load_fixtures(sport)
        stored_fa_ids = [p["id"] for p in fx["players"] if p["id"] not in roster_ids]

    opportunities = _detect_injury_opportunities(sport, roster_ids, stored_fa_ids)

    # Store new alerts (deduplicate by injured+pickup combo for this connection).
    existing = {
        (a.injured_player_id, a.pickup_player_id)
        for a in db.query(InjuryAlert)
        .filter(InjuryAlert.connection_id == conn.id)
        .all()
    }
    new_count = 0
    for opp in opportunities:
        key = (opp["injured_player_id"], opp["pickup_player_id"])
        if key not in existing:
            db.add(InjuryAlert(
                connection_id=conn.id,
                sport=sport,
                **opp,
            ))
            new_count += 1
    db.commit()

    return {"scanned": True, "opportunities_found": len(opportunities), "new_alerts": new_count}


@router.get("/{connection_id}")
def get_alerts(connection_id: int, unread_only: bool = False, db: Session = Depends(get_db)) -> list[dict]:
    """List injury alerts for a connection."""
    query = db.query(InjuryAlert).filter(InjuryAlert.connection_id == connection_id)
    if unread_only:
        query = query.filter(InjuryAlert.is_read == False)  # noqa: E712
    alerts = query.order_by(InjuryAlert.created_at.desc()).limit(50).all()
    return [
        {
            "id": a.id,
            "sport": a.sport,
            "injured_player_name": a.injured_player_name,
            "injury_status": a.injury_status,
            "injury_note": a.injury_note,
            "pickup_player_name": a.pickup_player_name,
            "pickup_marginal": float(a.pickup_marginal) if a.pickup_marginal else None,
            "pickup_rationale": a.pickup_rationale,
            "is_read": a.is_read,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]


@router.post("/{alert_id}/read")
def mark_read(alert_id: int, db: Session = Depends(get_db)) -> dict:
    """Mark an alert as read."""
    alert = db.query(InjuryAlert).filter(InjuryAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    alert.is_read = True
    db.commit()
    return {"id": alert.id, "is_read": True}


@router.get("/count/{connection_id}")
def unread_count(connection_id: int, db: Session = Depends(get_db)) -> dict:
    """Get the count of unread alerts for a connection."""
    count = (
        db.query(InjuryAlert)
        .filter(InjuryAlert.connection_id == connection_id, InjuryAlert.is_read == False)  # noqa: E712
        .count()
    )
    return {"connection_id": connection_id, "unread": count}
