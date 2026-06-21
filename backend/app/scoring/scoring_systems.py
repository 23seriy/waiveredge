"""Fantasy scoring systems.

v1 supports points-league scoring (a single weighted sum per stat line). This is
the cleanest base for value-over-replacement ranking because every player reduces
to one comparable number. 9-category (roto/H2H-categories) support is a planned
extension — see NOTES at the bottom.

Pure stdlib. No third-party imports so the scoring core runs anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# NBA default points-league scoring — only for use in NBA-specific code paths.
# For sport-agnostic code, always get weights from SportConfig.default_points_scoring.
NBA_DEFAULT_POINTS_SCORING: dict[str, float] = {
    "pts": 1.0,
    "reb": 1.2,
    "ast": 1.5,
    "stl": 3.0,
    "blk": 3.0,
    "fg3m": 0.5,
    "turnover": -1.0,
}

# Backwards-compat alias — only used by nba_fixtures.py.
DEFAULT_POINTS_SCORING = NBA_DEFAULT_POINTS_SCORING

# Stat keys we read off a box-score line. Matches the balldontlie /v1/stats shape.
STAT_KEYS = ("pts", "reb", "ast", "stl", "blk", "fg3m", "turnover", "min")


def fantasy_points(stat_line: dict, weights: dict[str, float]) -> float:
    """Weighted fantasy points for a single game's stat line.

    ``weights`` is required — there is no silent fallback to a sport-specific
    default.  Callers must supply the correct weights for their sport.

    Unknown keys in ``weights`` simply contribute 0 if absent from the line, and
    stats present in the line but absent from ``weights`` are ignored — so the
    same function serves any league's custom scoring.
    """
    return float(sum(float(stat_line.get(k, 0) or 0) * mult for k, mult in weights.items()))


# ---------------------------------------------------------------------------
# 9-category (roto / H2H-categories) scoring
# ---------------------------------------------------------------------------

# Raw per-game stats we project. Superset for both modes; FG%/FT% need made+att.
RAW_STATS = ("pts", "reb", "ast", "stl", "blk", "fg3m", "turnover",
             "fgm", "fga", "ftm", "fta")

# Standard 9-category set (Yahoo/ESPN default).
NINE_CAT = ("fg_pct", "ft_pct", "fg3m", "pts", "reb", "ast", "stl", "blk", "turnover")

# Standard MLB 5x5 roto categories.
MLB_5X5 = ("avg", "hr", "rbi", "r", "sb", "w", "sv", "era", "whip", "k")

# Per-category metadata. Counting cats map to a raw `stat`; `percentage` cats are
# valued by volume-weighted impact using made/att; `rate` cats are ratio stats
# (ERA, WHIP); `negative` cats are better low.
CATEGORY_META: dict[str, dict] = {
    # NBA 9-cat
    "fg_pct":   {"percentage": True, "made": "fgm", "att": "fga"},
    "ft_pct":   {"percentage": True, "made": "ftm", "att": "fta"},
    "fg3m":     {"stat": "fg3m"},
    "pts":      {"stat": "pts"},
    "reb":      {"stat": "reb"},
    "ast":      {"stat": "ast"},
    "stl":      {"stat": "stl"},
    "blk":      {"stat": "blk"},
    "turnover": {"stat": "turnover", "negative": True},
    # MLB 5x5 hitting
    "avg":  {"percentage": True, "made": "h", "att": "ab"},
    "hr":   {"stat": "hr"},
    "rbi":  {"stat": "rbi"},
    "r":    {"stat": "r"},
    "sb":   {"stat": "sb"},
    # MLB 5x5 pitching
    "w":    {"stat": "w"},
    "sv":   {"stat": "sv"},
    "era":  {"rate": True, "num": ["er"], "den": "ip", "scale": 9.0, "negative": True},
    "whip": {"rate": True, "num": ["ha", "bba"], "den": "ip", "negative": True},
    "k":    {"stat": "k_pitching"},
}

# Human labels for rationales.
CATEGORY_LABEL = {
    # NBA
    "fg_pct": "FG%", "ft_pct": "FT%", "fg3m": "3PM", "pts": "PTS", "reb": "REB",
    "ast": "AST", "stl": "STL", "blk": "BLK", "turnover": "TO",
    # MLB
    "avg": "AVG", "hr": "HR", "rbi": "RBI", "r": "R", "sb": "SB",
    "w": "W", "sv": "SV", "era": "ERA", "whip": "WHIP", "k": "K",
}


@dataclass
class LeagueScoring:
    """League scoring config.

    ``mode='points'`` ranks by the weighted `fantasy_points` sum (`weights`).
    ``mode='categories'`` ranks by a per-category z-score vector over `categories`.

    No defaults — callers must supply sport-specific weights and categories
    to prevent silent cross-sport fallback bugs.
    """
    mode: str = "points"
    weights: dict = field(default_factory=dict)
    categories: list = field(default_factory=list)


def league_from_sport_config(cfg: dict | None, sport_cfg: object) -> LeagueScoring:
    """Build a LeagueScoring using a SportConfig for defaults.

    Falls back to the *sport's own* defaults when the request/fixture config is
    missing or incomplete.  There is no cross-sport fallback — sport_cfg must
    have ``default_points_scoring``, ``default_categories``, and ``category_meta``.
    """
    defaults_weights = sport_cfg.default_points_scoring  # type: ignore[union-attr]
    defaults_cats = sport_cfg.default_categories          # type: ignore[union-attr]
    cat_meta = sport_cfg.category_meta                    # type: ignore[union-attr]

    if not cfg:
        return LeagueScoring(weights=dict(defaults_weights), categories=list(defaults_cats))
    if cfg.get("mode") == "categories":
        cats = [c for c in (cfg.get("categories") or defaults_cats) if c in cat_meta]
        return LeagueScoring(mode="categories", categories=cats or list(defaults_cats))
    return LeagueScoring(mode="points", weights=cfg.get("weights") or dict(defaults_weights))


# NOTES / roadmap:
#   - Per-league weight/category overrides arrive via league_connections.scoring_json
#     once Yahoo OAuth import is wired up (see app/data/ingest.py).
#   - Punt-weighted category ranking is a planned fast-follow (see issue #1).
