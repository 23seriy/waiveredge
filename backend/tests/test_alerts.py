"""Tests for injury-opportunity detection (hermetic — fixtures injected)."""
from app.api.alerts import _detect_injury_opportunities

FX = {
    "players": [
        {"id": 1, "name": "Starter Center", "team_id": 10, "positions": ["C"]},
        {"id": 2, "name": "Backup Center", "team_id": 10, "positions": ["C"]},
        {"id": 3, "name": "Other Guard", "team_id": 11, "positions": ["PG"]},
    ],
    "injuries": [{"player_id": 1, "status": "out", "note": "knee"}],
}


def test_out_starter_creates_pickup_for_fa_teammate():
    opps = _detect_injury_opportunities("nba", roster_player_ids=set(),
                                        free_agent_ids=[2], fx=FX)
    assert len(opps) == 1
    assert opps[0]["injured_player_id"] == 1
    assert opps[0]["pickup_player_id"] == 2


def test_no_opportunity_when_teammate_not_free_agent():
    opps = _detect_injury_opportunities("nba", roster_player_ids=set(),
                                        free_agent_ids=[], fx=FX)
    assert opps == []


def test_no_opportunity_for_non_out_status():
    fx = {**FX, "injuries": [{"player_id": 1, "status": "questionable", "note": ""}]}
    opps = _detect_injury_opportunities("nba", roster_player_ids=set(),
                                        free_agent_ids=[2], fx=fx)
    assert opps == []


def test_no_opportunity_for_different_position():
    opps = _detect_injury_opportunities("nba", roster_player_ids=set(),
                                        free_agent_ids=[3], fx=FX)
    assert opps == []
