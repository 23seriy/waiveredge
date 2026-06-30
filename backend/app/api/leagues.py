"""League connection + per-user recommendation endpoints.

Once a user has connected their Yahoo league via OAuth, these endpoints:
- GET /api/leagues/{id}         — connection info + roster
- POST /api/leagues/{id}/sync   — refresh roster from Yahoo
- GET /api/leagues/{id}/recs    — personalized recommendations
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..data.yahoo import YahooFantasyClient
from ..db import get_db
from ..models import LeagueConnection, RosterEntry
from ..recommendations import build_espn_id_map, build_recommendations, load_fixtures, resolve_names
from .paywall import check_pro_or_free, require_pro

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
    """Derive sport from league_id. Supports Yahoo (469.l.233345) and ESPN (espn-mlb-123456)."""
    if not league_id:
        return "nba"
    if league_id.startswith("espn-"):
        parts = league_id.split("-")
        return parts[1] if len(parts) >= 3 else "nba"
    game_id = league_id.split(".")[0]
    if game_id in _YAHOO_MLB_GAMES:
        return "mlb"
    return "nba"


def _get_connection(connection_id: int, db: Session) -> LeagueConnection:
    conn = db.query(LeagueConnection).filter(LeagueConnection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="League connection not found.")
    return conn


@router.get("")
def list_leagues(ids: str = "", db: Session = Depends(get_db)) -> list[dict]:
    """Return basic info for a list of connection IDs (comma-separated).

    The frontend stores connection IDs in localStorage and passes them here
    to display the user's connected leagues on the connect page.
    """
    if not ids.strip():
        return []
    try:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError:
        return []
    if not id_list:
        return []
    conns = db.query(LeagueConnection).filter(LeagueConnection.id.in_(id_list)).all()
    result = []
    for conn in conns:
        sport = _sport_for_league(conn.league_id)
        roster_count = db.query(RosterEntry).filter(RosterEntry.connection_id == conn.id).count()
        result.append({
            "id": conn.id,
            "platform": conn.platform,
            "league_id": conn.league_id,
            "team_key": conn.team_key,
            "sport": sport,
            "roster_count": roster_count,
            "created_at": conn.created_at.isoformat() if conn.created_at else None,
        })
    return result


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


@router.get("/{connection_id}/pending")
def pending_moves(connection_id: int, db: Session = Depends(get_db)) -> dict:
    """Fetch pending waiver claims and recent transactions from the platform."""
    conn = _get_connection(connection_id, db)

    if conn.platform != "espn":
        return {"pending": [], "platform": conn.platform}

    from ..data.espn import ESPNFantasyClient

    tokens = conn.oauth_tokens or {}
    sport = _sport_for_league(conn.league_id)
    client = ESPNFantasyClient(
        sport=sport,
        espn_s2=tokens.get("espn_s2", ""),
        swid=tokens.get("swid", ""),
    )
    espn_league_id = tokens.get("espn_league_id")
    team_id = tokens.get("espn_team_id")
    season = tokens.get("season")
    if not espn_league_id or not team_id or not season:
        return {"pending": [], "platform": "espn"}

    txns = client.pending_transactions(espn_league_id, season, team_id)
    return {"pending": txns, "platform": "espn"}


@router.post("/{connection_id}/sync")
def sync_roster(connection_id: int, db: Session = Depends(get_db)) -> dict:
    """Refresh the roster and free agents. Supports Yahoo and ESPN."""
    from ..config import settings
    if not settings.taste_paywall_enabled:
        require_pro(connection_id, db)
    conn = _get_connection(connection_id, db)

    if conn.platform == "espn":
        return _sync_espn(conn, db)
    if conn.platform == "yahoo":
        return _sync_yahoo(conn, db)
    raise HTTPException(status_code=400, detail=f"Unsupported platform: {conn.platform}")


def _sync_espn(conn: LeagueConnection, db: Session) -> dict:
    """Re-sync an ESPN connection."""
    from ..data.espn import ESPNFantasyClient

    tokens = conn.oauth_tokens or {}
    client = ESPNFantasyClient(
        sport=_sport_for_league(conn.league_id),
        espn_s2=tokens.get("espn_s2", ""),
        swid=tokens.get("swid", ""),
    )
    espn_league_id = tokens.get("espn_league_id")
    team_id = tokens.get("espn_team_id")
    season = tokens.get("season", 2026)
    if not espn_league_id:
        raise HTTPException(status_code=400, detail="Missing ESPN league ID in connection.")

    try:
        roster_data = client.roster(espn_league_id, season, team_id) if team_id else []
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"ESPN roster fetch failed ({exc.response.status_code}).") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ESPN roster fetch failed: {exc}") from exc

    try:
        fas = client.free_agents(espn_league_id, season, count=200)
    except Exception:
        fas = []

    sport = _sport_for_league(conn.league_id)
    try:
        fx = load_fixtures(sport)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"{sport.upper()} data is not available yet. Please try again later.") from exc
    roster_names = [p["name"] for p in roster_data]
    resolved_ids, unresolved = resolve_names(roster_names, fx["players"])
    fa_names = [p["name"] for p in fas]
    fa_ids, _ = resolve_names(fa_names, fx["players"])

    espn_id_map = build_espn_id_map(roster_data + fas, fx["players"])
    scoring_data = dict(conn.scoring_json or {})
    scoring_data["free_agent_ids"] = fa_ids
    scoring_data["espn_player_keys"] = espn_id_map
    conn.scoring_json = scoring_data

    db.query(RosterEntry).filter(RosterEntry.connection_id == conn.id).delete()
    players_by_id = {p["id"]: p for p in fx["players"]}
    for pid in resolved_ids:
        p = players_by_id.get(pid, {})
        slot = p.get("positions", ["UTIL"])[0] or "UTIL"
        db.add(RosterEntry(connection_id=conn.id, player_id=pid, slot=slot, droppable=True))
    db.commit()

    return {"synced": len(resolved_ids), "unresolved": unresolved,
            "roster_size": len(resolved_ids), "free_agents_found": len(fa_ids)}


def _sync_yahoo(conn: LeagueConnection, db: Session) -> dict:
    """Re-sync a Yahoo connection."""
    if not conn.oauth_tokens:
        raise HTTPException(status_code=400, detail="No OAuth tokens on this connection.")

    yc = YahooFantasyClient(conn.oauth_tokens)

    team_key = conn.team_key
    if not team_key and conn.league_id:
        team_key = yc.my_team_key(conn.league_id)
        if team_key:
            conn.team_key = team_key
            db.commit()
    if not team_key:
        raise HTTPException(status_code=400, detail="Could not determine your team in this league.")

    try:
        yahoo_roster = yc.roster(team_key)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch roster from Yahoo: {exc}") from exc
    finally:
        if yc.tokens_refreshed:
            conn.oauth_tokens = yc.current_tokens
            db.commit()

    if not yahoo_roster:
        raise HTTPException(status_code=502, detail="Yahoo returned an empty roster.")

    try:
        yahoo_fas = yc.free_agents(conn.league_id, max_players=500)
    except Exception:
        yahoo_fas = []
    if yc.tokens_refreshed:
        conn.oauth_tokens = yc.current_tokens

    sport = _sport_for_league(conn.league_id)
    fx = load_fixtures(sport)
    roster_names = [p["name"] for p in yahoo_roster]
    resolved_ids, unresolved = resolve_names(roster_names, fx["players"])

    fa_names = [p["name"] for p in yahoo_fas]
    fa_ids, _ = resolve_names(fa_names, fx["players"])

    scoring_data = dict(conn.scoring_json or {})
    scoring_data["free_agent_ids"] = fa_ids
    conn.scoring_json = scoring_data

    # Build name→Yahoo player data lookup for roster entries.
    yahoo_by_name = {p["name"]: p for p in yahoo_roster}

    # Store free agent player keys for transaction support.
    fa_by_name = {p["name"]: p for p in yahoo_fas}
    fa_keys: dict[int, str] = {}
    for p in fx["players"]:
        fa_info = fa_by_name.get(p["name"])
        if fa_info and fa_info.get("player_key") and p["id"] in fa_ids:
            fa_keys[p["id"]] = fa_info["player_key"]

    scoring_data["free_agent_keys"] = fa_keys
    conn.scoring_json = scoring_data

    db.query(RosterEntry).filter(RosterEntry.connection_id == conn.id).delete()
    players_by_id = {p["id"]: p for p in fx["players"]}
    for pid in resolved_ids:
        p = players_by_id.get(pid, {})
        yahoo_p = yahoo_by_name.get(p.get("name", ""), {})
        slot = yahoo_p.get("slot") or p.get("positions", ["UTIL"])[0] or "UTIL"
        player_key = yahoo_p.get("player_key", "")
        db.add(RosterEntry(connection_id=conn.id, player_id=pid, player_key=player_key,
                           slot=slot, droppable=True))
    db.commit()

    return {"synced": len(resolved_ids), "unresolved": unresolved,
            "roster_size": len(resolved_ids), "free_agents_found": len(fa_ids)}


def _refresh_yahoo_free_agents(conn: LeagueConnection, fx: dict, db: Session) -> list[int]:
    """Re-fetch free agents from Yahoo so recs use current data."""
    if not conn.oauth_tokens:
        return []
    try:
        yc = YahooFantasyClient(conn.oauth_tokens)
        yahoo_fas = yc.free_agents(conn.league_id, max_players=500)
        if yc.tokens_refreshed:
            conn.oauth_tokens = yc.current_tokens
        fa_names = [p["name"] for p in yahoo_fas]
        fa_ids, _ = resolve_names(fa_names, fx["players"])
        # Update stored FA IDs + keys for transaction support.
        scoring_data = dict(conn.scoring_json or {})
        scoring_data["free_agent_ids"] = fa_ids
        fa_by_name = {p["name"]: p for p in yahoo_fas}
        fa_keys: dict[int, str] = {}
        for p in fx["players"]:
            fa_info = fa_by_name.get(p["name"])
            if fa_info and fa_info.get("player_key") and p["id"] in fa_ids:
                fa_keys[p["id"]] = fa_info["player_key"]
        scoring_data["free_agent_keys"] = fa_keys
        conn.scoring_json = scoring_data
        db.commit()
        return fa_ids
    except Exception:
        # Fall back to stored FA IDs if refresh fails.
        return list(conn.scoring_json.get("free_agent_ids", []) if conn.scoring_json else [])


@router.get("/{connection_id}/recs")
def league_recommendations(connection_id: int, db: Session = Depends(get_db)) -> dict:
    """Personalized recommendations for a connected league.

    When TASTE_PAYWALL_ENABLED=true: free users receive the #1 rec in full and
    locked stubs (position + game count only) for ranks 2-10. Pro users always
    receive the full list. When the flag is off, the legacy hard gate (402 for
    non-Pro) is preserved unchanged.
    """
    from ..config import settings

    if not settings.taste_paywall_enabled:
        require_pro(connection_id, db)

    conn = _get_connection(connection_id, db)
    roster_entries = db.query(RosterEntry).filter(RosterEntry.connection_id == conn.id).all()
    if not roster_entries:
        raise HTTPException(status_code=400, detail="No roster stored. Call POST /sync first.")

    sport = _sport_for_league(conn.league_id)
    fx = load_fixtures(sport)
    cfg = fx["roster"]

    roster_ids = {r.player_id for r in roster_entries}
    if conn.platform == "yahoo":
        fresh_fa_ids = _refresh_yahoo_free_agents(conn, fx, db)
        free_agents = [pid for pid in fresh_fa_ids if pid not in roster_ids]
    else:
        scoring_data = conn.scoring_json or {}
        stored_fa_ids = scoring_data.get("free_agent_ids")
        if stored_fa_ids:
            free_agents = [pid for pid in stored_fa_ids if pid not in roster_ids]
        else:
            free_agents = [p["id"] for p in fx["players"] if p["id"] not in roster_ids]
    droppable = [r.player_id for r in roster_entries if r.droppable]

    scoring = conn.scoring_json or {}
    scoring_type = scoring.get("scoring_type", "")
    mode = "categories" if scoring_type in ("head", "roto") else "points"
    league_weights = scoring.get("weights") or _yahoo_scoring_weights(scoring)

    fx["roster"] = {
        "week_start": cfg["week_start"],
        "week_end": cfg["week_end"],
        "scoring": league_weights or cfg.get("scoring"),
        "mode": mode,
        "categories": None,
        "roster": [{"player_id": r.player_id, "slot": r.slot} for r in roster_entries],
        "free_agents": free_agents,
        "droppable": droppable,
    }

    all_recs = build_recommendations(fx, sport)
    paywall_meta = None

    if settings.taste_paywall_enabled and settings.stripe_secret_key:
        is_pro = check_pro_or_free(connection_id, db)
        if not is_pro:
            locked_stubs = [
                {"locked": True, "add_position": r.get("add_position"), "n_games": r.get("n_games")}
                for r in all_recs[1:]
            ]
            all_recs = (all_recs[:1] if all_recs else []) + locked_stubs
            paywall_meta = {"enabled": True, "free_count": 1}

    return {
        "connection_id": conn.id,
        "league_id": conn.league_id,
        "week": {"start": cfg["week_start"], "end": cfg["week_end"]},
        "scoring_mode": mode,
        "recommendations": all_recs,
        "paywall": paywall_meta,
    }


class ExecuteRequest(BaseModel):
    add_player_id: int
    drop_player_id: int | None = None


@router.post("/{connection_id}/execute")
def execute_transaction(connection_id: int, req: ExecuteRequest, db: Session = Depends(get_db)) -> dict:
    """Execute an add/drop transaction on the user's fantasy platform.

    Yahoo: submits via the official Transactions API.
    ESPN: submits via the undocumented write API (falls back to deep link).
    """
    require_pro(connection_id, db)
    conn = _get_connection(connection_id, db)

    if conn.platform == "espn":
        return _execute_espn(conn, req)
    if conn.platform == "yahoo":
        return _execute_yahoo(conn, req, db)
    raise HTTPException(status_code=400, detail=f"Unsupported platform: {conn.platform}")


def _execute_yahoo(conn: LeagueConnection, req: ExecuteRequest, db: Session) -> dict:
    """Execute an add/drop via Yahoo Fantasy API."""
    if not conn.oauth_tokens:
        raise HTTPException(status_code=400, detail="No OAuth tokens on this connection.")
    if not conn.team_key:
        raise HTTPException(status_code=400, detail="No team key — sync your roster first.")

    # Look up Yahoo player keys from stored data.
    scoring_data = conn.scoring_json or {}
    fa_keys = scoring_data.get("free_agent_keys", {})
    add_key = fa_keys.get(str(req.add_player_id)) or fa_keys.get(req.add_player_id)
    if not add_key:
        raise HTTPException(status_code=400, detail="Add player key not found. Sync your roster first.")

    drop_key: str | None = None
    if req.drop_player_id:
        roster_entry = (
            db.query(RosterEntry)
            .filter(RosterEntry.connection_id == conn.id, RosterEntry.player_id == req.drop_player_id)
            .first()
        )
        if not roster_entry or not roster_entry.player_key:
            raise HTTPException(status_code=400, detail="Drop player key not found. Sync your roster first.")
        drop_key = roster_entry.player_key

    yc = YahooFantasyClient(conn.oauth_tokens)

    try:
        result = yc.add_drop_player(
            league_key=conn.league_id,
            team_key=conn.team_key,
            add_player_key=add_key,
            drop_player_key=drop_key,
        )
    except Exception as exc:
        error_msg = str(exc)
        if "waivers" in error_msg.lower():
            raise HTTPException(status_code=409, detail="This player is on waivers — submit a waiver claim on Yahoo instead.") from exc
        if "roster" in error_msg.lower() and "full" in error_msg.lower():
            raise HTTPException(status_code=409, detail="Your roster is full. Select a player to drop.") from exc
        raise HTTPException(status_code=502, detail=f"Yahoo transaction failed: {error_msg}") from exc
    finally:
        if yc.tokens_refreshed:
            conn.oauth_tokens = yc.current_tokens
            db.commit()

    return {"success": True, "platform": "yahoo", "detail": "Transaction submitted to Yahoo."}


def _espn_deep_link(conn: LeagueConnection) -> str:
    """Build a deep link to the ESPN free-agent page for this league."""
    tokens = conn.oauth_tokens or {}
    espn_league_id = tokens.get("espn_league_id", "")
    sport = _sport_for_league(conn.league_id)
    espn_sport_path = {
        "nba": "basketball",
        "mlb": "baseball",
        "nfl": "football",
        "nhl": "hockey",
        "wnba": "womens-basketball",
    }.get(sport, "basketball")
    season = tokens.get("season", 2026)
    team_id = tokens.get("espn_team_id", "")
    url = (
        f"https://fantasy.espn.com/{espn_sport_path}/players/add"
        f"?leagueId={espn_league_id}&seasonId={season}"
    )
    if team_id:
        url += f"&teamId={team_id}"
    return url


def _execute_espn(conn: LeagueConnection, req: ExecuteRequest) -> dict:
    """Execute an add/drop via ESPN Fantasy API.

    Falls back to a deep link if cookies or ESPN player IDs are missing.
    """
    from ..data.espn import ESPNFantasyClient

    tokens = conn.oauth_tokens or {}
    espn_s2 = tokens.get("espn_s2", "")
    swid = tokens.get("swid", "")
    espn_league_id = tokens.get("espn_league_id")
    team_id = tokens.get("espn_team_id")
    season = tokens.get("season", 2026)

    # Without cookies we can't write — fall back to deep link.
    if not espn_s2 or not swid or not espn_league_id or not team_id:
        return {
            "success": False, "platform": "espn",
            "detail": "Missing ESPN credentials. Use the link to make this move.",
            "deep_link": _espn_deep_link(conn),
        }

    # Look up ESPN player IDs from stored mapping.
    scoring_data = conn.scoring_json or {}
    espn_keys: dict = scoring_data.get("espn_player_keys", {})
    add_espn_id = espn_keys.get(str(req.add_player_id))
    if not add_espn_id:
        return {
            "success": False, "platform": "espn",
            "detail": "Add player ESPN ID not found. Sync your roster first, then try again.",
            "deep_link": _espn_deep_link(conn),
        }

    drop_espn_id = None
    if req.drop_player_id:
        drop_espn_id = espn_keys.get(str(req.drop_player_id))
        if not drop_espn_id:
            return {
                "success": False, "platform": "espn",
                "detail": "Drop player ESPN ID not found. Sync your roster first, then try again.",
                "deep_link": _espn_deep_link(conn),
            }

    sport = _sport_for_league(conn.league_id)
    client = ESPNFantasyClient(sport=sport, espn_s2=espn_s2, swid=swid)

    try:
        result = client.add_drop_player(
            league_id=espn_league_id,
            season=season,
            team_id=team_id,
            add_espn_id=int(add_espn_id),
            drop_espn_id=int(drop_espn_id) if drop_espn_id else None,
        )
    except httpx.HTTPStatusError as exc:
        error_body = exc.response.text[:300]
        # ESPN returns 409 for waivers / roster-full situations.
        if exc.response.status_code == 409:
            if "waivers" in error_body.lower():
                raise HTTPException(
                    status_code=409,
                    detail="This player is on waivers — submit a waiver claim on ESPN instead.",
                ) from exc
            raise HTTPException(
                status_code=409,
                detail=f"ESPN rejected the transaction: {error_body}",
            ) from exc
        raise HTTPException(
            status_code=502,
            detail=f"ESPN transaction failed ({exc.response.status_code}): {error_body}",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ESPN transaction failed: {exc}") from exc

    return {"success": True, "platform": "espn", "detail": "Transaction executed on ESPN."}
