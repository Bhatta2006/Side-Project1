"""Trust boundaries and evidence integrity for the content-placement playbook."""

import sys

import pytest
from runner_support import SIGNING, WORKER, profiles
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.catalog.atoms import Adapter
from socrat.catalog.registry import default_catalog
from socrat.catalog.validate_atoms import check_adapter
from socrat.execution.protocol import CaseResult, ExecutionResult, JobEnvelope, sign
from socrat.learn import sessions
from socrat.learn.feedback import submission_copy
from socrat.models import (
    LearningSession,
    Submission,
)
from socrat.planner.sessions import compose


def complete_current(client, headers, view):  # noqa: F811
    if view["current"]["kind"] == "atom" and view["current"]["atom"].get("check"):
        with Session(client.app.state.engine) as db:
            row = db.get(LearningSession, view["id"])
            atom = row.payload["blocks"][view["index"]]["atom"]
            step = atom["steps"][row.payload["step"]]
            order = sessions.option_order(
                row.id, view["index"], row.payload["step"], len(step["options"])
            )
            choice = order.index(step["answer"])
        body = dict(
            block=view["index"], step=view["current"]["atom"]["check"]["step"], choice=choice
        )
        response = client.post(
            f"/api/v1/learning-sessions/{view['id']}/answer", json=body, headers=headers
        )
        assert response.status_code == 200, response.text
    body = {"block": view["index"]}
    if view["current"]["kind"] == "reflection":
        body["reflection"] = "clear"
    response = client.post(
        f"/api/v1/learning-sessions/{view['id']}/advance", json=body, headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def verified_solve(client, headers, pid):  # noqa: F811
    worker = {"Authorization": "Bearer " + WORKER}
    response = client.post(
        "/api/v1/execution/worker/heartbeat",
        json={"worker_id": "playbook-worker", "images": [p["image"] for p in profiles()]},
        headers=worker,
    )
    assert response.status_code == 200
    response = client.post(
        f"/api/v1/problems/{pid}/submit",
        json={"source": default_catalog().problem(pid).reference},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    envelope = JobEnvelope.model_validate(
        client.post(
            "/api/v1/execution/worker/claim", json={"worker_id": "playbook-worker"}, headers=worker
        ).json()["job"]
    )
    manifest = envelope.manifest
    result = ExecutionResult(
        job_id=manifest.job_id,
        nonce=manifest.nonce,
        code_hash=manifest.code_hash,
        test_digest=manifest.test_digest,
        image=manifest.image,
        operational_status="healthy",
        cases=[
            CaseResult(
                index=i,
                status="passed",
                wall_ms=5,
                stdout=(t.expected or "") if t.visibility == "public" else "",
            )
            for i, t in enumerate(envelope.tests)
        ],
        reason_code="execution_finalized",
    ).model_dump()
    response = client.post(
        "/api/v1/execution/worker/result",
        json={
            "worker_id": "playbook-worker",
            "envelope": {"result": result, "signature": sign(result, SIGNING)},
        },
        headers=worker,
    )
    assert response.status_code == 200 and response.json()["verdict"] == "accepted", response.text


def test_adapter_checker_rejects_plausible_but_wrong_output():
    with pytest.raises(ValueError, match="disagrees"):
        check_adapter(
            "python", Adapter(code="print(3)", expected="4\n"), {"python": [sys.executable]}
        )


@pytest.mark.parametrize("minutes", [10, 20, 30, 45, 60, 90])
def test_session_composer_preserves_independence_and_one_new_idea(minutes):
    catalog = default_catalog()
    blocks = compose(
        catalog,
        "basics:values",
        {},
        ["double-it"],
        minutes,
        True,
        False,
        None,
        {},
        False,
        False,
        100,
        "python",
    )
    assert len({b["concept"] for b in blocks}) == 1
    assert sum(b.get("mode") == "independent" for b in blocks) == 1
    assert sum(b["seconds"] for b in blocks) <= minutes * 60 + 10
    assert not any(b.get("mode") == "guided" for b in blocks)


def test_visible_tests_and_assistance_are_never_labelled_independent():
    public = Submission(status="done", verdict="accepted", mode="run", assistance=0)
    helped = Submission(status="done", verdict="accepted", mode="submit", assistance=3)
    independent = Submission(status="done", verdict="accepted", mode="submit", assistance=0)
    assert "independent evidence" not in submission_copy(public)
    assert "independent evidence" not in submission_copy(helped)
    assert "independent evidence" in submission_copy(independent)


def test_session_revision_prevents_lost_progress(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    view = client.post("/api/v1/learning-sessions", json={}, headers=headers).json()
    with Session(client.app.state.engine) as first, Session(client.app.state.engine) as second:
        a = first.get(LearningSession, view["id"])
        b = second.get(LearningSession, view["id"])
        a.payload = {**a.payload, "summary_viewed": 1}
        first.commit()
        b.payload = {**b.payload, "summary_viewed": 2}
        with pytest.raises(StaleDataError):
            second.commit()
        second.rollback()
    with Session(client.app.state.engine) as db:
        assert db.get(LearningSession, view["id"]).payload["summary_viewed"] == 1
