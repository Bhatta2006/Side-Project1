"""The math workbench: generated exercises are verified by the harness, answers graded by it."""

import copy

from sqlalchemy import select
from sqlalchemy.orm import Session
from test_coursegen_package import web  # noqa: F401
from test_learner_api import client, login, onboard  # noqa: F401
from test_style_engine import admin_headers

from socrat.catalog.registry import default_catalog
from socrat.catalog.schema import Exercise
from socrat.coursegen import package as pkg
from socrat.models import Evidence


def exercise(**kw) -> dict:
    base = dict(
        id="expand",
        prompt="Expand (x+1)^2.",
        check="equivalent",
        expected="x^2+2*x+1",
        hints=["Multiply it out.", "Two cross terms."],
        plot=["(x+1)^2"],
        difficulty=1,
        explanation="(x+1)(x+1) = x^2 + 2x + 1.",
    )
    return base | kw


def test_exercises_are_accepted_only_when_the_checker_accepts_their_own_answers():
    good = [
        exercise(id="a"),
        exercise(id="b", check="equation", expected="x=3", plot=[]),
        exercise(id="c", check="numeric", expected="9.8", unit="m/s^2", plot=[]),
    ]
    parsed, problems = pkg.check_exercises(good)
    assert problems == [] and [e.id for e in parsed] == ["a", "b", "c"]

    bad = good + [exercise(id="d", expected="x^^2 +", plot=[])]
    _, problems = pkg.check_exercises(bad)
    assert any("exercise d" in p and "checker accepts" in p for p in problems)

    _, problems = pkg.check_exercises([exercise(id="a", plot=["import os"]), *good[1:]])
    assert any("cannot plot" in p for p in problems)
    assert pkg.check_exercises([exercise()])[1] == ["Write 3-6 exercises; got 1."]


def _catalog_with_exercises():
    cat = copy.deepcopy(default_catalog())
    first = next(
        q for q, c in cat.concepts.items() if q.startswith("zero:") and not cat.prerequisites[q]
    )
    exercises = [
        Exercise.model_validate(exercise()),
        Exercise.model_validate(exercise(id="hard", expected="x=3", check="steps", plot=[])),
    ]
    cat.concepts[first] = cat.concepts[first].model_copy(update={"exercises": exercises})
    return cat, first


def test_the_workbench_grades_with_the_harness_and_records_evidence_once(client, monkeypatch):  # noqa: F811
    cat, concept = _catalog_with_exercises()
    monkeypatch.setattr("socrat.workbench.routes.catalog", lambda: cat)
    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner)
    course, slug = concept.split(":")
    assert client.get(f"/api/v1/workbench/{course}/{slug}", headers=learner).status_code == 404

    admin = admin_headers(client)
    onboard(client, admin)
    listing = client.get(f"/api/v1/workbench/{course}/{slug}", headers=admin).json()
    assert [e["id"] for e in listing["exercises"]] == ["expand", "hard"]
    assert (
        "expected" not in listing["exercises"][0] and "explanation" not in listing["exercises"][0]
    )

    def attempt(**kw):
        body = dict(concept=concept, exercise="expand") | kw
        return client.post("/api/v1/workbench/check", json=body, headers=admin).json()

    wrong = attempt(given="x^2+1")
    assert wrong["verdict"] == "incorrect" and wrong["evidence"] is False
    right = attempt(given="x*x + 2x + 1", hints_used=1)
    assert right["verdict"] == "correct" and right["evidence"] is True
    assert "x^2" in right["explanation"]
    assert attempt(given="(x+1)^2")["evidence"] is False  # counted once
    steps = client.post(
        "/api/v1/workbench/check",
        json=dict(concept=concept, exercise="hard", lines=["2x+3=9", "2x=6", "x=3"]),
        headers=admin,
    ).json()
    assert steps["verdict"] == "correct"
    revealed = client.post(
        "/api/v1/workbench/check",
        json=dict(concept=concept, exercise="nope", give_up=True),
        headers=admin,
    )
    assert revealed.status_code == 404

    with Session(client.app.state.engine) as db:
        rows = db.scalars(select(Evidence).where(Evidence.activity_id.like("workbench:%"))).all()
        assert sorted((r.activity_id.split(":")[-1], r.score, r.assistance) for r in rows) == [
            ("expand", 1.0, 1),
            ("hard", 1.0, 0),
        ]


def test_giving_up_is_a_miss_that_shows_the_worked_solution(client, monkeypatch):  # noqa: F811
    cat, concept = _catalog_with_exercises()
    monkeypatch.setattr("socrat.workbench.routes.catalog", lambda: cat)
    admin = admin_headers(client)
    onboard(client, admin)
    out = client.post(
        "/api/v1/workbench/check",
        json=dict(concept=concept, exercise="expand", give_up=True, hints_used=2),
        headers=admin,
    ).json()
    assert out["expected"] == "x^2+2*x+1" and out["evidence"] is True
    with Session(client.app.state.engine) as db:
        row = db.scalar(select(Evidence).where(Evidence.activity_id.like("workbench:%")))
        assert row.score == 0.0 and row.assistance == 2


def test_a_math_course_is_built_with_verified_exercises_and_flawed_ones_are_sent_back(client, web):  # noqa: F811
    import asyncio
    import json

    from test_coursegen import BRIEF, OUTLINE
    from test_coursegen_package import ATOMS, FACTS_OK, PASS, QUIZ, lesson
    from test_style_engine import StyledScripted

    from socrat.assistant.gateway import Event, usage_event
    from socrat.coursegen import jobs
    from socrat.coursegen.outline import ARCHITECT

    shape = dict(studio="workbench", loop="solve", evidence=["numeric"], tools=["graph", "cas"])
    admin = admin_headers(client)
    client.post("/api/v1/admin/courses/briefs", json=BRIEF | {"budget_usd": 50}, headers=admin)
    state = client.app.state

    class Outline:
        def make(self, settings):
            class Provider:
                name = "anthropic"

                async def converse(self, system, turns, max_tokens, *args, **kwargs):
                    reply = OUTLINE | {"shape": shape}
                    if system != ARCHITECT:
                        reply = {"verdict": "pass", "summary": "ok", "issues": []}
                    yield Event("text", text=json.dumps(reply))
                    yield usage_event(1000, 2000)

            return Provider()

    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), Outline().make))
    client.post("/api/v1/admin/courses/ai-basics/publish", headers=admin)
    client.post(
        "/api/v1/admin/courses/ai-basics/concepts/generate",
        json={"concepts": ["what-is-ml"]},
        headers=admin,
    )
    flawed = QUIZ | {"exercises": [exercise(id="a"), exercise(id="b", expected="(((", plot=[])]}
    sound = QUIZ | {
        "exercises": [
            exercise(id="a"),
            exercise(id="b", check="equation", expected="x=3", plot=[]),
            exercise(id="c", expected="2*x", plot=[]),
        ]
    }
    script = StyledScripted(
        author=[lesson()],
        quiz=[flawed, sound],
        atoms=[ATOMS, ATOMS],
        facts=[FACTS_OK],
        reviewer=[PASS],
    )
    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), script.make, web()))
    assert 'Add "exercises"' in script.prompts["quiz"][0]
    assert "Write 3-6 exercises" in script.prompts["quiz"][1]
    detail = client.get("/api/v1/admin/courses/ai-basics").json()
    concept = next(c for c in detail["course"]["concepts"] if c["id"] == "what-is-ml")
    assert concept["status"] == "live" and [e["id"] for e in concept["exercises"]] == [
        "a",
        "b",
        "c",
    ]
