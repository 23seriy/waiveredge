"""Unit tests for matchups.py — DvPTable, compute_dvp, clamping, shrinkage.

Covers: empty logs, sample-size shrinkage, clamping bounds, neutral matchup,
is_soft/sample_size accessors, and multi-position handling.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.scoring.matchups import (  # noqa: E402
    MIN_SAMPLE,
    MULT_CEIL,
    MULT_FLOOR,
    SOFT_THRESHOLD,
    compute_dvp,
)
from app.scoring.types import GameLog  # noqa: E402

WEIGHTS = {"pts": 1.0}


def _log(pid, gid, date, team, opp, pos, **stats):
    return GameLog(pid, gid, date, team, opp, pos, stats)


def test_empty_logs_returns_neutral_dvp():
    dvp = compute_dvp([], WEIGHTS)
    assert dvp.multiplier(1, "PG") == 1.0
    assert dvp.multiplier(99, "C") == 1.0
    assert not dvp.is_soft(1, "PG")
    assert dvp.sample_size(1, "PG") == 0


def test_uniform_scoring_yields_neutral():
    # All games score 20 pts -> every (opp, pos) matches league avg -> mult = 1.0
    logs = [
        _log(1, 1, "2026-06-01", 1, 2, "PG", pts=20),
        _log(2, 2, "2026-06-01", 1, 3, "PG", pts=20),
        _log(3, 3, "2026-06-01", 1, 4, "PG", pts=20),
        _log(4, 4, "2026-06-02", 1, 2, "PG", pts=20),
        _log(5, 5, "2026-06-02", 1, 3, "PG", pts=20),
        _log(6, 6, "2026-06-02", 1, 4, "PG", pts=20),
    ]
    dvp = compute_dvp(logs, WEIGHTS)
    assert dvp.multiplier(2, "PG") == 1.0
    assert dvp.multiplier(3, "PG") == 1.0


def test_soft_and_tough_matchups():
    logs = []
    for i in range(6):
        # vs team 2: huge points -> soft
        logs.append(_log(100 + i, i, f"2026-06-0{i + 1}", 1, 2, "PG", pts=50))
        # vs team 3: tiny points -> tough
        logs.append(_log(200 + i, i + 100, f"2026-06-0{i + 1}", 1, 3, "PG", pts=5))
    dvp = compute_dvp(logs, WEIGHTS)
    assert dvp.multiplier(2, "PG") > 1.0
    assert dvp.multiplier(3, "PG") < 1.0
    assert dvp.is_soft(2, "PG")
    assert not dvp.is_soft(3, "PG")


def test_multiplier_clamped():
    logs = []
    for i in range(10):
        # vs team 2: absurdly high -> should clamp at MULT_CEIL
        logs.append(_log(100 + i, i, f"2026-06-0{min(i + 1, 9)}", 1, 2, "PG", pts=200))
        # vs team 3: near zero -> should clamp at MULT_FLOOR
        logs.append(_log(200 + i, i + 100, f"2026-06-0{min(i + 1, 9)}", 1, 3, "PG", pts=1))
    dvp = compute_dvp(logs, WEIGHTS)
    assert dvp.multiplier(2, "PG") == MULT_CEIL
    assert dvp.multiplier(3, "PG") == MULT_FLOOR


def test_sample_size_shrinkage():
    # With only 1 game (below MIN_SAMPLE), the multiplier is shrunk toward 1.0
    logs_small = [_log(1, 1, "2026-06-01", 1, 2, "PG", pts=50)]
    logs_large = [_log(i, i, f"2026-06-0{min(i + 1, 9)}", 1, 2, "PG", pts=50) for i in range(MIN_SAMPLE + 2)]
    # Add the same league baseline: more games at league avg to create contrast
    for i in range(MIN_SAMPLE + 2):
        logs_small.append(_log(100 + i, 100 + i, f"2026-06-0{min(i + 1, 9)}", 1, 3, "PG", pts=20))
        logs_large.append(_log(100 + i, 100 + i, f"2026-06-0{min(i + 1, 9)}", 1, 3, "PG", pts=20))

    dvp_small = compute_dvp(logs_small, WEIGHTS)
    dvp_large = compute_dvp(logs_large, WEIGHTS)
    # Both should show team 2 as soft, but the small-sample one is shrunk closer to 1.0
    small_mult = dvp_small.multiplier(2, "PG")
    large_mult = dvp_large.multiplier(2, "PG")
    assert small_mult < large_mult or small_mult == MULT_CEIL, \
        "Small sample should be shrunk closer to 1.0 than large sample"


def test_sample_size_accessor():
    logs = [
        _log(1, 1, "2026-06-01", 1, 2, "PG", pts=20),
        _log(2, 2, "2026-06-02", 1, 2, "PG", pts=25),
    ]
    dvp = compute_dvp(logs, WEIGHTS)
    assert dvp.sample_size(2, "PG") == 2
    assert dvp.sample_size(99, "C") == 0  # no data for this combo


def test_different_positions_tracked_separately():
    logs = [
        _log(1, 1, "2026-06-01", 1, 2, "PG", pts=50),
        _log(1, 1, "2026-06-02", 1, 2, "PG", pts=50),
        _log(1, 1, "2026-06-03", 1, 2, "PG", pts=50),
        _log(2, 2, "2026-06-01", 1, 2, "C", pts=10),
        _log(2, 2, "2026-06-02", 1, 2, "C", pts=10),
        _log(2, 2, "2026-06-03", 1, 2, "C", pts=10),
    ]
    dvp = compute_dvp(logs, WEIGHTS)
    pg_mult = dvp.multiplier(2, "PG")
    c_mult = dvp.multiplier(2, "C")
    # PG avg = 50, C avg = 10. league PG avg = 50, league C avg = 10.
    # Both at league avg -> both neutral
    assert pg_mult == 1.0
    assert c_mult == 1.0


def test_soft_threshold_constant():
    assert SOFT_THRESHOLD > 1.0
    assert MULT_CEIL >= SOFT_THRESHOLD


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
