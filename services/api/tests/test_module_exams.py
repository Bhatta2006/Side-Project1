"""Backlog 4.1: when a module's last lesson is released its exam is written once; code checks the
items and the set, and the module checkpoint draws on them with the concepts' own items."""
# ruff: noqa: F811

import json

from sqlalchemy.orm import Session
from test_coursegen_package import (
    ATOMS,
    PASS,
    QUIZ,
    Scripted,
    generate,
    lesson,
    published,  # noqa: F401
    run,
    web,  # noqa: F401
)
from test_learner_api import client  # noqa: F401

from socrat.assistant.gateway import Event, usage_event
from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.coursegen import exams
from socrat.learn import quizzes
from socrat.models import GenerationJob

BOTH = ["what-is-ml", "loss"]


def item(n, concepts=("what-is-ml",), difficulty=4):
    return {
        "id": f"e{n}",
        "concepts": list(concepts),
        "prompt": f"A new situation number {n}: which idea explains what happens here?",
        "options": ["The model fits its examples", "The rule was typed by hand", "Chance"],
        "answer": 0,
        "explanation": "Models fit the examples they are given; that is what learning means.",
        "difficulty": difficulty,
    }


EXAM = {"items": [item(1, BOTH), item(2, BOTH), item(3), item(4, ("loss",)), item(5)]}


def test_checks_reject_a_weak_exam():
    kept, _ = exams.check(EXAM, BOTH)
    assert len(kept) == 5 and {c for c, _ in kept} == set(BOTH)
    assert all(i.id.startswith("x-") for _, i in kept)
    unmixed = {"items": [item(n) for n in range(6)]}
    assert exams.check(unmixed, BOTH)[0] == []  # nothing combines concepts
    easy = {"items": [item(n, BOTH, difficulty=2) for n in range(6)]}
    assert exams.check(easy, BOTH)[0] == []  # an exam is harder than the lesson checks
    foreign = {"items": [*EXAM["items"][:4], item(9, ("not-in-module",))]}
    assert exams.check(foreign, BOTH)[0] == []  # only 4 usable items left


def test_the_module_exam_is_written_once_and_reaches_the_checkpoint(client, published, web):
    client.app.state.settings.gen_module_exams = True
    generate(client, published, *BOTH)
    for _ in BOTH:
        script = Scripted(
            author=[lesson()], quiz=[QUIZ], atoms=[ATOMS], facts=[{"claims": []}], reviewer=[PASS]
        )
        assert run(client, script.make, web())
    with Session(client.app.state.engine) as db:
        job = db.query(GenerationJob).filter_by(kind="exam").one()  # once, after the last
        assert (job.target, job.state) == ("ideas", "queued")

    class Provider:
        name = "anthropic"

        async def converse(self, system, turns, *args, **kwargs):
            assert system == exams.EXAM and "loss" in turns[0].content
            yield Event("text", text=json.dumps(EXAM))
            yield usage_event(100, 200)

    assert run(client, lambda settings: Provider())
    cat = generated.merged(default_catalog())
    pool = {i.id for _, i in quizzes.gate_pool(cat, "ai-basics:ideas", "python")}
    assert {"x-e1", "x-e2", "x-e3", "x-e4", "x-e5"} <= pool
    assert cat.concept("ai-basics:loss").quiz_item("x-e4").difficulty == 4
    assert exams.module_complete(cat.course("ai-basics"), "loss") is None  # has its exam


# ------------------------------------------------------------------ backlog 4.3


def test_a_lesson_without_root_units_tags_with_its_outline_misconceptions(client, published, web):
    from socrat import learner
    from socrat.coursegen import package as pkg

    client.app.state.settings.gen_outline_tags = True
    generate(client, published, "what-is-ml")
    tagged = QUIZ | {
        "quiz": [
            q | {"misconceptions": ["", "what-is-ml_m1", *[""] * (len(q["options"]) - 2)]}
            for q in QUIZ["quiz"]
        ]
    }
    script = Scripted(
        author=[lesson()], quiz=[tagged], atoms=[ATOMS], facts=[{"claims": []}], reviewer=[PASS]
    )
    assert run(client, script.make, web())
    assert "what-is-ml_m1" in script.prompts["quiz"][0]  # offered to the quiz writer
    concept = generated.merged(default_catalog()).concept("ai-basics:what-is-ml")
    assert any("what-is-ml_m1" in (q.misconceptions or []) for q in concept.quiz)
    with Session(client.app.state.engine) as db:
        beliefs = learner.misconceptions_for(db, "ai-basics:what-is-ml")
    assert beliefs["what-is-ml_m1"] == pkg.outline_tags(concept)["what-is-ml_m1"]
