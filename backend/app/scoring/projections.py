"""Per-game fantasy projections from recent game logs.

Deterministic and explainable: a recency-weighted average of past fantasy output.
No ML in v1 — that is a feature, not a limitation. Every projection can be traced
to the exact games that produced it, which matters when a user is deciding whether
to trust an "add this player" recommendation.
"""
from __future__ import annotations

from .scoring_systems import DEFAULT_POINTS_SCORING, fantasy_points
from .types import GameLog, Projection

# Exponential recency decay: the most recent game is weighted 1.0, the previous
# 0.85, then 0.72, ... so hot/cold recent form moves the projection without
# ignoring the larger sample.
RECENCY_DECAY = 0.85


def project_player(
    logs: list[GameLog],
    weights: dict[str, float] | None = None,
    decay: float = RECENCY_DECAY,
) -> Projection:
    """Recency-weighted fantasy points per game for one player.

    ``logs`` may be in any order; they are sorted most-recent-first internally.
    """
    if not logs:
        return Projection(player_id=-1, fppg=0.0, games_sampled=0, per_game={})

    w = weights or DEFAULT_POINTS_SCORING
    ordered = sorted(logs, key=lambda lg: lg.date, reverse=True)

    # Collect all stat keys present in this player's logs (sport-agnostic).
    all_keys: set[str] = set()
    for lg in ordered:
        all_keys.update(lg.stats.keys())

    weighted_sum = 0.0
    weight_total = 0.0
    per_game_sum: dict[str, float] = {s: 0.0 for s in all_keys}
    for i, lg in enumerate(ordered):
        wt = decay ** i
        weighted_sum += fantasy_points(lg.stats, w) * wt
        weight_total += wt
        for s in all_keys:
            per_game_sum[s] += float(lg.stats.get(s, 0) or 0) * wt

    fppg = weighted_sum / weight_total if weight_total else 0.0
    per_game = {s: round(per_game_sum[s] / weight_total, 3) for s in all_keys} if weight_total else {}
    return Projection(
        player_id=ordered[0].player_id,
        fppg=round(fppg, 2),
        games_sampled=len(ordered),
        per_game=per_game,
    )


def project_all(
    logs_by_player: dict[int, list[GameLog]],
    weights: dict[str, float] | None = None,
) -> dict[int, Projection]:
    return {pid: project_player(lgs, weights) for pid, lgs in logs_by_player.items()}
