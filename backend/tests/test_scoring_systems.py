"""Tests for scoring_systems.py — LeagueScoring, league_from_sport_config, constants."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.scoring.scoring_systems import (  # noqa: E402
    CATEGORY_META,
    NBA_DEFAULT_POINTS_SCORING,
    NINE_CAT,
    RAW_STATS,
    LeagueScoring,
    fantasy_points,
    league_from_sport_config,
)


# Minimal SportConfig stub for tests — mirrors app.sports.SportConfig structure.
@dataclass
class _FakeSportConfig:
    default_points_scoring: dict = field(default_factory=lambda: dict(NBA_DEFAULT_POINTS_SCORING))
    default_categories: tuple = NINE_CAT
    category_meta: dict = field(default_factory=lambda: dict(CATEGORY_META))


_NBA_CFG = _FakeSportConfig()
_MLB_CFG = _FakeSportConfig(
    default_points_scoring={"h": 1.0, "hr": 4.0, "rbi": 1.0},
    default_categories=("r", "hr", "rbi", "sb", "avg"),
    category_meta={"r": {"stat": "r"}, "hr": {"stat": "hr"}, "rbi": {"stat": "rbi"},
                   "sb": {"stat": "sb"}, "avg": {"percentage": True, "made": "h", "att": "ab"}},
)


def test_default_league_scoring_has_empty_weights():
    ls = LeagueScoring()
    assert ls.mode == "points"
    assert ls.weights == {}  # No silent NBA fallback


def test_league_from_sport_config_none_uses_sport_defaults():
    ls = league_from_sport_config(None, _NBA_CFG)
    assert ls.mode == "points"
    assert ls.weights == NBA_DEFAULT_POINTS_SCORING


def test_league_from_sport_config_mlb_none_uses_mlb_defaults():
    ls = league_from_sport_config(None, _MLB_CFG)
    assert ls.mode == "points"
    assert "hr" in ls.weights
    assert "pts" not in ls.weights  # No NBA leakage


def test_league_from_sport_config_points_explicit():
    ls = league_from_sport_config({"mode": "points", "weights": {"pts": 2.0}}, _NBA_CFG)
    assert ls.mode == "points"
    assert ls.weights["pts"] == 2.0


def test_league_from_sport_config_categories():
    ls = league_from_sport_config({"mode": "categories", "categories": ["pts", "reb", "ast"]}, _NBA_CFG)
    assert ls.mode == "categories"
    assert ls.categories == ["pts", "reb", "ast"]


def test_league_from_sport_config_categories_filters_invalid():
    ls = league_from_sport_config({"mode": "categories", "categories": ["pts", "NOT_REAL", "blk"]}, _NBA_CFG)
    assert "pts" in ls.categories
    assert "blk" in ls.categories
    assert "NOT_REAL" not in ls.categories


def test_league_from_sport_config_categories_default_when_empty():
    ls = league_from_sport_config({"mode": "categories", "categories": []}, _NBA_CFG)
    assert ls.categories == list(NINE_CAT)


def test_league_from_sport_config_mlb_categories_default():
    ls = league_from_sport_config({"mode": "categories", "categories": []}, _MLB_CFG)
    assert ls.categories == list(_MLB_CFG.default_categories)


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


# ---------------------------------------------------------------------------
# WNBA sport config
# ---------------------------------------------------------------------------

def test_wnba_sport_config_exists():
    from app.sports import get_sport
    wnba = get_sport("wnba")
    assert wnba.key == "wnba"
    assert wnba.active is True
    assert wnba.has_data is True
    assert "G" in wnba.positions
    assert "F" in wnba.positions
    assert "C" in wnba.positions


def test_wnba_default_scoring_is_basketball():
    from app.sports import get_sport
    wnba = get_sport("wnba")
    assert "pts" in wnba.default_points_scoring
    assert "reb" in wnba.default_points_scoring
    assert "ast" in wnba.default_points_scoring
    # Should NOT have baseball stats
    assert "hr" not in wnba.default_points_scoring
    assert "ip" not in wnba.default_points_scoring


def test_wnba_categories_are_nine_cat():
    from app.sports import get_sport
    wnba = get_sport("wnba")
    assert len(wnba.default_categories) == 9
    for cat in wnba.default_categories:
        assert cat in wnba.category_meta, f"{cat} missing from WNBA category_meta"


def test_wnba_league_from_sport_config_defaults():
    from app.sports import get_sport
    wnba = get_sport("wnba")
    ls = league_from_sport_config(None, wnba)
    assert ls.mode == "points"
    assert ls.weights == dict(wnba.default_points_scoring)


def test_wnba_espn_game_code():
    from app.data.espn import GAME_CODES
    assert GAME_CODES["wnba"] == "wfba"


def test_wnba_in_sport_dirs():
    from app.recommendations import SPORT_DIRS
    assert "wnba" in SPORT_DIRS
    assert "sample_data_wnba" in str(SPORT_DIRS["wnba"])


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
