"""The Daily Review (item 4): a recall half-life model orders practised concepts by how
likely they are forgotten. It reads evidence and changes nothing that counts."""

# ruff: noqa: F811
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.config import Settings
from socrat.learn import recall
from socrat.models import ConceptState as ConceptRow
from socrat.models import Enrollment, User, now

OLD = "basics:values"
FRESH = "basics:conditions"
DAY = recall.DAY


@pytest.fixture
def enabled(client):
    settings = client.app.state.settings
    settings.daily_review_enabled = True
    yield client
    settings.daily_review_enabled = False


def row(concept, score, at, assistance=0, kind="review"):
    return SimpleNamespace(
        concept=concept, kind=kind, score=score, assistance=assistance, created_at=at
    )


def add(client, concept, score, at, assistance=0):
    """Recorded the way the app records a review answer, so the schedule is real too."""
    from socrat.learn import service as learn

    with Session(client.app.state.engine) as db, db.begin():
        enrollment = db.scalar(select(Enrollment).order_by(Enrollment.created_at.desc()))
        learn.record_evidence(
            db, enrollment, concept, "review", score, f"review:{concept}", at, assistance
        )


def review(client, headers):
    response = client.get("/api/v1/daily-review", headers=headers)
    assert response.status_code == 200
    return response.json()


# The model


def test_half_life_matches_its_stated_calibration():
    assert recall.half_life(1, 0, 0) == pytest.approx(1.5, abs=0.1)
    assert recall.half_life(3, 0, 0) == pytest.approx(5.0, abs=0.3)
    assert recall.half_life(6, 0, 0) == pytest.approx(19.4, abs=1.0)


def test_help_counts_less_and_misses_shorten_it():
    alone, helped = recall.half_life(2, 0, 0), recall.half_life(0, 2, 0)
    assert helped < alone
    assert recall.half_life(2, 0, 3) < alone
    assert recall.MIN_HALF_LIFE <= recall.half_life(0, 0, 50)
    assert recall.half_life(500, 0, 0) == recall.MAX_HALF_LIFE


def test_recall_halves_at_the_half_life_and_tutor_flags_are_not_practice():
    t = 1_000_000
    folded = recall.fold([row("a", 1.0, t), row("a", 0.0, t + 5, kind="tutor")])
    item = folded["a"]
    assert (item.independent, item.misses, item.last_at) == (1, 0, t)
    assert item.chance(t) == 1.0
    assert item.chance(t + int(item.half_life_days * DAY)) == pytest.approx(0.5, abs=0.01)


def test_the_learners_forgetting_rate_scales_it_within_bounds():
    assert recall.half_life(3, 0, 0, scale=1.5) > recall.half_life(3, 0, 0)
    assert recall.half_life(3, 0, 0, scale=9) == recall.half_life(3, 0, 0, scale=1.5)


# The endpoint


def test_defaults_off_and_hidden(client):
    assert Settings().daily_review_enabled is False
    assert client.get("/api/v1/features").json()["daily_review"] is False
    headers = login(client)
    onboard(client, headers)
    assert client.get("/api/v1/daily-review", headers=headers).status_code == 404


def test_lists_what_has_faded_most_first_and_skips_what_is_fresh(enabled):
    client = enabled
    headers = login(client)
    onboard(client, headers)
    stamp = now()
    add(client, OLD, 1.0, stamp - 6 * DAY)
    add(client, "basics:text", 1.0, stamp - 3 * DAY)
    add(client, "basics:text", 1.0, stamp - 3 * DAY + 60)
    add(client, FRESH, 1.0, stamp - 60)

    body = review(client, headers)
    concepts = [i["concept"] for i in body["items"]]
    assert body["model"] == recall.MODEL
    assert concepts == [OLD, "basics:text"]  # least likely recalled first
    first = body["items"][0]
    assert first["activity"] == f"review:{OLD}"
    assert 0 < first["recall"] < body["items"][1]["recall"] < recall.SUCCESS + 0.2
    assert first["state"] == "probably faded"
    assert "6 days ago" in first["reason"] and "on your own 1 time" in first["reason"]
    assert body["refreshed_today"] == 1  # the fresh one was a review today


def test_a_snoozed_review_stays_off_the_list(enabled):
    client = enabled
    headers = login(client)
    onboard(client, headers)
    add(client, OLD, 1.0, now() - 6 * DAY)
    snooze = client.post(f"/api/v1/reviews/{OLD}/snooze", json={"days": 3}, headers=headers)
    assert snooze.status_code == 200
    assert review(client, headers)["items"] == []


def test_reading_the_list_changes_no_mastery_state(enabled):
    client = enabled
    headers = login(client)
    onboard(client, headers)
    add(client, OLD, 0.0, now() - 2 * DAY)

    def states():
        with Session(client.app.state.engine) as db:
            return sorted((r.concept, str(r.state)) for r in db.scalars(select(ConceptRow)))

    before = states()
    assert review(client, headers)["items"][0]["concept"] == OLD
    assert states() == before


def test_concepts_locked_by_the_plan_are_left_out(enabled, monkeypatch):
    from socrat import entitlements

    client = enabled
    headers = login(client)
    onboard(client, headers)
    add(client, OLD, 1.0, now() - 6 * DAY)
    monkeypatch.setattr(entitlements, "plan_locked", lambda *a: {OLD})
    assert review(client, headers)["items"] == []
    with Session(client.app.state.engine) as db:
        assert db.scalar(select(User))  # still signed in; nothing else changed


def test_adaptive_answers_count_once_even_without_evidence(enabled):
    """An adaptive review of unreviewed content writes no evidence, but it is still practice."""
    from socrat.models import Evidence, QuizResponse

    client = enabled
    headers = login(client)
    onboard(client, headers)
    stamp = now()
    add(client, OLD, 1.0, stamp - 6 * DAY)
    assert review(client, headers)["items"][0]["concept"] == OLD
    with Session(client.app.state.engine) as db, db.begin():
        enrollment = db.scalar(select(Enrollment).order_by(Enrollment.created_at.desc()))
        common = dict(enrollment_id=enrollment.id, concept=OLD, created_at=stamp - 30)
        db.add(
            QuizResponse(
                item_id="x", mode="review", pool="practice", correct=True, score=1.0, **common
            )
        )
        # Had the item been reviewed, the same answer would also be evidence: not counted twice.
        db.add(Evidence(kind="review", score=1.0, activity_id=f"adaptive:review:{OLD}", **common))

    body = review(client, headers)
    assert body["items"] == []  # refreshed just now
    assert body["refreshed_today"] == 1
    with Session(client.app.state.engine) as db:
        enrollment = db.scalar(select(Enrollment).order_by(Enrollment.created_at.desc()))
        item = recall.for_enrollment(db, enrollment)[OLD]
    assert item.independent == 2  # the recorded review and the adaptive answer, once
