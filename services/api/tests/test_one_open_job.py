"""At most one open generation job per course, kind and target (migration 0045).

Callers check ``jobs.active()`` and then insert; two concurrent requests (two page loads that
both prefetch the next lesson, a double-clicked "regenerate") can both pass that check. The
database now refuses the second insert, so a lesson is never queued, written and paid twice.
"""

# ruff: noqa: F811
import json

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_learner_api import client  # noqa: F401

from socrat.coursegen import jobs
from socrat.database import make_engine
from socrat.models import GenerationJob


def test_a_second_open_job_for_the_same_work_is_refused_by_the_database(client):
    bind = client.app.state.engine
    with Session(bind) as db, db.begin():
        first = jobs.enqueue(db, "package", "kids-math", {}, None, target="counting")
        first_id = first.id
    # A second request that passed its own active() check before the first one committed.
    with Session(bind) as db, db.begin():
        with pytest.raises(jobs.AlreadyQueued) as refused:
            jobs.enqueue(db, "package", "kids-math", {}, None, target="counting")
        assert refused.value.status_code == 409
        assert refused.value.detail == "generation_in_progress"
        # The savepoint keeps the caller's transaction usable for its other work.
        assert jobs.enqueue_once(db, "package", "kids-math", {}, None, target="counting") is None
        other = jobs.enqueue(db, "package", "kids-math", {}, None, target="adding")
        exercise = jobs.enqueue(db, "exercise", "kids-math", {}, None, target="counting")
        assert other.id and exercise.id
    with Session(bind) as db:
        open_jobs = db.scalars(
            select(GenerationJob).where(
                GenerationJob.course_id == "kids-math", GenerationJob.target == "counting"
            )
        ).all()
        assert sorted((j.kind, j.id == first_id) for j in open_jobs) == [
            ("exercise", False),
            ("package", True),
        ]


def test_a_finished_or_failed_job_does_not_block_a_new_one(client):
    bind = client.app.state.engine
    with Session(bind) as db, db.begin():
        job = jobs.enqueue(db, "package", "kids-math", {}, None, target="shapes")
        job.state = "failed"
    with Session(bind) as db, db.begin():
        again = jobs.enqueue(db, "package", "kids-math", {}, None, target="shapes")
        assert again.state == "queued"


def test_migration_keeps_the_oldest_open_duplicate_and_downgrades(tmp_path):
    url = f"sqlite:///{tmp_path / 'jobs.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "0044_course_revisions")
    engine = make_engine(url)
    insert = sa.text(
        "INSERT INTO generation_jobs (id, kind, course_id, target, input, state, log, cost_usd,"
        " error, attempts, not_before, stage, created_at, updated_at) VALUES (:id, 'package',"
        " 'c', 't', '{}', :state, '[]', 0, '', 0, 0, '', :at, :at)"
    )
    with engine.begin() as conn:
        for job_id, state, at in (("a", "queued", 1), ("b", "running", 2), ("c", "done", 3)):
            conn.execute(insert, {"id": job_id, "state": state, "at": at})
    command.upgrade(config, "0045_one_open_generation_job")
    with engine.connect() as conn:
        rows = dict(conn.execute(sa.text("SELECT id, state FROM generation_jobs")).fetchall())
        log = json.loads(
            conn.execute(sa.text("SELECT log FROM generation_jobs WHERE id = 'b'")).scalar_one()
        )
    assert rows == {"a": "queued", "b": "cancelled", "c": "done"}
    assert log[-1]["event"] == "cancelled_duplicate"
    with engine.begin() as conn, pytest.raises(sa.exc.IntegrityError):
        conn.execute(insert, {"id": "d", "state": "queued", "at": 4})
    command.downgrade(config, "0044_course_revisions")
    names = {i["name"] for i in sa.inspect(make_engine(url)).get_indexes("generation_jobs")}
    assert "uq_generation_jobs_one_open" not in names
