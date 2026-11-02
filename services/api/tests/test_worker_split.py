"""API and worker split: heartbeat health check, the worker running generation, queue depth."""

# ruff: noqa: F811
import asyncio
import sys

import pytest
from sqlalchemy.orm import Session
from test_learner_api import client, login  # noqa: F401

from socrat import worker
from socrat.config import Settings
from socrat.models import GeneratedCourse, GenerationJob, now


def test_heartbeat_is_healthy_only_while_fresh(tmp_path):
    path = str(tmp_path / "beat")
    assert not worker.healthy(path)  # never written
    worker.beat(path)
    assert worker.healthy(path)
    import time

    assert not worker.healthy(path, at=time.time() + worker.HEARTBEAT_MAX_AGE + 5)  # a hung loop
    (tmp_path / "beat").write_text("not a time")
    assert not worker.healthy(path)
    assert not worker.healthy("")  # no file configured: cannot be called healthy
    worker.beat("")  # and beating nowhere is a no-op, not an error


def test_check_flag_sets_the_exit_code(tmp_path, monkeypatch):
    path = tmp_path / "beat"
    monkeypatch.setenv("SOCRAT_WORKER_HEARTBEAT_FILE", str(path))
    monkeypatch.setattr(sys, "argv", ["worker", "--check"])
    with pytest.raises(SystemExit) as stale:
        worker.main()
    assert stale.value.code == 1
    worker.beat(str(path))
    with pytest.raises(SystemExit) as fresh:
        worker.main()
    assert fresh.value.code == 0


def run_serve(settings, engine, monkeypatch, loop):
    monkeypatch.setattr(worker, "generation_loop", loop)

    async def go():
        task = asyncio.create_task(worker.serve(settings, engine))
        await asyncio.sleep(0.3)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(go())


def test_worker_runs_generation_only_when_asked(client, tmp_path, monkeypatch):
    engine = client.app.state.engine
    started: list[int] = []

    async def loop(_engine, _settings):
        started.append(1)
        await asyncio.sleep(60)

    beat = str(tmp_path / "beat")
    base = dict(
        environment="test",
        database_url=str(engine.url),
        worker_heartbeat_file=beat,
        reminders_enabled=False,
    )
    run_serve(Settings(**base), engine, monkeypatch, loop)
    assert started == []  # default: the API keeps generating
    assert worker.healthy(beat)  # and the loop beat while it ran

    run_serve(
        Settings(**base, worker_runs_generation=True, worker_generation_concurrency=2),
        engine,
        monkeypatch,
        loop,
    )
    assert started == [1, 1]


def test_a_dead_generation_loop_stops_the_worker_loudly(client, monkeypatch):
    async def loop(_engine, _settings):
        raise ValueError("boom")

    settings = Settings(
        environment="test",
        database_url=str(client.app.state.engine.url),
        worker_runs_generation=True,
    )
    monkeypatch.setattr(worker, "generation_loop", loop)
    with pytest.raises(RuntimeError, match="generation loop stopped"):
        asyncio.run(asyncio.wait_for(worker.serve(settings, client.app.state.engine), 5))


def test_queue_depth_is_reported_and_ignores_paused_courses(client):
    client.app.state.settings.admin_subjects = ["boss"]
    admin = login(client, subject="boss", name="Boss")
    stamp = now()
    with Session(client.app.state.engine) as db, db.begin():
        db.add(GeneratedCourse(id="live", payload={}))
        db.add(GeneratedCourse(id="held", payload={}, paused="budget"))
        db.flush()
        for cid, state, age in (
            ("live", "queued", 600),
            ("live", "queued", 30),
            ("live", "running", 10),
            ("held", "queued", 9000),  # waiting on purpose
            ("live", "done", 9999),
        ):
            db.add(
                GenerationJob(
                    kind="package", course_id=cid, input={}, state=state, created_at=stamp - age
                )
            )
    queue = client.get("/api/v1/admin/engine-costs", headers=admin).json()["queue"]
    assert queue["queued"] == 2 and queue["running"] == 1
    assert 599 <= queue["oldest_queued_seconds"] <= 620
