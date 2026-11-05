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


def test_programming_courses_get_practice_sets_too_but_only_dsa_company_questions(client):  # noqa: F811
    headers = login(client, subject="ada", name="Ada")
    onboard(client, headers)
    overview = client.get("/api/v1/drills", headers=headers)
    assert overview.status_code == 200
    assert all(c["concept"].startswith("zero:") for c in overview.json()["concepts"])


ARRANGED = {
    "questions": [
        {
            "kind": "order",
            "prompt": "Put the steps of adding fractions in order.",
            "sequence": [
                "Find a common denominator",
                "Rewrite each fraction",
                "Add the numerators",
            ],
            "hint": "What must match first?",
            "explanation": "Parts must be the same size before you can count them together.",
        },
        {
            "kind": "match",
            "prompt": "Match each fraction to its decimal.",
            "pairs": [["1/2", "0.5"], ["1/4", "0.25"], ["3/4", "0.75"]],
            "explanation": "Divide the top by the bottom.",
        },
        {
            "kind": "number",
            "prompt": "What is 1/2 + 1/2?",
            "answer": "1",
            "explanation": "Two halves make one whole.",
        },
        {"kind": "order", "prompt": "Too short", "sequence": ["a", "b"], "explanation": "x"},
        {
            "kind": "match",
            "prompt": "Same right side twice",
            "pairs": [["a", "x"], ["b", "x"], ["c", "y"]],
            "explanation": "x",
        },
    ]
}


def test_order_and_match_questions_are_built_shuffled_and_graded_by_the_key():
    kept = service.parse(json.dumps(ARRANGED))
    # The two malformed arrangements are dropped, the sound ones kept.
    assert [q["kind"] for q in kept] == ["order", "match", "number"]
    order, match, _ = kept
    steps = ARRANGED["questions"][0]["sequence"]
    assert sorted(order["options"]) == sorted(steps) and order["options"] != steps
    assert order["answer"] == " → ".join(steps)
    # The key maps each position of the correct sequence to its place among the shown options.
    right = ",".join(str(order["options"].index(s)) for s in steps)
    assert service.correct(order, right)
    assert not service.correct(order, "0,1,2" if right != "0,1,2" else "2,1,0")
    for bad in ("", "0,1", "0,0,1", "0,1,9", "a,b,c", "0,1,2,3"):
        assert service.picks(bad, order) is None and not service.correct(order, bad)

    assert match["lefts"] == ["1/2", "1/4", "3/4"]
    pairs = {"1/2": "0.5", "1/4": "0.25", "3/4": "0.75"}
    mine = ",".join(str(match["options"].index(pairs[left])) for left in match["lefts"])
    assert service.correct(match, mine)
    swapped = mine.split(",")
    swapped[0], swapped[1] = swapped[1], swapped[0]
    assert not service.correct(match, ",".join(swapped))


def test_the_shuffle_is_stable_and_never_hands_over_the_answer():
    items = ["one", "two", "three"]
    assert service.shuffled(items, "q") == service.shuffled(items, "q")
    for seed in map(str, range(200)):
        assert service.shuffled(items, seed) != items
    assert service.shuffled(["a", "b"], "x") != ["a", "b"]


def test_an_arranged_question_is_answered_once_and_never_leaks_its_key(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr("socrat.drills.routes.require_feature", lambda *a: None)
    monkeypatch.setattr(
        "socrat.drills.routes.make_provider", lambda settings: Scripted(json.dumps(ARRANGED))
    )
    headers = login(client, subject="nia", name="Nia")
    onboard(client, headers)
    _, concept = _first_open_concept(client, headers)
    body = client.post("/api/v1/drills", json={"concept": concept}, headers=headers).json()
    assert [q["kind"] for q in body["items"]] == ["order", "match", "number"]
    shown = json.dumps(body)
    for secret in ('"key"', '"sequence"', '"pairs"', "Find a common denominator → "):
        assert secret not in shown, secret
    assert body["items"][1]["lefts"] == ["1/2", "1/4", "3/4"]

    url = f"/api/v1/drills/{body['id']}/answers"
    order = body["items"][0]["options"]
    steps = ARRANGED["questions"][0]["sequence"]
    invalid = client.post(url, json={"question": 0, "answer": "0,0,1"}, headers=headers)
    assert invalid.status_code == 404  # not counted as an answer
    right = ",".join(str(order.index(s)) for s in steps)
    done = client.post(url, json={"question": 0, "answer": right}, headers=headers).json()
    assert done["correct"] is True and done["expected"] == " → ".join(steps)
    again = client.post(url, json={"question": 0, "answer": right}, headers=headers)
    assert again.status_code == 409
    wrong = client.post(url, json={"question": 1, "answer": "0,1,2"}, headers=headers).json()
    assert wrong["expected"] == "1/2 = 0.5; 1/4 = 0.25; 3/4 = 0.75"
    # "0,1,2" can never be right for a match: the shuffle never leaves the answer in place.
    assert wrong["correct"] is False
    reread = client.get(f"/api/v1/drills/{body['id']}", headers=headers).json()
    assert reread["answered"] == 2 and reread["correct"] == 1
