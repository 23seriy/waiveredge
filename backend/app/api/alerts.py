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

from ..config import settings
from ..db import SessionLocal, get_db
from ..email import send_email
from ..models import InjuryAlert, LeagueConnection, RosterEntry, User
from ..recommendations import _is_fresh, build_recommendations, load_fixtures, resolve_names
from ..scoring.engine import role_multiplier
from ..scoring.types import Injury as ScoringInjury
from ..scoring.types import Player
from .leagues import _sport_for_league

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _detect_injury_opportunities(
    sport: str,
    roster_player_ids: set[int],
    free_agent_ids: list[int],
    fx: dict | None = None,
) -> list[dict]:
    """Find players whose teammates just got injured, creating pickup opportunities.

    Returns a list of alert dicts for each detected opportunity. ``fx`` may be
    injected (for tests); otherwise fixtures are loaded for the sport.
    """
    if fx is None:
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


def _format_alert_email(sport: str, connection_id: int, new_alerts: list[dict]) -> tuple[str, str]:
    """Build (subject, html) for a digest of newly-detected pickup opportunities."""
    n = len(new_alerts)
    subject = f"WaiverEdge: {n} injury pickup{'s' if n != 1 else ''} in your {sport.upper()} league"
    rows = "".join(
        f"<li><b>{a['pickup_player_name']}</b> — {a['pickup_rationale']}</li>"
        for a in new_alerts
    )
    link = f"{settings.frontend_url.rstrip('/')}/{sport}/alerts/{connection_id}"
    html = (
        f"<h2>{n} new waiver pickup{'s' if n != 1 else ''} from injuries</h2>"
        f"<ul>{rows}</ul>"
        f'<p><a href="{link}">View in WaiverEdge</a></p>'
    )
    return subject, html


def _notify_new_alerts(conn: LeagueConnection, db: Session, sport: str, new_alerts: list[dict]) -> None:
    """Email a Pro user a digest of new alerts (best-effort).

    Skips when: no real email (synthetic ESPN accounts), user opted out, or the
    user isn't on Pro (alerts are a paid feature).
    """
    user = db.query(User).filter(User.id == conn.user_id).first()
    if not user or not user.email or user.email.endswith("@waiveredge.local"):
        return
    if user.tier != "pro" or not user.alert_email:
        return
    subject, html = _format_alert_email(sport, conn.id, new_alerts)
    send_email(user.email, subject, html)


def scan_and_store(conn: LeagueConnection, db: Session) -> tuple[int, int]:
    """Scan one connection for injury opportunities and persist new alerts.

    Returns ``(opportunities_found, new_alerts)``. New alerts are deduplicated
    against existing ones for the connection by (injured, pickup) pair.
    """
    sport = _sport_for_league(conn.league_id)
    roster_ids = {
        r.player_id
        for r in db.query(RosterEntry).filter(RosterEntry.connection_id == conn.id).all()
    }

    # Get free agent IDs from stored data or fall back to all non-rostered.
    scoring_data = conn.scoring_json or {}
    stored_fa_ids = scoring_data.get("free_agent_ids", [])
    if not stored_fa_ids:
        fx = load_fixtures(sport)
        stored_fa_ids = [p["id"] for p in fx["players"] if p["id"] not in roster_ids]

    opportunities = _detect_injury_opportunities(sport, roster_ids, stored_fa_ids)

    existing = {
        (a.injured_player_id, a.pickup_player_id)
        for a in db.query(InjuryAlert).filter(InjuryAlert.connection_id == conn.id).all()
    }
    created: list[dict] = []
    for opp in opportunities:
        if (opp["injured_player_id"], opp["pickup_player_id"]) not in existing:
            db.add(InjuryAlert(connection_id=conn.id, sport=sport, **opp))
            created.append(opp)
    db.commit()
    if created:
        _notify_new_alerts(conn, db, sport, created)
    return len(opportunities), len(created)


def scan_all_connections() -> dict:
    """Scan every connection for injury alerts. Used by the background scheduler.

    Best-effort per connection (one failure doesn't abort the batch). Skips
    sports whose fixtures aren't fresh so the scan never triggers a slow rebuild.
    """
    db = SessionLocal()
    scanned = 0
    total_new = 0
    try:
        for conn in db.query(LeagueConnection).all():
            try:
                if not _is_fresh(_sport_for_league(conn.league_id)):
                    continue
                _, new = scan_and_store(conn, db)
                scanned += 1
                total_new += new
            except Exception:
                db.rollback()
    finally:
        db.close()
    return {"connections_scanned": scanned, "new_alerts": total_new}


@router.post("/scan/{connection_id}")
def scan_injuries(connection_id: int, db: Session = Depends(get_db)) -> dict:
    """Scan for injury-driven pickup opportunities for a connected league."""
    conn = db.query(LeagueConnection).filter(LeagueConnection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")
    found, new_count = scan_and_store(conn, db)
    return {"scanned": True, "opportunities_found": found, "new_alerts": new_count}


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
