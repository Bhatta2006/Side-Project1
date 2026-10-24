"""Database-stored courses join the catalog; planned concepts show on the roadmap but are held."""

import pytest
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.catalog import generated
from socrat.catalog.registry import CatalogError, default_catalog
from socrat.catalog.schema import Concept, Course
from socrat.models import GeneratedCourse

LESSON = "## Idea\n\n" + "A model learns a rule from examples instead of being told it. " * 6


def quiz(n):
    return dict(
        id=f"q{n}",
        prompt=f"Question number {n}?",
        options=["yes", "no"],
        answer=0,
        explanation="Because the lesson says so.",
        difficulty=1,
    )


def concept(cid, module, status="planned", prerequisites=()):
    base = dict(
        id=cid,
        title=cid.replace("-", " ").title(),
        summary=f"What {cid} means and when to use it.",
        module=module,
        prerequisites=list(prerequisites),
        difficulty=1,
        estimated_minutes=30,
        status=status,
    )
    if status == "live":
        base |= dict(
            lesson=LESSON,
            key_points=["Examples in, rule out.", "More data usually helps."],
            resources=[
                dict(
                    title="Intro one",
                    url="https://example.com/a",
                    kind="article",
                    source="Ex",
                    minutes=5,
                ),
                dict(
                    title="Intro two",
                    url="https://example.com/b",
                    kind="article",
                    source="Ex",
                    minutes=5,
                ),
            ],
            quiz=[quiz(1), quiz(2)],
        )
    return base


def ai_basics(**overrides):
    return Course.model_validate(
        dict(
            id="ai-basics",
            title="AI Basics",
            tagline="What machine learning is and how models learn.",
            description="A first course on machine learning ideas, built by the pipeline.",
            version="0.1.0",
            languages=["python"],
            levels=[
                dict(id="brand-new", label="New", description="Start at the beginning."),
                dict(
                    id="knows-some", label="Some", description="Skip ahead.", start_concept="loss"
                ),
            ],
            modules=[
                dict(
                    id="ideas",
                    title="Core ideas",
                    summary="What learning from data means.",
                    concepts=["what-is-ml", "loss"],
                ),
            ],
            concepts=[
                concept("what-is-ml", "ideas", "live", ["zero:programs-and-output"]),
                concept("loss", "ideas", prerequisites=["what-is-ml"]),
            ],
        )
        | overrides
    )


@pytest.fixture
def stored(client):  # noqa: F811
    engine = client.app.state.engine
    with Session(engine) as db, db.begin():
        generated.save_course(db, default_catalog(), ai_basics())
    return engine


def test_planned_concepts_need_no_lesson_but_live_ones_do():
    assert Concept.model_validate(concept("xy", "m")).lesson == ""
    with pytest.raises(ValueError, match="needs a lesson"):
        Concept.model_validate(concept("xy", "m", status="draft"))


def test_learner_enrolls_in_a_stored_course_and_planned_lessons_are_held(client, stored):  # noqa: F811
    headers = login(client)
    assert "ai-basics" in {c["id"] for c in client.get("/api/v1/courses").json()["items"]}
    onboard(client, headers, course="ai-basics")
    plan = client.get("/api/v1/plan").json()
    statuses = {c["concept"]: c["status"] for m in plan["modules"] for c in m["concepts"]}
    assert statuses["ai-basics:loss"] == "preparing"
    assert statuses["ai-basics:what-is-ml"] != "preparing"
    assert client.get("/api/v1/concepts/ai-basics:what-is-ml").status_code == 200
    held = client.get("/api/v1/concepts/ai-basics:loss")
    assert held.status_code == 423 and held.json()["error"]["code"] == "concept_preparing"


def test_save_validates_against_the_whole_catalog(client, stored):  # noqa: F811
    base = default_catalog()
    with Session(stored) as db:
        with pytest.raises(CatalogError, match="already exists"):
            generated.save_course(db, base, ai_basics(id="dsa"))
        broken = ai_basics()
        broken.concepts[1].prerequisites.append("zero:no-such-concept")
        with pytest.raises(CatalogError, match="unknown prerequisite"):
            generated.save_course(db, base, broken)


def test_an_invalid_stored_course_leaves_the_file_courses_serving(client, stored):  # noqa: F811
    with Session(stored) as db, db.begin():
        row = db.get(GeneratedCourse, "ai-basics")
        row.payload = {**row.payload, "modules": []}
        row.updated_at += 1
    courses = {c["id"] for c in client.get("/api/v1/courses").json()["items"]}
    assert "ai-basics" not in courses and "dsa" in courses


def test_placement_skips_planned_concepts(client, stored):  # noqa: F811
    headers = login(client)
    enrollment = onboard(client, headers, course="ai-basics", level="knows-some")
    assert enrollment["status"] in {"placement", "active"}
    question = client.get("/api/v1/placement")
    assert question.status_code == 200, question.text
