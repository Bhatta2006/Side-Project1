"""In-browser Run/Submit: the browser gets inputs only, and the server judges output digests."""

import pytest
from test_learner_api import ORIGIN, login, onboard

from socrat.catalog.registry import default_catalog
from socrat.judge.service import normalized, output_digest


@pytest.fixture
def client(tmp_path):
    from alembic import command
    from alembic.config import Config
    from fastapi.testclient import TestClient

    from socrat.config import Settings
    from socrat.main import create_app

    url = f"sqlite:///{tmp_path / 'browser.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    app = create_app(Settings(database_url=url, environment="test", dev_login_enabled=True))
    with TestClient(app, base_url=ORIGIN) as test_client:
        yield test_client
    app.state.engine.dispose()


def expected_outputs(problem_id):
    return [t.expected for t in default_catalog().problem(problem_id).tests]


def report(client, headers, job, outputs, status="executed"):
    task = job["browser"]
    cases = [
        dict(
            index=t["index"], status=status, digest=output_digest(out), wall_ms=3, stdout=out[:100]
        )
        for t, out in zip(task["tests"], outputs, strict=True)
    ]
    return client.post(
        f"/api/v1/submissions/{job['id']}/browser-result",
        json={"token": task["token"], "cases": cases},
        headers=headers,
    )


def test_runtimes_and_features_advertise_browser_languages(client):
    login(client)
    assert client.get("/api/v1/runtimes").json()["languages"] == {"python": True, "cpp": True}
    assert client.get("/api/v1/features").json()["code_execution"] is True


def test_browser_submit_gets_inputs_only_and_is_judged_by_digest(client):
    headers = login(client)
    onboard(client, headers)
    job = client.post(
        "/api/v1/problems/double-it/submit", json={"source": "print(1)"}, headers=headers
    ).json()
    assert job["status"] == "running"
    task = job["browser"]
    assert task["language"] == "python" and task["time_limit_ms"] >= 1500
    assert all(set(t) == {"index", "input"} for t in task["tests"])
    expected = expected_outputs("double-it")
    assert len(task["tests"]) == len(expected)
    assert "expected" not in str(job) and "Welcome to Socrat" not in str(job)

    wrong = report(client, headers, job, ["nope"] * len(expected))
    assert wrong.status_code == 200 and wrong.json()["verdict"] == "wrong_answer"
    # A finished job cannot be re-reported into a pass.
    again = report(client, headers, job, expected)
    assert again.json()["verdict"] == "wrong_answer"

    job = client.post(
        "/api/v1/problems/double-it/submit", json={"source": "print(2)"}, headers=headers
    ).json()
    # Trailing spaces and CRLF do not matter, as with the worker judge.
    accepted = report(client, headers, job, [o.replace("\n", "  \r\n") for o in expected])
    assert accepted.json()["verdict"] == "accepted"
    assert accepted.json()["browser"] is None
    hidden = [c for c in accepted.json()["cases"] if not c["public"]]
    assert hidden and all(c["expected"] is None and c["stdout"] is None for c in hidden)
    assert client.get("/api/v1/problems/double-it").json()["solved"]
    assert client.get("/api/v1/progress").json()["solves"]["independent_solves"] == 1


def test_browser_reports_need_the_token_owner_and_a_known_status(client):
    headers = login(client)
    onboard(client, headers)
    job = client.post(
        "/api/v1/problems/double-it/run", json={"source": "print(1)"}, headers=headers
    ).json()
    n = len(job["browser"]["tests"])
    body = dict(
        token="0" * 64,
        cases=[dict(index=i, status="executed", digest="", wall_ms=1) for i in range(n)],
    )
    url = f"/api/v1/submissions/{job['id']}/browser-result"
    assert client.post(url, json=body, headers=headers).status_code == 409
    body["token"] = job["browser"]["token"]
    body["cases"][0]["status"] = "passed"  # only the server may say "passed"
    assert client.post(url, json=body, headers=headers).status_code == 422
    body["cases"][0]["status"] = "timeout"
    assert client.post(url, json=body, headers=headers).json()["verdict"] == "timeout"

    other = login(client, subject="bob", name="Bob")
    assert client.post(url, json=body, headers=other).status_code == 404


def test_custom_input_runs_report_their_output(client):
    headers = login(client)
    onboard(client, headers)
    job = client.post(
        "/api/v1/problems/double-it/run",
        json={"source": "print(input())", "custom_input": "Ada"},
        headers=headers,
    ).json()
    assert job["browser"]["tests"] == [{"index": 0, "input": "Ada"}]
    result = report(client, headers, job, ["Ada\n"]).json()
    assert result["verdict"] == "ran" and result["cases"][0]["stdout"] == "Ada\n"


def test_normalization_matches_the_worker_judge():
    from socrat.execution.protocol import same_output

    for a, b in [("1 \r\n2\n\n", "1\n2"), (" x\n", "x\n"), ("a\rb", "a\nb")]:
        assert (normalized(a) == normalized(b)) == same_output(a, b)
