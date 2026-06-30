"""NBA injury feed from ESPN's free public API.

ESPN exposes current injury status per player at a public endpoint (the same
host used for WNBA fixtures), so we get a live injury signal without the paid
balldontlie ALL-STAR tier. Statuses are mapped to the strings the scoring
engine understands (see scoring/engine.py AVAILABILITY): out, doubtful,
questionable, day-to-day.

This activates the previously-dormant role_mult / avail_prob signals for NBA.
"""
from __future__ import annotations

import unicodedata

import httpx

NBA_INJURIES_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"


def _normalize_name(name: str) -> str:
    """Casefold + fold accents + strip punctuation for tolerant name matching.

    Mirrors recommendations._normalize_name; kept local so this module stays
    dependency-light and hermetically testable. (Consolidation is a Phase 3
    cleanup item.)
    """
    decomposed = unicodedata.normalize("NFKD", name)
    out: list[str] = []
    for ch in decomposed.casefold():
        if unicodedata.combining(ch):
            continue
        if ch.isalnum():
            out.append(ch)
        elif ch.isspace():
            out.append(" ")
    return " ".join("".join(out).split())


def parse_injuries(payload: dict, players: list[dict]) -> list[dict]:
    """Map an ESPN injuries payload onto our fixture player IDs.

    Returns fixture-shaped injury records: ``{player_id, status, note}``.
    Only players present in our fixtures are kept (matched by normalized name);
    unmatched ESPN athletes are dropped.
    """
    index = {_normalize_name(p["name"]): p["id"] for p in players}
    out: list[dict] = []
    seen: set[int] = set()
    for team in payload.get("injuries", []):
        for item in team.get("injuries", []):
            athlete = item.get("athlete") or {}
            pid = index.get(_normalize_name(athlete.get("displayName") or ""))
            if pid is None or pid in seen:
                continue
            itype = item.get("type") or {}
            status = (itype.get("description") or item.get("status") or "").strip().lower()
            if not status:
                continue
            out.append({
                "player_id": pid,
                "status": status,
                "note": (item.get("shortComment") or "").strip(),
            })
            seen.add(pid)
    return out


def fetch_nba_injuries(players: list[dict], timeout: float = 15.0) -> list[dict]:
    """Fetch live NBA injuries from ESPN and map them onto our fixture players."""
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(NBA_INJURIES_URL)
        resp.raise_for_status()
        return parse_injuries(resp.json(), players)
