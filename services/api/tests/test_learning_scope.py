"""Curriculum boundaries, progressive questions, selected sources and ungraded lessons."""

from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.learn import service as learn
from socrat.mastery.model import ConceptState
from socrat.models import now


def test_playground_suggests_weak_topics_from_progress(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    with Session(client.app.state.engine) as db, db.begin():
        enrollment = learn.active_enrollment(db, client.get("/api/v1/me").json()["id"])
        learn.set_state(
            db,
            enrollment,
            "basics:values",
            ConceptState(alpha=1, beta=4, evidence_count=2, failures=2),
            now(),
        )
    overview = client.get("/api/v1/playground").json()
    assert overview["suggestions"][0]["id"] == "basics:values"
    assert client.get("/api/v1/playground/lessons/basics:values").status_code == 404


def test_independent_work_blocks_playground(client, monkeypatch):  # noqa: F811
    from socrat.learn import sessions

    headers = login(client)
    onboard(client, headers)
    monkeypatch.setattr(sessions, "instruction_blocked", lambda *args: True)
    assert client.get("/api/v1/playground").status_code == 423
    assert (
        client.post(
            "/api/v1/playground/generate",
            json={"confusion": "Explain binary search"},
            headers=headers,
        ).status_code
        == 423
    )


def test_roadmap_tracks_completion_from_saved_activity(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)

    def first():
        return next(
            c
            for m in client.get("/api/v1/plan").json()["modules"]
            for c in m["concepts"]
            if c["concept"] == "basics:values"
        )

    assert first()["lesson_done"] is False
    client.post("/api/v1/activities/lesson:basics:values/complete", headers=headers)
    node = first()
    assert node["lesson_done"] and not node["quiz_done"]
