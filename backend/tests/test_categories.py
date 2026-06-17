"""Unit tests for the 9-category (z-score) engine.

Runs with pytest OR standalone (`python tests/test_categories.py`).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.scoring.categories import (  # noqa: E402
    Reference,
    _cat_raw,
    rank_category_adds,
)
from app.scoring.matchups import compute_dvp  # noqa: E402
from app.scoring.scoring_systems import RAW_STATS  # noqa: E402
from app.scoring.types import Player, Projection, ScheduledGame  # noqa: E402

WINDOW = ("2026-01-01", "2026-01-07")
NEUTRAL_DVP = compute_dvp([])  # all multipliers 1.0, nothing soft


def _proj(pid: int, **per_game) -> Projection:
    pg = {s: 0.0 for s in RAW_STATS}
    pg.update(per_game)
    return Projection(pid, 0.0, 10, pg)


def test_counting_z_sign():
    # Pool spread on PTS; above-mean is positive z, below-mean negative.
    ref = Reference([{"pts": 10}, {"pts": 20}, {"pts": 30}], ["pts"])
    assert ref.z({"pts": 30}, "pts") > 0 > ref.z({"pts": 10}, "pts")


def test_pct_impact_is_volume_weighted():
    lp = {"fg_pct": 0.50}
    # Exactly league average -> zero impact regardless of volume.
    assert _cat_raw({"fga": 20, "fgm": 10}, "fg_pct", lp) == 0.0
    # Same +10% over league, but more attempts => more impact.
    hi_vol = _cat_raw({"fga": 20, "fgm": 12}, "fg_pct", lp)   # 60% on 20 att -> 2.0
    lo_vol = _cat_raw({"fga": 5, "fgm": 3}, "fg_pct", lp)     # 60% on 5 att  -> 0.5
    assert hi_vol > lo_vol > 0


def test_turnover_is_negated():
    # More turnovers is worse: high-TO gets negative z, low-TO positive.
    ref = Reference([{"turnover": 1}, {"turnover": 3}, {"turnover": 5}], ["turnover"])
    assert ref.z({"turnover": 5}, "turnover") < 0 < ref.z({"turnover": 1}, "turnover")


def test_schedule_density_lifts_category_value():
    # Two identical 20-ppg players; team 1 plays twice this week, team 2 once.
    fa_more = Player(1, "Four Game", 1, ["PG"])
    fa_less = Player(2, "Two Game", 2, ["PG"])
    weak = Player(3, "Bench", 9, ["PG"])
    projections = {1: _proj(1, pts=20), 2: _proj(2, pts=20), 3: _proj(3, pts=5)}
    schedule = [
        ScheduledGame(101, "2026-01-02", 1, 4), ScheduledGame(102, "2026-01-04", 1, 5),  # team1 x2
        ScheduledGame(103, "2026-01-03", 2, 6),                                           # team2 x1
        ScheduledGame(104, "2026-01-03", 9, 7),                                           # team9 x1
    ]
    pbt = {1: [fa_more], 2: [fa_less], 9: [weak]}
    recs = rank_category_adds([weak], [fa_more, fa_less], set(), projections, schedule,
                              WINDOW, NEUTRAL_DVP, {}, pbt, ["pts"])
    by_id = {r.add_player_id: r for r in recs}
    assert by_id[1].add_value > by_id[2].add_value, "2-game-week player should out-value the 1-game one"
    assert recs[0].add_player_id == 1


def test_weak_cats_surfaced_and_value_over_replacement():
    # Roster is pts-heavy but weak in stl/blk; FA is a stl/blk specialist.
    r1 = Player(1, "Scorer A", 1, ["PG"])
    r2 = Player(2, "Scorer B", 2, ["PG"])
    fa = Player(3, "Stocks Guy", 3, ["PG"])
    filler = Player(4, "Filler", 4, ["PG"])  # widens the reference distribution
    projections = {
        1: _proj(1, pts=32, stl=0.5, blk=0.3),
        2: _proj(2, pts=29, stl=0.6, blk=0.4),
        3: _proj(3, pts=11, stl=2.6, blk=2.2),
        4: _proj(4, pts=18, stl=1.2, blk=1.0),
    }
    schedule = [
        ScheduledGame(201, "2026-01-02", 1, 5), ScheduledGame(202, "2026-01-02", 2, 6),
        ScheduledGame(203, "2026-01-02", 3, 7), ScheduledGame(204, "2026-01-02", 4, 8),
    ]
    pbt = {1: [r1], 2: [r2], 3: [fa], 4: [filler]}
    recs = rank_category_adds(
        [r1, r2], [fa], set(), projections, schedule, WINDOW, NEUTRAL_DVP, {}, pbt,
        ["pts", "stl", "blk"], reference_players=[r1, r2, fa, filler],
    )
    rec = recs[0]
    assert rec.add_player_id == 3
    assert rec.total_z is not None and rec.per_cat_z is not None
    # The stl/blk specialist should be flagged as helping the roster's weak cats.
    assert "stl" in rec.helps and "blk" in rec.helps
    # Specialist's stl/blk z are clearly positive; pts z clearly negative.
    assert rec.per_cat_z["stl"] > 0 and rec.per_cat_z["blk"] > 0
    assert rec.per_cat_z["pts"] < 0
    # Drop is the weaker of the two rostered scorers (lower total z).
    assert rec.drop_player_id in (1, 2)


# ---- manual runner ----------------------------------------------------------
if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
