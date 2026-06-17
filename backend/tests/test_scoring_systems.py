"""Tests for scoring_systems.py — LeagueScoring, league_from_config, constants."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.scoring.scoring_systems import (  # noqa: E402
    CATEGORY_META,
    DEFAULT_POINTS_SCORING,
    NINE_CAT,
    RAW_STATS,
    LeagueScoring,
    fantasy_points,
    league_from_config,
)


def test_default_league_scoring_is_points():
    ls = LeagueScoring()
    assert ls.mode == "points"
    assert ls.weights == DEFAULT_POINTS_SCORING


def test_league_from_config_none_returns_default():
    ls = league_from_config(None)
    assert ls.mode == "points"


def test_league_from_config_points_explicit():
    ls = league_from_config({"mode": "points", "weights": {"pts": 2.0}})
    assert ls.mode == "points"
    assert ls.weights["pts"] == 2.0


def test_league_from_config_categories():
    ls = league_from_config({"mode": "categories", "categories": ["pts", "reb", "ast"]})
    assert ls.mode == "categories"
    assert ls.categories == ["pts", "reb", "ast"]


def test_league_from_config_categories_filters_invalid():
    ls = league_from_config({"mode": "categories", "categories": ["pts", "NOT_REAL", "blk"]})
    assert "pts" in ls.categories
    assert "blk" in ls.categories
    assert "NOT_REAL" not in ls.categories


def test_league_from_config_categories_default_when_empty():
    ls = league_from_config({"mode": "categories", "categories": []})
    assert ls.categories == list(NINE_CAT)


def test_nine_cat_matches_category_meta():
    for cat in NINE_CAT:
        assert cat in CATEGORY_META, f"{cat} in NINE_CAT but not in CATEGORY_META"


def test_raw_stats_are_strings():
    for s in RAW_STATS:
        assert isinstance(s, str)


def test_fantasy_points_ignores_unknown_stats():
    line = {"pts": 10, "made_up_stat": 999}
    # made_up_stat should be ignored, not crash.
    assert fantasy_points(line, {"pts": 1.0}) == 10.0


def test_fantasy_points_handles_none_values():
    line = {"pts": None, "reb": 5}
    # None should be treated as 0.
    assert fantasy_points(line, {"pts": 1.0, "reb": 1.0}) == 5.0


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
