"""Tests for ESPN connect account-key derivation."""
from app.api.espn import _espn_user_email


def test_same_league_different_teams_get_distinct_accounts():
    a = _espn_user_email("nba", "123456", team_id=1)
    b = _espn_user_email("nba", "123456", team_id=2)
    assert a != b


def test_email_includes_sport_and_league_and_team():
    email = _espn_user_email("mlb", "987", team_id=4)
    assert email == "espn-mlb-987-t4@waiveredge.local"


def test_missing_team_id_omits_team_suffix():
    email = _espn_user_email("wnba", "55", team_id=None)
    assert email == "espn-wnba-55@waiveredge.local"
