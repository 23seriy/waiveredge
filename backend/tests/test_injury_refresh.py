"""Tests for the lightweight NBA injury-only refresh (hermetic — no network)."""
import json

import app.data.espn_injuries as espn_injuries
from app.recommendations import refresh_nba_injuries


def test_writes_injuries_json_from_feed(tmp_path, monkeypatch):
    (tmp_path / "players.json").write_text(json.dumps([
        {"id": 1, "name": "Star Player", "team_id": 10, "positions": ["C"]},
    ]))
    monkeypatch.setattr(
        espn_injuries, "fetch_nba_injuries",
        lambda players: [{"player_id": 1, "status": "out", "note": "ankle"}],
    )

    count = refresh_nba_injuries(data_dir=tmp_path)

    assert count == 1
    written = json.loads((tmp_path / "injuries.json").read_text())
    assert written == [{"player_id": 1, "status": "out", "note": "ankle"}]


def test_noop_when_no_fixtures(tmp_path, monkeypatch):
    # players.json absent -> skip without calling the feed or writing.
    called = False

    def _should_not_run(players):
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(espn_injuries, "fetch_nba_injuries", _should_not_run)
    assert refresh_nba_injuries(data_dir=tmp_path) == 0
    assert called is False
    assert not (tmp_path / "injuries.json").exists()
