"""Unit tests for projections.py — project_player and project_all.

Covers edge cases: empty logs, single game, recency decay behavior,
per-game stat aggregation, and project_all batch.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.scoring.projections import RECENCY_DECAY, project_all, project_player  # noqa: E402
from app.scoring.types import GameLog  # noqa: E402

WEIGHTS = {"pts": 1.0, "reb": 1.0, "ast": 1.0}


def _log(pid, gid, date, **stats):
    return GameLog(pid, gid, date, team_id=1, opponent_id=2, position="PG", stats=stats)


def test_empty_logs_returns_zero():
    proj = project_player([], WEIGHTS)
    assert proj.player_id == -1
    assert proj.fppg == 0.0
    assert proj.games_sampled == 0
    assert proj.per_game == {}


def test_single_log():
    logs = [_log(1, 1, "2026-06-01", pts=20, reb=5, ast=5)]
    proj = project_player(logs, WEIGHTS)
    assert proj.player_id == 1
    assert proj.fppg == 30.0  # 20 + 5 + 5
    assert proj.games_sampled == 1


def test_equal_logs_average():
    logs = [
        _log(1, 1, "2026-06-01", pts=10, reb=0, ast=0),
        _log(1, 2, "2026-06-02", pts=10, reb=0, ast=0),
    ]
    proj = project_player(logs, WEIGHTS)
    assert proj.fppg == 10.0  # identical -> average is 10


def test_recency_weights_recent_game_higher():
    # Old game: 10 fp, recent game: 40 fp -> projection > simple mean (25)
    logs = [
        _log(1, 1, "2026-06-01", pts=10, reb=0, ast=0),
        _log(1, 2, "2026-06-10", pts=40, reb=0, ast=0),
    ]
    proj = project_player(logs, WEIGHTS)
    simple_mean = 25.0
    assert proj.fppg > simple_mean, "Recency decay should weight the newer game higher"


def test_recency_weights_old_game_higher():
    # Old game: 40 fp, recent game: 10 fp -> projection < simple mean (25)
    logs = [
        _log(1, 1, "2026-06-01", pts=40, reb=0, ast=0),
        _log(1, 2, "2026-06-10", pts=10, reb=0, ast=0),
    ]
    proj = project_player(logs, WEIGHTS)
    simple_mean = 25.0
    assert proj.fppg < simple_mean, "Recency decay should pull toward the newer (lower) game"


def test_per_game_stats_populated():
    logs = [
        _log(1, 1, "2026-06-01", pts=20, reb=10, ast=5),
    ]
    proj = project_player(logs, WEIGHTS)
    assert "pts" in proj.per_game
    assert proj.per_game["pts"] == 20.0
    assert proj.per_game["reb"] == 10.0


def test_custom_decay():
    logs = [
        _log(1, 1, "2026-06-01", pts=0, reb=0, ast=0),
        _log(1, 2, "2026-06-10", pts=30, reb=0, ast=0),
    ]
    # decay=1.0 means no recency effect -> simple average
    proj = project_player(logs, WEIGHTS, decay=1.0)
    assert proj.fppg == 15.0  # (30 + 0) / 2

    # decay=0.0 means only the most recent game matters
    proj_recent = project_player(logs, WEIGHTS, decay=0.0)
    assert proj_recent.fppg == 30.0  # only the most recent game


def test_none_stat_values_treated_as_zero():
    logs = [_log(1, 1, "2026-06-01", pts=None, reb=5, ast=None)]
    proj = project_player(logs, WEIGHTS)
    assert proj.fppg == 5.0  # pts=0 + reb=5 + ast=0


def test_project_all_batch():
    logs_by_player = {
        1: [_log(1, 1, "2026-06-01", pts=20, reb=5, ast=5)],
        2: [_log(2, 2, "2026-06-01", pts=10, reb=3, ast=2)],
    }
    projs = project_all(logs_by_player, WEIGHTS)
    assert len(projs) == 2
    assert projs[1].fppg == 30.0
    assert projs[2].fppg == 15.0


def test_project_all_empty():
    projs = project_all({}, WEIGHTS)
    assert projs == {}


def test_mlb_weights():
    mlb_weights = {"h": 1.0, "hr": 4.0, "rbi": 1.0}
    logs = [_log(1, 1, "2026-06-01", h=2, hr=1, rbi=3)]
    proj = project_player(logs, mlb_weights)
    # 2*1 + 1*4 + 3*1 = 9
    assert proj.fppg == 9.0


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
