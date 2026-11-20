"""Lesson 0 plan PR 2: a learner's course is a roadmap sized by their mode; only module 1 is
detailed with the outline, a later concept is detailed just before its first lesson."""

import asyncio
import json

import pytest
from sqlalchemy.orm import Session
from test_coursegen import BRIEF, OUTLINE, concept
from test_learner_api import client, login  # noqa: F401
from test_learner_plan import learner_request, profile

from socrat.assistant.gateway import Event, usage_event
from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.coursegen import jobs
from socrat.coursegen import learner_plan as lp
from socrat.coursegen.outline import (
    ARCHITECT,
    CRITIC,
    DETAIL_FIELDS,
    DETAILER,
    Brief,
    roadmap_issues,
    to_course,
)
from socrat.models import GeneratedCourse

DETAILED = concept("x")
STUB_KEYS = {k for k in DETAILED if k not in DETAIL_FIELDS}


def stub(cid, prerequisites=()):
    return {k: v for k, v in concept(cid, prerequisites).items() if k in STUB_KEYS}


ROADMAP = OUTLINE | {
    "modules": [
        OUTLINE["modules"][0] | {"concepts": [stub("what-is-ml"), stub("loss", ["what-is-ml"])]},
        dict(
            id="training",
            title="Training",
            summary="Ends with: train a tiny model.",
            concepts=[stub("gradient", ["loss"]), stub("overfit", ["gradient"])],
        ),
    ]
}


def details_for(prompt: str) -> dict:
    """A DETAILER reply for exactly the concepts the prompt asks for."""
    asked = json.loads(prompt.split("Write the details of these concepts:\n")[1].split("\n\n")[0])
    return {
        "concepts": [
            {"id": c["id"], **{k: v for k, v in concept(c["id"]).items() if k in DETAIL_FIELDS}}
            for c in asked
        ]
    }


class Planner:
    """architect -> ROADMAP, detailer -> details for what it is asked, critic -> pass."""

    def __init__(self, outline=ROADMAP, critic=None):
        self.outline = outline
        self.detailed: list[str] = []
        self.architect: list[str] = []
        self.detail_prompts: list[str] = []
        self.critic = list(critic or [])

    def make(self, settings):
        script = self

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                prompt = turns[0].content
                if system == ARCHITECT:
                    script.architect.append(prompt)
                    text = json.dumps(script.outline)
                elif system == DETAILER:
                    script.detail_prompts.append(prompt)
                    reply = details_for(prompt)
                    script.detailed += [c["id"] for c in reply["concepts"]]
                    text = json.dumps(reply)
                else:
                    assert system == CRITIC
                    verdict = script.critic.pop(0) if script.critic else PASSED
                    text = json.dumps(verdict)
                yield Event("text", text=text)
                yield usage_event(100, 200)

        return Provider()


PASSED = {"verdict": "pass", "summary": "ok", "issues": []}


def revise(*where):
    return {
        "verdict": "revise",
        "summary": "Needs work.",
        "issues": [{"where": w, "problem": f"{w} is thin.", "fix": f"Deepen {w}."} for w in where],
    }


def planned_brief(mode="builder"):
    plan = lp.resolve(profile()).model_copy(update={"mode": mode})
    return Brief.model_validate(BRIEF).model_copy(update={"plan": plan})


def test_a_roadmap_may_leave_later_modules_without_details_an_admin_course_may_not():
    course = to_course(
        planned_brief(), ROADMAP | {"modules": [OUTLINE["modules"][0]] + ROADMAP["modules"][1:]}
    )
    outlines = {c.id: c.outline for c in course.concepts}
    assert outlines["what-is-ml"] is not None and outlines["gradient"] is None
    with pytest.raises(ValueError, match="missing a required field"):
        to_course(Brief.model_validate(BRIEF), ROADMAP)


def test_a_roadmap_is_capped_by_the_learners_mode():
    many = ROADMAP | {
        "modules": [
            dict(ROADMAP["modules"][0], id=f"m{i}", concepts=[stub(f"c{i}-{j}") for j in range(3)])
            for i in range(5)
        ]
    }
    assert roadmap_issues(planned_brief("sprint"), many) == [
        "5 modules; this learner's roadmap has at most 4",
        "15 concepts; this learner's roadmap has at most 12",
    ]
    assert roadmap_issues(planned_brief("explorer"), many) == []
    assert roadmap_issues(Brief.model_validate(BRIEF), many) == []  # admin briefs: no caps


def test_the_outline_details_module_one_and_later_lessons_detail_their_module(
    client,  # noqa: F811
    monkeypatch,
):
    learner_request(client, monkeypatch, profile())
    state = client.app.state
    script = Planner()
    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), script.make))
    assert sorted(script.detailed) == ["loss", "what-is-ml"]  # module 1 only
    with Session(state.engine) as db:
        course = generated.course(db, "ai-basics")
        outlines = {c.id: c.outline for c in course.concepts}
        assert outlines["loss"] is not None and outlines["gradient"] is None
        brief = Brief.model_validate(db.get(GeneratedCourse, "ai-basics").brief)
    assert "at most 6 modules and 18 concepts" in script.architect[0]  # builder caps

    # Before "gradient"'s first lesson, its module is detailed (and nothing else).
    script.detailed = []
    stored = asyncio.run(
        jobs.detail_if_missing(
            state.engine,
            state.settings,
            default_catalog(),
            _job(state),
            brief,
            course,
            "gradient",
            script.make,
        )
    )
    assert script.detailed == ["gradient", "overfit"]
    found = {c.id: c for c in stored.concepts}
    assert found["gradient"].outline.objectives and found["gradient"].status == "planned"
    # Already detailed: no call.
    script.detailed = []
    asyncio.run(
        jobs.detail_if_missing(
            state.engine,
            state.settings,
            default_catalog(),
            _job(state),
            brief,
            stored,
            "gradient",
            script.make,
        )
    )
    assert script.detailed == []


def test_a_concept_that_cannot_be_detailed_fails_its_package_job(client, monkeypatch):  # noqa: F811
    learner_request(client, monkeypatch, profile())
    state = client.app.state
    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), Planner().make))

    class Silent:
        name = "anthropic"

        async def converse(self, system, turns, max_tokens, *args, **kwargs):
            yield Event("text", text=json.dumps({"concepts": []}))
            yield usage_event(10, 10)

    with Session(state.engine) as db:
        course = generated.course(db, "ai-basics")
        brief = Brief.model_validate(db.get(GeneratedCourse, "ai-basics").brief)
    with pytest.raises(ValueError, match="no details could be written"):
        asyncio.run(
            jobs.detail_if_missing(
                state.engine,
                state.settings,
                default_catalog(),
                _job(state),
                brief,
                course,
                "overfit",
                lambda s: Silent(),
            )
        )


def _job(state):
    from socrat.models import GenerationJob

    with Session(state.engine) as db:
        return db.query(GenerationJob).filter_by(kind="outline").one().id


def test_a_published_roadmap_serves_learners_before_later_modules_are_detailed(
    client,  # noqa: F811
    monkeypatch,
):
    from test_learner_api import onboard

    learner_request(client, monkeypatch, profile())
    state = client.app.state
    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), Planner().make))
    from socrat.models import GenerationJob

    with Session(state.engine) as db, db.begin():
        for job in db.query(GenerationJob).filter_by(kind="package"):
            job.state = "cancelled"  # the queued first lesson; the worker is not run here
    state.settings.admin_subjects = ["boss"]
    admin = login(client, subject="boss", name="Boss")
    published = client.post("/api/v1/admin/courses/ai-basics/publish", headers=admin)
    assert published.status_code == 200, published.text
    learner = login(client, subject="ada", name="Ada")  # the course is private to its maker
    onboard(client, learner, course="ai-basics")
    for path in (
        "/api/v1/today",
        "/api/v1/progress",
        "/api/v1/courses",
    ):
        assert client.get(path).status_code == 200, path
    # A concept with no details yet is simply not reached: locked, never an error.
    assert client.get("/api/v1/concepts/ai-basics:gradient").status_code == 423


def test_critic_notes_on_later_modules_wait_for_their_details(client, monkeypatch):  # noqa: F811
    learner_request(client, monkeypatch, profile())
    state = client.app.state
    script = Planner(critic=[revise("training", "gradient")])
    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), script.make))
    assert len(script.architect) == 1  # the learner was not held up by a rewrite
    with Session(state.engine) as db:
        course = generated.course(db, "ai-basics")
        brief = Brief.model_validate(db.get(GeneratedCourse, "ai-basics").brief)
    assert [n.split(":")[0] for n in brief.review_notes] == ["training", "gradient"]
    asyncio.run(
        jobs.detail_if_missing(
            state.engine,
            state.settings,
            default_catalog(),
            _job(state),
            brief,
            course,
            "gradient",
            script.make,
        )
    )
    assert "Deepen gradient." in script.detail_prompts[-1]


def test_a_module_one_issue_gets_one_repair_round_only(client, monkeypatch):  # noqa: F811
    learner_request(client, monkeypatch, profile())
    state = client.app.state
    script = Planner(critic=[revise("what-is-ml"), revise("what-is-ml"), revise("what-is-ml")])
    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), script.make))
    assert len(script.architect) == 2
    assert "what-is-ml is thin." in script.architect[1]
    with Session(state.engine) as db:
        assert db.get(GeneratedCourse, "ai-basics") is not None  # kept after the one repair
