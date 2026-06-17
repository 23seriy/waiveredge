"""API endpoint tests using FastAPI TestClient.

These verify the HTTP-layer contract (status codes, response shapes, error
handling) for every public endpoint. The engine itself is tested in
test_scoring.py and test_categories.py; these tests confirm wiring.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "waiveredge"
    assert "has_api_key" in body


# ---------------------------------------------------------------------------
# GET /api/streamers
# ---------------------------------------------------------------------------

def test_streamers_returns_grid_and_players():
    resp = client.get("/api/streamers?top=5")
    assert resp.status_code == 200
    body = resp.json()
    assert "week" in body and "start" in body["week"] and "end" in body["week"]
    assert "schedule_grid" in body
    assert "streamers" in body
    assert len(body["streamers"]) <= 5

    # Schedule grid entries have required keys.
    for team in body["schedule_grid"]:
        assert "abbreviation" in team
        assert "games" in team
        assert isinstance(team["games"], int)
        assert "matchups" in team

    # Streamer entries have required keys.
    if body["streamers"]:
        s = body["streamers"][0]
        for key in ("player_id", "name", "position", "team", "n_games",
                    "fppg", "projected_total", "matchups"):
            assert key in s, f"Missing key '{key}' in streamer"


def test_streamers_sorted_by_projected_total():
    resp = client.get("/api/streamers?top=20")
    body = resp.json()
    totals = [s["projected_total"] for s in body["streamers"]]
    assert totals == sorted(totals, reverse=True), "Streamers should be sorted by projected_total desc"


def test_streamers_top_clamped_to_50():
    resp = client.get("/api/streamers?top=999")
    assert resp.status_code == 200
    assert len(resp.json()["streamers"]) <= 50


# ---------------------------------------------------------------------------
# POST /api/recommendations/manual — points mode
# ---------------------------------------------------------------------------

def test_manual_points_mode():
    resp = client.post("/api/recommendations/manual", json={
        "roster": ["Nikola Jokic", "Luka Doncic", "Trae Young"],
        "scoring_mode": "points",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["scoring_mode"] == "points"
    assert body["resolved_count"] == 3
    assert len(body["recommendations"]) > 0
    # Points-mode recs should NOT have category extras.
    rec = body["recommendations"][0]
    assert rec["total_z"] is None
    assert rec["per_cat_z"] is None
    assert "marginal" in rec and "rationale" in rec


def test_manual_categories_mode():
    resp = client.post("/api/recommendations/manual", json={
        "roster": ["Nikola Jokic", "Luka Doncic", "Trae Young"],
        "scoring_mode": "categories",
        "categories": ["pts", "reb", "ast", "stl", "blk", "fg3m", "turnover", "fg_pct", "ft_pct"],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["scoring_mode"] == "categories"
    assert len(body["recommendations"]) > 0
    rec = body["recommendations"][0]
    # Category-mode recs carry z-score extras.
    assert rec["total_z"] is not None
    assert isinstance(rec["per_cat_z"], dict)
    assert len(rec["per_cat_z"]) > 0


def test_manual_returns_unresolved_names():
    resp = client.post("/api/recommendations/manual", json={
        "roster": ["Nikola Jokic", "NotARealPlayer123"],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["resolved_count"] == 1
    assert "NotARealPlayer123" in body["unresolved"]


def test_manual_400_when_no_names_resolve():
    resp = client.post("/api/recommendations/manual", json={
        "roster": ["FakeName1", "FakeName2"],
    })
    assert resp.status_code == 400
    body = resp.json()
    assert "detail" in body


def test_manual_accent_folding():
    """Verify Jokić matches regardless of accent."""
    resp1 = client.post("/api/recommendations/manual", json={
        "roster": ["Nikola Jokic"],
    })
    resp2 = client.post("/api/recommendations/manual", json={
        "roster": ["Nikola Jokić"],
    })
    assert resp1.status_code == 200 and resp2.status_code == 200
    assert resp1.json()["resolved_count"] == resp2.json()["resolved_count"] == 1


def test_manual_default_scoring_mode_is_points():
    """When scoring_mode is omitted, default to points."""
    resp = client.post("/api/recommendations/manual", json={
        "roster": ["Nikola Jokic"],
    })
    assert resp.status_code == 200
    assert resp.json()["scoring_mode"] == "points"


# ---------------------------------------------------------------------------
# GET /api/recommendations/sample
# ---------------------------------------------------------------------------

def test_sample_points():
    resp = client.get("/api/recommendations/sample")
    assert resp.status_code == 200
    body = resp.json()
    assert body["scoring_mode"] == "points"
    assert len(body["recommendations"]) > 0


def test_sample_categories():
    resp = client.get("/api/recommendations/sample?mode=categories")
    assert resp.status_code == 200
    body = resp.json()
    assert body["scoring_mode"] == "categories"
    assert len(body["recommendations"]) > 0
    assert body["recommendations"][0]["total_z"] is not None


# ---------------------------------------------------------------------------
# Validation edge cases
# ---------------------------------------------------------------------------

def test_manual_empty_roster_rejected():
    resp = client.post("/api/recommendations/manual", json={
        "roster": [],
    })
    assert resp.status_code == 422  # Pydantic validation (min_length=1)


def test_manual_invalid_scoring_mode_rejected():
    resp = client.post("/api/recommendations/manual", json={
        "roster": ["Nikola Jokic"],
        "scoring_mode": "invalid_mode",
    })
    assert resp.status_code == 422  # Literal validation
