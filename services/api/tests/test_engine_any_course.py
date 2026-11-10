"""The engine serves any course, not a programming course with other words in it.

Pins the 2026-11-10 changes: nothing about DSA reaches a non-programming course's prompts, a
waiting learner is served before background work, a learner's first lesson starts when their
plan exists, and one disputed quiz item is dropped instead of costing a round.
"""

# ruff: noqa: F811
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_applied_lessons import learner_outline, outline_script, run  # noqa: F401
from test_coursegen import BRIEF
from test_learner_api import client  # noqa: F401

from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.coursegen import jobs
from socrat.coursegen import package as pkg
from socrat.coursegen.outline import GRANULARITY, Brief, architect_prompt
from socrat.models import GenerationJob


def brief(adapter: str) -> Brief:
    return Brief.model_validate(BRIEF | {"adapter": adapter})


def test_only_a_programming_course_is_shown_the_dsa_course():
    catalog = default_catalog()
    software = architect_prompt(brief("software"), catalog)
    assert "match the hand-authored DSA course" in software
    for adapter in ("math-science", "music", "general"):
        prompt = architect_prompt(brief(adapter), catalog)
        assert "DSA" not in prompt and "dsa:" not in prompt
        assert GRANULARITY in prompt
        assert len(prompt) < len(software) / 4  # the plan is asked for with a short prompt


def test_the_reference_lesson_is_for_code_courses_only():
    catalog = default_catalog()
    assert pkg.gold(catalog, catalog.course("dsa")) is not None
    reading = catalog.course("dsa").model_copy(
        update={"shape": {"studio": "reading", "loop": "read-reflect", "evidence": ["quiz"]}}
    )
    reading = type(reading).model_validate(reading.model_dump(mode="json"))
    assert pkg.gold(catalog, reading) is None


def test_a_waiting_learner_is_served_before_background_lessons(client):
    bind = client.app.state.engine
    with Session(bind) as db, db.begin():
        old = jobs.enqueue(db, "package", "course-a", {"trigger": "prefetch"}, None, "later")
        old.created_at -= 500  # queued long before the others
        ahead = jobs.enqueue(db, "package", "course-a", {"trigger": "initial"}, None, "second")
        first = jobs.enqueue(db, "package", "course-b", {"trigger": "first"}, None, "one")
        plan = jobs.enqueue(db, "outline", "course-c", {"brief": {}}, None)
        nxt = jobs.enqueue(
            db, "package", "course-d", {"trigger": "prefetch", "urgent": True}, None, "now"
        )
        nxt.created_at += 5
        order = [plan.id, first.id, nxt.id, ahead.id, old.id]
    assert [jobs.claim(bind) for _ in order] == order
    assert jobs.claim(bind) is None


def test_a_learners_first_lesson_starts_when_the_plan_is_saved(learner_outline):
    assert run(learner_outline, outline_script())
    with Session(learner_outline.app.state.engine) as db:
        saved = generated.course(db, "ai-basics")
        queued = db.scalars(select(GenerationJob).where(GenerationJob.kind == "package")).all()
    assert saved is not None
    first = saved.modules[0].concepts[0]
    assert [(j.target, j.input["trigger"], j.priority) for j in queued] == [(first, "first", 1)]


def test_it_can_be_switched_off(learner_outline):
    learner_outline.app.state.settings.gen_early_first_lesson = False
    assert run(learner_outline, outline_script())
    with Session(learner_outline.app.state.engine) as db:
        assert db.scalars(select(GenerationJob).where(GenerationJob.kind == "package")).all() == []


def test_an_unscored_dimension_is_unknown_not_a_failure():
    from test_coursegen_package import FACTS_OK, PASS, SCORES

    partial = PASS | {"scores": {k: v for k, v in SCORES.items() if k != "accessibility"}}
    passed, _, scores = pkg.verdict(FACTS_OK, partial)
    assert passed and "accessibility" not in scores
