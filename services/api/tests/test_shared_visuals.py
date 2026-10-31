"""The shared visual cache: one generation per concept, reused by every learner."""

# ruff: noqa: F811  (fixtures are imported from the explainer and learner API tests)

import uuid
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_explainer import configured, work  # noqa: F401
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.explainer import shared
from socrat.models import (
    ActivityRecord,
    AssistantMessage,
    Enrollment,
    PlaygroundJob,
    SharedVisual,
)

CONCEPT = "zero:programs-and-output"
BODY = dict(concept=CONCEPT)


def start(client, headers, **extra):
    return client.post("/api/v1/playground/shared", headers=headers, json={**BODY, **extra})


def state(client, **extra):
    return client.get("/api/v1/playground/shared", params={**BODY, **extra})


def second_learner(client):
    headers = login(client, subject="bob", name="Bob")
    onboard(client, headers)
    return headers


def generations(client):
    with Session(client.app.state.engine) as db:
        return db.scalar(select(func.count()).select_from(PlaygroundJob))


def test_a_miss_generates_once_and_the_next_learner_is_served_from_the_index(client, configured):
    headers, provider = configured
    assert state(client).json()["state"] == "none"
    first = start(client, headers).json()
    assert first["state"] == "generating" and first["mine"] and not provider.calls
    work(client)
    assert len(provider.calls) == 1
    ready = state(client).json()
    assert ready["state"] == "ready" and "html" not in ready["artifact"]

    bob = second_learner(client)
    again = start(client, bob).json()
    assert again["state"] == "ready" and again["artifact"]["id"] == ready["artifact"]["id"]
    assert len(provider.calls) == 1 and generations(client) == 1  # nothing was generated for bob
    frame = urlparse(again["artifact"]["frame_url"])
    served = client.get(frame.path + "?" + frame.query)
    assert (
        served.status_code == 200
        and "sandbox allow-scripts" in served.headers["content-security-policy"]
    )
    with Session(client.app.state.engine) as db:
        assert db.scalar(select(SharedVisual.hits)) == 1


def test_learners_who_ask_while_it_runs_wait_on_the_same_generation(client, configured):
    headers, provider = configured
    start(client, headers)
    bob = second_learner(client)
    waiting = start(client, bob).json()
    assert waiting["state"] == "generating" and waiting["mine"] is False
    assert generations(client) == 1
    work(client)
    assert state(client).json()["state"] == "ready" and len(provider.calls) == 1


def test_a_cache_hit_makes_no_job_and_spends_no_chat(client, configured):
    headers, _ = configured
    start(client, headers)
    work(client)
    bob = second_learner(client)
    for _ in range(3):
        assert start(client, bob).json()["state"] == "ready"
    with Session(client.app.state.engine) as db:
        owners = set(db.scalars(select(PlaygroundJob.user_id)))
        prompts = db.scalar(
            select(func.count())
            .select_from(AssistantMessage)
            .where(AssistantMessage.role == "user")
        )
    assert len(owners) == 1 and prompts == 0  # bob made nothing; no one's chat was spent


def test_an_edited_lesson_is_regenerated_instead_of_served_stale(client, configured, monkeypatch):
    headers, provider = configured
    start(client, headers)
    work(client)
    monkeypatch.setattr(shared, "fingerprint", lambda concept: "edited-lesson")
    assert state(client).json()["state"] == "none"  # the old visual is not offered
    assert start(client, headers).json()["state"] == "generating"
    work(client)
    assert len(provider.calls) == 2 and state(client).json()["state"] == "ready"


def test_several_learners_must_flag_a_visual_before_it_is_retired(client, configured):
    headers, provider = configured
    start(client, headers)
    work(client)
    artifact = state(client).json()["artifact"]["id"]
    url = f"/api/v1/playground/artifacts/{artifact}/report"
    reason = {"reason": "The explanation is incorrect"}
    assert client.post(url, headers=headers, json=reason).status_code == 200
    assert state(client).json()["state"] == "ready"  # one flag is not enough
    bob = second_learner(client)
    assert client.post(url, headers=bob, json=reason).status_code == 200
    assert state(client).json()["state"] == "none"
    assert client.get("/api/v1/playground/artifacts/" + artifact).status_code == 404  # bob: gone
    assert start(client, bob).json()["state"] == "generating"  # the next click rebuilds it
    work(client)
    assert len(provider.calls) == 2


def test_one_learner_flagging_twice_does_not_retire_it(client, configured):
    headers, _ = configured
    start(client, headers)
    work(client)
    url = "/api/v1/playground/artifacts/" + state(client).json()["artifact"]["id"] + "/report"
    for _ in range(2):
        client.post(url, headers=headers, json={"reason": "The explanation is incorrect"})
    assert state(client).json()["state"] == "ready"


def test_a_failed_generation_can_be_retried_by_the_next_learner(client, configured):
    headers, provider = configured
    start(client, headers)
    with Session(client.app.state.engine) as db, db.begin():
        job = db.scalar(select(PlaygroundJob))
        job.status, job.error = "failed", "playground_generation_invalid"
    failed = state(client).json()
    assert failed["state"] == "failed" and failed["error"] == "playground_generation_invalid"
    bob = second_learner(client)
    assert start(client, bob).json()["state"] == "generating"
    work(client)
    assert state(client).json()["state"] == "ready" and len(provider.calls) == 1


def test_no_visual_while_the_problem_is_a_pending_transfer_check(client, configured):
    headers, _ = configured
    with Session(client.app.state.engine) as db, db.begin():
        enrollment = db.scalar(select(Enrollment).where(Enrollment.active.is_(True)))
        db.add(
            ActivityRecord(
                enrollment_id=enrollment.id,
                activity_id=f"transfer:{CONCEPT}",
                outcome={"state": "pending", "problem": "ticket-stub", "at": 1},
            )
        )
    assert state(client, problem="ticket-stub").status_code == 423
    assert start(client, headers, problem="ticket-stub").status_code == 423
    assert generations(client) == 0
    assert state(client, problem="another-problem").status_code == 200


def test_the_cache_needs_a_signed_in_learner_and_a_real_concept(client, configured):
    headers, _ = configured
    assert client.post("/api/v1/playground/shared", json=BODY).status_code == 403  # no CSRF token
    assert start(client, headers, concept="zero:not-a-concept").status_code == 404
    assert start(client, headers, level="extreme").status_code == 422


def test_every_plan_can_watch_and_fill_without_spending_its_own_allowance(
    client, configured, monkeypatch
):
    from socrat import entitlements

    headers, provider = configured
    monkeypatch.setattr(entitlements, "ENABLED", True)  # plans on: this learner is on Free
    own = dict(prompt="Explain electromagnetic induction", request_id=str(uuid.uuid4()))
    assert client.post("/api/v1/playground/generate", headers=headers, json=own).status_code == 402

    assert start(client, headers).json()["state"] == "generating"
    work(client)
    assert state(client).json()["state"] == "ready" and len(provider.calls) == 1
    with Session(client.app.state.engine) as db:
        user_id = db.scalar(select(Enrollment.user_id).where(Enrollment.active.is_(True)))
        assert db.scalar(select(PlaygroundJob.shared)) is True
        assert entitlements.used(db, user_id, "playground", 0) == 0
        assert entitlements.used(db, user_id, "chat", 0) == 0
        assert not db.scalar(select(AssistantMessage).where(AssistantMessage.role == "user"))


def test_one_learner_cannot_start_unlimited_fills(client, configured, monkeypatch):
    headers, _ = configured
    client.app.state.settings.explainer_daily_messages = 1
    assert start(client, headers).json()["state"] == "generating"
    work(client)
    other = start(client, headers, concept="zero:variables-and-types")
    assert other.status_code == 429 and other.json()["error"]["code"] == "playground_daily_limit"
