"""Evaluation framework (master prompt 16): the generation benchmark's archetypes and scorer, and
the observational learning-outcome report."""

# ruff: noqa: F811
import asyncio
import importlib.util
import json
from pathlib import Path

from sqlalchemy.orm import Session
from test_coursegen import BRIEF, OUTLINE
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.coursegen.outline import Brief, to_course
from socrat.engine import benchmark, domains
from socrat.models import Enrollment, Evidence, GenerationJob

DAY = 86_400


def test_the_eight_archetypes_are_covered_and_classified_to_their_domain():
    assert {r[0] for r in benchmark.REQUESTS} == {
        "children-math",
        "university-physics",
        "programming",
        "electrical",
        "music",
        "language-speaking",
        "visual-creative",
        "professional-communication",
    }
    for case, text, expected in benchmark.REQUESTS:
        assert domains.classify(text).id == expected, case


def test_the_scorer_measures_what_code_can_check_and_names_what_it_cannot():
    from test_generated_courses import concept as live_concept

    course = to_course(Brief.model_validate(BRIEF), OUTLINE)
    released = live_concept("what-is-ml", "ideas", "live", ["zero:programs-and-output"])
    from socrat.catalog.schema import Concept

    course = course.model_copy(
        update={"concepts": [Concept.model_validate(released), course.concepts[1]]}
    )
    merged = generated.extend(default_catalog(), [course])
    job = GenerationJob(
        kind="package",
        course_id=course.id,
        input={},
        cost_usd=0.4,
        log=[{"event": "released", "calls": [{"role": "author", "ms": 1200}]}],
    )
    got = benchmark.score(course, merged, "software", [job])
    assert got["concepts"] == 2 and got["released"] == 1
    assert got["prerequisite_order"] == 1.0 and got["module_coherence"] == 1.0
    assert 0 <= got["objective_quality"] <= 1
    assert got["assessment_contracts"] == 1.0  # every quiz item has a derived contract
    assert got["cost_usd"] == 0.4 and got["model_calls"] == 1 and got["model_ms"] == 1200
    assert "Factual and mathematical correctness" in got["needs_human_review"][0]


def test_benchmark_runner_lists_requests_without_a_model():
    path = Path(__file__).parents[3] / "scripts" / "dev" / "benchmark.py"
    spec = importlib.util.spec_from_file_location("bench", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    listed = asyncio.run(module.run(None, True))
    assert [r["id"] for r in listed] == [r[0] for r in benchmark.REQUESTS]
    json.dumps(listed)


def test_outcome_report_separates_independent_assisted_delayed_and_transfer(client):
    client.app.state.settings.admin_subjects = ["boss"]
    headers = login(client)
    onboard(client, headers)
    with Session(client.app.state.engine) as db, db.begin():
        enrollment = db.query(Enrollment).one()
        rows = [
            ("quiz", 1.0, 0, 0, {}),
            ("code", 0.0, 3, 1, {"misconception": "off-by-one"}),
            ("code", 1.0, 2, 2, {}),
            ("code", 1.0, 0, 3, {}),
            ("review", 1.0, 0, 6, {}),
            ("transfer", 0.0, 0, 7, {}),
        ]
        for kind, score, help_, day, details in rows:
            db.add(
                Evidence(
                    enrollment_id=enrollment.id,
                    concept="zero:programs-and-output",
                    kind=kind,
                    score=score,
                    assistance=help_,
                    activity_id=f"x:{day}",
                    created_at=1_000_000 + day * DAY,
                    details=details,
                )
            )
    admin = login(client, subject="boss", name="Boss")
    got = client.get("/api/v1/admin/engine-costs/outcomes", headers=admin).json()
    assert got["independent_success"] == 0.75 and got["assisted_success"] == 0.5
    assert got["delayed_retention"] == 1.0 and got["transfer_success"] == 0.0
    assert got["hint_level_early"] > got["hint_level_late"]
    assert got["misconception_share_early"] > got["misconception_share_late"]
    assert got["days_to_unaided_application"] == {"concepts": 1, "median": 3.0}
    assert "Observational" in got["experiment_note"]
