"""Lesson 0 plan PR 4: a learner who has ten minutes gets ten-minute days, not the rounded-up
enrolment budget; what does not fit moves to the next study day."""

from test_learner_api import client, login, onboard  # noqa: F401

from socrat.coursegen.requests import _true_minutes
from socrat.models import GeneratedCourse


def first_days(client, headers, **extra):  # noqa: F811
    onboard(client, headers, course="basics", **extra)
    return client.get("/api/v1/plan").json()["days"]


def test_ten_minutes_is_ten_and_the_rest_moves_to_tomorrow(client):  # noqa: F811
    ada = login(client, subject="ada", name="Ada")
    days = first_days(client, ada, session_minutes=10)
    first = days[0]
    # The first item always fits; anything after it must fit in what is left.
    total = sum(i["minutes"] for i in first["items"])
    assert len(first["items"]) == 1 or total <= 10
    assert first["minutes"] == total
    assert len(days) > 1 and days[1]["items"]  # the overflow is on the next study day
    bob = login(client, subject="bob", name="Bob")
    loose = first_days(client, bob)  # 45 scheduled minutes and no session length
    assert sum(i["minutes"] for i in loose[0]["items"]) > total


def test_without_a_session_length_the_scheduled_budget_packs_as_before(client):  # noqa: F811
    ada = login(client, subject="ada", name="Ada")
    loose = first_days(client, ada)
    bob = login(client, subject="bob", name="Bob")
    same = first_days(client, bob, session_minutes=45)  # equal to minutes_per_day
    # Same budget and start; a Lesson 0 learner's written lessons count computed minutes
    # (backlog 2.3), so the day may hold more, never more than the budget.
    assert loose[0]["items"][0]["id"] == same[0]["items"][0]["id"]
    assert sum(i["minutes"] for i in same[0]["items"]) <= 45


def test_the_enrol_view_offers_the_true_minutes_for_a_lesson0_course_only():
    planned = GeneratedCourse(id="x", brief={"plan": {"session_minutes": 10}})
    assert _true_minutes(planned) == 10
    assert _true_minutes(GeneratedCourse(id="y", brief={"plan": None})) is None
    assert _true_minutes(GeneratedCourse(id="z", brief={})) is None
    assert _true_minutes(None) is None


# ------------------------------------------------------------------ backlog 2.3


def test_a_written_lesson_counts_its_computed_minutes(client):  # noqa: F811
    from socrat.catalog.registry import default_catalog
    from socrat.planner.engine import written_minutes

    ada = login(client, subject="ada", name="Ada")
    days = first_days(client, ada, session_minutes=10)
    first = days[0]["items"][0]
    assert first["kind"] == "lesson"
    concept = default_catalog().concept(first["concept"])
    assert first["minutes"] == written_minutes(concept.lesson, len(concept.quiz))["lesson"]
    assert sum(i["minutes"] for i in days[0]["items"]) <= 10 or len(days[0]["items"]) == 1


def test_changing_minutes_in_settings_updates_the_true_session_length(client):  # noqa: F811
    ada = login(client, subject="ada", name="Ada")
    first_days(client, ada, session_minutes=10)
    changed = client.patch("/api/v1/enrollments/current", json={"minutes_per_day": 30}, headers=ada)
    assert changed.status_code == 200, changed.text
    from sqlalchemy.orm import Session

    from socrat.models import Enrollment

    with Session(client.app.state.engine) as db:
        assert db.query(Enrollment).one().goal["session_minutes"] == 30


def test_a_first_lesson_longer_than_the_session_goes_back():
    from types import SimpleNamespace as NS

    from socrat.coursegen.jobs import first_session_over
    from socrat.coursegen.learner_plan import LearnerPlan

    brief = NS(plan=LearnerPlan(request="SQL", session_minutes=10))
    course = NS(modules=[NS(concepts=["intro", "next"])])
    short = NS(id="intro", lesson="word " * 900, quiz=[1, 2, 3])  # 5 + 5 = 10 minutes
    long = NS(id="intro", lesson="word " * 2000, quiz=[1, 2, 3])  # 12 + 5 = 17 minutes
    assert first_session_over(brief, course, short) == ""
    assert "takes 17 minutes" in first_session_over(brief, course, long)
    assert first_session_over(brief, course, NS(**{**vars(long), "id": "next"})) == ""
    assert first_session_over(NS(plan=None), course, long) == ""  # not a Lesson 0 course
