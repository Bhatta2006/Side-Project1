"""Generation's hooks into the learner layer (generation-plug-points.md, learner-memory.md):
the outline of a private course, first lessons before the owner enrols, quiz briefs, and quiz
options tagged with the root units' misconception ids so a wrong answer is recorded as one."""

import asyncio
import sys
import types

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_brain_units import Script, offline_links, research_job  # noqa: F401
from test_course_brain import DETECTIVE, adult, ask, build, me
from test_generated_courses import ai_basics, concept
from test_learner_api import client, login  # noqa: F401

from socrat.assistant.gateway import Event, usage_event
from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.catalog.schema import QuizItem
from socrat.coursegen import jobs, keyed
from socrat.coursegen import package as pkg
from socrat.coursegen.brain import learner as learner_hook
from socrat.coursegen.brain.researcher import run_research
from socrat.coursegen.outline import Brief, brief_text
from socrat.models import Evidence, GeneratedCourse, GenerationJob

URL = "/api/v1/learning-requests"
PRIVATE = DETECTIVE + " Use my company spreadsheet as the examples."


@pytest.fixture
def brain(client):  # noqa: F811
    s = client.app.state.settings
    s.learning_requests_enabled = True
    s.course_brain = True
    s.research_providers = []
    s.research_read_pages = False
    s.gen_learner_brief = True
    return client


@pytest.fixture
def layer(monkeypatch):
    """A stand-in learner layer that records who asked for what."""
    calls: list[tuple] = []
    fake = types.ModuleType("socrat.learner")
    fake.snapshot = lambda db, enrollment, now: {"enrollment": enrollment.id}
    fake.brief = lambda snap, purpose, **_: (
        calls.append(("enrollment", purpose)) or {"patch_first": [purpose]}
    )

    def user_brief(db, user_id, now, purpose="outline"):
        calls.append(("user", purpose))
        return {"shown_elsewhere": ["Fractions"], "purpose": purpose}

    fake.user_brief = user_brief
    monkeypatch.setitem(sys.modules, "socrat.learner", fake)
    import socrat

    monkeypatch.setattr(socrat, "learner", fake, raising=False)
    return calls


def outline_prompts(app_client, course_id):
    engine, settings = app_client.app.state.engine, app_client.app.state.settings
    with Session(engine) as db:
        job_id = (
            db.scalars(
                select(GenerationJob).where(
                    GenerationJob.kind == "outline", GenerationJob.course_id == course_id
                )
            )
            .one()
            .id
        )
    seen: list[str] = []

    class Recorder:
        name = "anthropic"

        async def converse(self, system, turns, max_tokens, *args, **kwargs):
            seen.append(turns[0].content)
            yield Event("text", text="{}")  # no valid outline: the job ends, prompts are kept
            yield usage_event(10, 10)

    asyncio.run(jobs.run_outline(engine, settings, default_catalog(), job_id, lambda s: Recorder()))
    return seen


def test_a_private_course_is_planned_with_its_learners_brief(brain, layer, offline_links):  # noqa: F811
    engine, settings = brain.app.state.engine, brain.app.state.settings
    ada = login(brain, "ada", "Ada")
    adult(brain, ada)
    mine = ask(brain, ada, PRIVATE)
    with Session(engine) as db:
        job_id = research_job(db).id
    asyncio.run(run_research(engine, settings, job_id, Script().make))

    seen = outline_prompts(brain, mine["course_id"])
    assert seen and all("<learner_brief>" in p and "Fractions" in p for p in seen)
    assert ("user", "outline") in layer

    # A course the brain may share is planned from the request alone.
    bob = login(brain, "bob", "Bob")
    adult(brain, bob)
    shared = ask(brain, bob, DETECTIVE)
    layer.clear()
    seen = outline_prompts(brain, shared["course_id"])
    assert seen and not any("<learner_brief>" in p for p in seen) and layer == []


def test_the_learner_brief_is_never_stored_with_the_course():
    brief = Brief(
        id="x-course",
        title="X course",
        audience="People who want to learn X.",
        outcome="Use X on a real problem.",
        learner_brief="<learner_brief>{}</learner_brief>",
    )
    assert "<learner_brief>" in brief_text(brief)
    assert "learner_brief" not in brief.model_dump(mode="json", exclude={"learner_brief"})


def test_admin_briefs_and_shared_builds_are_not_fitted(brain, layer):
    with Session(brain.app.state.engine) as db:
        assert learner_hook.outline_block(db, None, None, 0) == ""
        assert learner_hook.builds_private(db, None) is False
        # No routing decision (brain off): the maker's course starts private to them.
        assert learner_hook.builds_private(db, "no-such-request") is True
    assert layer == []


def test_first_lessons_before_the_owner_enrols_use_the_user_brief(brain, layer):
    ada = login(brain, "ada", "Ada")
    adult(brain, ada)
    mine = ask(brain, ada, PRIVATE)
    build(brain, mine["course_id"], me(brain))
    with Session(brain.app.state.engine) as db:
        lesson = learner_hook.lesson_block(db, mine["course_id"], 0)
        quiz = learner_hook.quiz_block(db, mine["course_id"], 0)
    assert "Fractions" in lesson and "Aim wrong options" in quiz
    assert layer == [("user", "module"), ("user", "quiz")]

    # Once enrolled, the brief comes from their evidence in this course.
    published = brain.post(f"{URL}/{mine['id']}/publish", json={}, headers=ada).json()
    brain.post("/api/v1/enrollments", json=published["enroll"], headers=ada)
    layer.clear()
    with Session(brain.app.state.engine) as db:
        assert "patch_first" in learner_hook.quiz_block(db, mine["course_id"], 0)
    assert layer == [("enrollment", "quiz")]


# ------------------------------------------------------------------ misconception tags


def test_tags_that_do_not_fit_are_dropped_not_the_item():
    base = dict(
        id="q1",
        prompt="Solve 2x = 6.",
        options=["x = 3", "x = 12", "x = 4"],
        answer=0,
        explanation="Divide both sides by 2.",
        difficulty=1,
    )
    tagged = QuizItem.model_validate(
        base | {"misconceptions": ["sign_flip", "multiply_instead", ""]}
    )
    assert tagged.misconceptions == ["", "multiply_instead", ""]  # never on the answer
    assert QuizItem.model_validate(base | {"misconceptions": ["a"]}).misconceptions is None
    assert (
        QuizItem.model_validate(base | {"misconceptions": ["", "Bad Tag!", ""]}).misconceptions
        is None
    )
    shown = tagged.order("seed")
    wrong = shown.index(1)  # the display position of "x = 12"
    assert tagged.trap("seed", wrong) == "multiply_instead"
    assert tagged.trap("seed", shown.index(0)) == ""
    assert "misconceptions" not in QuizItem.model_validate(base).model_dump(exclude_none=True)


def test_marked_options_carry_tags_and_unknown_ids_are_dropped():
    raw = {
        "quiz": [
            {
                "id": "q1",
                "prompt": "Solve 2x = 6.",
                "options": [
                    {"text": "x = 3", "correct": True},
                    {"text": "x = 12", "correct": False, "misconception": "multiply_instead"},
                    {"text": "x = 4", "correct": False, "misconception": "made_up"},
                ],
                "explanation": "Divide both sides by 2.",
                "difficulty": 1,
            }
        ]
    }
    kept = pkg.keep_tags(raw, {"multiply_instead"})
    item = keyed.settle(kept["quiz"][0])
    assert item["misconceptions"] == ["", "multiply_instead", ""]
    assert QuizItem.model_validate(item).misconceptions == ["", "multiply_instead", ""]
    assert "multiply_instead" in pkg.tags_block({"multiply_instead": "times both"}, marked=True)
    assert pkg.tags_block({}, marked=True) == ""


def test_a_wrong_tagged_answer_is_recorded_as_that_misconception(brain):
    ada = login(brain, "ada", "Ada")
    adult(brain, ada)
    mine = ask(brain, ada, PRIVATE)
    course_id = mine["course_id"]
    live = concept("what-is-ml", "ideas", "live")
    for item in live["quiz"]:
        item["misconceptions"] = ["", "guess_yes_no"]  # option 1 ("no") is the trap
    course = ai_basics(
        id=course_id,
        title="Linear equations",
        concepts=[live, concept("loss", "ideas", prerequisites=["what-is-ml"])],
    )
    with Session(brain.app.state.engine) as db, db.begin():
        generated.save_course(db, default_catalog(), course, status="review")
        db.get(GeneratedCourse, course_id).owner_id = me(brain)
        for job in db.scalars(select(GenerationJob).where(GenerationJob.course_id == course_id)):
            job.state = "done"
    published = brain.post(f"{URL}/{mine['id']}/publish", json={}, headers=ada).json()
    assert (
        brain.post("/api/v1/enrollments", json=published["enroll"], headers=ada).status_code == 200
    )

    activity = f"quiz:{course_id}:what-is-ml"
    quiz = brain.get(f"/api/v1/quiz/{activity}").json()
    for question in quiz["questions"]:
        # The display position of option 1 ("no"), the tagged wrong answer.
        wrong = (
            QuizItem.model_validate(next(q for q in live["quiz"] if q["id"] == question["id"]))
            .order(quiz["id"])
            .index(1)
        )
        brain.post(
            f"/api/v1/quiz/{activity}/answer",
            json={"item": question["id"], "choice": wrong},
            headers=ada,
        )
    with Session(brain.app.state.engine) as db:
        rows = db.scalars(
            select(Evidence).where(Evidence.concept == f"{course_id}:what-is-ml")
        ).all()
        assert rows and rows[-1].details.get("misconception") == "guess_yes_no"
