"""Course shape: what a course needs to be learned (studio, practice loop, evidence)."""

import asyncio
import json

import pytest
from pydantic import ValidationError
from test_coursegen import BRIEF, OUTLINE, Scripted
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.catalog import shape
from socrat.catalog.registry import default_catalog
from socrat.coursegen import jobs
from socrat.coursegen.outline import ARCHITECT, Brief, from_course, to_course

PHYSICS = dict(
    studio="lab",
    loop="predict-observe-explain",
    evidence=["numeric", "explanation"],
    tools=["simulation", "graph"],
    label="Physics lab",
)


def test_each_studio_accepts_only_what_it_supports():
    lab = shape.CourseShape.model_validate(PHYSICS)
    assert lab.name == "Physics lab"
    assert shape.CourseShape.model_validate(PHYSICS | {"label": ""}).name == "Lab"
    for bad in (
        PHYSICS | {"loop": "solve", "evidence": ["tests"]},  # lab has no tests evidence
        PHYSICS | {"tools": ["editor"]},
        PHYSICS | {"studio": "reading"},  # reading has no simulation tools or numeric evidence
        PHYSICS | {"evidence": ["numeric", "numeric"]},
        PHYSICS | {"evidence": []},
        PHYSICS | {"studio": "score"},
    ):
        with pytest.raises(ValidationError):
            shape.CourseShape.model_validate(bad)
    math = shape.CourseShape(
        studio="workbench", loop="derive", evidence=["derivation", "numeric"], tools=["cas"]
    )
    assert math.name == "Workbench"


def test_hand_authored_courses_are_programming_courses():
    catalog = default_catalog()
    for course in catalog.courses.values():
        assert course.shape is None and shape.effective(course) == shape.CODE


def test_an_outline_must_carry_a_valid_shape_and_it_round_trips():
    brief = Brief.model_validate(BRIEF)
    no_shape = {k: v for k, v in OUTLINE.items() if k != "shape"}
    with pytest.raises(ValueError, match="missing a required field"):
        to_course(brief, no_shape)
    with pytest.raises(ValueError, match="has no tools"):
        to_course(brief, OUTLINE | {"shape": PHYSICS | {"loop": "solve", "tools": ["editor"]}})
    course = to_course(brief, OUTLINE | {"shape": PHYSICS})
    assert course.shape.studio == "lab"
    assert from_course(course)["shape"]["label"] == "Physics lab"
    assert from_course(course.model_copy(update={"shape": None}))["shape"]["studio"] == "code"


def test_the_architect_is_told_to_choose_a_shape_and_it_is_stored_and_served(client):  # noqa: F811
    client.app.state.settings.admin_subjects = ["boss"]
    admin = login(client, subject="boss", name="Boss")
    assert ARCHITECT.count('"studio": "code | workbench | lab | reading"') == 1
    client.post("/api/v1/admin/courses/briefs", json=BRIEF, headers=admin)
    script = Scripted(
        architect=[json.dumps(OUTLINE | {"shape": PHYSICS})],
        critic=[json.dumps({"verdict": "pass", "summary": "ok", "issues": []})],
    )
    state = client.app.state
    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), script.make))
    detail = client.get("/api/v1/admin/courses/ai-basics").json()
    assert detail["course"]["shape"]["studio"] == "lab"
    client.post("/api/v1/admin/courses/ai-basics/publish", headers=admin)
    cards = {c["id"]: c for c in client.get("/api/v1/courses").json()["items"]}
    assert cards["ai-basics"]["shape"]["name"] == "Physics lab"
    assert (
        cards["zero"]["shape"]["studio"] == "code" and cards["zero"]["shape"]["name"] == "Practice"
    )


def publish_physics(client, admin):  # noqa: F811
    client.post("/api/v1/admin/courses/briefs", json=BRIEF, headers=admin)
    script = Scripted(
        architect=[json.dumps(OUTLINE | {"shape": PHYSICS})],
        critic=[json.dumps({"verdict": "pass", "summary": "ok", "issues": []})],
    )
    state = client.app.state
    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), script.make))
    assert client.post("/api/v1/admin/courses/ai-basics/publish", headers=admin).status_code == 200


def test_only_admin_accounts_get_the_studio_so_other_learners_see_no_change(client):  # noqa: F811
    client.app.state.settings.admin_subjects = ["boss"]
    admin = login(client, subject="boss", name="Boss")
    publish_physics(client, admin)
    onboard(client, admin, course="ai-basics")
    mine = client.get("/api/v1/auth/status").json()["profile"]["enrollment"]
    assert mine["shape"]["studio"] == "lab" and mine["shape"]["name"] == "Physics lab"

    client.app.state.settings.style_engine_enabled = False  # the kill switch
    assert client.get("/api/v1/auth/status").json()["profile"]["enrollment"]["shape"] is None
    client.app.state.settings.style_engine_enabled = True

    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner, course="ai-basics")
    theirs = client.get("/api/v1/auth/status").json()["profile"]["enrollment"]
    assert theirs["course"] == "ai-basics" and theirs["shape"] is None
