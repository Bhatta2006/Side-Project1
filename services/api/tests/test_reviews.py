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


# ---------------------------------------------------------------- across courses (prompt 9.6)


def _two_courses(client):
    """Ada finished some of Zero, then started CP; CP's fast-io builds on Zero's
    input-and-arithmetic. Review state is written directly: the schedule is the model's job."""
    import time

    from socrat.mastery.model import ConceptState
    from socrat.models import ConceptState as Row

    headers = login(client, subject="ada", name="Ada")
    onboard(client, headers)
    stamp = int(time.time())
    with Session(client.app.state.engine) as db, db.begin():
        zero = db.scalars(select(Enrollment)).one()
        zero.status, zero.active = "active", False
        db.query(Row).delete()  # only the schedule this test sets
        cp = Enrollment(
            user_id=zero.user_id,
            course_id="cp",
            language="python",
            level_id=zero.level_id,
            minutes_per_day=30,
            weekdays=[0, 1, 2, 3, 4, 5, 6],
            status="active",
            active=True,
        )
        db.add(cp)
        db.flush()
        due = ConceptState(
            evidence_count=3,
            review_step=2,
            last_evidence_at=stamp - 9 * DAY,
            next_review_at=stamp - 60,
        )
        later = ConceptState(
            evidence_count=2,
            review_step=1,
            last_evidence_at=stamp - DAY,
            next_review_at=stamp + 3 * DAY,
        )
        db.add(Row(enrollment_id=zero.id, concept="zero:input-and-arithmetic", state=due.to_dict()))
        db.add(Row(enrollment_id=zero.id, concept=CONCEPT, state=later.to_dict()))
        db.add(Row(enrollment_id=cp.id, concept=CONCEPT, state=due.to_dict()))
        db.add(Row(enrollment_id=cp.id, concept="cp:fast-io", state=later.to_dict()))
    return headers


def test_reviews_from_every_course_with_overlap_and_what_the_current_course_needs(client):
    headers = _two_courses(client)
    own = client.get("/api/v1/reviews").json()
    assert {i["concept"] for i in own["items"]} == {CONCEPT, "cp:fast-io"}  # active course only

    everywhere = client.get("/api/v1/reviews?scope=all").json()
    assert everywhere["scope"] == "all" and everywhere["daily_limit"] >= 1
    by = {i["concept"]: i for i in everywhere["items"]}
    assert set(by) == {CONCEPT, "cp:fast-io", "zero:input-and-arithmetic"}
    # Scheduled in both enrolments: listed once, at the earlier date, naming both courses.
    assert by[CONCEPT]["courses"] == ["cp", "zero"] and by[CONCEPT]["due"] is True
    needed = by["zero:input-and-arithmetic"]
    assert needed["builds_on"] is True and needed["current_course"] is False
    assert "builds on this" in needed["reason"] and needed["course"] == "zero"
    assert everywhere["due_now"] == 2
    # Due at the same time, the prerequisite the current course needs comes first.
    assert everywhere["items"][0]["concept"] == "zero:input-and-arithmetic"

    # Snoozing a review held by the paused course works, and bringing it back too.
    held = client.post(
        "/api/v1/reviews/zero:input-and-arithmetic/snooze", json={"days": 3}, headers=headers
    )
    assert held.status_code == 200
    listed = {i["concept"]: i for i in client.get("/api/v1/reviews?scope=all").json()["items"]}
    assert listed["zero:input-and-arithmetic"]["snoozed_until"] == held.json()["snoozed_until"]
    client.delete("/api/v1/reviews/zero:input-and-arithmetic/snooze", headers=headers)
    listed = {i["concept"]: i for i in client.get("/api/v1/reviews?scope=all").json()["items"]}
    assert listed["zero:input-and-arithmetic"]["snoozed_until"] is None


def test_concepts_placement_only_assumed_known_are_not_listed_as_reviews(client):
    """Found in a live run: a learner placed late had ten earlier concepts marked known without
    ever practising them, and the Reviews page listed all ten with reasons about practice that
    never happened. The planner already skipped them; the list must too."""
    import time

    from socrat.mastery.model import ConceptState, placed
    from socrat.models import ConceptState as Row

    headers = login(client)
    onboard(client, headers)
    stamp = int(time.time())
    with Session(client.app.state.engine) as db, db.begin():
        enrollment = db.scalars(select(Enrollment)).one()
        db.query(Row).delete()
        db.add(
            Row(enrollment_id=enrollment.id, concept=CONCEPT, state=placed(True, stamp).to_dict())
        )
        real = ConceptState(
            evidence_count=2,
            review_step=1,
            last_evidence_at=stamp - DAY,
            next_review_at=stamp + DAY,
        )
        db.add(
            Row(
                enrollment_id=enrollment.id,
                concept="zero:input-and-arithmetic",
                state=real.to_dict(),
            )
        )
    shown = [i["concept"] for i in client.get("/api/v1/reviews").json()["items"]]
    assert shown == ["zero:input-and-arithmetic"]
