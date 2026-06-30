"""Tests for transactional email + alert digest formatting (hermetic — no network)."""
import app.email as email_mod
from app.api.alerts import _format_alert_email


def test_send_email_noops_without_api_key(monkeypatch):
    monkeypatch.setattr(email_mod.settings, "resend_api_key", "")
    # Returns False and makes no HTTP call (would raise if it tried — no key path).
    assert email_mod.send_email("a@b.com", "subj", "<p>hi</p>") is False


def test_format_alert_email_lists_pickups_and_links():
    alerts = [
        {"pickup_player_name": "Backup Center", "pickup_rationale": "elevated role — Star (C) out"},
        {"pickup_player_name": "Backup Guard", "pickup_rationale": "elevated role — Point (PG) out"},
    ]
    subject, html = _format_alert_email("nba", connection_id=7, new_alerts=alerts)
    assert "2 injury pickups" in subject
    assert "NBA" in subject
    assert "Backup Center" in html and "Backup Guard" in html
    assert "/nba/alerts/7" in html


def test_format_alert_email_singular():
    subject, _ = _format_alert_email("mlb", 1, [{"pickup_player_name": "X", "pickup_rationale": "y"}])
    assert "1 injury pickup " in subject  # singular, no trailing 's'
