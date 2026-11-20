"""Daybreak game moments: a web-only layer over evidence the server already holds. It must
default off and show in /features."""

# ruff: noqa: F811
from test_learner_api import client  # noqa: F401

from socrat.config import Settings


def test_game_moments_defaults_off():
    assert Settings().game_moments_enabled is False


def test_features_report_game_moments(client):
    settings = client.app.state.settings
    assert client.get("/api/v1/features").json()["game_moments"] is False
    settings.game_moments_enabled = True
    try:
        assert client.get("/api/v1/features").json()["game_moments"] is True
    finally:
        settings.game_moments_enabled = False
