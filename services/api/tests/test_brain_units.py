"""Root units: researched once per topic, validated by code, reused by later courses, pinned by
the lessons written from them, and withdrawn by quarantine. Plus the learner-layer plug point."""

import asyncio
import json
import sys
import types

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_course_brain import ALGEBRA, DETECTIVE, DRILLS, adult, ask, build, me
from test_learner_api import client, login  # noqa: F401

from socrat.assistant.gateway import Event, usage_event
from socrat.catalog.registry import default_catalog
from socrat.coursegen import jobs, links, research
from socrat.coursegen.brain import learner as learner_hook
from socrat.coursegen.brain import units as unitstore
from socrat.coursegen.brain.researcher import EXTRACTOR, run_research, validate
from socrat.coursegen.outline import Brief
from socrat.models import (
    ConceptUnitPin,
    CourseMatch,
    Enrollment,
    GeneratedConcept,
    GeneratedCourse,
    GenerationJob,
    RootUnit,
    Source,
    UnitSource,
)

URL = "/api/v1/learning-requests"
SOURCES = [{"n": 1, "title": "A", "url": "https://a.example/x"}, {"n": 2, "title": "B"}]

FOUND = {
    "sources": [
        {
            "title": "Linear equations (OpenStax)",
            "url": "https://openstax.org/books/algebra/linear",
            "role": "explain",
            "supports": "Solving one-variable linear equations by inverse operations.",
            "fit": 5,
        },
        {
            "title": "Solving equations (Wikibooks)",
            "url": "https://en.wikibooks.org/wiki/Algebra/Equations",
            "role": "examples",
            "supports": "Worked examples of two-step equations.",
            "fit": 4,
        },
    ]
}
EXTRACTED = {
    "concepts": [
        {
            "key": "two-step",
            "title": "Two-step equations",
            "summary": "Undo the last operation first.",
            "objectives": ["Solve ax + b = c for x"],
        }
    ],
    "explanations": [
        {
            "id": "balance",
            "concept": "two-step",
            "text": "Do the same to both sides.",
            "supports": [1],
        }
    ],
    "worked_examples": [
        {
            "id": "we-1",
            "concept": "two-step",
            "problem": "x + 7 = 12",
            "steps": ["subtract 7"],
            "answer": "x = 5",
            "supports": [2],
        }
    ],
    "exercise_seeds": [
        {
            "id": "seed-1",
            "concept": "two-step",
            "statement": "3x + 4 = 19",
            "answer": "x = 5",
            "check": "equation",
            "difficulty": 2,
            "error_tags": ["wrong_inverse_order"],
            "supports": [1],
        },
        {  # a wrong key: the checker must reject it
            "id": "seed-bad",
            "concept": "two-step",
            "statement": "2x + 1 = 7",
            "answer": "x = 4",
            "check": "equation",
            "supports": [1],
        },
        {  # cites a source that was never found
            "id": "seed-orphan",
            "concept": "two-step",
            "statement": "x - 2 = 3",
            "answer": "x = 5",
            "check": "equation",
            "supports": [9],
        },
    ],
    "misconceptions": [
        {
            "id": "subtract_before_divide",
            "concept": "two-step",
            "belief": "Divide first.",
            "symptom": "3x + 4 = 19 gives x = 19/3 - 4",
            "fix": "Undo addition before multiplication.",
            "supports": [1],
        }
    ],
    "probes": [],
}


def test_validation_keeps_only_supported_checked_material():
    concepts, content, problems = validate(EXTRACTED, SOURCES)
    assert [c["key"] for c in concepts] == ["two-step"]
    assert [s["id"] for s in content["exercise_seeds"]] == ["seed-1"]
    assert any("seed-bad" in p and "checker" in p for p in problems)
    assert any("seed-orphan" in p and "no supporting source" in p for p in problems)
    _, _, fatal = validate({"concepts": []}, SOURCES)
    assert "no concepts" in fatal and "no supported explanation" in fatal
    assert validate(None, SOURCES)[2] == ["the extractor did not reply with JSON"]


class Script:
    """researcher -> FOUND, extractor -> EXTRACTED; counts calls per role."""

    def __init__(self):
        self.calls = {"researcher": 0, "extractor": 0}

    def make(self, settings):
        script = self

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                role = "extractor" if system == EXTRACTOR else "researcher"
                assert system in (EXTRACTOR, research.RESEARCHER)
                script.calls[role] += 1
                # Canonical input only: no learner words reach research.
                assert "detective" not in turns[0].content.lower()
                yield Event("text", text=json.dumps(EXTRACTED if role == "extractor" else FOUND))
                yield usage_event(500, 900)

        return Provider()


@pytest.fixture
def offline_links(monkeypatch):
    async def broken(urls, client=None):  # noqa: F811
        return []

    monkeypatch.setattr(links, "broken", broken)


@pytest.fixture
def brain(client):  # noqa: F811
    client.app.state.settings.learning_requests_enabled = True
    client.app.state.settings.course_brain = True
    client.app.state.settings.research_providers = []
    client.app.state.settings.research_read_pages = False
    return client


def research_job(db):
    return db.scalars(select(GenerationJob).where(GenerationJob.kind == "research")).one()


def test_first_request_researches_the_unit_once_and_the_outline_waits(brain, offline_links):
    engine, settings = brain.app.state.engine, brain.app.state.settings
    ada = login(brain, "ada", "Ada")
    adult(brain, ada)
    first = ask(brain, ada, DETECTIVE)
    with Session(engine) as db:
        match = db.scalar(select(CourseMatch).where(CourseMatch.request_id == first["id"]))
        assert match.outcome == "extend_and_new"
        assert match.units == ["mathematics/equation-linear.beginner"]
        job = research_job(db)
        assert (job.course_id, job.target, job.priority) == (
            "root:mathematics",
            "equation-linear.beginner",
            0,
        )
        assert "detective" not in json.dumps(job.input).lower()  # canonical fields only
        outline = db.scalars(select(GenerationJob).where(GenerationJob.kind == "outline")).one()
        assert Brief.model_validate(outline.input["brief"]).units == match.units
        outline_id = outline.id

    # The outline is handed back while its research is open: nothing paid, no attempt counted.
    script = Script()
    asyncio.run(jobs.run_outline(engine, settings, default_catalog(), outline_id, script.make))
    with Session(engine) as db:
        waiting = db.get(GenerationJob, outline_id)
        assert (waiting.state, waiting.stage, waiting.attempts) == ("queued", "waiting", 0)
        assert waiting.cost_usd == 0 and script.calls == {"researcher": 0, "extractor": 0}

    # A second learner with the same topic in the same minute: the same research job.
    bob = login(brain, "bob", "Bob")
    adult(brain, bob)
    ask(brain, bob, DETECTIVE + " Please.")
    with Session(engine) as db:
        assert (
            len(db.scalars(select(GenerationJob).where(GenerationJob.kind == "research")).all())
            == 1
        )
        job_id = research_job(db).id

    asyncio.run(run_research(engine, settings, job_id, script.make))
    assert script.calls == {"researcher": 1, "extractor": 1}
    with Session(engine) as db:
        job = db.get(GenerationJob, job_id)
        assert job.state == "done" and job.output["status"] == "validated"
        unit = db.get(RootUnit, job.output["unit_id"])
        assert (unit.root_id, unit.unit_key, unit.revision) == (
            "mathematics",
            "equation-linear.beginner",
            1,
        )
        assert [s["id"] for s in unit.content["exercise_seeds"]] == ["seed-1"]
        assert len(db.scalars(select(Source)).all()) == 2
        assert {u.n for u in db.scalars(select(UnitSource))} == {1, 2}
        # Now the waiting outline gets the material in its brief.
        assert unitstore.waiting(db, [unitstore.ref("mathematics", unit.unit_key)]) == []
        block = unitstore.block(db, [unit])
        assert "seed-1" in block and "openstax.org" in block

    # A crash after research and a retry: the committed unit is reused, research is not repaid.
    with Session(engine) as db:
        unit2, job2 = unitstore.ensure(
            db, "mathematics", "equation-linear.beginner", {"topic": "equation linear"}, None
        )
        assert unit2 is not None and job2 is None


def test_a_later_course_with_another_style_is_built_from_stored_material(brain, offline_links):
    engine, settings = brain.app.state.engine, brain.app.state.settings
    ada = login(brain, "ada", "Ada")
    adult(brain, ada)
    first = ask(brain, ada, DETECTIVE)
    with Session(engine) as db:
        job_id = research_job(db).id
    asyncio.run(run_research(engine, settings, job_id, Script().make))

    drills = ask(brain, ada, DRILLS, minutes_per_day=None, goal="Pass the algebra exam.")
    with Session(engine) as db:
        match = db.scalar(select(CourseMatch).where(CourseMatch.request_id == drills["id"]))
        assert match.outcome == "from_material"
        assert match.units == ["mathematics/equation-linear.beginner"]
        assert (
            len(db.scalars(select(GenerationJob).where(GenerationJob.kind == "research")).all())
            == 1
        )
        outline = db.scalars(
            select(GenerationJob).where(
                GenerationJob.kind == "outline", GenerationJob.course_id == drills["course_id"]
            )
        ).one()
        assert outline.input["brief"]["units"] == match.units
    assert first["course_id"] != drills["course_id"]


def test_pins_and_quarantine_stop_serving_to_new_learners(brain, offline_links):
    engine, settings = brain.app.state.engine, brain.app.state.settings
    ada = login(brain, "ada", "Ada")
    adult(brain, ada)
    first = ask(brain, ada, DETECTIVE)
    with Session(engine) as db:
        job_id = research_job(db).id
    asyncio.run(run_research(engine, settings, job_id, Script().make))
    build(brain, first["course_id"], me(brain))
    brain.post(f"{URL}/{first['id']}/publish", json={}, headers=ada)
    with Session(engine) as db, db.begin():
        unit = unitstore.current(db, "mathematics", "equation-linear.beginner")
        unitstore.pin(db, first["course_id"], "what-is-ml", [unit])
        unitstore.pin(db, first["course_id"], "what-is-ml", [unit])  # idempotent
        unit_id = unit.id
    with Session(engine) as db, db.begin():
        assert len(db.scalars(select(ConceptUnitPin)).all()) == 1
        touched = unitstore.quarantine(db, unit_id, "a source was corrected")
        assert touched == [first["course_id"]]

    bob = login(brain, "bob", "Bob")
    adult(brain, bob)
    second = ask(brain, bob, DETECTIVE)
    assert second["status"] == "confirmed"  # not served the withdrawn course
    with Session(engine) as db:
        why = db.scalar(select(CourseMatch).where(CourseMatch.request_id == second["id"]))
        assert why.candidates[0]["why"].startswith("written from a withdrawn")
        # The withdrawn unit is not reused either: research runs again for a new revision.
        assert why.outcome == "extend_and_new"


def test_learner_layer_shapes_private_lessons_only(brain, monkeypatch):
    engine = brain.app.state.engine
    calls = []
    fake = types.ModuleType("socrat.learner")
    fake.snapshot = lambda db, enrollment, now: {"enrollment": enrollment.id}
    fake.brief = lambda snap, purpose, **_: calls.append(purpose) or {"patch_first": ["x"]}
    monkeypatch.setitem(sys.modules, "socrat.learner", fake)

    ada = login(brain, "ada", "Ada")
    adult(brain, ada)
    first = ask(brain, ada, DETECTIVE + " Use my company spreadsheet as the examples.")
    build(brain, first["course_id"], me(brain))
    published = brain.post(f"{URL}/{first['id']}/publish", json={}, headers=ada).json()
    assert (
        brain.post("/api/v1/enrollments", json=published["enroll"], headers=ada).status_code == 200
    )
    with Session(engine) as db:
        block = learner_hook.lesson_block(db, first["course_id"], 0)
        assert "<learner_brief>" in block and "patch_first" in block and calls == ["module"]

    bob = login(brain, "bob", "Bob")
    adult(brain, bob)
    shared = ask(brain, bob, DETECTIVE)
    build(brain, shared["course_id"], me(brain))
    brain.post(f"{URL}/{shared['id']}/publish", json={}, headers=bob)
    with Session(engine) as db:
        assert db.get(GeneratedCourse, shared["course_id"]).serve == "shared"
        assert learner_hook.lesson_block(db, shared["course_id"], 0) == ""

    # A broken layer never blocks a lesson.
    fake.brief = lambda *a, **k: 1 / 0
    with Session(engine) as db:
        assert learner_hook.lesson_block(db, first["course_id"], 0) == ""
        assert db.scalars(select(Enrollment)).first() is not None


def test_without_the_layer_installed_nothing_changes():
    if "socrat.learner" in sys.modules:
        pytest.skip("a learner layer is installed")
    assert learner_hook.layer() is None


def test_unit_keys_are_canonical():
    assert unitstore.key_of("equation linear", "beginner") == "equation-linear.beginner"
    assert unitstore.parse_ref("mathematics/equation-linear.beginner") == (
        "mathematics",
        "equation-linear.beginner",
    )
    assert ALGEBRA["domain"] == "mathematics"


def test_the_outline_is_planned_from_the_stored_material(brain, offline_links):
    engine, settings = brain.app.state.engine, brain.app.state.settings
    ada = login(brain, "ada", "Ada")
    adult(brain, ada)
    first = ask(brain, ada, DETECTIVE)
    with Session(engine) as db:
        job_id = research_job(db).id
        outline_id = (
            db.scalars(
                select(GenerationJob).where(
                    GenerationJob.kind == "outline", GenerationJob.course_id == first["course_id"]
                )
            )
            .one()
            .id
        )
    asyncio.run(run_research(engine, settings, job_id, Script().make))
    seen: list[str] = []

    class Recorder:
        name = "anthropic"

        async def converse(self, system, turns, max_tokens, *args, **kwargs):
            seen.append(turns[0].content)
            yield Event("text", text="{}")  # no valid outline: the job ends, prompts are kept
            yield usage_event(10, 10)

    asyncio.run(
        jobs.run_outline(engine, settings, default_catalog(), outline_id, lambda s: Recorder())
    )
    assert any("<subject_material>" in p and "seed-1" in p for p in seen)
    inside = [
        p.split("<subject_material>")[1].split("</subject_material>")[0]
        for p in seen
        if "<subject_material>" in p
    ]
    assert inside and not any("detective" in part.lower() for part in inside)


def test_a_correction_withdraws_researches_again_and_rewrites(brain, offline_links):
    engine, settings = brain.app.state.engine, brain.app.state.settings
    settings.admin_subjects = ["boss"]
    ada = login(brain, "ada", "Ada")
    adult(brain, ada)
    first = ask(brain, ada, DETECTIVE)
    with Session(engine) as db:
        job_id = research_job(db).id
    asyncio.run(run_research(engine, settings, job_id, Script().make))
    build(brain, first["course_id"], me(brain))
    brain.post(f"{URL}/{first['id']}/publish", json={}, headers=ada)
    with Session(engine) as db, db.begin():
        old = unitstore.current(db, "mathematics", "equation-linear.beginner")
        unitstore.pin(db, first["course_id"], "what-is-ml", [old])
        old_id = old.id

    boss = login(brain, "boss", "Boss")
    fixed = brain.post(
        f"/api/v1/admin/brain/units/{old_id}/correct",
        json={"reason": "seed-1 used the wrong sign in its hint"},
        headers=boss,
    )
    assert fixed.status_code == 200, fixed.text
    body = fixed.json()
    assert body["courses"] == [first["course_id"]]
    assert body["rewrites"] == [f"{first['course_id']}:what-is-ml"]
    audit = brain.get("/api/v1/admin/brain/units?root=mathematics", headers=boss).json()
    assert audit["items"][0]["status"] == "quarantined"
    why = brain.get(f"/api/v1/admin/brain/matches/{first['id']}", headers=boss).json()
    assert why["outcome"] == "extend_and_new" and "request" in why["private"]
    assert DETECTIVE not in json.dumps(why)  # private fields are named, never shown

    with Session(engine) as db:
        concept = db.get(GeneratedConcept, (first["course_id"], "what-is-ml"))
        assert concept.payload["status"] == "planned"  # nobody is served the old lesson
        rewrite = db.scalars(
            select(GenerationJob).where(
                GenerationJob.kind == "package",
                GenerationJob.course_id == first["course_id"],
                GenerationJob.target == "what-is-ml",
                GenerationJob.state == "queued",
            )
        ).first()
        assert rewrite.input["trigger"] == "quarantine"
        fresh = db.scalars(
            select(GenerationJob).where(
                GenerationJob.kind == "research", GenerationJob.state == "queued"
            )
        ).one()
        assert fresh.input["correction"].startswith("seed-1")
        rewrite_id, fresh_id = rewrite.id, fresh.id

    # The rewrite waits for the corrected revision instead of writing from nothing.
    asyncio.run(jobs.run_package(engine, settings, default_catalog(), rewrite_id, Script().make))
    with Session(engine) as db:
        assert db.get(GenerationJob, rewrite_id).stage == "waiting"

    script = Script()
    asyncio.run(run_research(engine, settings, fresh_id, script.make))
    with Session(engine) as db, db.begin():
        new = unitstore.current(db, "mathematics", "equation-linear.beginner")
        assert new.revision == 2 and new.quality["correction"].startswith("seed-1")
        assert unitstore.waiting(db, ["mathematics/equation-linear.beginner"]) == []
        # Rewritten from revision 2: the pin moves and the course is servable again.
        unitstore.pin(db, first["course_id"], "what-is-ml", [new])
        pins = db.scalars(select(ConceptUnitPin)).all()
        assert [p.unit_id for p in pins] == [new.id]
        assert unitstore.courses_on_quarantined_units(db, [first["course_id"]]) == set()


def test_a_routine_refresh_does_not_hold_up_new_courses(brain, offline_links):
    engine, settings = brain.app.state.engine, brain.app.state.settings
    ada = login(brain, "ada", "Ada")
    adult(brain, ada)
    ask(brain, ada, DETECTIVE)
    with Session(engine) as db:
        job_id = research_job(db).id
    asyncio.run(run_research(engine, settings, job_id, Script().make))
    with Session(engine) as db, db.begin():
        unit = unitstore.current(db, "mathematics", "equation-linear.beginner")
        unit.review_after = 1  # stale
        got, job = unitstore.ensure(
            db, "mathematics", unit.unit_key, {"topic": "equation linear"}, None
        )
        assert got is not None and job is not None and job.input["refresh"] is True
        # The stale revision is still served meanwhile: nothing waits for the refresh.
        assert unitstore.waiting(db, [unitstore.ref("mathematics", unit.unit_key)]) == []
