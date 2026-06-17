"""Typed data structures for the scoring engine.

Plain dataclasses, stdlib only. The engine operates on these regardless of whether
the underlying data came from the balldontlie API or sample fixtures.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Canonical positions and roster-slot eligibility.
POSITIONS = ("PG", "SG", "SF", "PF", "C")

SLOT_ELIGIBILITY: dict[str, set[str]] = {
    "PG": {"PG"},
    "SG": {"SG"},
    "G": {"PG", "SG"},
    "SF": {"SF"},
    "PF": {"PF"},
    "F": {"SF", "PF"},
    "C": {"C"},
    "UTIL": set(POSITIONS),
}


@dataclass(frozen=True)
class Team:
    id: int
    abbreviation: str
    full_name: str


@dataclass
class Player:
    id: int
    name: str
    team_id: int
    positions: list[str]

    @property
    def primary(self) -> str:
        return self.positions[0] if self.positions else "UTIL"

    def eligible_for(self, slot: str) -> bool:
        accepted = SLOT_ELIGIBILITY.get(slot, set(POSITIONS))
        return any(p in accepted for p in self.positions)


@dataclass
class GameLog:
    player_id: int
    game_id: int
    date: str            # ISO date
    team_id: int
    opponent_id: int
    position: str        # the player's primary position at the time
    stats: dict          # raw box-score line (pts, reb, ast, ...)


@dataclass
class ScheduledGame:
    id: int
    date: str
    home_team_id: int
    visitor_team_id: int

    def opponent_of(self, team_id: int) -> int:
        return self.visitor_team_id if team_id == self.home_team_id else self.home_team_id

    def involves(self, team_id: int) -> bool:
        return team_id in (self.home_team_id, self.visitor_team_id)


@dataclass
class Injury:
    player_id: int
    status: str          # Out | Doubtful | Questionable | Game-Time Decision | Day-To-Day
    note: str = ""


@dataclass
class Projection:
    player_id: int
    fppg: float          # recency-weighted fantasy points per game (points mode)
    games_sampled: int
    per_game: dict[str, float] = field(default_factory=dict)  # recency-weighted per-game mean per raw stat (category mode)


@dataclass
class GameContribution:
    """Per-game breakdown of a player's projected weekly value."""
    game_id: int
    opponent_id: int
    matchup_mult: float
    avail_prob: float
    points: float        # fppg * role_mult * matchup_mult * avail_prob


@dataclass
class ValueResult:
    player_id: int
    value: float                 # summed projected fantasy points over the window
    n_games: int
    soft_matchups: int
    role_mult: float
    role_note: str
    avail_prob: float
    contributions: list[GameContribution] = field(default_factory=list)


@dataclass
class CategoryValueResult:
    """Per-candidate result in category (9-cat) mode.

    `add_value` in a Recommendation maps to `total_z`; the per-category breakdown
    is carried so the rationale and API can explain *which* categories the player
    helps (and by how much).
    """
    player_id: int
    n_games: int
    soft_matchups: int
    role_mult: float
    role_note: str
    avail_prob: float
    weekly: dict[str, float]          # projected weekly totals per raw stat
    per_cat_z: dict[str, float]       # signed z per active category (TO already negated)
    total_z: float                    # sum of per_cat_z over active categories


@dataclass
class Recommendation:
    add_player_id: int
    add_name: str
    add_position: str
    add_value: float
    drop_player_id: int | None
    drop_name: str | None
    drop_value: float
    slot: str
    n_games: int
    soft_matchups: int
    marginal: float              # add_value - drop_value (value gained for THIS roster)
    rationale: str
    # Category-mode extras (None in points mode)
    total_z: float | None = None
    per_cat_z: dict[str, float] | None = None
    helps: list[str] | None = None  # active categories this add improves where the roster is weak
