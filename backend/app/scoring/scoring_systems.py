"""Fantasy scoring systems.

v1 supports points-league scoring (a single weighted sum per stat line). This is
the cleanest base for value-over-replacement ranking because every player reduces
to one comparable number. 9-category (roto/H2H-categories) support is a planned
extension — see NOTES at the bottom.

Pure stdlib. No third-party imports so the scoring core runs anywhere.
"""
from __future__ import annotations

# A common points-league scoring profile (close to ESPN/Yahoo points defaults).
# Every league can override these weights; the engine is agnostic to the values.
DEFAULT_POINTS_SCORING: dict[str, float] = {
    "pts": 1.0,
    "reb": 1.2,
    "ast": 1.5,
    "stl": 3.0,
    "blk": 3.0,
    "fg3m": 0.5,
    "turnover": -1.0,
}

# Stat keys we read off a box-score line. Matches the balldontlie /v1/stats shape.
STAT_KEYS = ("pts", "reb", "ast", "stl", "blk", "fg3m", "turnover", "min")


def fantasy_points(stat_line: dict, weights: dict[str, float] | None = None) -> float:
    """Weighted fantasy points for a single game's stat line.

    Unknown keys in ``weights`` simply contribute 0 if absent from the line, and
    stats present in the line but absent from ``weights`` are ignored — so the
    same function serves any league's custom scoring.
    """
    w = weights or DEFAULT_POINTS_SCORING
    return float(sum(float(stat_line.get(k, 0) or 0) * mult for k, mult in w.items()))


# NOTES / roadmap:
#   - 9-cat leagues: replace the single value with a per-category z-score vector and
#     rank by aggregate z (value-over-replacement still applies, per category).
#   - Per-league weight overrides arrive via league_connections.scoring_json once
#     Yahoo OAuth import is wired up (see app/data/ingest.py).
