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

# Yahoo game key prefixes → sport. MLB game IDs are 469 (2026), 454 (2025), etc.
# NBA game IDs are 418 (2025-26), 428, etc. We match by checking the league_id.
_YAHOO_MLB_GAMES = {"469", "454", "439", "422", "404", "388", "370", "357", "346", "328"}
_YAHOO_NBA_GAMES = {"418", "428", "410", "395", "375", "364", "353", "340"}


# Yahoo stat IDs → our fixture stat keys. Covers both hitting and pitching.
_YAHOO_STAT_MAP: dict[str, str] = {
    "7": "r", "8": "h", "9": "h",     # runs, hits, singles (count as hits)
    "10": "h", "11": "h",              # doubles, triples (count as hits)
    "12": "hr", "13": "rbi", "16": "sb",
    "18": "bb", "20": "bb",            # walks, HBP (count as BB for fantasy)
    "21": "k_hitting",                  # batter strikeouts
    "28": "w", "32": "sv",
    "33": "ip",                         # outs → rough IP proxy (outs/3)
    "34": "ha", "37": "er",
    "39": "bba", "41": "bba",          # pitcher walks, HBP → walks against
    "42": "k_pitching",
    "50": "ip",
}


def _yahoo_scoring_weights(scoring_json: dict | None) -> dict[str, float] | None:
    """Build fantasy point weights from Yahoo league scoring categories."""
    if not scoring_json:
        return None
    categories = scoring_json.get("categories", [])
    if not categories:
        return None
    weights: dict[str, float] = {}
    for cat in categories:
        mod = cat.get("modifier", 0)
        if mod == 0:
            continue
        stat_id = str(cat.get("stat_id", ""))
        our_key = _YAHOO_STAT_MAP.get(stat_id)
        if our_key:
            # Accumulate — some Yahoo stats map to the same key (e.g. 1B/2B/3B → h)
            weights[our_key] = weights.get(our_key, 0) + mod
    return weights if weights else None


def _sport_for_league(league_id: str | None) -> str:
    """Derive sport from Yahoo league_id (e.g. '469.l.233345' → 'mlb')."""
    if not league_id:
        return "nba"
    game_id = league_id.split(".")[0]
    if game_id in _YAHOO_MLB_GAMES:
        return "mlb"
    return "nba"


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
    # Enrich with player names from fixtures.
    sport = _sport_for_league(conn.league_id)
    try:
        fx = load_fixtures(sport)
        names_by_id = {p["id"]: p["name"] for p in fx["players"]}
    except Exception:
        names_by_id = {}
    return {
        "id": conn.id,
        "platform": conn.platform,
        "league_id": conn.league_id,
        "team_key": conn.team_key,
        "scoring": conn.scoring_json,
        "sport": sport,
        "roster": [
            {"player_id": r.player_id, "name": names_by_id.get(r.player_id, f"Player #{r.player_id}"),
             "slot": r.slot, "droppable": r.droppable}
            for r in roster
        ],
    }


@router.post("/{connection_id}/sync")
def sync_roster(connection_id: int, db: Session = Depends(get_db)) -> dict:
    """Refresh the roster from Yahoo and persist it."""
    conn = _get_connection(connection_id, db)
    if conn.platform != "yahoo":
        raise HTTPException(status_code=400, detail="Cannot sync: not a Yahoo connection.")
    if not conn.oauth_tokens:
        raise HTTPException(status_code=400, detail="No OAuth tokens on this connection.")

    yc = YahooFantasyClient(conn.oauth_tokens)

    # If team_key was missing from the initial OAuth callback, try to find it now.
    team_key = conn.team_key
    if not team_key and conn.league_id:
        team_key = yc.my_team_key(conn.league_id)
        if team_key:
            conn.team_key = team_key
            db.commit()
    if not team_key:
        raise HTTPException(status_code=400, detail="Could not determine your team in this league. "
                            "You may not be a manager in this league.")

    yahoo_roster = yc.roster(team_key)
    if yc.tokens_refreshed:
        conn.oauth_tokens = yc.current_tokens
        db.commit()

    if not yahoo_roster:
        raise HTTPException(status_code=502, detail="Yahoo returned an empty roster.")

    sport = _sport_for_league(conn.league_id)
    fx = load_fixtures(sport)
    names = [p["name"] for p in yahoo_roster]
    resolved_ids, unresolved = resolve_names(names, fx["players"])

    db.query(RosterEntry).filter(RosterEntry.connection_id == conn.id).delete()
    yahoo_by_name = {p["name"]: p for p in yahoo_roster}
    players_by_id = {p["id"]: p for p in fx["players"]}
    for pid in resolved_ids:
        p = players_by_id.get(pid, {})
        yahoo_p = yahoo_by_name.get(p.get("name", ""), {})
        slot = yahoo_p.get("slot") or p.get("positions", ["UTIL"])[0] or "UTIL"
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

    sport = _sport_for_league(conn.league_id)
    fx = load_fixtures(sport)
    cfg = fx["roster"]

    roster_ids = {r.player_id for r in roster_entries}
    free_agents = [p["id"] for p in fx["players"] if p["id"] not in roster_ids]
    droppable = [r.player_id for r in roster_entries if r.droppable]

    scoring = conn.scoring_json or {}
    scoring_type = scoring.get("scoring_type", "")
    mode = "categories" if scoring_type in ("head", "roto") else "points"

    # Use the Yahoo league's actual scoring weights when available.
    yahoo_weights = _yahoo_scoring_weights(scoring)

    fx["roster"] = {
        "week_start": cfg["week_start"],
        "week_end": cfg["week_end"],
        "scoring": yahoo_weights or cfg.get("scoring"),
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
