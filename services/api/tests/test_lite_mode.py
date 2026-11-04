"""Lite mode (Phase 6): the web app holds heavy parts on slow connections only when the server
offers it, so the flag must default off and be visible in /features."""

# ruff: noqa: F811
from test_learner_api import client  # noqa: F401

from socrat.config import Settings


def test_lite_mode_defaults_off():
    assert Settings().lite_mode_enabled is False


def test_features_report_lite_mode(client):
    settings = client.app.state.settings
    assert client.get("/api/v1/features").json()["lite_mode"] is False
    settings.lite_mode_enabled = True
    try:
        assert client.get("/api/v1/features").json()["lite_mode"] is True
    finally:
        settings.lite_mode_enabled = False
