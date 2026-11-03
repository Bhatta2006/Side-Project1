"""Review queue controls (master prompt 9.6): reasons, snooze and bring-back, without touching
the evidence or the schedule itself."""

# ruff: noqa: F811
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.catalog.registry import default_catalog
from socrat.learn import service as learn
from socrat.mastery.model import DAY
from socrat.models import Enrollment, Evidence

CONCEPT = "zero:programs-and-output"


def _take_quiz(client, headers):
    client.post(f"/api/v1/activities/lesson:{CONCEPT}/complete", headers=headers)
    url = f"/api/v1/quiz/quiz:{CONCEPT}"
    quiz = client.get(url).json()
    answers = {q.id: q.shown(quiz["id"])["answer"] for q in default_catalog().concept(CONCEPT).quiz}
    for question in quiz["questions"]:
        body = {"item": question["id"], "choice": answers[question["id"]]}
        client.post(f"{url}/answer", json=body, headers=headers)


def test_queue_explains_each_review_and_a_snooze_moves_it_off_the_plan(client):
    headers = login(client)
    onboard(client, headers)
    assert client.get("/api/v1/reviews").json()["items"] == []
    _take_quiz(client, headers)

    item = next(i for i in client.get("/api/v1/reviews").json()["items"] if i["concept"] == CONCEPT)
    assert item["due"] is False and item["snoozed_until"] is None
    assert "spaces the next review" in item["reason"]
    with Session(client.app.state.engine) as db:
        evidence_before = len(db.scalars(select(Evidence)).all())
        state_before = learn.states_for(db, db.scalars(select(Enrollment)).one())[CONCEPT]

    held = client.post(f"/api/v1/reviews/{CONCEPT}/snooze", json={"days": 14}, headers=headers)
    assert held.status_code == 200 and held.json()["snoozed_until"] > item["due_at"]
    listed = next(
        i for i in client.get("/api/v1/reviews").json()["items"] if i["concept"] == CONCEPT
    )
    assert listed["snoozed_until"] == held.json()["snoozed_until"]

    # The schedule and the evidence are untouched: a snooze is only a plan override.
    with Session(client.app.state.engine) as db:
        assert len(db.scalars(select(Evidence)).all()) == evidence_before
        state = learn.states_for(db, db.scalars(select(Enrollment)).one())[CONCEPT]
        assert state.next_review_at == state_before.next_review_at

    back = client.delete(f"/api/v1/reviews/{CONCEPT}/snooze", headers=headers)
    assert back.json()["snoozed_until"] is None
    assert client.get("/api/v1/reviews").json()["items"][0]["snoozed_until"] is None


def test_snooze_is_bounded_and_needs_a_scheduled_review(client):
    headers = login(client)
    onboard(client, headers)
    url = f"/api/v1/reviews/{CONCEPT}/snooze"
    assert client.post(url, json={"days": 1}, headers=headers).status_code == 404  # nothing due
    _take_quiz(client, headers)
    assert client.post(url, json={"days": 0}, headers=headers).status_code == 422
    assert client.post(url, json={"days": 15}, headers=headers).status_code == 422
    assert client.post(url, json={"days": 2}, headers=headers).status_code == 200


def test_reason_names_a_recent_miss():
    from socrat.learn.reviews import reason
    from socrat.mastery.model import ConceptState

    missed = ConceptState(failures=1, review_step=1, last_evidence_at=0)
    assert "missed it last time" in reason(missed, 3 * DAY)
    spaced = ConceptState(review_step=3, last_evidence_at=DAY)
    assert "7 days" in reason(spaced, 3 * DAY) and "2 days ago" in reason(spaced, 3 * DAY)


def test_planner_keeps_a_snoozed_review_off_until_the_snooze_ends():
    from datetime import date

    from socrat.mastery.model import ConceptState
    from socrat.planner.engine import Adaptive, build_plan

    cat = default_catalog()
    path = cat.course_concepts("zero")
    now, today = 1_000 * DAY, date(2026, 11, 2)  # a Monday
    done = ConceptState(alpha=20, beta=1, evidence_count=5, review_step=2, next_review_at=now)
    states = {q: done for q in path[:6]}
    completed = {f"lesson:{q}" for q in path[:6]}
    target = min(path[:6])  # equal due times are taken in name order, two a day

    def review_days(overrides: dict) -> list[int]:
        plan = build_plan(
            cat,
            path,
            states,
            completed,
            [],
            today,
            now,
            set(range(7)),
            60,
            course_id="zero",
            adaptive=Adaptive(course_id="zero", overrides=overrides),
        )
        return [
            n for n, d in enumerate(plan.days) for i in d["items"] if i["id"] == f"review:{target}"
        ]

    assert review_days({}) == [0]  # due today
    later = review_days({"snoozed": {target: now + 3 * DAY}})
    assert later and later[0] == 3  # back on the plan the day the snooze ends
    assert review_days({"snoozed": {target: now - DAY}}) == [0]  # an expired snooze is ignored
