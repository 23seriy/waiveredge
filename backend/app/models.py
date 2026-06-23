"""SQLAlchemy ORM models. Mirrors migrations/0001_init.sql."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # balldontlie id
    abbreviation: Mapped[str] = mapped_column(String(8))
    full_name: Mapped[str] = mapped_column(String(64))


class Player(Base):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # balldontlie id
    name: Mapped[str] = mapped_column(String(128), index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), index=True)
    positions: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    primary_position: Mapped[str | None] = mapped_column(String(4))


class Game(Base):
    __tablename__ = "games"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    season: Mapped[int | None] = mapped_column(Integer, index=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    visitor_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    status: Mapped[str | None] = mapped_column(String(32))


class PlayerGameLog(Base):
    __tablename__ = "player_game_logs"
    __table_args__ = (UniqueConstraint("player_id", "game_id", name="uq_player_game"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    team_id: Mapped[int] = mapped_column(Integer)
    opponent_id: Mapped[int] = mapped_column(Integer, index=True)
    position: Mapped[str] = mapped_column(String(4), index=True)
    minutes: Mapped[int | None] = mapped_column(Integer)
    pts: Mapped[int] = mapped_column(Integer, default=0)
    reb: Mapped[int] = mapped_column(Integer, default=0)
    ast: Mapped[int] = mapped_column(Integer, default=0)
    stl: Mapped[int] = mapped_column(Integer, default=0)
    blk: Mapped[int] = mapped_column(Integer, default=0)
    fg3m: Mapped[int] = mapped_column(Integer, default=0)
    turnover: Mapped[int] = mapped_column(Integer, default=0)


class TeamDvP(Base):
    """Cached defense-vs-position multipliers (recomputed nightly)."""
    __tablename__ = "team_dvp"
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), primary_key=True)
    position: Mapped[str] = mapped_column(String(4), primary_key=True)
    window_label: Mapped[str] = mapped_column(String(32), primary_key=True, default="season")
    fpts_allowed: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    multiplier: Mapped[float] = mapped_column(Numeric(5, 3), default=1.0)
    sample: Mapped[int] = mapped_column(Integer, default=0)


class Injury(Base):
    __tablename__ = "injuries"
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(String(256))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    tier: Mapped[str] = mapped_column(String(16), default="free")  # free | pro
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(64))
    alert_email: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_push: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LeagueConnection(Base):
    """A linked fantasy league (Yahoo OAuth, ESPN, or manual import)."""
    __tablename__ = "league_connections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    platform: Mapped[str] = mapped_column(String(16))  # yahoo | espn | manual
    league_id: Mapped[str | None] = mapped_column(String(64))
    team_key: Mapped[str | None] = mapped_column(String(64))
    scoring_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    oauth_tokens: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InjuryAlert(Base):
    """A detected injury change + the resulting pickup opportunity."""
    __tablename__ = "injury_alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("league_connections.id"), index=True)
    sport: Mapped[str] = mapped_column(String(8), default="nba")
    injured_player_name: Mapped[str] = mapped_column(String(128))
    injured_player_id: Mapped[int | None] = mapped_column(Integer)
    injury_status: Mapped[str] = mapped_column(String(32))
    injury_note: Mapped[str | None] = mapped_column(String(256))
    pickup_player_name: Mapped[str | None] = mapped_column(String(128))
    pickup_player_id: Mapped[int | None] = mapped_column(Integer)
    pickup_marginal: Mapped[float | None] = mapped_column(Numeric(8, 2))
    pickup_rationale: Mapped[str | None] = mapped_column(String(512))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RosterEntry(Base):
    __tablename__ = "rosters"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("league_connections.id"), index=True)
    player_id: Mapped[int] = mapped_column(Integer, index=True)
    player_key: Mapped[str | None] = mapped_column(String(32))  # Yahoo/ESPN platform key
    slot: Mapped[str] = mapped_column(String(8))
    droppable: Mapped[bool] = mapped_column(Boolean, default=True)
