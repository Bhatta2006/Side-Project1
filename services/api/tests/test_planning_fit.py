"""An outline only plans activities its course's studio can produce.

First live run: two of six lessons of a children's fractions course failed every round because
the outline planned activities (a lab, a code assessment) that a maths course cannot produce,
and the reviewer kept failing the lesson for the missing activity. The plan is now fitted to
the studio when the outline is tidied, and again when the contract is shown to authors, so
outlines stored before the fix are covered too.
"""

import copy

from test_coursegen import BRIEF, OUTLINE

from socrat.catalog import shape
from socrat.catalog.registry import default_catalog
from socrat.catalog.schema import Outline
from socrat.coursegen import package as pkg
from socrat.coursegen.outline import Brief, tidy, to_course

MATHS = dict(studio="workbench", loop="solve", evidence=["numeric"], tools=["graph", "cas"])


def maths_outline() -> dict:
    outline = copy.deepcopy(OUTLINE) | {"shape": copy.deepcopy(MATHS)}
    first = outline["modules"][0]["concepts"][0]
    first["assessment"] = ["code", "quiz", "explain"]
    first["practice"] = ["lab", "problem-set", "worked-example"]
    second = outline["modules"][0]["concepts"][1]
    second["assessment"] = ["code"]
    second["practice"] = ["lab"]
    return outline


def test_tidy_drops_activities_the_studio_cannot_produce():
    tidied = tidy(maths_outline(), default_catalog())
    first, second = tidied["modules"][0]["concepts"]
    assert first["assessment"] == ["quiz", "explain"]
    assert first["practice"] == ["problem-set", "worked-example"]
    assert second["assessment"] == ["quiz"]  # never empty
    assert second["practice"] == []


def test_a_code_or_lab_course_keeps_its_own_activities():
    code = tidy(copy.deepcopy(OUTLINE) | {"modules": maths_outline()["modules"]}, default_catalog())
    assert code["modules"][0]["concepts"][0]["assessment"] == ["code", "quiz", "explain"]
    lab = dict(
        studio="lab", loop="predict-observe-explain", evidence=["numeric"], tools=["simulation"]
    )
    physics = tidy(maths_outline() | {"shape": lab}, default_catalog())
    first = physics["modules"][0]["concepts"][0]
    assert "lab" in first["practice"] and "code" not in first["assessment"]
    # A programming lab is fine in a code course.
    assert "lab" in code["modules"][0]["concepts"][0]["practice"]


def test_authors_see_a_fitted_contract_and_no_code_for_a_maths_course():
    # An outline stored before the fix: the model planned a lab and code for maths.
    raw = maths_outline()
    course = to_course(Brief.model_validate(BRIEF), tidy(raw, default_catalog()))
    planned = raw["modules"][0]["concepts"][0]
    stale = Outline.model_validate({k: planned[k] for k in Outline.model_fields if k in planned})
    concept = course.concepts[0].model_copy(update={"outline": stale})
    ctx = pkg.context(default_catalog(), course, BRIEF, concept)
    assert '"lab"' not in ctx and '"code"' not in ctx
    assert "This course has no code" in ctx and "Course code languages" not in ctx
    assert shape.producible("workbench", "practice", ["lab", "retrieval"]) == ["retrieval"]


def test_a_maths_lesson_may_not_carry_program_listings():
    course = to_course(Brief.model_validate(BRIEF), tidy(maths_outline(), default_catalog()))
    concept = course.concepts[0]
    lesson = "## A\n## B\n## C\n```python\nprint(1)\n```\n<details>x</details>" + "x" * 4000
    issues = pkg.check_lesson(concept, course, {"lesson": lesson})
    assert any("outside the course languages" in i for i in issues)
    code_course = to_course(
        Brief.model_validate(BRIEF), tidy(copy.deepcopy(OUTLINE), default_catalog())
    )
    assert not any(
        "outside the course languages" in i
        for i in pkg.check_lesson(code_course.concepts[0], code_course, {"lesson": lesson})
    )
