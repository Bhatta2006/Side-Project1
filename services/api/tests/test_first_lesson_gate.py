# ruff: noqa: F811
"""Backlog 2.5: the first lesson of a Lesson 0 course passes a gate written in code: it fits the
session, opens with the learner's door, keeps an asked-for code language and gives them a keyed
check. Lessons not written for the learner (a shared course) are held only to the session."""

from types import SimpleNamespace as NS

from test_coursegen import BRIEF, OUTLINE
from test_coursegen_package import published, web  # noqa: F401
from test_learner_api import client  # noqa: F401

from socrat.coursegen import learner_plan as lp
from socrat.coursegen.jobs import first_lesson_issues
from socrat.coursegen.outline import Brief, to_course

PLAN = lp.LearnerPlan(
    request="Teach me machine learning in Python",
    constraints=lp.extract("Teach me machine learning in Python"),
    door="cricket scores",
    session_minutes=25,
)
BRIEF_ = Brief.model_validate(BRIEF).model_copy(update={"plan": PLAN})
COURSE = to_course(BRIEF_, OUTLINE)
GOOD = (
    "## Cricket scores\n\nA cricket scores sheet predicts the next match from past ones.\n\n"
    "```python\nprint(1)\n```\n" + "word " * 300
)


def lesson(text=GOOD, cid="what-is-ml", quiz=(1, 2, 3)):
    return NS(id=cid, lesson=text, quiz=list(quiz))


def test_a_first_lesson_that_keeps_every_promise_passes():
    assert first_lesson_issues(BRIEF_, COURSE, lesson(), personal=True) == []


def test_each_broken_promise_sends_it_back():
    no_door = GOOD.replace("Cricket scores", "Models").replace("cricket scores", "a table")
    assert "door" in first_lesson_issues(BRIEF_, COURSE, lesson(no_door), True)[0]
    late_door = "## Models\n\n" + "word " * 200 + "cricket scores"
    assert "door" in first_lesson_issues(BRIEF_, COURSE, lesson(late_door), True)[0]
    no_python = GOOD.replace("```python", "```text")
    assert (
        "show the code in python" in first_lesson_issues(BRIEF_, COURSE, lesson(no_python), True)[0]
    )
    assert "keyed check" in first_lesson_issues(BRIEF_, COURSE, lesson(quiz=()), True)[0]
    long = GOOD + "word " * 5000
    assert "takes" in first_lesson_issues(BRIEF_, COURSE, lesson(long), True)[0]


def test_only_the_first_lesson_of_a_lesson0_course_is_gated():
    bad = lesson("## Models\n\nno door here", quiz=())
    assert first_lesson_issues(BRIEF_, COURSE, NS(**{**vars(bad), "id": "loss"}), True) == []
    admin = Brief.model_validate(BRIEF)
    assert first_lesson_issues(admin, COURSE, bad, True) == []
    # Shared since (the author never saw the door): only the session still applies.
    assert first_lesson_issues(BRIEF_, COURSE, bad, personal=False) == []


def test_on_the_last_round_a_first_lesson_is_released_with_the_gate_noted(
    client,  # noqa: F811
    published,  # noqa: F811
    web,  # noqa: F811
):
    from sqlalchemy.orm import Session
    from test_coursegen_package import ATOMS, PASS, Scripted, run
    from test_coursegen_package import lesson as written
    from test_learner_api import login
    from test_learner_plan import PROBE_QUIZ, attach_plan

    from socrat.catalog import generated
    from socrat.catalog.registry import default_catalog
    from socrat.models import GenerationJob

    client.app.state.settings.gen_package_rounds = 1
    attach_plan(client)
    client.post(
        "/api/v1/admin/courses/ai-basics/concepts/generate",
        json={"concepts": ["what-is-ml"]},
        headers=login(client, subject="boss", name="Boss"),
    )
    script = Scripted(  # no door, no Python: the gate objects, but there is no round left
        author=[written()],
        quiz=[PROBE_QUIZ],
        atoms=[ATOMS],
        facts=[{"claims": []}],
        reviewer=[PASS],
    )
    assert run(client, script.make, web())
    assert generated.merged(default_catalog()).concept("ai-basics:what-is-ml").lesson
    with Session(client.app.state.engine) as db:
        log = db.query(GenerationJob).filter_by(kind="package").one().log
    waived = [e for e in log if e.get("event") == "first_lesson_gate_waived"]
    assert waived and "door" in " ".join(waived[0]["issues"])
