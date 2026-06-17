"""Tests for the recommendations service layer.

Covers top_streamers(), manual_recommendations in both modes, and
build_recommendations dispatch logic — using the same test-double
fixtures pattern as test_scoring.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.recommendations import (  # noqa: E402
    build_recommendations,
    manual_recommendations,
    top_streamers,
)


def _fixtures() -> dict:
    """Minimal test-double fixtures with 3 players on 2 teams."""
    def line(pts, reb=4, ast=3, stl=1, blk=0, fg3m=2, turnover=2, fgm=5, fga=10, ftm=3, fta=4):
        return {"pts": pts, "reb": reb, "ast": ast, "stl": stl, "blk": blk,
                "fg3m": fg3m, "turnover": turnover, "fgm": fgm, "fga": fga, "ftm": ftm, "fta": fta}

    logs = []
    for i, date in enumerate(("2026-01-10", "2026-01-12", "2026-01-14"), 1):
        logs.append({"player_id": 1, "game_id": f"g{i}a", "date": date, "team_id": 2,
                     "opponent_id": 1, "position": "PG", "stats": line(40, ast=7)})
        logs.append({"player_id": 2, "game_id": f"g{i}b", "date": date, "team_id": 1,
                     "opponent_id": 2, "position": "PG", "stats": line(5, ast=1)})
        logs.append({"player_id": 3, "game_id": f"g{i}c", "date": date, "team_id": 1,
                     "opponent_id": 2, "position": "PG", "stats": line(18)})
    return {
        "teams": [{"id": 1, "abbreviation": "AAA", "full_name": "Team A"},
                  {"id": 2, "abbreviation": "BBB", "full_name": "Team B"}],
        "players": [{"id": 1, "name": "Test Star", "team_id": 2, "positions": ["PG"]},
                    {"id": 2, "name": "Test Weak", "team_id": 1, "positions": ["PG"]},
                    {"id": 3, "name": "Test Mid", "team_id": 1, "positions": ["PG"]}],
        "game_logs": logs,
        "schedule": [{"id": "w1", "date": "2026-01-20", "home_team_id": 2, "visitor_team_id": 1},
                     {"id": "w2", "date": "2026-01-22", "home_team_id": 1, "visitor_team_id": 2}],
        "injuries": [],
        "roster": {"week_start": "2026-01-19", "week_end": "2026-01-25",
                   "scoring": {"pts": 1.0, "reb": 1.2, "ast": 1.5, "stl": 3.0, "blk": 3.0,
                               "fg3m": 0.5, "turnover": -1.0},
                   "roster": [], "free_agents": [], "droppable": []},
    }


# ---------------------------------------------------------------------------
# build_recommendations
# ---------------------------------------------------------------------------

def test_build_recommendations_points_mode():
    fx = _fixtures()
    fx["roster"]["roster"] = [{"player_id": 2, "slot": "PG"}, {"player_id": 3, "slot": "PG"}]
    fx["roster"]["free_agents"] = [1]
    fx["roster"]["droppable"] = [2, 3]
    recs = build_recommendations(fx)
    assert len(recs) == 1
    assert recs[0]["add_name"] == "Test Star"
    assert recs[0]["total_z"] is None  # points mode


def test_build_recommendations_categories_mode():
    fx = _fixtures()
    fx["roster"]["mode"] = "categories"
    fx["roster"]["categories"] = ["pts", "ast", "stl"]
    fx["roster"]["roster"] = [{"player_id": 2, "slot": "PG"}, {"player_id": 3, "slot": "PG"}]
    fx["roster"]["free_agents"] = [1]
    fx["roster"]["droppable"] = [2, 3]
    recs = build_recommendations(fx)
    assert len(recs) == 1
    assert recs[0]["total_z"] is not None
    assert isinstance(recs[0]["per_cat_z"], dict)


# ---------------------------------------------------------------------------
# manual_recommendations — category mode wiring
# ---------------------------------------------------------------------------

def test_manual_recommendations_categories_mode():
    result = manual_recommendations(
        roster_names=["Test Weak", "Test Mid"],
        fixtures=_fixtures(),
        scoring_mode="categories",
        categories=["pts", "ast", "stl"],
    )
    assert result["scoring_mode"] == "categories"
    assert result["resolved_count"] == 2
    assert len(result["recommendations"]) > 0
    rec = result["recommendations"][0]
    assert rec["total_z"] is not None
    assert rec["add_name"] == "Test Star"


def test_manual_recommendations_default_mode_is_points():
    result = manual_recommendations(
        roster_names=["Test Weak"],
        fixtures=_fixtures(),
    )
    assert result["scoring_mode"] == "points"


# ---------------------------------------------------------------------------
# top_streamers — shape validation (uses real fixtures)
# ---------------------------------------------------------------------------

def test_top_streamers_returns_expected_shape():
    result = top_streamers(top_n=5)
    assert "week" in result
    assert "schedule_grid" in result
    assert "streamers" in result
    assert len(result["streamers"]) <= 5

    # Each streamer has the required fields.
    for s in result["streamers"]:
        assert s["n_games"] > 0
        assert s["fppg"] >= 10  # our filter threshold
        assert s["projected_total"] > 0
        assert isinstance(s["matchups"], list)


def test_top_streamers_sorted_descending():
    result = top_streamers(top_n=20)
    totals = [s["projected_total"] for s in result["streamers"]]
    assert totals == sorted(totals, reverse=True)


def test_top_streamers_schedule_grid_sorted_by_games():
    result = top_streamers(top_n=1)
    games = [t["games"] for t in result["schedule_grid"]]
    assert games == sorted(games, reverse=True)


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
