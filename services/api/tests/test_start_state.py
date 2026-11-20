"""Lesson 0 plan PR 3: ``view.start`` says when the learner can safely start (their first
activity is a written lesson), so /start can enable "Start learning" at the right moment."""

from sqlalchemy import select
from sqlalchemy.orm import Session
from test_course_brain import DETECTIVE, adult, ask, brain, build, me  # noqa: F401
from test_learner_api import client, login  # noqa: F401

from socrat.coursegen import jobs
from socrat.models import GenerationJob

URL = "/api/v1/learning-requests"


def start(client, request_id):  # noqa: F811
    return client.get(f"{URL}/{request_id}").json()["start"]


def test_the_start_state_follows_the_first_lesson(brain):  # noqa: F811
    ada = login(brain, "ada", "Ada")
    adult(brain, ada)
    first = ask(brain, ada, DETECTIVE, minutes_per_day=10)
    assert start(brain, first["id"]) == dict(state="waiting", concept=None, minutes=10, retry=False)

    build(brain, first["course_id"], me(brain), live=False)
    with Session(brain.app.state.engine) as db, db.begin():
        jobs.enqueue(db, "package", first["course_id"], {"trigger": "first"}, None, "what-is-ml")
    ready = start(brain, first["id"])
    assert ready["state"] == "roadmap_ready" and ready["concept"] == "what-is-ml"

    with Session(brain.app.state.engine) as db, db.begin():
        job = db.scalars(
            select(GenerationJob).where(
                GenerationJob.kind == "package", GenerationJob.target == "what-is-ml"
            )
        ).one()
        job.state = "dead"
    failed = start(brain, first["id"])
    assert failed["state"] == "first_lesson_failed" and failed["retry"] is True

    build(brain, first["course_id"], me(brain), live=True)  # the lesson was written after all
    assert start(brain, first["id"])["state"] == "first_lesson_ready"


def test_a_served_course_is_ready_at_once(brain):  # noqa: F811
    ada = login(brain, "ada", "Ada")
    adult(brain, ada)
    first = ask(brain, ada, DETECTIVE)
    build(brain, first["course_id"], me(brain))
    brain.post(f"{URL}/{first['id']}/publish", json={}, headers=ada)
    bob = login(brain, "bob", "Bob")
    adult(brain, bob)
    second = ask(brain, bob, DETECTIVE)
    assert second["status"] == "matched"
    assert start(brain, second["id"])["state"] == "first_lesson_ready"
