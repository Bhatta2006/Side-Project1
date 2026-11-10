"""A course's own sections: planned with the course, filled by each lesson, shown to the learner.

A language course has a vocabulary, history a timeline; the lesson-and-practice template has
neither. The plan declares the sections, each lesson adds entries, and the learner sees what
the lessons they have finished collected, next to the sections every course gets for free.
"""

# ruff: noqa: F811
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

from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.catalog.schema import Section
from socrat.coursegen import package as pkg
from socrat.coursegen.outline import tidy_sections
from socrat.learn import sections
from socrat.models import GeneratedCourse, need

WORDS = {
    "id": "words",
    "title": "Words you know",
    "purpose": "Every term the lessons introduced, with what it means.",
    "style": "cards",
    "fields": ["Term", "Meaning"],
}


def test_a_malformed_or_repeated_section_is_dropped_not_fatal():
    kept = tidy_sections(
        [
            WORDS,
            WORDS,  # the same id again
            {"id": "key-ideas", "title": "Key ideas", "purpose": "x" * 20, "fields": ["Idea"]},
            {"id": "Bad Id", "title": "T", "purpose": "short", "fields": []},
            "not a section",
            {**WORDS, "id": "dates", "style": "spiral", "fields": ["When", "What", "", "Why"]},
        ]
    )
    assert [s["id"] for s in kept] == ["words", "dates"]
    assert kept[1]["style"] == "list" and kept[1]["fields"] == ["When", "What", "Why"]
    assert tidy_sections(None) == [] and tidy_sections("x") == []


def test_only_entries_that_fit_a_section_are_kept():
    section = Section.model_validate(WORDS)
    kept = pkg.check_entries(
        [
            {"section": "words", "values": ["model", "A rule learned from examples"]},
            {"section": "words", "values": ["Model", "the same term again"]},
            {"section": "words", "values": ["only one value"]},
            {"section": "nope", "values": ["a", "b"]},
            {"section": "words", "values": ["loss", ""]},
            "junk",
        ],
        [section],
    )
    assert [e.values[0] for e in kept] == ["model"]
    assert pkg.check_entries(None, [section]) == []


def test_the_writer_is_asked_for_entries_only_when_the_course_has_sections():
    course = default_catalog().course("zero")
    assert pkg.entries_block(course) == ""
    with_words = type(course).model_validate(course.model_dump(mode="json") | {"sections": [WORDS]})
    block = pkg.entries_block(with_words)
    assert '"words" (Words you know)' in block and "Term, Meaning" in block


def test_a_lesson_fills_the_section_and_the_learner_sees_it_after_finishing(client, published, web):
    bind = client.app.state.engine
    with Session(bind) as db, db.begin():
        row = need(db.get(GeneratedCourse, "ai-basics"))
        row.payload = {**row.payload, "sections": [WORDS]}
    generate(client, published, "what-is-ml")
    entries = [
        {"section": "words", "values": ["model", "A rule learned from examples"]},
        {"section": "ghost", "values": ["x", "y"]},
    ]
    script = Scripted(
        author=[lesson()],
        quiz=[QUIZ | {"entries": entries}],
        atoms=[ATOMS],
        facts=[FACTS_OK],
        reviewer=[PASS],
    )
    assert run(client, script.make, web())
    assert "Words you know" in script.prompts["quiz"][0]  # the writer was told about it
    live = generated.merged(default_catalog()).concept("ai-basics:what-is-ml")
    assert [(e.section, e.values[0]) for e in live.entries] == [("words", "model")]

    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner, course="ai-basics")
    before = client.get("/api/v1/sections").json()
    # Nothing finished yet: the course's own section is listed, empty; no built-in ones.
    assert [(s["id"], s["count"]) for s in before["sections"]] == [("words", 0)]
    assert before["lessons_done"] == 0

    done = client.post("/api/v1/activities/lesson:ai-basics:what-is-ml/complete", headers=learner)
    assert done.status_code == 200
    after = client.get("/api/v1/sections").json()
    by_id = {s["id"]: s for s in after["sections"]}
    assert after["lessons_done"] == 1
    assert by_id["words"]["groups"][0]["entries"] == [
        {"values": ["model", "A rule learned from examples"]}
    ]
    assert by_id["words"]["built_in"] is False and by_id["words"]["style"] == "cards"
    assert by_id["key-ideas"]["built_in"] is True and by_id["key-ideas"]["count"] == 2
    assert by_id["sources"]["groups"][0]["entries"][0]["url"].startswith("https://")


def test_every_course_gets_the_built_in_sections_from_its_lessons():
    cat = default_catalog()
    course = cat.course("zero")
    concept = cat.concept("zero:programs-and-output")
    built = {s["id"]: s for s in sections.build(course, [concept])}
    assert built["key-ideas"]["count"] == len(concept.key_points)
    assert "formulas" not in built  # nothing to show, so it is not listed
    assert sections.build(course, []) == []
