"""What a learner is told about lessons still being written, and the one automatic retry of a
lesson that failed its gates (coursegen.progress, jobs.retry_once)."""

# ruff: noqa: F811
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_learner_api import client  # noqa: F401

from socrat.coursegen import jobs, progress
from socrat.models import GenerationJob


def job(**fields) -> GenerationJob:
    base = dict(kind="package", course_id="c", target="t", input={}, log=[], created_at=100)
    return GenerationJob(**{**base, **fields})


def test_each_step_of_the_log_moves_the_lesson_forward_and_never_reaches_done():
    steps = [
        {"role": "search"},
        {"role": "researcher"},
        {"role": "author", "round": 1},
        {"role": "system", "event": "validating", "round": 1},
        {"role": "system", "event": "revising", "round": 1},
        {"role": "author", "round": 2},
        {"role": "system", "event": "validating", "round": 2},
        {"role": "system", "event": "revising", "round": 2},
        {"role": "system", "event": "validating", "round": 3},
    ]
    seen = []
    for n in range(1, len(steps) + 1):
        view = progress.of_job(job(state="running", log=steps[:n]), 3, 200)
        assert view["state"] == "writing"
        seen.append(view["progress"])
    assert seen == sorted(seen) and seen[0] > 0 and seen[-1] <= progress.CAP
    assert progress.of_job(job(state="running", log=steps[:3]), 3, 200)["label"] == (
        "Writing the lesson"
    )
    assert "Checking" in progress.of_job(job(state="running", log=steps[:4]), 3, 200)["label"]


def test_waiting_scheduled_failed_and_not_started_lessons_say_so():
    assert progress.of_job(None, 3, 200)["state"] == "later"
    assert progress.of_job(job(state="queued"), 3, 200)["label"] == "Waiting its turn"
    later = progress.of_job(job(state="queued", not_before=900), 3, 200)
    assert later["state"] == "scheduled" and later["at"] == 900
    stuck = progress.of_job(job(state="failed"), 3, 200)
    assert stuck["state"] == "stuck" and "course team" in stuck["label"]
    again = progress.of_job(job(state="queued", input={"retry_of": "x"}), 3, 200)
    assert again["label"].startswith("Second try")


def test_a_failed_lesson_is_written_once_more_then_waits_for_the_owner(client):
    bind = client.app.state.engine
    with Session(bind) as db, db.begin():
        first = jobs.enqueue(db, "package", "kids-math", {"trigger": "first"}, None, "counting")
        first.state, first_id = "failed", first.id
    again = jobs.retry_once(bind, first_id)
    assert again is not None
    with Session(bind) as db:
        retry = db.get(GenerationJob, again)
        assert retry.state == "queued" and retry.priority == jobs.PRIORITY["first"]
        assert retry.input["retry_of"] == first_id
    with Session(bind) as db, db.begin():
        db.get(GenerationJob, again).state = "failed"
    assert jobs.retry_once(bind, again) is None  # failed twice: the owner decides
    with Session(bind) as db:
        rows = db.scalars(
            select(GenerationJob).where(
                GenerationJob.course_id == "kids-math", GenerationJob.target == "counting"
            )
        ).all()
        assert len(rows) == 2


def test_the_preparing_endpoint_answers_for_a_course_that_is_not_generated(client):
    from test_learner_api import login, onboard

    onboard(client, login(client))
    response = client.get("/api/v1/me/preparing")
    assert response.status_code == 200
    assert response.json() == {"lessons": []}
