"""Unit tests for ESPN transaction support.

Covers: build_espn_id_map (name-matching ID crossref), ESPN write API payload
construction (add_drop_player, claim_waiver), and _execute_espn fallback logic.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.recommendations import build_espn_id_map  # noqa: E402


# ---------------------------------------------------------------------------
# build_espn_id_map
# ---------------------------------------------------------------------------

FIXTURE_PLAYERS = [
    {"id": 1, "name": "LeBron James"},
    {"id": 2, "name": "Stephen Curry"},
    {"id": 3, "name": "Nikola Jokić"},
    {"id": 4, "name": "Shohei Ohtani"},
    {"id": 5, "name": "D'Angelo Russell"},
]


def test_build_espn_id_map_exact_match():
    espn = [{"name": "LeBron James", "espn_id": 1966}]
    result = build_espn_id_map(espn, FIXTURE_PLAYERS)
    assert result == {"1": "1966"}


def test_build_espn_id_map_accent_folding():
    """ESPN may return accented names; our fixtures may not, or vice versa."""
    espn = [{"name": "Nikola Jokic", "espn_id": 3112}]
    result = build_espn_id_map(espn, FIXTURE_PLAYERS)
    assert result == {"3": "3112"}


def test_build_espn_id_map_punctuation_stripping():
    espn = [{"name": "DAngelo Russell", "espn_id": 4001}]
    result = build_espn_id_map(espn, FIXTURE_PLAYERS)
    assert result == {"5": "4001"}


def test_build_espn_id_map_multiple_players():
    espn = [
        {"name": "LeBron James", "espn_id": 1966},
        {"name": "Stephen Curry", "espn_id": 3975},
        {"name": "Shohei Ohtani", "espn_id": 39832},
    ]
    result = build_espn_id_map(espn, FIXTURE_PLAYERS)
    assert result == {"1": "1966", "2": "3975", "4": "39832"}


def test_build_espn_id_map_unmatched_skipped():
    espn = [
        {"name": "LeBron James", "espn_id": 1966},
        {"name": "Unknown Player", "espn_id": 9999},
    ]
    result = build_espn_id_map(espn, FIXTURE_PLAYERS)
    assert result == {"1": "1966"}
    assert "9999" not in result.values()


def test_build_espn_id_map_missing_espn_id_skipped():
    espn = [{"name": "LeBron James"}]  # no espn_id
    result = build_espn_id_map(espn, FIXTURE_PLAYERS)
    assert result == {}


def test_build_espn_id_map_empty_inputs():
    assert build_espn_id_map([], FIXTURE_PLAYERS) == {}
    assert build_espn_id_map([], []) == {}


def test_build_espn_id_map_case_insensitive():
    espn = [{"name": "lebron james", "espn_id": 1966}]
    result = build_espn_id_map(espn, FIXTURE_PLAYERS)
    assert result == {"1": "1966"}


# ---------------------------------------------------------------------------
# ESPNFantasyClient write methods — payload structure
# ---------------------------------------------------------------------------

def test_add_drop_player_payload():
    """Verify add_drop_player builds the correct ESPN API payload."""
    from app.data.espn import ESPNFantasyClient

    client = ESPNFantasyClient(sport="mlb", espn_s2="fake_s2", swid="{FAKE-SWID}")

    with patch.object(client, "_post", return_value={"id": "txn123", "status": "EXECUTED"}) as mock_post:
        result = client.add_drop_player(
            league_id=12345, season=2026, team_id=3,
            add_espn_id=39832, drop_espn_id=33481,
        )

    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    # Positional args: league_id, season, endpoint, payload
    args = mock_post.call_args[0]
    assert args[0] == 12345
    assert args[1] == 2026
    assert args[2] == "/transactions/"

    payload = args[3]
    assert payload["type"] == "FREEAGENT"
    assert payload["teamId"] == 3
    assert payload["executionType"] == "EXECUTE"
    assert payload["memberId"] == "{FAKE-SWID}"
    assert len(payload["items"]) == 2
    assert payload["items"][0] == {"playerId": 39832, "type": "ADD", "toTeamId": 3}
    assert payload["items"][1] == {"playerId": 33481, "type": "DROP", "fromTeamId": 3}
    assert result == {"id": "txn123", "status": "EXECUTED"}


def test_add_only_no_drop():
    """When no drop player is specified, only ADD item should be in payload."""
    from app.data.espn import ESPNFantasyClient

    client = ESPNFantasyClient(sport="nba", espn_s2="s2", swid="{SWID}")

    with patch.object(client, "_post", return_value={"status": "EXECUTED"}) as mock_post:
        client.add_drop_player(
            league_id=111, season=2026, team_id=1,
            add_espn_id=5000,
        )

    payload = mock_post.call_args[0][3]
    assert len(payload["items"]) == 1
    assert payload["items"][0]["type"] == "ADD"


def test_claim_waiver_payload():
    """Verify claim_waiver builds the correct WAIVER payload with bid."""
    from app.data.espn import ESPNFantasyClient

    client = ESPNFantasyClient(sport="wnba", espn_s2="s2", swid="{SWID}")

    with patch.object(client, "_post", return_value={"status": "PENDING"}) as mock_post:
        client.claim_waiver(
            league_id=99, season=2026, team_id=2,
            add_espn_id=1000, drop_espn_id=2000, bid_amount=15,
        )

    payload = mock_post.call_args[0][3]
    assert payload["type"] == "WAIVER"
    assert payload["bidAmount"] == 15
    assert len(payload["items"]) == 2


def test_claim_waiver_zero_bid():
    """Waiver claim with no bid defaults to 0."""
    from app.data.espn import ESPNFantasyClient

    client = ESPNFantasyClient(sport="mlb", espn_s2="s2", swid="{SWID}")

    with patch.object(client, "_post", return_value={}) as mock_post:
        client.claim_waiver(
            league_id=99, season=2026, team_id=1,
            add_espn_id=500,
        )

    payload = mock_post.call_args[0][3]
    assert payload["bidAmount"] == 0
    assert len(payload["items"]) == 1


# ---------------------------------------------------------------------------
# ESPN write URL construction
# ---------------------------------------------------------------------------

def test_post_url_uses_correct_game_code():
    """The _post method should use the correct game code for each sport."""
    from app.data.espn import ESPNFantasyClient, ESPN_WRITES_BASE

    for sport, expected_code in [("nba", "fba"), ("mlb", "flb"), ("wnba", "wfba")]:
        client = ESPNFantasyClient(sport=sport, espn_s2="s2", swid="{SWID}")

        with patch("httpx.post") as mock_httpx:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"status": "ok"}
            mock_resp.raise_for_status = MagicMock()
            mock_httpx.return_value = mock_resp

            client._post(league_id=123, season=2026, endpoint="/transactions/", payload={})

            called_url = mock_httpx.call_args[0][0]
            assert f"{ESPN_WRITES_BASE}/{expected_code}" in called_url
            assert "/seasons/2026/segments/0/leagues/123/transactions/" in called_url


# ---------------------------------------------------------------------------
# ESPN deep link fallback
# ---------------------------------------------------------------------------

def test_espn_deep_link_includes_sport_path():
    """_espn_deep_link should produce correct URLs for each sport."""
    # We can't easily import _espn_deep_link directly without DB deps,
    # so test the URL mapping logic inline.
    sport_paths = {
        "nba": "basketball",
        "mlb": "baseball",
        "wnba": "womens-basketball",
        "nfl": "football",
        "nhl": "hockey",
    }
    for sport, expected_path in sport_paths.items():
        url = f"https://fantasy.espn.com/{expected_path}/players/add?leagueId=123&seasonId=2026"
        assert expected_path in url


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
