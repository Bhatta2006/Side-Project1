"""Generation recovery (master prompt 7 and 10.3): transient failures retry with backoff and end
in a dead-letter state, content failures do not retry, published courses start writing their
first slice at once (from the learner's diagnosed start), owners can cancel and regenerate, and
every model call records its prompt version and time."""

# ruff: noqa: F811
import asyncio
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_learner_api import client, login  # noqa: F401
from test_learning_requests import URL

from socrat.assistant.gateway import ProviderError
from socrat.catalog.registry import default_catalog
from socrat.coursegen import jobs, prefetch, roles
from socrat.models import GenerationJob, now


@pytest.fixture
def on(client):
    client.app.state.settings.learning_requests_enabled = True
    client.app.state.settings.learning_requests_max_open = 5
    return client


def _job(client, kind="outline", state="queued", target="") -> str:
    with Session(client.app.state.engine) as db, db.begin():
        job = GenerationJob(kind=kind, course_id="c1", target=target, input={}, log=[], state=state)
        db.add(job)
        db.flush()
        return job.id


def _get(client, job_id) -> GenerationJob:
    with Session(client.app.state.engine) as db:
        job = db.get(GenerationJob, job_id)
        db.expunge(job)
        return job


def _run(client) -> bool:
    state = client.app.state
    return asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog()))


def test_transient_failures_back_off_and_end_in_the_dead_letter_state(client, monkeypatch):
    async def unreachable(*args, **kwargs):
        raise ProviderError("provider_unreachable")

    monkeypatch.setattr(jobs, "run_outline", unreachable)
    job_id = _job(client)
    assert _run(client)
    first = _get(client, job_id)
    assert first.state == "queued" and first.attempts == 1 and first.not_before > now()
    assert first.log[-1]["event"] == "provider_error" and first.log[-1]["retry_in"] == 60
    assert jobs.lifecycle(first) == "queued"
    assert not _run(client)  # still backing off: nothing claimable

    for expected in (2, 3):
        with Session(client.app.state.engine) as db, db.begin():
            db.get(GenerationJob, job_id).not_before = 0  # the backoff has passed
        assert _run(client)
        assert _get(client, job_id).attempts == expected
    dead = _get(client, job_id)
    assert dead.state == "dead" and "provider_unreachable" in dead.error
    assert jobs.lifecycle(dead) == "blocked"
    assert not _run(client)  # a dead job is never claimed again


def test_a_crash_retries_but_a_permanent_refusal_does_not(client, monkeypatch):
    crashed = _job(client, kind="mystery")  # unknown kind raises inside the runner
    assert _run(client)
    assert _get(client, crashed).state == "queued" and _get(client, crashed).attempts == 1
    with Session(client.app.state.engine) as db, db.begin():
        db.get(GenerationJob, crashed).state = "done"

    async def broke(*args, **kwargs):
        raise ProviderError("ai_budget_reached")

    monkeypatch.setattr(jobs, "run_outline", broke)
    refused = _job(client)
    assert _run(client)
    job = _get(client, refused)
    assert job.state == "failed" and job.attempts == 0 and "ai_budget_reached" in job.error
    assert jobs.transient(ProviderError("provider_http_503"))
    assert not jobs.transient(ProviderError("provider_http_400"))


def test_lifecycle_maps_jobs_to_the_stages_learners_see():
    job = GenerationJob(kind="package", course_id="c", target="x", input={}, log=[])
    assert jobs.lifecycle(None, "planned") == "planned"
    assert jobs.lifecycle(None, "live") == "published"
    for state, stage, expected in [
        ("queued", "", "queued"),
        ("running", "generating", "generating"),
        ("running", "validating", "validating"),
        ("failed", "", "failed"),
        ("cancelled", "", "cancelled"),
        ("dead", "", "blocked"),
        ("done", "", "superseded"),  # released once, then withdrawn back to planned
    ]:
        job.state, job.stage = state, stage
        assert jobs.lifecycle(job, "planned") == expected, state


def _course(modules: list[list[str]]):
    """Only modules and concept statuses matter to the slice."""
    return SimpleNamespace(
        modules=[SimpleNamespace(concepts=cs) for cs in modules],
        concepts=[SimpleNamespace(id=c, status="planned") for cs in modules for c in cs],
    )


def test_initial_slice_is_capped_and_starts_where_the_learner_starts():
    small = _course([["a", "b"], ["c"]])
    assert prefetch.initial_slice(small) == ["a", "b", "c"]  # a short course is written whole
    big = _course([["a", "b", "c", "d"], ["e", "f", "g"], ["h"], ["i"]])
    assert prefetch.initial_slice(big) == ["a", "b", "c", "d", "e", "f"]  # capped at 6
    assert prefetch.initial_slice(big, start="e") == ["e", "f", "g", "h", "i"]  # 3 modules on
    assert prefetch.initial_slice(big, start="missing") == prefetch.initial_slice(big)


def _published(on, ada):
    from test_coursegen import OUTLINE, Scripted, run

    made = on.post(URL, json={"text": "Teach me ML", "choices": ["reg-adult"]}, headers=ada).json()
    course_id = on.post(f"{URL}/{made['id']}/confirm", json={}, headers=ada).json()["course_id"]
    script = Scripted(
        architect=[json.dumps(OUTLINE)],
        critic=[json.dumps({"verdict": "pass", "summary": "ok", "issues": []})],
    )
    assert run(on, script)
    assert on.post(f"{URL}/{made['id']}/publish", headers=ada).json()["published"]
    return made["id"], course_id


def _packages(on, course_id) -> list[GenerationJob]:
    with Session(on.app.state.engine) as db:
        rows = db.scalars(
            select(GenerationJob).where(
                GenerationJob.course_id == course_id, GenerationJob.kind == "package"
            )
        ).all()
        for r in rows:
            db.expunge(r)
        return list(rows)


def test_publishing_starts_the_first_lessons_and_shows_honest_stages(on):
    ada = login(on, subject="ada")
    request_id, course_id = _published(on, ada)
    queued = _packages(on, course_id)
    assert sorted(j.target for j in queued) == ["loss", "what-is-ml"]
    assert {j.input["trigger"] for j in queued} == {"initial"}
    stages = {
        c["id"]: c["generation"]
        for m in on.get(f"{URL}/{request_id}").json()["blueprint"]["modules"]
        for c in m["concepts"]
    }
    assert set(stages.values()) == {"queued"}
    # Publishing again queues nothing new.
    on.post(f"{URL}/{request_id}/publish", headers=ada)
    assert len(_packages(on, course_id)) == 2


def test_owner_can_cancel_waiting_lessons_and_regenerate_one(on):
    ada = login(on, subject="ada")
    request_id, course_id = _published(on, ada)
    concept = "what-is-ml"
    busy = on.post(f"{URL}/{request_id}/concepts/{concept}/regenerate", headers=ada)
    assert busy.status_code == 409  # already queued

    cancelled = on.post(f"{URL}/{request_id}/cancel", headers=ada).json()
    assert cancelled["cancelled"] == 2
    assert {j.state for j in _packages(on, course_id)} == {"cancelled"}
    stages = [
        c["generation"]
        for m in on.get(f"{URL}/{request_id}").json()["blueprint"]["modules"]
        for c in m["concepts"]
    ]
    assert set(stages) == {"cancelled"}

    again = on.post(f"{URL}/{request_id}/concepts/{concept}/regenerate", headers=ada).json()
    fresh = [j for j in _packages(on, course_id) if j.id == again["queued"]]
    assert fresh and fresh[0].state == "queued" and fresh[0].input["trigger"] == "owner"

    assert on.post(f"{URL}/{request_id}/concepts/nope/regenerate", headers=ada).status_code == 404
    bob = login(on, subject="bob", name="Bob")
    assert on.post(f"{URL}/{request_id}/cancel", headers=bob).status_code == 404


def test_prompt_version_names_the_exact_instructions():
    assert roles.prompt_version("Write a lesson.") == roles.prompt_version("Write a lesson.")
    assert roles.prompt_version("Write a lesson.") != roles.prompt_version("Write a lesson!")
    assert len(roles.prompt_version("x")) == 12
