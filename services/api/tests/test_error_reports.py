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
        json={"message": "The run button spins forever", "route": "/problems/greeting"},
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


def report(http, headers, message, category="bug"):
    sent = http.post(
        "/api/v1/problem-reports",
        json={"message": message, "route": "/today", "category": category},
        headers=headers,
    )
    assert sent.status_code == 200


def test_admin_sees_who_reported_what_and_the_log_counts_solved(client):
    app, http = client
    bob = login(http, subject="bob", name="Bob")
    report(http, bob, "The hint button does nothing")
    report(http, bob, "Dark mode please", category="idea")
    admin = login(http)
    report(http, admin, "Typo on the plan page", category="content")

    queue = http.get("/api/v1/admin/errors").json()["items"]
    by_message = {i["message"]: i for i in queue}
    hint = by_message["[bug] The hint button does nothing"]
    assert hint["reporter"]["name"] == "Bob" and hint["category"] == "bug"
    assert hint["resolved_at"] is None

    assert http.post(f"/api/v1/admin/errors/{hint['id']}/resolve", headers=admin).status_code == 200
    [solved] = http.get("/api/v1/admin/errors?status=resolved").json()["items"]
    assert solved["id"] == hint["id"]
    assert solved["resolved_at"] and solved["resolved_by"]["name"] == "Ada"
    assert solved["thanks_seen_at"] is None
    assert hint["id"] not in {i["id"] for i in http.get("/api/v1/admin/errors").json()["items"]}

    log = http.get("/api/v1/admin/reports/log").json()
    rows = {r["reporter"]["name"]: r for r in log["reporters"]}
    assert (rows["Bob"]["reported"], rows["Bob"]["solved"], rows["Bob"]["open"]) == (2, 1, 1)
    assert (rows["Ada"]["reported"], rows["Ada"]["solved"]) == (1, 0)
    assert log["totals"] == dict(reporters=2, reported=3, solved=1, open=2)
    assert list(rows) == ["Bob", "Ada"]  # most reports first

    login(http, subject="bob", name="Bob")
    assert http.get("/api/v1/admin/reports/log").status_code == 403
    assert http.get("/api/v1/admin/errors?status=resolved").status_code == 403


def test_reporter_gets_one_thank_you_per_resolution_when_switched_on(client):
    app, http = client
    bob = login(http, subject="bob", name="Bob")
    report(http, bob, "The run button spins forever")
    admin = login(http)
    [item] = http.get("/api/v1/admin/errors").json()["items"]
    http.post(f"/api/v1/admin/errors/{item['id']}/resolve", headers=admin)

    bob = login(http, subject="bob", name="Bob")
    # Off by default: nothing to show.
    assert http.get("/api/v1/problem-reports/thanks").json() == {"items": []}

    app.state.settings = app.state.settings.model_copy(update={"report_thanks_enabled": True})
    [note] = http.get("/api/v1/problem-reports/thanks").json()["items"]
    assert note == dict(
        id=item["id"],
        category="bug",
        message="The run button spins forever",
        resolved_at=note["resolved_at"],
    )
    assert note["resolved_at"]

    # Someone else cannot dismiss Bob's note.
    carol = login(http, subject="carol", name="Carol")
    assert http.get("/api/v1/problem-reports/thanks").json() == {"items": []}
    assert http.post(
        "/api/v1/problem-reports/thanks/seen", json={"ids": [item["id"]]}, headers=carol
    ).json() == {"marked": 0}

    bob = login(http, subject="bob", name="Bob")
    assert (
        http.post("/api/v1/problem-reports/thanks/seen", json={"ids": [item["id"]]}).status_code
        == 403
    )
    assert http.post(
        "/api/v1/problem-reports/thanks/seen", json={"ids": [item["id"]]}, headers=bob
    ).json() == {"marked": 1}
    assert http.get("/api/v1/problem-reports/thanks").json() == {"items": []}

    admin = login(http)
    [seen] = http.get("/api/v1/admin/errors?status=resolved").json()["items"]
    assert seen["thanks_seen_at"]


def test_a_returning_server_error_clears_its_resolution(client):
    app, http = client
    http.get("/api/v1/test-boom")
    admin = login(http)
    [item] = http.get("/api/v1/admin/errors").json()["items"]
    http.post(f"/api/v1/admin/errors/{item['id']}/resolve", headers=admin)
    http.get("/api/v1/test-boom")
    [back] = http.get("/api/v1/admin/errors").json()["items"]
    assert back["id"] == item["id"] and back["resolved_at"] is None and back["resolved_by"] is None


def test_report_thanks_migration_downgrades_cleanly(tmp_path):
    import sqlite3

    from alembic import command
    from alembic.config import Config

    path = tmp_path / "m.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    command.upgrade(config, "head")

    def columns():
        with sqlite3.connect(path) as db:
            return {r[1] for r in db.execute("PRAGMA table_info(error_reports)")}

    assert {"resolved_at", "resolved_by", "thanks_seen_at"} <= columns()
    command.downgrade(config, "0034_launch_grants")
    assert not {"resolved_at", "resolved_by", "thanks_seen_at"} & columns()
    assert "status" in columns()
    command.upgrade(config, "head")
    assert "thanks_seen_at" in columns()
