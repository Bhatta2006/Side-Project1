"""Match before build: a request is offered a course the learner may already take, and never
one they may not see."""

# ruff: noqa: F811
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401
from test_learning_requests import URL, _published_course, on  # noqa: F401

from socrat.coursegen import match
from socrat.models import GenerationJob, LearningRequest


def intent(**fields):
    base = dict(subject="Fractions", language="en", register="general", desired_level="beginner")
    return {**base, **fields}


def test_the_same_subject_is_recognised_without_filler_order_or_plurals():
    same = match.subject_key
    assert same("Introduction to fractions") == same("Fraction basics") == same("fractions")
    assert same("Linear algebra") == same("algebra, linear")
    assert same("Linear algebra") != same("Algebra")
    assert same("C") == same("c") != same("C++")  # short names are compared as written
    assert same("Go") != same("C")


def test_fit_is_exact_close_or_nothing():
    assert match.fit(intent(), intent(subject="fractions basics")) == ("exact", [])
    kind, why = match.fit(
        intent(register="university", desired_level="advanced", style_request="As a story"),
        intent(),
    )
    assert kind == "close" and len(why) == 3
    assert "general reader" in why[0] and "beginner" in why[1]
    assert match.fit(intent(), intent(subject="Decimals")) is None
    assert match.fit(intent(), intent(language="es")) is None
    # A child is never offered an adult's course, nor an adult a child's.
    assert match.fit(intent(register="kid"), intent()) is None
    assert match.fit(intent(), intent(register="little-kid")) is None
    assert match.fit(intent(register="kid"), intent(register="kid")) == ("exact", [])


def ask(on, headers, text="Teach me algebra from zero"):
    made = on.post(URL, json={"text": text, "choices": ["reg-adult"]}, headers=headers)
    assert made.status_code == 200, made.text
    return made.json()


def test_matching_is_off_by_default(on):
    ada = login(on, subject="ada")
    made = ask(on, ada)
    assert on.get(f"{URL}/{made['id']}/matches", headers=ada).status_code == 404
    body = {"course": "algebra-000000"}
    assert on.post(f"{URL}/{made['id']}/take", json=body, headers=ada).status_code == 404


def test_a_private_course_is_never_matched_and_a_shared_one_can_be_started(on):
    on.app.state.settings.request_matching = True
    ada = login(on, subject="ada", name="Ada Lovelace")
    rid, course_id = _published_course(on, ada)

    bob = login(on, subject="bob", name="Bob")
    onboard(on, bob)
    wish = ask(on, bob)
    found = f"{URL}/{wish['id']}/matches"
    assert on.get(found, headers=bob).json() == {"items": []}  # Ada has not shared it
    taken = on.post(f"{URL}/{wish['id']}/take", json={"course": course_id}, headers=bob)
    assert taken.status_code == 404  # and it cannot be taken by naming it

    ada = login(on, subject="ada", name="Ada Lovelace")
    shared = on.post(f"{URL}/{rid}/share", json={"consent": True, "credit": "name"}, headers=ada)
    assert shared.status_code == 200
    bob = login(on, subject="bob", name="Bob")
    items = on.get(found, headers=bob).json()["items"]
    assert [(m["course"], m["fit"], m["mine"], m["by"]) for m in items] == [
        (course_id, "exact", False, "Ada Lovelace")
    ]
    assert items[0]["ready"] == 1 and items[0]["lessons"] > 1 and not items[0]["enrolled"]
    other = ask(on, bob, "Teach me organic chemistry")
    assert on.get(f"{URL}/{other['id']}/matches", headers=bob).json() == {"items": []}

    with Session(on.app.state.engine) as db:
        jobs_before = len(db.scalars(select(GenerationJob)).all())
    view = on.post(f"{URL}/{wish['id']}/take", json={"course": course_id}, headers=bob).json()
    assert (view["status"], view["course_id"], view["published"]) == ("matched", course_id, True)
    assert view["community"] is None  # Bob does not manage Ada's course
    assert view["enroll"]["course"] == course_id
    again = on.post(f"{URL}/{wish['id']}/take", json={"course": course_id}, headers=bob)
    assert again.json()["status"] == "matched"  # idempotent
    assert on.get(found, headers=bob).json() == {"items": []}  # settled
    # Confirming afterwards builds nothing; the request stays what it became.
    assert on.post(f"{URL}/{wish['id']}/confirm", json={}, headers=bob).json()["status"] == (
        "matched"
    )
    assert on.post(f"{URL}/{wish['id']}/publish", headers=bob).status_code == 404
    with Session(on.app.state.engine) as db:
        assert len(db.scalars(select(GenerationJob)).all()) == jobs_before  # nothing generated
        row = db.get(LearningRequest, wish["id"])
        assert row.status == "matched"
    enrolled = on.post("/api/v1/enrollments", json=view["enroll"], headers=bob)
    assert enrolled.status_code == 200, enrolled.text
    # A matched request no longer counts as open (the chemistry one still does).
    on.app.state.settings.learning_requests_max_open = 2
    assert on.post(URL, json={"text": "Teach me geology"}, headers=bob).status_code == 200


def test_a_learners_own_course_is_matched_first_and_others_requests_are_refused(on):
    on.app.state.settings.request_matching = True
    ada = login(on, subject="ada")
    _, course_id = _published_course(on, ada)
    wish = ask(on, ada, "I want to learn algebra")
    items = on.get(f"{URL}/{wish['id']}/matches", headers=ada).json()["items"]
    assert [(m["course"], m["mine"], m["by"]) for m in items] == [(course_id, True, None)]
    bob = login(on, subject="bob")
    assert on.get(f"{URL}/{wish['id']}/matches", headers=bob).status_code == 404
    body = {"course": course_id}
    assert on.post(f"{URL}/{wish['id']}/take", json=body, headers=bob).status_code == 404
    assert on.post(f"{URL}/{wish['id']}/take", json={"course": "X"}, headers=bob).status_code == 422
