"""Lesson 0 onboarding: goal and doors, a code-checked calibration, gentle grading, claim."""
# ruff: noqa: F811

import json

import pytest
from test_learner_api import ORIGIN, client, login  # noqa: F401
from test_learning_requests import MODEL_INTENT

from socrat import limits, onboarding
from socrat.assistant.gateway import Event, usage_event
from socrat.models import LearningRequest, OnboardingDraft

URL = "/api/v1/onboarding"
ANON = {"Origin": ORIGIN}

CALIBRATION = {
    "win": {
        "prompt": "Four friends split a 400 rupee dinner equally. How much does each pay?",
        "scene": "",
        "options": ["100 rupees", "400 rupees", "80 rupees"],
        "answer": 0,
        "nudges": [
            "",
            "That is the whole bill. Who else is paying?",
            "Close: count the friends again.",
        ],
    },
    "snag": {
        "prompt": "Asha paid the taxi, Ravi paid lunch. Which rows show only what Asha paid?",
        "scene": "who | item | cost\nAsha | taxi | 300\nRavi | lunch | 200",
        "options": ["Rows where who is Asha", "Every row with a cost", "Rows above 250"],
        "answer": 0,
        "nudges": [
            "",
            "Those are all the costs. What tells you who paid?",
            "Wrong! That is a mistake.",
        ],
        "gaps": ["", "conditional filtering", "filter by the wrong column"],
        "hint": "Look at the column that names who paid.",
    },
    "reveal": {
        "explain": "You kept only the rows where one column matched a value. That is all it takes.",
        "concept": "A filter (WHERE)",
        "real_world": "Apps use it to show only your own expenses.",
    },
}


def scripted(calibration=CALIBRATION, doors=None):
    """One provider for every onboarding call, answering by which instructions it got."""

    class Provider:
        name = "anthropic"

        async def converse(self, system, turns, max_tokens, *args, **kwargs):
            if system == onboarding.DOORS_SYSTEM:
                body = {
                    "doors": doors
                    or ["Split trip expenses", "Track cricket stats", "A movie watchlist"]
                }
            elif system == onboarding.CALIBRATION_SYSTEM:
                body = calibration
            else:
                body = MODEL_INTENT
            yield Event("text", text=json.dumps(body))
            yield usage_event(100, 200)

    provider = Provider()
    return lambda settings: provider


@pytest.fixture
def model(monkeypatch):
    limits.LIMITER.clear()
    monkeypatch.setattr(onboarding, "make", scripted())


def right(task_view, text):
    return task_view["options"].index(text)


def test_lesson0_end_to_end(client, model):
    made = client.post(
        URL, json={"text": "I want to learn SQL for my college project"}, headers=ANON
    )
    assert made.status_code == 200, made.text
    draft = made.json()
    assert draft["doors"][0] == "Split trip expenses" and draft["calibration"] == "pending"
    did = draft["id"]

    chosen = client.post(
        f"{URL}/{did}/choose", json={"mode": "builder", "door": "Split trip expenses"}, headers=ANON
    ).json()
    assert chosen["calibration"] == "ready" and chosen["snag"] is None
    assert "answer" not in chosen["win"] and "nudges" not in chosen["win"]  # the key stays here

    # Snag before the win is refused; a wrong win attempt gets a gentle nudge, not the answer.
    assert (
        client.post(
            f"{URL}/{did}/answer", json={"step": "snag", "choice": 0}, headers=ANON
        ).status_code
        == 409
    )
    wrong = right(chosen["win"], "400 rupees")
    got = client.post(
        f"{URL}/{did}/answer", json={"step": "win", "choice": wrong, "ms": 9000}, headers=ANON
    ).json()
    assert got["result"] == dict(
        correct=False, nudge="That is the whole bill. Who else is paying?", done=False, answer=None
    )
    got = client.post(
        f"{URL}/{did}/answer",
        json={"step": "win", "choice": right(chosen["win"], "100 rupees")},
        headers=ANON,
    ).json()
    assert got["result"]["correct"] and got["result"]["done"] and got["snag"] is not None

    snag = got["snag"]
    harsh = right(snag, "Rows above 250")
    got = client.post(
        f"{URL}/{did}/answer", json={"step": "snag", "choice": harsh, "ms": 20000}, headers=ANON
    ).json()
    assert got["result"]["nudge"] == onboarding.GENTLE  # the model's harsh nudge never shows
    assert client.post(f"{URL}/{did}/hint", headers=ANON).json()["hint"].startswith("Look at")
    got = client.post(
        f"{URL}/{did}/answer",
        json={
            "step": "snag",
            "choice": right(snag, "Rows where who is Asha"),
            "ms": 15000,
            "note": "only Asha",
        },
        headers=ANON,
    ).json()
    assert got["reveal"]["concept"] == "A filter (WHERE)"

    # Claiming needs an account and a birth year.
    assert client.post(f"{URL}/{did}/claim", json={"minutes": 25}, headers=ANON).status_code == 401
    ada = login(client)
    assert client.post(f"{URL}/{did}/claim", json={"minutes": 25}, headers=ada).status_code == 409
    client.patch("/api/v1/me", json={"birth_year": 2004}, headers=ada)
    assert client.post(f"{URL}/{did}/claim", json={"minutes": 7}, headers=ada).status_code == 422
    claimed = client.post(f"{URL}/{did}/claim", json={"minutes": 25}, headers=ada).json()
    req = claimed["request"]
    assert req["status"] == "confirmed" and req["course_id"]
    intent = req["intent"]
    assert intent["minutes_per_day"] == 25 and "projects" in intent["approach"]
    assert "Split trip expenses" in intent["style_request"]
    assert "filter_by_the_wrong_column" in intent["style_request"]
    # Same claim again is the same request.
    again = client.post(f"{URL}/{did}/claim", json={"minutes": 25}, headers=ada).json()
    assert again["request"]["id"] == req["id"]

    from sqlalchemy.orm import Session

    with Session(client.app.state.engine) as db:
        row = db.get(OnboardingDraft, did)
        prof = row.profile
        assert db.get(LearningRequest, req["id"]).user_id == row.user_id
    assert prof["learner_goal"]["learning_mode"] == "builder"
    assert prof["personalization"]["primary_analogy_domain"] == "Split trip expenses"
    cal = prof["calibration"]
    assert cal["outcome"] == "after_retries" and cal["used_hint"] and cal["explained_thinking"]
    assert cal["detected_gaps"] == ["filter_by_the_wrong_column"]
    assert prof["meta"]["profile_confidence"] == "low_initial_draft"
    assert prof["meta"]["schema"] == onboarding.PROFILE_SCHEMA
    with Session(client.app.state.engine) as db:
        assert onboarding.profile_for(db, req["id"]) == prof  # what generation reads
        assert onboarding.profile_for(db, "no-such-request") is None

    # Once claimed, the draft is that learner's alone.
    client.cookies.clear()
    assert client.get(f"{URL}/{did}").status_code == 404


def test_without_a_model_nothing_is_invented(client):
    limits.LIMITER.clear()
    draft = client.post(
        URL, json={"text": "Teach me how stock investing works"}, headers=ANON
    ).json()
    assert draft["source"] == "rules" and draft["doors"] == onboarding.FALLBACK_DOORS
    chosen = client.post(
        f"{URL}/{draft['id']}/choose",
        json={"mode": "explorer", "door": "Money and shopping"},
        headers=ANON,
    ).json()
    assert chosen["calibration"] == "none" and chosen["win"] is None
    ada = login(client)
    client.patch("/api/v1/me", json={"birth_year": 2000}, headers=ada)
    got = client.post(f"{URL}/{draft['id']}/claim", json={"minutes": 10}, headers=ada).json()
    assert got["request"]["status"] == "confirmed"


def test_the_checks_reject_what_a_learner_must_not_see():
    good = onboarding.check_calibration(json.loads(json.dumps(CALIBRATION)), "seed")
    task = good["snag"]
    assert task["options"][task["answer"]] == "Rows where who is Asha"
    assert task["gaps"][task["answer"]] == ""

    leaky = json.loads(json.dumps(CALIBRATION))
    leaky["win"]["options"][0] = "100 rupees each, because 400 divided by 4 friends is exactly 100"
    with pytest.raises(ValueError, match="gives itself away"):
        onboarding.check_calibration(leaky, "seed")

    wordy = json.loads(json.dumps(CALIBRATION))
    wordy["win"]["prompt"] = "One. Two. Three. Four."
    with pytest.raises(ValueError, match="too long"):
        onboarding.check_calibration(wordy, "seed")

    assert onboarding.check_doors({"doors": ["a"]}) == []
    assert (
        len(onboarding.check_doors({"doors": ["Cricket", "Cooking", "Trips", "Games", "More"]}))
        == 4
    )


def test_visitors_are_rate_limited(client, model):
    client.app.state.settings.onboarding_per_hour = 2
    for _ in range(2):
        assert (
            client.post(URL, json={"text": "Teach me chess openings"}, headers=ANON).status_code
            == 200
        )
    assert (
        client.post(URL, json={"text": "Teach me chess openings"}, headers=ANON).status_code == 429
    )


def test_the_goal_is_read_in_the_background_and_a_block_still_stops_the_flow(
    client, model, monkeypatch
):
    import asyncio

    from sqlalchemy.orm import Session

    draft = client.post(URL, json={"text": "Teach me quantum mechanics"}, headers=ANON).json()
    assert draft["source"] == "rules"  # the doors do not wait for the reading
    eng, settings = client.app.state.engine, client.app.state.settings
    asyncio.run(onboarding.read_goal(eng, settings, draft["id"], "Teach me quantum mechanics"))
    with Session(eng) as db:
        row = db.get(OnboardingDraft, draft["id"])
        assert row.source == "model" and row.intent["subject"] == "Quantum mechanics"

    blocked = dict(MODEL_INTENT, blocked="seeks help to harm people")
    harmful = client.post(URL, json={"text": "something harmful"}, headers=ANON).json()

    class Blocked:
        name = "anthropic"

        async def converse(self, system, turns, max_tokens, *args, **kwargs):
            yield Event("text", text=json.dumps(blocked))
            yield usage_event(10, 10)

    monkeypatch.setattr(onboarding, "make", lambda settings: Blocked())
    asyncio.run(onboarding.read_goal(eng, settings, harmful["id"], "something harmful"))
    got = client.post(
        f"{URL}/{harmful['id']}/choose", json={"mode": "sprint", "door": "Anything"}, headers=ANON
    )
    assert got.status_code == 422


def test_an_unknown_choice_in_the_model_reply_is_dropped_not_fatal():
    from socrat.coursegen import intent as intents

    reply = dict(MODEL_INTENT, code_languages=["sql", "python"], approach=["projects", "videos"])
    got = intents.Intent.model_validate(intents._soften(reply))
    assert got.code_languages == ["python"] and got.approach == ["projects"]


def test_vertex_low_effort_roles_think_little():
    from socrat.assistant.vertex import VertexProvider
    from socrat.config import Settings

    base = Settings(ai_provider="offline")
    think = lambda **kw: VertexProvider(base.model_copy(update=kw), client=object())._thinking()  # noqa: E731
    assert think(ai_effort="low") == "low"
    assert think(ai_effort="medium") == ""  # the tutor keeps the model's default
    assert think(ai_effort="low", vertex_thinking_level="high") == "high"  # configured wins


def test_a_visitor_never_waits_the_generation_timeout():
    from socrat.config import Settings
    from socrat.coursegen import roles

    base = Settings(ai_provider="offline")
    assert roles.role_settings(base, "onboarding").ai_timeout_seconds == 25
    assert roles.role_settings(base, "architect").ai_timeout_seconds == base.gen_timeout_seconds
