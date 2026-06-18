"""Sport registry — per-sport configuration for the scoring engine.

Each sport defines its positions, default scoring weights, category sets,
and metadata. The scoring engine, recommendations service, and API endpoints
reference this registry so adding a new sport is config-only (until the data
source is wired up).

To add a new sport:
1. Define a SportConfig below and register it in SPORTS.
2. Add a data source in app/data/ that produces fixtures in the standard shape.
3. Set ``has_data=True`` once the data pipeline is live.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SportConfig:
    key: str                                # url slug + game key ("nba", "mlb")
    name: str                               # display name
    icon: str                               # emoji
    active: bool                            # is the season currently running?
    has_data: bool                          # do we have a working data pipeline?
    positions: tuple[str, ...]              # canonical roster positions
    default_points_scoring: dict[str, float]
    raw_stats: tuple[str, ...]              # per-game stats we project
    default_categories: tuple[str, ...]     # standard category set
    category_meta: dict[str, dict] = field(default_factory=dict)
    category_labels: dict[str, str] = field(default_factory=dict)
    note: str = ""


# ---------------------------------------------------------------------------
# NBA
# ---------------------------------------------------------------------------

NBA = SportConfig(
    key="nba",
    name="NBA Basketball",
    icon="\U0001f3c0",
    active=False,
    has_data=True,
    note="Offseason — returns Oct 2026",
    positions=("PG", "SG", "SF", "PF", "C"),
    default_points_scoring={
        "pts": 1.0, "reb": 1.2, "ast": 1.5, "stl": 3.0,
        "blk": 3.0, "fg3m": 0.5, "turnover": -1.0,
    },
    raw_stats=("pts", "reb", "ast", "stl", "blk", "fg3m", "turnover",
               "fgm", "fga", "ftm", "fta"),
    default_categories=("fg_pct", "ft_pct", "fg3m", "pts", "reb", "ast", "stl", "blk", "turnover"),
    category_meta={
        "fg_pct":   {"percentage": True, "made": "fgm", "att": "fga"},
        "ft_pct":   {"percentage": True, "made": "ftm", "att": "fta"},
        "fg3m":     {"stat": "fg3m"},
        "pts":      {"stat": "pts"},
        "reb":      {"stat": "reb"},
        "ast":      {"stat": "ast"},
        "stl":      {"stat": "stl"},
        "blk":      {"stat": "blk"},
        "turnover": {"stat": "turnover", "negative": True},
    },
    category_labels={
        "fg_pct": "FG%", "ft_pct": "FT%", "fg3m": "3PM", "pts": "PTS", "reb": "REB",
        "ast": "AST", "stl": "STL", "blk": "BLK", "turnover": "TO",
    },
)


# ---------------------------------------------------------------------------
# MLB  (config-only for now; has_data=False until data pipeline lands)
# ---------------------------------------------------------------------------

MLB = SportConfig(
    key="mlb",
    name="MLB Baseball",
    icon="\u26be",
    active=True,
    has_data=False,
    note="In-season — data pipeline coming soon",
    positions=("C", "1B", "2B", "SS", "3B", "OF", "SP", "RP", "DH"),
    default_points_scoring={
        "h": 1.0, "r": 1.0, "hr": 4.0, "rbi": 1.0, "sb": 2.0,
        "bb": 1.0, "k_hitting": -0.5,
        # Pitching (SP/RP)
        "ip": 3.0, "k_pitching": 1.0, "w": 5.0, "sv": 5.0,
        "er": -2.0, "ha": -1.0, "bba": -1.0,
    },
    raw_stats=("h", "r", "hr", "rbi", "sb", "bb", "k_hitting", "ab",
               "ip", "k_pitching", "w", "sv", "er", "ha", "bba"),
    default_categories=("r", "hr", "rbi", "sb", "avg",
                        "w", "sv", "k_pitching", "era", "whip"),
    category_meta={
        "r":           {"stat": "r"},
        "hr":          {"stat": "hr"},
        "rbi":         {"stat": "rbi"},
        "sb":          {"stat": "sb"},
        "avg":         {"percentage": True, "made": "h", "att": "ab"},
        "w":           {"stat": "w"},
        "sv":          {"stat": "sv"},
        "k_pitching":  {"stat": "k_pitching"},
        "era":         {"percentage": True, "made": "er", "att": "ip", "negative": True},
        "whip":        {"percentage": True, "made": "ha", "att": "ip", "negative": True},
    },
    category_labels={
        "r": "R", "hr": "HR", "rbi": "RBI", "sb": "SB", "avg": "AVG",
        "w": "W", "sv": "SV", "k_pitching": "K", "era": "ERA", "whip": "WHIP",
    },
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

SPORTS: dict[str, SportConfig] = {s.key: s for s in (NBA, MLB)}
SUPPORTED_KEYS = tuple(SPORTS.keys())


def get_sport(key: str) -> SportConfig:
    """Look up a sport config by key. Raises ValueError for unknown keys."""
    sport = SPORTS.get(key)
    if not sport:
        raise ValueError(f"Unknown sport '{key}'. Supported: {', '.join(SUPPORTED_KEYS)}")
    return sport
