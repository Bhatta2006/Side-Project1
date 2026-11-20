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
    same = first_days(client, bob, session_minutes=45)  # equal to minutes_per_day: no change
    assert [i["id"] for i in loose[0]["items"]] == [i["id"] for i in same[0]["items"]]


def test_the_enrol_view_offers_the_true_minutes_for_a_lesson0_course_only():
    planned = GeneratedCourse(id="x", brief={"plan": {"session_minutes": 10}})
    assert _true_minutes(planned) == 10
    assert _true_minutes(GeneratedCourse(id="y", brief={"plan": None})) is None
    assert _true_minutes(GeneratedCourse(id="z", brief={})) is None
    assert _true_minutes(None) is None
