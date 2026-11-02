"""A browser report is only a claim: with a native worker online, an accepted submit is re-run
there before it earns credit, and the native verdict is the one that stands."""

import pytest
from runner_support import SIGNING, WORKER, profiles
from test_browser_execution import expected_outputs, report
from test_learner_api import ORIGIN, login, onboard

from socrat.execution.protocol import CaseResult, ExecutionResult, JobEnvelope, sign

AUTH = {"Authorization": "Bearer " + WORKER}


@pytest.fixture
def client(tmp_path):
    from alembic import command
    from alembic.config import Config
    from fastapi.testclient import TestClient

    from socrat.config import Settings
    from socrat.main import create_app

    url = f"sqlite:///{tmp_path / 'recheck.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    settings = Settings(
        database_url=url,
        environment="test",
        dev_login_enabled=True,
        execution_profiles=profiles(),
        browser_runtimes=["python"],
        execution_signing_secret=SIGNING,
        execution_worker_secret=WORKER,
    )
    app = create_app(settings)
    with TestClient(app, base_url=ORIGIN) as test_client:
        yield test_client
    app.state.engine.dispose()


def bring_worker_online(client):
    images = [p["image"] for p in profiles()]
    client.post(
        "/api/v1/execution/worker/heartbeat",
        json={"worker_id": "w1", "images": images},
        headers=AUTH,
    )


def native_result(client, passes: bool):
    """Claim the queued native re-run and report it passed or failed."""
    claimed = client.post("/api/v1/execution/worker/claim", json={"worker_id": "w1"}, headers=AUTH)
    envelope = JobEnvelope.model_validate(claimed.json()["job"])
    manifest = envelope.manifest
    cases = [
        CaseResult(
            index=i,
            status="passed" if passes else "wrong_answer",
            wall_ms=5,
            stdout=t.expected or "" if t.visibility == "public" else "",
        )
        for i, t in enumerate(envelope.tests)
    ]
    result = ExecutionResult(
        job_id=manifest.job_id,
        nonce=manifest.nonce,
        code_hash=manifest.code_hash,
        test_digest=manifest.test_digest,
        image=manifest.image,
        operational_status="healthy",
        cases=cases,
        reason_code="execution_finalized",
    ).model_dump()
    return client.post(
        "/api/v1/execution/worker/result",
        json={
            "worker_id": "w1",
            "envelope": {"result": result, "signature": sign(result, SIGNING)},
        },
        headers=AUTH,
    )


def solved(client):
    return client.get("/api/v1/problems/greeting").json()["solved"]


def accepted_in_browser(client, headers, source="print(1)"):
    job = client.post(
        "/api/v1/problems/greeting/submit", json={"source": source}, headers=headers
    ).json()
    return job, report(client, headers, job, expected_outputs("greeting"))


def test_a_pass_the_server_can_reproduce_earns_credit_after_the_native_rerun(client):
    headers = login(client)
    onboard(client, headers)
    bring_worker_online(client)
    job, first = accepted_in_browser(client, headers)
    assert first.json()["status"] == "running" and first.json()["verdict"] == ""
    assert first.json()["verification"] == "pending"
    assert first.json()["browser"] is None, "the report was taken; it cannot be sent again"
    assert not solved(client), "no credit until the server has re-run it"

    assert native_result(client, passes=True).status_code == 200
    again = client.get(f"/api/v1/submissions/{job['id']}").json()
    assert again["verdict"] == "accepted" and again["verification"] == "native"
    assert solved(client)
    assert client.get("/api/v1/progress").json()["solves"]["independent_solves"] == 1


def test_a_claimed_pass_the_server_cannot_reproduce_is_rejected_and_earns_nothing(client):
    headers = login(client)
    onboard(client, headers)
    bring_worker_online(client)
    job, _ = accepted_in_browser(client, headers)

    native_result(client, passes=False)
    again = client.get(f"/api/v1/submissions/{job['id']}").json()
    assert again["verdict"] == "wrong_answer" and again["verification"] == "native"
    assert not solved(client)
    assert client.get("/api/v1/progress").json()["solves"]["independent_solves"] == 0


def test_an_abandoned_rerun_lets_the_browser_result_stand(client, monkeypatch):
    from socrat.judge import service as judge

    headers = login(client)
    onboard(client, headers)
    bring_worker_online(client)
    job, _ = accepted_in_browser(client, headers)
    assert not solved(client)

    # Nobody claims the re-run before its lease runs out: an outage must not punish the learner.
    import socrat.learn.routes as routes

    later = routes.now() + judge.LEASE_SECONDS + 3600
    monkeypatch.setattr(routes, "now", lambda: later)
    again = client.get(f"/api/v1/submissions/{job['id']}").json()
    assert again["verdict"] == "accepted" and again["verification"] == "browser"
    assert solved(client)


def test_without_a_native_worker_the_browser_result_stands_as_before(client):
    headers = login(client)
    onboard(client, headers)
    job, first = accepted_in_browser(client, headers)
    assert first.json()["verdict"] == "accepted" and first.json()["verification"] is None
    assert solved(client)
    assert client.get(f"/api/v1/submissions/{job['id']}").json()["verification"] is None
