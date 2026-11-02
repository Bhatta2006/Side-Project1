"""Adaptive quiz API behind ``adaptive_quiz_enabled`` (M3 task 14)."""

import re

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog.registry import default_catalog
from socrat.models import Evidence, ItemRating, LearnerAbility, QuizEngineSession, QuizResponse
from socrat.quiz import service

ORIGIN = "http://localhost:3000"
CONCEPT = "zero:programs-and-output"


def make_client(tmp_path, enabled):
    from alembic import command
    from alembic.config import Config
    from fastapi.testclient import TestClient

    from socrat.config import Settings
    from socrat.main import create_app

    url = f"sqlite:///{tmp_path / 'adaptive.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    settings = Settings(
        database_url=url,
        environment="test",
        dev_login_enabled=True,
        adaptive_quiz_enabled=enabled,
    )
    app = create_app(settings)
    return app, TestClient(app, base_url=ORIGIN)


@pytest.fixture
def on(tmp_path):
    app, client = make_client(tmp_path, True)
    with client:
        yield app, client
    app.state.engine.dispose()


@pytest.fixture
def off(tmp_path):
    app, client = make_client(tmp_path, False)
    with client:
        yield app, client
    app.state.engine.dispose()


def learner(client, course="zero"):
    response = client.post(
        "/api/v1/auth/dev-login",
        json={"subject": "ada", "display_name": "Ada"},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200
    headers = {"Origin": ORIGIN, "X-CSRF-Token": client.get("/api/v1/me").json()["csrf_token"]}
    client.patch("/api/v1/me", json={"birth_year": 2001, "timezone": "UTC"}, headers=headers)
    body = dict(
        course=course,
        language="python",
        level="brand-new",
        minutes_per_day=45,
        weekdays=[0, 1, 2, 3, 4, 5, 6],
    )
    assert client.post("/api/v1/enrollments", json=body, headers=headers).status_code == 200
    return headers


def correct_choice(session_id, item_key):
    cat = default_catalog()
    return service.render(cat, service.item_by_key(cat, item_key), session_id, "python")["answer"]


def test_flag_off_hides_every_route(off):
    _, client = off
    headers = learner(client)
    assert client.get("/api/v1/features").json()["adaptive_quiz"] is False
    start = client.post(
        "/api/v1/adaptive-quiz/sessions",
        json={"mode": "concept_check", "concepts": [CONCEPT]},
        headers=headers,
    )
    assert start.status_code == 404
    bad_body = client.post("/api/v1/adaptive-quiz/sessions", json={"x": 1}, headers=headers)
    assert bad_body.status_code == 404
    for path in ("next", "summary"):
        assert client.get(f"/api/v1/adaptive-quiz/sessions/abc/{path}").status_code == 404
    answer = client.post(
        "/api/v1/adaptive-quiz/sessions/abc/answer", json={"item": "abc"}, headers=headers
    )
    assert answer.status_code == 404
    # The existing concept quiz is untouched.
    assert client.get(f"/api/v1/quiz/quiz:{CONCEPT}").status_code == 200


def test_concept_check_round_trip_writes_ratings_responses_and_evidence(on):
    app, client = on
    headers = learner(client)
    assert client.get("/api/v1/features").json()["adaptive_quiz"] is True
    view = client.post(
        "/api/v1/adaptive-quiz/sessions",
        json={"mode": "concept_check", "concepts": [CONCEPT]},
        headers=headers,
    ).json()
    assert view["engine"] == "adaptive" and view["track"] == "foundations"
    session_id = view["id"]
    first = view["current"]
    assert first["concept"] == CONCEPT and first["band"] == 1  # win-first from θ 900
    assert "answer" not in first
    assert client.get(f"/api/v1/adaptive-quiz/sessions/{session_id}/next").json() == view

    keys = []
    while not view["finished"]:
        key = view["current"]["item"]
        keys.append(key)
        result = client.post(
            f"/api/v1/adaptive-quiz/sessions/{session_id}/answer",
            json={"item": key, "choice": correct_choice(session_id, key), "time_s": 12},
            headers=headers,
        ).json()
        assert result["outcome"] == "correct" and result["explanation"]
        view = result["session"]
    assert len(keys) == len(set(keys)) >= 1
    assert view["stop_reason"] in {"exhausted", "ceiling", "max_items", "stable"}

    summary = client.get(f"/api/v1/adaptive-quiz/sessions/{session_id}/summary").json()
    assert summary["finished"] and summary["evidence"]["independent"] == len(keys)
    assert summary["headline"].endswith(f"band {summary['evidence']['top_band']}")
    assert summary["patterns"][0]["theta"] > 900
    assert summary["concept_ability"][CONCEPT] == summary["patterns"][0]["theta"]

    with Session(app.state.engine) as db:
        responses = list(db.scalars(select(QuizResponse)))
        assert {r.item_id for r in responses} == set(keys)
        assert all(r.pool == "practice" and r.mode == "concept_check" for r in responses)
        evidence = list(db.scalars(select(Evidence).where(Evidence.kind == "quiz")))
        reviewed = [key for key in keys if service.item_by_key(default_catalog(), key).reviewed]
        assert len(evidence) == len(reviewed) and all(e.score == 1.0 for e in evidence)
        assert {e.details["item"] for e in evidence} == set(reviewed)
        assert all(e.activity_id == f"adaptive:concept_check:{CONCEPT}" for e in evidence)
        assert db.get(LearnerAbility, (responses[0].enrollment_id, CONCEPT)).n == len(keys)
        cat = default_catalog()
        assert all(
            db.get(ItemRating, k).d_current < service.item_by_key(cat, k).d_prior for k in keys
        )

    # A retake with nothing unseen left still asks real questions (earlier items) instead of
    # finishing empty and failing with no answers.
    again = client.post(
        "/api/v1/adaptive-quiz/sessions",
        json={"mode": "concept_check", "concepts": [CONCEPT]},
        headers=headers,
    ).json()
    assert not again["finished"] and again["current"]["item"] in keys


def test_wrong_skip_and_guard_rails(on):
    app, client = on
    headers = learner(client)
    view = client.post(
        "/api/v1/adaptive-quiz/sessions",
        json={"mode": "concept_check", "concepts": [CONCEPT]},
        headers=headers,
    ).json()
    session_id, key = view["id"], view["current"]["item"]
    url = f"/api/v1/adaptive-quiz/sessions/{session_id}"
    assert client.post(f"{url}/answer", json={"item": "nope"}, headers=headers).status_code == 409
    assert (
        client.post(f"{url}/answer", json={"item": key, "choice": 9}, headers=headers).status_code
        == 422
    )
    # Legacy items have no hint ladder.
    assert (
        client.post(f"{url}/hint", headers=headers).json()["error"]["code"] == "no_hint_available"
    )
    skipped = client.post(f"{url}/answer", json={"item": key}, headers=headers).json()
    assert skipped["outcome"] == "skipped" and skipped["explanation"] is None
    view = skipped["session"]
    if not view["finished"]:
        key = view["current"]["item"]
        wrong = (correct_choice(session_id, key) + 1) % len(view["current"]["options"])
        result = client.post(
            f"{url}/answer", json={"item": key, "choice": wrong}, headers=headers
        ).json()
        assert result["outcome"] == "wrong"
    with Session(app.state.engine) as db:
        responses = list(db.scalars(select(QuizResponse)))
        assert all(r.item_id != view["id"] for r in responses)
        assert len(responses) == (0 if view["finished"] else 1)
        evidence = list(db.scalars(select(Evidence).where(Evidence.kind == "quiz")))
        reviewed = not view["finished"] and service.item_by_key(default_catalog(), key).reviewed
        assert [e.score for e in evidence] == ([0.0] if reviewed else [])
        stored = db.get(QuizEngineSession, session_id)
        assert stored.state["steps"][0]["outcome"] == "skipped"


def test_assessment_modes_fall_back_to_the_existing_services(on):
    app, client = on
    headers = learner(client)
    for mode in ("placement", "checkpoint", "weekly"):
        result = client.post(
            "/api/v1/adaptive-quiz/sessions",
            json={"mode": mode, "concepts": [CONCEPT]},
            headers=headers,
        ).json()
        assert result == {
            "engine": "legacy",
            "reason": "assessment_pool_not_calibrated",
            "mode": mode,
        }
    with Session(app.state.engine) as db:
        assert db.scalar(select(QuizEngineSession)) is None


def test_unknown_mode_concept_or_session(on):
    _, client = on
    headers = learner(client)
    sessions = "/api/v1/adaptive-quiz/sessions"
    assert (
        client.post(
            sessions, json={"mode": "nonsense", "concepts": [CONCEPT]}, headers=headers
        ).status_code
        == 404
    )
    assert (
        client.post(
            sessions, json={"mode": "concept_check", "concepts": ["zero:nope"]}, headers=headers
        ).status_code
        == 404
    )
    assert (
        client.post(
            sessions, json={"mode": "concept_check", "concepts": ["Bad Value"]}, headers=headers
        ).status_code
        == 422
    )
    assert client.get(f"{sessions}/missing/next").status_code == 404


def test_generated_items_are_served_but_write_no_evidence_until_reviewed(on, monkeypatch):
    app, client = on
    headers = learner(client)
    # for-loops sits behind earlier lessons; open it so the engine can be exercised.
    monkeypatch.setattr(service.learn, "require_unlocked", lambda *args: None)
    view = client.post(
        "/api/v1/adaptive-quiz/sessions",
        json={"mode": "concept_check", "concepts": ["zero:for-loops"]},
        headers=headers,
    ).json()
    session_id, served = view["id"], []
    while not view["finished"]:
        key = view["current"]["item"]
        served.append(key)
        if key.startswith("quiz:"):  # a family item: generated (":s<seed>") or static
            assert view["current"]["hints_available"] == 3
        if re.fullmatch(r"quiz:zero:for-loops:accumulator:s\d+", key):
            assert view["current"]["format"] == "fill_blank"
            assert "___" in view["current"]["code"]
            if len(served) == 1 or not any(k.startswith("quiz:") for k in served[:-1]):
                hint = client.post(
                    f"/api/v1/adaptive-quiz/sessions/{session_id}/hint", headers=headers
                )
                assert hint.json()["level"] == 1 and hint.json()["remaining"] == 2
        view = client.post(
            f"/api/v1/adaptive-quiz/sessions/{session_id}/answer",
            json={"item": key, "choice": correct_choice(session_id, key)},
            headers=headers,
        ).json()["session"]
    generated = [k for k in served if k.startswith("quiz:")]  # all from unreviewed families
    assert generated, served
    with Session(app.state.engine) as db:
        responses = {r.item_id for r in db.scalars(select(QuizResponse))}
        assert set(generated) <= responses
        evidence = list(db.scalars(select(Evidence).where(Evidence.kind == "quiz")))
        assert {e.details["item"] for e in evidence} == set(served) - set(generated)
