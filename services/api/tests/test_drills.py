"""Practice sets: questions written for the learner's own course, graded by the server."""

import json

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.assistant.gateway import Event, ProviderError, usage_event
from socrat.drills import service
from socrat.models import ActivityRecord

SET = {
    "questions": [
        {
            "kind": "choice",
            "prompt": "Mia has 2 apples and finds 1 more. How many now?",
            "options": ["2", "3", "4"],
            "answer": "3",
            "hint": "Count on from 2.",
            "explanation": "2 and 1 more makes 3.",
        },
        {
            "kind": "number",
            "prompt": "What is half of 10 stars?",
            "answer": "5",
            "explanation": "10 split into two equal groups is 5 each.",
        },
        {
            "kind": "text",
            "prompt": "A shape with three sides is called a...?",
            "answer": "triangle",
            "accept": ["a triangle"],
            "explanation": "Tri means three.",
        },
        {"kind": "choice", "prompt": "Broken", "options": ["a"], "answer": "b", "explanation": "x"},
    ]
}


def test_answers_are_graded_exactly_and_bad_questions_are_dropped():
    kept = service.parse("Here you go:\n```json\n" + json.dumps(SET) + "\n```")
    assert [q["kind"] for q in kept] == ["choice", "number", "text"]
    choice, num, text = kept
    assert service.correct(choice, "3") and not service.correct(choice, "4")
    assert (
        service.correct(num, "5.0")
        and service.correct(num, "10/2")
        and not service.correct(num, "6")
    )
    assert service.correct(text, "Triangle!") and service.correct(text, "a  triangle")
    assert not service.correct(text, "square")
    with pytest.raises(ValueError):
        service.parse('{"questions": []}')
    with pytest.raises(ValueError):
        service.parse("no json at all")


class Scripted:
    name = "anthropic"

    def __init__(self, reply: str | None):
        self.reply = reply
        self.prompts: list[str] = []

    async def converse(self, system, turns, max_tokens, *args, **kwargs):
        self.prompts.append(system + "\n" + turns[-1].content)
        if self.reply is None:
            raise ProviderError("provider_offline")
        yield Event("text", text=self.reply)
        yield usage_event(500, 800)


def _first_open_concept(client, headers):  # noqa: F811
    from socrat.learn.routes import catalog

    cat = catalog()
    overview = client.get("/api/v1/drills", headers=headers).json()
    open_ = [c["concept"] for c in overview["concepts"] if not c["locked"]]
    assert open_ and all(c["concept"].startswith("zero:") for c in overview["concepts"])
    return cat, open_[0]


def test_a_set_is_made_for_the_learners_course_and_each_question_answered_once(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr("socrat.drills.routes.require_feature", lambda *a: None)
    script = Scripted(json.dumps(SET))
    monkeypatch.setattr("socrat.drills.routes.make_provider", lambda settings: script)
    headers = login(client, subject="mia", name="Mia")
    onboard(client, headers)
    cat, concept = _first_open_concept(client, headers)

    made = client.post("/api/v1/drills", json={"concept": concept}, headers=headers)
    assert made.status_code == 200, made.text
    body = made.json()
    assert body["source"] == "model" and body["questions"] == 3 and len(body["items"]) == 3
    assert all("expected" not in q and "explanation" not in q for q in body["items"])
    assert cat.concept(concept).title in script.prompts[0]

    wrong = client.post(
        f"/api/v1/drills/{body['id']}/answers", json={"question": 0, "answer": "4"}, headers=headers
    ).json()
    assert wrong["correct"] is False and wrong["expected"] == "3"
    again = client.post(
        f"/api/v1/drills/{body['id']}/answers", json={"question": 0, "answer": "3"}, headers=headers
    )
    assert again.status_code == 409
    right = client.post(
        f"/api/v1/drills/{body['id']}/answers", json={"question": 1, "answer": "5"}, headers=headers
    ).json()
    assert (
        right["correct"] is True and right["set"]["correct"] == 1 and right["set"]["answered"] == 2
    )

    # Another course's topic is refused, and the set never counts as a finished plan step.
    other = next(q for q in cat.concepts if q.startswith("dsa:"))
    assert (
        client.post("/api/v1/drills", json={"concept": other}, headers=headers).status_code == 404
    )
    with Session(client.app.state.engine) as db:
        row = db.scalar(select(ActivityRecord).where(ActivityRecord.activity_id.like("drill:%")))
        assert row.completed_at is None
    listed = client.get("/api/v1/drills", headers=headers).json()["sets"]
    assert [s["id"] for s in listed] == [body["id"]]


def test_without_a_model_the_topics_own_concept_checks_are_used(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr("socrat.drills.routes.require_feature", lambda *a: None)
    monkeypatch.setattr("socrat.drills.routes.make_provider", lambda settings: Scripted(None))
    headers = login(client, subject="ravi", name="Ravi")
    onboard(client, headers)
    cat, concept = _first_open_concept(client, headers)
    response = client.post("/api/v1/drills", json={"concept": concept}, headers=headers)
    fallback = service.from_concept_checks(cat.concept(concept), "python")
    if len(fallback) >= 2:
        assert response.status_code == 200 and response.json()["source"] == "checks"
    else:
        assert (
            response.status_code == 503
            and response.json()["error"]["code"] == "practice_unavailable"
        )


def test_programming_courses_practise_in_the_library_not_here(client):  # noqa: F811
    headers = login(client, subject="ada", name="Ada")
    onboard(client, headers)
    response = client.get("/api/v1/drills", headers=headers)
    assert response.status_code == 404 and response.json()["error"]["code"] == "not_in_course"
