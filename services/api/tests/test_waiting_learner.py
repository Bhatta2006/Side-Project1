"""Lesson 0 plan PR 5 (``gen_waiting_learner``): a learner waiting on a job is not left behind
a crashed worker or a queue of background lessons, and a crash after the outline was paid for
does not pay the architect again."""

import asyncio

from sqlalchemy import update
from sqlalchemy.orm import Session
from test_learner_api import client, login  # noqa: F401
from test_learner_plan import learner_request, profile
from test_roadmap import Planner

from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.coursegen import jobs
from socrat.models import GenerationJob, now


def queue(engine, course, priority, state="queued", age=0):
    with Session(engine) as db, db.begin():
        job = jobs.enqueue(db, "package", course, {"trigger": "x"}, None, f"t-{course}")
        job.priority, job.state, job.updated_at = priority, state, now() - age
        return job.id


def test_a_learners_orphaned_job_is_reclaimed_in_minutes_not_an_hour(client):  # noqa: F811
    engine = client.app.state.engine
    mine = queue(engine, "a", jobs.PRIORITY["first"], "running", age=jobs.STALE_SECONDS_WAITING + 5)
    queue(engine, "b", jobs.BACKGROUND, "running", age=jobs.STALE_SECONDS_WAITING + 5)
    assert jobs.claim(engine) is None  # without the flag: an hour, as before
    assert jobs.claim(engine, waiting_fast=True) == mine
    assert jobs.claim(engine, waiting_fast=True) is None  # a background job still waits an hour


def test_the_learner_slot_takes_only_what_a_learner_waits_on(client):  # noqa: F811
    engine = client.app.state.engine
    queue(engine, "a", jobs.BACKGROUND)
    urgent = queue(engine, "b", jobs.PRIORITY["outline"])
    assert jobs.claim(engine, max_priority=jobs.WAITING_PRIORITY) == urgent
    assert jobs.claim(engine, max_priority=jobs.WAITING_PRIORITY) is None
    assert jobs.claim(engine) is not None  # the general slot takes the rest


def test_the_heartbeat_keeps_a_running_job_fresh(client, monkeypatch):  # noqa: F811
    engine = client.app.state.engine
    job_id = queue(engine, "a", 0, "running", age=500)
    monkeypatch.setattr(jobs, "HEARTBEAT_SECONDS", 0.01)

    async def beat_briefly():
        task = asyncio.create_task(jobs._heartbeat(engine, job_id))
        await asyncio.sleep(0.05)
        task.cancel()

    asyncio.run(beat_briefly())
    with Session(engine) as db:
        assert now() - db.get(GenerationJob, job_id).updated_at < 5


def crash_once_at_save(monkeypatch):
    """The worker dies once after the outline was paid for and checked, before it is saved."""
    real = jobs._save_outline
    calls = []

    async def save(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("worker restarted")
        await real(*args, **kwargs)

    monkeypatch.setattr(jobs, "_save_outline", save)


def test_an_interrupted_outline_resumes_without_a_second_architect_bill(
    client,  # noqa: F811
    monkeypatch,
):
    job_id = learner_request(client, monkeypatch, profile())
    state = client.app.state
    state.settings.gen_waiting_learner = True
    script = Planner()
    crash_once_at_save(monkeypatch)
    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), script.make))
    with Session(state.engine) as db, db.begin():
        job = db.get(GenerationJob, job_id)
        assert job.state == "queued" and "outline" in job.output and "brief" in job.output
        assert generated.course(db, "ai-basics") is None
    with Session(state.engine) as db, db.begin():
        db.execute(update(GenerationJob).where(GenerationJob.id == job_id).values(not_before=0))
    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), script.make))
    assert len(script.architect) == 1
    with Session(state.engine) as db:
        job = db.get(GenerationJob, job_id)
        assert job.state == "done"
        assert any(e.get("event") == "resumed_from_stored_outline" for e in job.log)
        course = generated.course(db, "ai-basics")
        assert course is not None and course.modules


def test_without_the_flag_nothing_is_stored_for_a_resume(client, monkeypatch):  # noqa: F811
    job_id = learner_request(client, monkeypatch, profile())
    state = client.app.state
    crash_once_at_save(monkeypatch)
    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), Planner().make))
    with Session(state.engine) as db:
        assert db.get(GenerationJob, job_id).output is None
