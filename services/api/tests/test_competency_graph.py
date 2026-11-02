"""Competency graph and assessment contracts (master prompt 3.3 and 12.2): outlines carry
category, related concepts, required evidence, expected performance and practice; code checks
them for consistency before the critic is asked; the learner sees them with the architect's
assumptions; every assessment has a derived record of what it measures and how it is scored."""

# ruff: noqa: F811
import copy
import json

import pytest
from test_coursegen import BRIEF, OUTLINE, Scripted, admin, run  # noqa: F401
from test_learner_api import client, login  # noqa: F401

from socrat.catalog import generated
from socrat.catalog.registry import CatalogError, default_catalog
from socrat.coursegen.outline import Brief, from_course, graph_issues, to_course
from socrat.engine import assessments, domains

GRAPH = {
    "category": "both",
    "related": [],
    "evidence": ["recall", "application"],
    "expected": "Explain a model's predictions on new data in plain words.",
    "practice": ["retrieval", "worked-example"],
}


def outline_with(**fields) -> dict:
    out = copy.deepcopy(OUTLINE)
    for c in out["modules"][0]["concepts"]:
        c.update(copy.deepcopy(GRAPH) | fields)
    return out


def test_graph_fields_survive_the_round_trip():
    brief = Brief.model_validate(BRIEF)
    course = to_course(brief, outline_with(related=[]))
    concept = course.concepts[0]
    assert concept.outline.category == "both" and concept.outline.evidence == [
        "recall",
        "application",
    ]
    again = from_course(course)["modules"][0]["concepts"][0]
    assert again["practice"] == ["retrieval", "worked-example"] and again["expected"]
    plain = to_course(brief, OUTLINE).concepts[0].outline  # an older outline without them
    assert plain.category == "knowledge" and plain.evidence == [] and plain.related == []


def test_code_flags_an_inconsistent_graph():
    brief = Brief.model_validate(BRIEF)
    weak = to_course(brief, outline_with(category="skill", evidence=["recognition"]))
    assert any("needs application or performance" in i for i in graph_issues(weak))
    selfish = outline_with()
    selfish["modules"][0]["concepts"][1]["related"] = ["loss", "what-is-ml"]
    issues = graph_issues(to_course(brief, selfish))
    assert any("related to itself" in i for i in issues)
    assert any("already a prerequisite" in i for i in issues)
    music = domains.ADAPTERS["music"]
    no_doing = to_course(brief, outline_with())
    assert any("learned by doing" in i for i in graph_issues(no_doing, music))
    doing = to_course(brief, outline_with(evidence=["performance"]))
    assert graph_issues(doing, music) == []
    assert graph_issues(to_course(brief, OUTLINE), music) == []  # empty fields are not judged


def test_unknown_related_concept_is_refused_by_the_catalog():
    brief = Brief.model_validate(BRIEF)
    course = to_course(brief, outline_with(related=["zero:no-such-concept"]))
    with pytest.raises(CatalogError, match="unknown related concept"):
        generated.extend(default_catalog(), [course])
    fine = to_course(brief, outline_with(related=["zero:programs-and-output"]))
    generated.extend(default_catalog(), [fine])


def test_architect_graph_problems_go_back_to_the_architect(client, admin):
    bad = outline_with(category="skill", evidence=["recognition"])
    good = outline_with() | {"assumptions": ["Learner can use a spreadsheet"], "unresolved": []}
    client.post("/api/v1/admin/courses/briefs", json=BRIEF, headers=admin)
    script = Scripted(
        architect=[json.dumps(bad), json.dumps(good)],
        critic=[json.dumps({"verdict": "pass", "summary": "ok", "issues": []})],
    )
    assert run(client, script)
    assert "needs application or performance" in script.prompts["architect"][1]
    log = client.get("/api/v1/admin/courses/ai-basics").json()["jobs"][0]["log"]
    planned = [e for e in log if e["role"] == "architect" and "concepts" in e]
    assert planned[-1]["assumptions"] == ["Learner can use a spreadsheet"]


def test_every_assessment_has_a_derived_contract():
    catalog = default_catalog()
    with_quiz = next(k for k, c in catalog.concepts.items() if c.quiz and c.status == "live")
    records = assessments.describe(catalog.concepts[with_quiz], with_quiz)
    fields = {
        "competency",
        "id",
        "format",
        "difficulty",
        "evaluation",
        "scoring",
        "partial_credit",
        "alternates",
        "feedback",
        "assistance",
        "evidence",
    }
    assert records and all(set(r) == fields for r in records)
    assert all(r["competency"] == with_quiz for r in records)
    mcq = next(r for r in records if r["format"] == "quiz:mcq")
    assert mcq["evidence"] == "recognition" and mcq["partial_credit"] is False
    with_exercise = next((k for k, c in catalog.concepts.items() if c.exercises), None)
    if with_exercise:
        ex = [
            r
            for r in assessments.describe(catalog.concepts[with_exercise], with_exercise)
            if r["format"].startswith("exercise:")
        ]
        assert ex and all(r["evidence"] == "application" for r in ex)
