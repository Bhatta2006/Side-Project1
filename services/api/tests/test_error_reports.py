"""Error reporting: server exceptions, browser crashes and learner reports reach /admin."""

import json

import pytest
from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_learner_api import ORIGIN, login

from socrat.models import ErrorReport


@pytest.fixture
def client(tmp_path):
    from alembic import command
    from alembic.config import Config
    from fastapi.testclient import TestClient

    from socrat.config import Settings
    from socrat.main import create_app

    url = f"sqlite:///{tmp_path / 'errors.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    app = create_app(
        Settings(
            database_url=url, environment="test", dev_login_enabled=True, admin_subjects=["ada"]
        )
    )
    boom = APIRouter()

    @boom.get("/api/v1/test-boom")
    def explode():
        raise RuntimeError("the database said no")

    app.include_router(boom)
    with TestClient(app, base_url=ORIGIN, raise_server_exceptions=False) as test_client:
        yield app, test_client
    app.state.engine.dispose()


def rows(app):
    with Session(app.state.engine) as db:
        return list(db.scalars(select(ErrorReport).order_by(ErrorReport.first_at)))


def test_server_exceptions_are_grouped_and_hide_nothing_sensitive(client):
    app, http = client
    first = http.get("/api/v1/test-boom?token=secret")
    http.get("/api/v1/test-boom")
    assert first.status_code == 500
    [row] = rows(app)
    assert row.source == "server" and row.count == 2
    assert row.message == "RuntimeError: the database said no"
    assert row.route == "/api/v1/test-boom"
    assert "secret" not in json.dumps(row.detail)
    assert row.detail["request_id"]
    assert "RuntimeError" in row.detail["stack"]


def test_browser_reports_need_same_origin_and_valid_shape(client):
    app, http = client
    body = json.dumps(dict(kind="error", message="x is undefined", stack="at f", route="/today"))
    assert http.post("/api/v1/client-errors", content=body).status_code == 403
    sent = http.post("/api/v1/client-errors", content=body, headers={"Origin": ORIGIN})
    assert sent.status_code == 204
    bad = json.dumps(dict(kind="error", message="x", route="/today?email=a@b.c"))
    assert (
        http.post("/api/v1/client-errors", content=bad, headers={"Origin": ORIGIN}).status_code
        == 422
    )
    [row] = rows(app)
    assert (row.source, row.route, row.message) == ("browser", "/today", "error: x is undefined")
    assert row.user_id is None


def test_learner_reports_and_the_admin_queue(client):
    app, http = client
    headers = login(http)
    sent = http.post(
        "/api/v1/problem-reports",
        json={"message": "The run button spins forever", "route": "/problems/double-it"},
        headers=headers,
    )
    assert sent.status_code == 200
    queue = http.get("/api/v1/admin/errors").json()["items"]
    assert [i["source"] for i in queue] == ["learner"]
    assert queue[0]["message"] == "[bug] The run button spins forever"
    assert queue[0]["reporter"]
    assert http.post(f"/api/v1/admin/errors/{queue[0]['id']}/resolve", headers=headers).json()
    assert http.get("/api/v1/admin/errors").json()["items"] == []
    other = login(http, subject="bob", name="Bob")
    assert http.get("/api/v1/admin/errors").status_code == 403
    assert other


def test_error_logs_from_socrat_code_become_reports(client):
    import logging

    app, _ = client
    logging.getLogger("socrat.ai_budget").error("ai_daily_budget_reached")
    assert [r.message for r in rows(app)] == ["socrat.ai_budget: ai_daily_budget_reached"]
