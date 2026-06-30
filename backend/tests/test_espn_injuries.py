"""Tests for the ESPN NBA injury parser (hermetic — no network)."""
from app.data.espn_injuries import parse_injuries

PLAYERS = [
    {"id": 100, "name": "Nikola Jokić", "team_id": 1, "positions": ["C"]},
    {"id": 200, "name": "Jock Landale", "team_id": 2, "positions": ["C"]},
    {"id": 300, "name": "LeBron James", "team_id": 3, "positions": ["F"]},
]


def _payload(items):
    return {"injuries": [{"id": "1", "displayName": "Team", "injuries": items}]}


def test_maps_status_from_type_description_and_matches_by_name():
    payload = _payload([
        {"athlete": {"displayName": "Jock Landale"},
         "type": {"description": "day-to-day"}, "shortComment": "ankle"},
    ])
    out = parse_injuries(payload, PLAYERS)
    assert out == [{"player_id": 200, "status": "day-to-day", "note": "ankle"}]


def test_accent_folded_match():
    payload = _payload([
        {"athlete": {"displayName": "Nikola Jokic"}, "type": {"description": "out"}},
    ])
    out = parse_injuries(payload, PLAYERS)
    assert out == [{"player_id": 100, "status": "out", "note": ""}]


def test_unmatched_athletes_are_dropped():
    payload = _payload([
        {"athlete": {"displayName": "Some Rookie"}, "type": {"description": "out"}},
    ])
    assert parse_injuries(payload, PLAYERS) == []


def test_status_falls_back_to_status_field_and_lowercases():
    payload = _payload([
        {"athlete": {"displayName": "LeBron James"}, "status": "Questionable"},
    ])
    out = parse_injuries(payload, PLAYERS)
    assert out == [{"player_id": 300, "status": "questionable", "note": ""}]


def test_blank_status_skipped():
    payload = _payload([{"athlete": {"displayName": "LeBron James"}}])
    assert parse_injuries(payload, PLAYERS) == []
