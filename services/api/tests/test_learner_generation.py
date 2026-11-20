"""Lesson generation fitted to the one learner a private course is written for: the real learner
layer behind generation's hook (``coursegen/brain/learner.py``, generation-plug-points.md)."""

# ruff: noqa: F811
import json

from sqlalchemy import select
from sqlalchemy.orm import Session
from test_coursegen_package import (  # noqa: F401
    ATOMS,
    FACTS_OK,
    PASS,
    QUIZ,
    Scripted,
    generate,
    lesson,
    published,
    run,
    web,
)
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.coursegen.brain import learner as learner_hook
from socrat.models import GeneratedCourse, User, now


def owned_by_ada(client, **fields):
    onboard(client, login(client, subject="ada", name="Ada"), course="ai-basics")
    with Session(client.app.state.engine) as db, db.begin():
        ada = db.scalars(select(User).where(User.subject == "ada")).one()
        course = db.get(GeneratedCourse, "ai-basics")
        course.owner_id, course.visibility = ada.id, "private"
        for name, value in fields.items():
            setattr(course, name, value)


def block(client):
    with Session(client.app.state.engine) as db:
        return learner_hook.lesson_block(db, "ai-basics", now())


def test_the_hook_finds_the_layer_and_gets_a_whole_brief(client, published):
    assert learner_hook.layer() is not None
    assert block(client) == ""  # the owner's (admin) course: nobody's private course
    owned_by_ada(client)
    text = block(client)
    body = text.split("<learner_brief>\n", 1)[1].split("\n</learner_brief>", 1)[0]
    data = json.loads(body)  # within generation's 4,000 characters, never cut mid-JSON
    assert data["purpose"] == "module" and {"skip", "patch_first", "delivery"} <= set(data)
    assert data["delivery"]["daily_minutes"] == 45


def test_a_brain_shared_course_is_never_fitted_to_one_learner(client, published):
    owned_by_ada(client, serve="shared")
    assert block(client) == ""


def test_lessons_get_the_brief_only_behind_the_flag(client, published, web):
    owned_by_ada(client)
    admin = login(client, subject="boss", name="Boss")  # Ada's sign-in replaced the session

    def written(concept):
        generate(client, admin, concept)  # may already be queued by Ada's enrolment (prefetch)
        script = Scripted(
            author=[lesson()], quiz=[QUIZ], atoms=[ATOMS], facts=[FACTS_OK], reviewer=[PASS]
        )
        assert run(client, script.make, web())
        return script.prompts["author"][0]

    assert "<learner_brief>" not in written("what-is-ml")  # flag off: unchanged
    client.app.state.settings.gen_learner_brief = True
    assert "<learner_brief>" in written("loss")
