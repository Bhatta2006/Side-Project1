"""The engine serves any course, not a programming course with other words in it.

Pins the 2026-11-10 changes (and the 2026-11-20 removal of the reference course): no prompt
mentions a built-in course, a
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


def test_no_course_is_offered_to_the_planner_as_a_model_to_copy():
    catalog = default_catalog()
    for adapter in ("software", "math-science", "music", "general"):
        prompt = architect_prompt(brief(adapter), catalog)
        assert "DSA" not in prompt and "dsa:" not in prompt
        assert "hand-authored" not in prompt
        assert GRANULARITY in prompt
    # The same plan is asked for whatever the subject: nothing about it depends on a course.
    assert architect_prompt(brief("software"), catalog) == architect_prompt(
        brief("software"), default_catalog()
    )


def test_the_lesson_author_is_never_handed_a_reference_lesson():
    assert not hasattr(pkg, "gold") and not hasattr(pkg, "GOLD")
    prompt = pkg.lesson_prompt("Concept: loops", None, [])
    assert "hand-authored" not in prompt and "DSA" not in prompt


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


def test_an_early_lesson_steps_aside_for_a_learner_placed_further_in(learner_outline):
    from socrat.coursegen import prefetch

    assert run(learner_outline, outline_script())
    bind = learner_outline.app.state.engine
    with Session(bind) as db, db.begin():
        saved = generated.course(db, "ai-basics")
        assert saved is not None
        early = db.scalars(select(GenerationJob).where(GenerationJob.kind == "package")).one()
        later = saved.modules[-1].concepts[0]  # where a placed learner really begins
        assert early.target != later
        early_id = early.id
        queued = prefetch.initial(db, "ai-basics", later)
        assert queued[0].target == later and queued[0].input["trigger"] == "first"
        first_id = queued[0].id
    with Session(bind) as db:
        stepped = db.get(GenerationJob, early_id)
        assert stepped is not None and stepped.state == "cancelled"
    assert jobs.claim(bind) == first_id
