"""Paywall enforcement — gate Pro features behind tier check.

Free tier: public streamers, manual roster (basic), schedule grid.
Pro tier: league import (Yahoo/ESPN), personalized recs, 9-cat mode,
          injury alerts, AI rationales.

The gate is simple: check the user's tier on the league_connection's
user. If no user/connection context, allow (public endpoints).
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import LeagueConnection, User

# Features available without Pro.
FREE_FEATURES = {"streamers", "sample_recommendations", "manual_basic", "health", "sports"}

# Features that require Pro.
PRO_FEATURES = {"league_sync", "league_recs", "alerts", "explain", "espn_connect"}


def require_pro(connection_id: int, db: Session) -> User:
    """Verify the user behind a connection is on the Pro tier.

    Raises 402 Payment Required if on free tier.
    Returns the User if Pro or if billing is not configured.
    """
    conn = db.query(LeagueConnection).filter(LeagueConnection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")

    user = db.query(User).filter(User.id == conn.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # If Stripe is not configured, allow all features (dev mode).
    from ..config import settings
    if not settings.stripe_secret_key:
        return user

    if user.tier != "pro":
        raise HTTPException(
            status_code=402,
            detail={
                "message": "This feature requires WaiverEdge Pro.",
                "upgrade_url": "/pricing",
                "current_tier": user.tier,
            },
        )
    return user


def check_pro_or_free(connection_id: int | None, db: Session) -> bool:
    """Check if a connection's user is Pro. Returns False (free) without raising."""
    if connection_id is None:
        return False
    try:
        conn = db.query(LeagueConnection).filter(LeagueConnection.id == connection_id).first()
        if not conn:
            return False
        user = db.query(User).filter(User.id == conn.user_id).first()
        return user is not None and user.tier == "pro"
    except Exception:
        return False
