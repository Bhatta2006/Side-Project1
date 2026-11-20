"""The end of a session (item 3): the server picks and orders the screens. Evidence leads, the
streak shows once a day, a fresh badge once ever, and the next step closes. Showing screens
never changes what counts."""

# ruff: noqa: F811
import pytest
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.config import Settings
from socrat.learn import achievements, session_end

LESSON = "lesson:basics:values"


@pytest.fixture
def enabled(client):
    settings = client.app.state.settings
    settings.session_end_enabled = True
    yield client
    settings.session_end_enabled = False


def finish_lesson(client, headers):
    assert client.post(f"/api/v1/activities/{LESSON}/complete", headers=headers).json()["completed"]


def end(client, headers, activity=LESSON):
    return client.post("/api/v1/session-end", json={"activity": activity}, headers=headers)


def test_defaults_off_and_hidden(client):
    assert Settings().session_end_enabled is False
    assert client.get("/api/v1/features").json()["session_end"] is False
    headers = login(client)
    onboard(client, headers)
    assert end(client, headers).status_code == 404


def test_evidence_leads_streak_once_a_day_next_closes(enabled):
    client = enabled
    headers = login(client)
    onboard(client, headers)
    finish_lesson(client, headers)

    first = end(client, headers).json()
    kinds = [s["kind"] for s in first["screens"]]
    assert first["arrangement"] == session_end.ARRANGEMENT
    assert kinds[0] == "evidence" and kinds[-1] == "next" and "streak" in kinds
    evidence = first["screens"][0]
    assert evidence["concept"] == "basics:values" and evidence["title"]
    assert evidence["status"] in {"mastered", "shown_alone", "building"}
    streak = next(s for s in first["screens"] if s["kind"] == "streak")
    assert streak["current"] == 1 and streak["first_day"] is True
    assert len(streak["week"]) == 7 and sum(d["today"] for d in streak["week"]) == 1
    assert next(d for d in streak["week"] if d["today"])["studied"] is True
    assert first["screens"][-1]["activity"]["id"] != LESSON  # the lesson is done; what is next

    again = end(client, headers).json()
    assert [s["kind"] for s in again["screens"]] == ["evidence", "next"]  # streak shown already


def test_no_streak_screen_before_studying_today(enabled):
    client = enabled
    headers = login(client)
    onboard(client, headers)
    kinds = [s["kind"] for s in end(client, headers).json()["screens"]]
    assert kinds == ["evidence", "next"]


def test_unknown_activity_still_ends_cleanly(enabled):
    client = enabled
    headers = login(client)
    onboard(client, headers)
    screens = end(client, headers, "checkpoint:basics:start").json()["screens"]
    assert screens[0] == {"kind": "evidence", "concept": None, "title": None, "status": None}


def test_needs_the_csrf_token(enabled):
    client = enabled
    headers = login(client)
    onboard(client, headers)
    response = client.post(
        "/api/v1/session-end", json={"activity": LESSON}, headers={"Origin": headers["Origin"]}
    )
    assert response.status_code == 403


def test_a_fresh_badge_is_shown_once(enabled, monkeypatch):
    client = enabled
    headers = login(client)
    onboard(client, headers)
    stamp = {"at": None}

    def fake(db, catalog, user, enrollment, longest):
        return [
            dict(
                id="first-steps",
                title="First steps",
                description="Finished a lesson",
                goal=1,
                value=1,
                earned=True,
                earned_at=stamp["at"],
            ),
            dict(
                id="old",
                title="Old",
                description="Long ago",
                goal=1,
                value=1,
                earned=True,
                earned_at=1,
            ),
        ]

    monkeypatch.setattr(achievements, "for_learner", fake)
    from socrat.models import now

    stamp["at"] = now()
    badges = [s for s in end(client, headers).json()["screens"] if s["kind"] == "badge"]
    assert [b["id"] for b in badges] == ["first-steps"]
    assert not [s for s in end(client, headers).json()["screens"] if s["kind"] == "badge"]
