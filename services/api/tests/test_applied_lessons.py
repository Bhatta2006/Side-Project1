"""Every module of a learner's course ends with an "Apply" lesson (flag ``gen_applied_lessons``).

Taken from Wondering's course structure (research/wondering/2026-11-05: every section ends with a
lesson marked ``isAppliedLesson``, "Apply the key ideas from <section> in a practical scenario").
"""
# ruff: noqa: F811

import copy
import json

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_coursegen import BRIEF, OUTLINE, Scripted, concept, run
from test_learner_api import client, login  # noqa: F401

from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.coursegen import applied
from socrat.coursegen.outline import Brief, graph_issues, to_course
from socrat.models import GenerationJob, User


def two_modules() -> dict:
    outline = copy.deepcopy(OUTLINE)
    outline["modules"].append(
        dict(
            id="training",
            title="Training",
            summary="How a model gets better from its loss.",
            concepts=[
                concept("gradient", ["loss"]),
                concept("step-size", ["gradient"]),
                concept("overfitting", ["gradient"]),
            ],
        )
    )
    outline["modules"].append(
        dict(
            id="wrap",
            title="Wrap up",
            summary="One closing idea on its own.",
            concepts=[concept("next-steps", ["overfitting"])],
        )
    )
    return outline


def course():
    return to_course(Brief.model_validate(BRIEF), two_modules())


def test_each_module_of_two_or_more_ends_with_an_apply_lesson():
    before = course()
    after = applied.add(before)
    ids = [c.id for c in after.concepts]
    assert ids == [
        "what-is-ml",
        "loss",
        "apply-ideas",
        "gradient",
        "step-size",
        "overfitting",
        "apply-training",
        "next-steps",  # a module of one concept has nothing to combine
    ]
    assert [m.concepts[-1] for m in after.modules] == [
        "apply-ideas",
        "apply-training",
        "next-steps",
    ]
    training = after.concept("apply-training")
    # It opens when the module is done: it needs what nothing else in the module builds on.
    assert training.prerequisites == ["step-size", "overfitting"]
    assert after.concept("apply-ideas").prerequisites == ["loss"]
    assert training.status == "planned" and training.module == "training"
    assert training.outline.assessment == ["quiz", "explain"]
    assert "transfer" in training.outline.evidence
    assert "Gradient, Step Size and Overfitting" in training.summary
    assert training.outline.misconceptions == ["More data always fixes a bad model"]
    # Code built it, so the code checks the architect's plan passes must still pass.
    assert graph_issues(after) == graph_issues(before)


def test_adding_is_idempotent_and_removing_gives_the_plan_back():
    once = applied.add(course())
    assert applied.add(once) == once
    assert applied.remove(once) == course()


@pytest.fixture
def learner_outline(client):
    """An outline job as a learner's request makes it: owned, with ``learning_request`` set."""
    client.app.state.settings.admin_subjects = ["boss"]
    admin = login(client, subject="boss", name="Boss")
    client.post("/api/v1/admin/courses/briefs", json=BRIEF, headers=admin)
    with Session(client.app.state.engine) as db, db.begin():
        owner = db.scalars(select(User).where(User.subject == "boss")).one()
        job = db.scalars(select(GenerationJob).where(GenerationJob.kind == "outline")).one()
        job.input = {**job.input, "learning_request": "req-1"}
        job.created_by = owner.id
    return client


def outline_script():
    return Scripted(
        architect=[json.dumps(two_modules())],
        critic=[json.dumps({"verdict": "pass", "summary": "ok", "issues": []})],
    )


def stored_ids(client) -> list[str]:
    with Session(client.app.state.engine) as db:
        saved = generated.course(db, "ai-basics")
    assert saved is not None
    return [c.id for c in saved.concepts]


def test_a_learner_outline_is_saved_with_apply_lessons_when_on(learner_outline):
    learner_outline.app.state.settings.gen_applied_lessons = True
    script = outline_script()
    assert run(learner_outline, script)
    assert "apply-ideas" in stored_ids(learner_outline)
    assert "apply-training" in stored_ids(learner_outline)
    # The critic judged the architect's plan, not the lessons code adds afterwards.
    assert "apply-" not in script.prompts["critic"][0]
    with Session(learner_outline.app.state.engine) as db:
        log = db.scalars(select(GenerationJob)).one().log
        saved = generated.course(db, "ai-basics")
    assert any(e.get("event") == "applied_lessons" for e in log)
    assert saved is not None and saved.concept("apply-training").status == "planned"
    # The whole course, apply lessons included, passed the catalog check on save.
    assert generated.merged(default_catalog()) is not None


def test_off_by_default_and_never_for_an_admin_course(client, learner_outline):
    assert run(learner_outline, outline_script())
    assert not any(applied.is_applied(c) for c in stored_ids(learner_outline))


def test_an_admin_course_gets_none_even_when_on(client):
    client.app.state.settings.admin_subjects = ["boss"]
    client.app.state.settings.gen_applied_lessons = True
    admin = login(client, subject="boss", name="Boss")
    client.post("/api/v1/admin/courses/briefs", json=BRIEF, headers=admin)
    assert run(client, outline_script())
    assert not any(applied.is_applied(c) for c in stored_ids(client))
