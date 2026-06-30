"""Tests for the production app_secret guard."""
import pytest

from app.config import Settings, _DEFAULT_APP_SECRET


def test_default_secret_allowed_in_development():
    s = Settings(environment="development", app_secret=_DEFAULT_APP_SECRET)
    assert s.app_secret == _DEFAULT_APP_SECRET


def test_default_secret_rejected_outside_development():
    with pytest.raises(ValueError):
        Settings(environment="production", app_secret=_DEFAULT_APP_SECRET)


def test_real_secret_allowed_in_production():
    s = Settings(environment="production", app_secret="a-real-random-secret")
    assert s.environment == "production"
