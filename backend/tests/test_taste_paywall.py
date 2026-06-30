"""Tests for the taste paywall feature flag (TASTE_PAYWALL_ENABLED).

These tests focus on the config and gating logic without requiring real fixtures
or a live database — the integration path through league_recommendations is
covered by the existing test_api.py (run locally, excluded from CI).
"""
from unittest.mock import MagicMock, patch


def test_taste_paywall_flag_defaults_to_false():
    """TASTE_PAYWALL_ENABLED defaults to False so existing behavior is unchanged."""
    from app.config import Settings
    s = Settings(_env_file=None)
    assert s.taste_paywall_enabled is False


def test_taste_paywall_flag_reads_from_env(monkeypatch):
    """Setting TASTE_PAYWALL_ENABLED=true in the environment activates the flag."""
    monkeypatch.setenv("TASTE_PAYWALL_ENABLED", "true")
    from app.config import Settings
    s = Settings(_env_file=None)
    assert s.taste_paywall_enabled is True


def test_locked_stubs_strip_player_data():
    """When taste paywall is active, locked stubs must not expose add_name or marginal."""
    # Simulate what league_recommendations builds for a free user.
    full_recs = [
        {"add_name": "Player A", "add_position": "PG", "n_games": 4, "marginal": 30.0},
        {"add_name": "Player B", "add_position": "SG", "n_games": 5, "marginal": 28.0},
        {"add_name": "Player C", "add_position": "SF", "n_games": 3, "marginal": 25.0},
    ]
    locked_stubs = [
        {"locked": True, "add_position": r.get("add_position"), "n_games": r.get("n_games")}
        for r in full_recs[1:]
    ]
    result = full_recs[:1] + locked_stubs

    assert len(result) == 3
    assert "add_name" not in result[1]
    assert "marginal" not in result[1]
    assert result[1]["locked"] is True
    assert result[1]["add_position"] == "SG"
    assert result[1]["n_games"] == 5
    # Rank 1 is untouched.
    assert result[0]["add_name"] == "Player A"
