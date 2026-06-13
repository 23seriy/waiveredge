"""Unit tests for the scoring core.

Runs with pytest (`python -m pytest`) OR standalone with stdlib only
(`python tests/test_scoring.py`) via the manual runner at the bottom.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.scoring.engine import (  # noqa: E402
    availability_prob,
    project_value,
    rank_waiver_adds,
    role_multiplier,
)
from app.scoring.matchups import MULT_CEIL, MULT_FLOOR, compute_dvp  # noqa: E402
from app.scoring.projections import project_player  # noqa: E402
from app.scoring.scoring_systems import fantasy_points  # noqa: E402
from app.scoring.types import GameLog, Injury, Player, Projection, ScheduledGame  # noqa: E402

SCORING = {"pts": 1.0, "reb": 1.0, "ast": 1.0, "stl": 1.0, "blk": 1.0, "turnover": -1.0}


def _log(pid, gid, date, team, opp, pos, **stats):
    return GameLog(pid, gid, date, team, opp, pos, stats)


def test_fantasy_points():
    line = {"pts": 20, "reb": 5, "ast": 5, "stl": 2, "blk": 1, "turnover": 3}
    # 20 + 5 + 5 + 2 + 1 - 3 = 30
    assert fantasy_points(line, SCORING) == 30.0


def test_recency_weighting():
    # Old games ~10 fp, most-recent game 40 fp -> projection pulled above the mean.
    logs = [
        _log(1, 1, "2026-06-01", 1, 2, "PG", pts=10),
        _log(1, 2, "2026-06-02", 1, 2, "PG", pts=10),
        _log(1, 3, "2026-06-10", 1, 2, "PG", pts=40),
    ]
    proj = project_player(logs, SCORING)
    assert proj.games_sampled == 3
    assert proj.fppg > 20.0  # recency lifts it above the simple mean of 20


def test_schedule_density_beats_talent():
    """The core invariant: a lower-talent player with more games this week wins."""
    # Player A: 30 fppg, team 1 plays 4 games. Player B: 40 fppg, team 2 plays 2.
    a = Player(1, "Volume Guy", 1, ["PG"])
    b = Player(2, "Star", 2, ["PG"])
    weak = Player(3, "Bench PG", 9, ["PG"])
    projections = {1: Projection(1, 30.0, 10), 2: Projection(2, 40.0, 10), 3: Projection(3, 10.0, 10)}
    schedule = [
        ScheduledGame(101, "2026-06-15", 1, 5), ScheduledGame(102, "2026-06-16", 1, 6),
        ScheduledGame(103, "2026-06-17", 1, 7), ScheduledGame(104, "2026-06-18", 1, 8),
        ScheduledGame(105, "2026-06-15", 2, 5), ScheduledGame(106, "2026-06-18", 2, 6),
    ]
    window = ("2026-06-15", "2026-06-21")
    dvp = compute_dvp([], SCORING)  # neutral (all multipliers 1.0)
    players_by_team = {1: [a], 2: [b], 9: [weak]}

    recs = rank_waiver_adds([weak], [a, b], set(), projections, schedule, window,
                            dvp, {}, players_by_team)
    assert recs[0].add_player_id == 1, "4-game player should outrank the higher-fppg 2-game star"
    # Sanity: 30*4=120 > 40*2=80
    assert recs[0].add_value == 120.0
    assert [r for r in recs if r.add_player_id == 2][0].add_value == 80.0


def test_role_multiplier_triggers_on_same_position_out():
    backup = Player(10, "Backup C", 5, ["C"])
    starter = Player(11, "Starter C", 5, ["C"])
    pbt = {5: [backup, starter]}
    injuries = {11: Injury(11, "Out", "ankle")}
    mult, note = role_multiplier(backup, injuries, pbt)
    assert mult > 1.0
    assert "Starter C" in note
    # No bump when the injured teammate plays a different position.
    other = {12: Injury(12, "Out")}
    pbt2 = {5: [backup, Player(12, "Out PG", 5, ["PG"])]}
    assert role_multiplier(backup, other, pbt2)[0] == 1.0


def test_availability_out_zeroes_value():
    assert availability_prob(1, {1: Injury(1, "Out")}) == 0.0
    assert availability_prob(1, {1: Injury(1, "Questionable")}) == 0.5
    assert availability_prob(1, {}) == 1.0

    p = Player(1, "Hurt", 1, ["SF"])
    sched = [ScheduledGame(1, "2026-06-15", 1, 2), ScheduledGame(2, "2026-06-17", 1, 3)]
    vr = project_value(p, Projection(1, 50.0, 10), sched, ("2026-06-15", "2026-06-21"),
                       compute_dvp([], SCORING), {1: Injury(1, "Out")}, {1: [p]})
    assert vr.value == 0.0  # ruled out -> no projected value despite 2 games


def test_dvp_is_clamped_and_centered():
    # One opponent (team 2) bleeds points to PGs; another (team 3) smothers them.
    logs = []
    for i in range(6):
        logs.append(_log(100 + i, i, f"2026-06-0{i+1}", 1, 2, "PG", pts=60))   # vs team 2: huge
        logs.append(_log(200 + i, i, f"2026-06-0{i+1}", 1, 3, "PG", pts=5))    # vs team 3: tiny
    dvp = compute_dvp(logs, SCORING)
    assert dvp.multiplier(2, "PG") <= MULT_CEIL
    assert dvp.multiplier(3, "PG") >= MULT_FLOOR
    assert dvp.multiplier(2, "PG") > dvp.multiplier(3, "PG")
    assert dvp.is_soft(2, "PG")



from app.recommendations import (  # noqa: E402
    _normalize_name,
    manual_recommendations,
    resolve_names,
)


def _engine_fixtures() -> dict:
    """Minimal real-shaped fixtures (test doubles) for engine-wiring tests.

    Three PGs: a strong free agent (Test Star), and two rostered players where
    Test Weak is the obvious drop. No network, no materialized data.
    """
    def line(pts, ast=3):
        return {"pts": pts, "reb": 4, "ast": ast, "stl": 1, "blk": 0, "fg3m": 2, "turnover": 2}

    logs = []
    for i, date in enumerate(("2026-01-10", "2026-01-12", "2026-01-14"), 1):
        logs.append({"player_id": 1, "game_id": f"g{i}", "date": date, "team_id": 2,
                     "opponent_id": 1, "position": "PG", "stats": line(40, 7)})
        logs.append({"player_id": 2, "game_id": f"g{i}", "date": date, "team_id": 1,
                     "opponent_id": 2, "position": "PG", "stats": line(5, 1)})
        logs.append({"player_id": 3, "game_id": f"g{i}", "date": date, "team_id": 1,
                     "opponent_id": 2, "position": "PG", "stats": line(18, 3)})
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


def test_normalize_name_strips_punctuation_case_and_accents():
    assert _normalize_name("D'Angelo  Russell") == _normalize_name("dangelo russell")
    assert _normalize_name("  Tyrese Haliburton  ") == "tyrese haliburton"
    # Hyphens / periods don't break matching.
    assert _normalize_name("Karl-Anthony Towns Jr.") == "karlanthony towns jr"
    # Accents are folded so plain ASCII matches real NBA names.
    assert _normalize_name("Nikola Jokić") == _normalize_name("nikola jokic")
    assert _normalize_name("Luka Dončić") == "luka doncic"


def test_resolve_names_partitions_known_and_unknown():
    players = [
        {"id": 1, "name": "LeBron James"},
        {"id": 2, "name": "Stephen Curry"},
        {"id": 3, "name": "Nikola Jokić"},
    ]
    ids, unresolved = resolve_names(
        ["lebron james", "stephen  curry", "Nobody Real", "LeBron James"],  # dup at end
        players,
    )
    assert ids == [1, 2]  # dedupe preserves first-seen order
    assert unresolved == ["Nobody Real"]


def test_manual_recommendations_runs_engine_on_user_roster():
    # Inject test-double fixtures: Test Weak is the obvious drop; Test Star (a 2-game
    # free agent with a big projection) should be the top recommended add.
    result = manual_recommendations(
        roster_names=["Test Weak", "Test Mid"],
        droppable_names=[],
        fixtures=_engine_fixtures(),
    )
    assert result["resolved_count"] == 2
    assert result["unresolved"] == []
    assert result["week"]["start"] and result["week"]["end"]
    assert len(result["recommendations"]) > 0
    top = result["recommendations"][0]
    for key in ("add_player_id", "add_name", "marginal", "rationale"):
        assert key in top
    assert top["add_name"] == "Test Star"
    assert top["drop_name"] == "Test Weak"


def test_manual_recommendations_reports_unresolved():
    result = manual_recommendations(
        roster_names=["Test Weak", "Not A Real Player"],
        fixtures=_engine_fixtures(),
    )
    assert result["resolved_count"] == 1
    assert result["unresolved"] == ["Not A Real Player"]


# ---- manual runner so the suite runs without pytest -------------------------
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
