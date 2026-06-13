"""Defense-vs-position (DvP) matchup multipliers.

We do NOT buy a matchup feed — we derive it from box scores, which makes it our
own defensible metric. For each (defending team, position) we compute the average
fantasy points that team has allowed to that position, relative to the league
average for that position. The result is a multiplier centered on 1.0:

    > 1.0  -> soft matchup (this team bleeds points to this position)
    < 1.0  -> tough matchup

Multipliers are clamped to keep a single hot/cold sample from dominating a weekly
projection — matchup is a tilt, not the whole story.
"""
from __future__ import annotations

from collections import defaultdict

from .scoring_systems import DEFAULT_POINTS_SCORING, fantasy_points
from .types import GameLog

# Clamp range. A matchup can swing a projection by at most +/-15%.
MULT_FLOOR = 0.85
MULT_CEIL = 1.15
# A matchup at or above this multiplier is flagged "soft" in recommendations.
SOFT_THRESHOLD = 1.05
# Below this many observed games for an (opponent, position) pair we fall back
# toward the neutral 1.0 to avoid overreacting to tiny samples.
MIN_SAMPLE = 3


class DvPTable:
    """Lookup of matchup multipliers, plus the league baselines used to build it."""

    def __init__(self, mult: dict[tuple[int, str], float], league_avg: dict[str, float],
                 sample: dict[tuple[int, str], int]):
        self._mult = mult
        self.league_avg = league_avg
        self._sample = sample

    def multiplier(self, opponent_id: int, position: str) -> float:
        return self._mult.get((opponent_id, position), 1.0)

    def is_soft(self, opponent_id: int, position: str) -> bool:
        return self.multiplier(opponent_id, position) >= SOFT_THRESHOLD

    def sample_size(self, opponent_id: int, position: str) -> int:
        return self._sample.get((opponent_id, position), 0)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute_dvp(all_logs: list[GameLog], weights: dict[str, float] | None = None) -> DvPTable:
    w = weights or DEFAULT_POINTS_SCORING

    # fantasy points allowed by (opponent, position) and league-wide by position.
    allowed: dict[tuple[int, str], list[float]] = defaultdict(list)
    league: dict[str, list[float]] = defaultdict(list)

    for lg in all_logs:
        fp = fantasy_points(lg.stats, w)
        allowed[(lg.opponent_id, lg.position)].append(fp)
        league[lg.position].append(fp)

    league_avg = {pos: (sum(v) / len(v) if v else 0.0) for pos, v in league.items()}

    mult: dict[tuple[int, str], float] = {}
    sample: dict[tuple[int, str], int] = {}
    for key, vals in allowed.items():
        _, pos = key
        n = len(vals)
        sample[key] = n
        base = league_avg.get(pos, 0.0)
        if base <= 0 or n == 0:
            mult[key] = 1.0
            continue
        raw = (sum(vals) / n) / base
        # Shrink toward 1.0 for small samples (linear up to MIN_SAMPLE).
        if n < MIN_SAMPLE:
            shrink = n / MIN_SAMPLE
            raw = 1.0 + (raw - 1.0) * shrink
        mult[key] = round(_clamp(raw, MULT_FLOOR, MULT_CEIL), 3)

    return DvPTable(mult, league_avg, sample)
