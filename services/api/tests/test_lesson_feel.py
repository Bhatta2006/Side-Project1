"""Lesson feel (item 2): a web-only change to how answers feel. It must default off, show in
/features, and never change what is recorded: the practice round of missed questions runs in
the browser and sends nothing."""

# ruff: noqa: F811
from test_learner_api import client  # noqa: F401

from socrat.config import Settings


def test_lesson_feel_defaults_off():
    assert Settings().lesson_feel_enabled is False


def test_features_report_lesson_feel(client):
    settings = client.app.state.settings
    assert client.get("/api/v1/features").json()["lesson_feel"] is False
    settings.lesson_feel_enabled = True
    try:
        assert client.get("/api/v1/features").json()["lesson_feel"] is True
    finally:
        settings.lesson_feel_enabled = False
