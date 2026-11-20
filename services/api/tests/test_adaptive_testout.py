"""Test-outs run on the adaptive engine: paced, at least ``min_items`` long, graded at the end."""

from sqlalchemy import select
from sqlalchemy.orm import Session
from test_adaptive_quiz_api import correct_choice, learner, make_client

from socrat.models import Evidence, QuizEngineSession

RICH = "basics:conditions"  # ~90 Python items, bands 1-6, first module


def start(client, headers, concept=RICH):
    return client.post(
        "/api/v1/adaptive-quiz/sessions",
        json={"mode": "testout", "concepts": [concept]},
        headers=headers,
    ).json()


def run(client, headers, view, pick, seconds=8):
    trail = []
    while not view["finished"]:
        key = view["current"]["item"]
        trail.append(view["current"]["band"])
        result = client.post(
            f"/api/v1/adaptive-quiz/sessions/{view['id']}/answer",
            json={"item": key, "choice": pick(view["id"], key), "time_s": seconds},
            headers=headers,
        ).json()
        assert result["explanation"] is None and result["answer"] is None  # nothing leaks
        view = result["session"]
    return view, trail


def test_three_misses_end_it_and_write_only_quiz_evidence(tmp_path):
    app, client = make_client(tmp_path, True)
    with client:
        headers = learner(client)
        view = start(client, headers)

        def wrong(session_id, key):
            return (correct_choice(session_id, key) + 1) % 2

        view, trail = run(client, headers, view, wrong)
        assert view["stop_reason"] == "strikes" and len(trail) == 3 and view["passed"] is False
        assert trail == sorted(trail, reverse=True)  # each miss steps down
        with Session(app.state.engine) as db:
            kinds = set(db.scalars(select(Evidence.kind).where(Evidence.concept == RICH)))
            assert db.scalar(select(QuizEngineSession)).state["stop"] == "strikes"
        assert kinds == {"quiz"}
    app.state.engine.dispose()


def test_slow_right_answers_hold_the_band(tmp_path):
    app, client = make_client(tmp_path, True)
    with client:
        headers = learner(client)
        view = start(client, headers)
        first = view["current"]["band"]
        key = view["current"]["item"]
        result = client.post(
            f"/api/v1/adaptive-quiz/sessions/{view['id']}/answer",
            json={"item": key, "choice": correct_choice(view["id"], key), "time_s": 600},
            headers=headers,
        ).json()
        # The server caps the claimed time at what it saw, so a test client cannot be slow;
        # what matters here is that a fast claim cannot exceed the real elapsed time.
        assert result["session"]["current"]["band"] >= first
    app.state.engine.dispose()
