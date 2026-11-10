"""A course's own sections: what the learner has collected so far, lesson by lesson.

Courses differ in more than their lessons. A language course has a vocabulary, history a
timeline, music a repertoire; the lesson-and-practice template has none of them. A course's
plan declares the sections its subject needs (``Course.sections``) and each lesson adds its
entries (``Concept.entries``). Four more are built here for every course from what its
lessons already hold: key ideas, mistakes to avoid, formulas and sources.

A section shows only lessons the learner has finished, so it is their notebook, not a
preview of the course, and it never shows anything a check is about to ask.
"""

import re

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.catalog.schema import Concept, Course
from socrat.learn import service as learn
from socrat.learn.routes import active, catalog, engine, user_of
from socrat.models import Enrollment

router = APIRouter(prefix="/api/v1/sections")

# Display maths in a lesson: $$ ... $$ on one or more lines.
_FORMULA = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
MAX_FORMULAS = 8  # per lesson


def _built_in(concept: Concept) -> dict[str, list[dict]]:
    """This lesson's rows for the sections every course has, by section id."""
    formulas = [" ".join(f.split()) for f in _FORMULA.findall(concept.lesson)]
    formulas = list(dict.fromkeys(f for f in formulas if 2 < len(f) <= 300))[:MAX_FORMULAS]
    return {
        "key-ideas": [{"values": [p]} for p in concept.key_points],
        "mistakes": [{"values": [p]} for p in concept.pitfalls],
        "formulas": [{"values": [f]} for f in formulas],
        "sources": [
            {"values": [r.title, r.source or r.kind], "url": str(r.url)} for r in concept.resources
        ],
    }


BUILT_IN = (
    dict(
        id="key-ideas",
        title="Key ideas",
        purpose="The points to remember from each lesson you have finished.",
        style="list",
        fields=["Idea"],
    ),
    dict(
        id="mistakes",
        title="Mistakes to avoid",
        purpose="The slips each lesson warned about.",
        style="list",
        fields=["Mistake"],
    ),
    dict(
        id="formulas",
        title="Formulas",
        purpose="Every formula your lessons have used, in one place.",
        style="list",
        fields=["Formula"],
    ),
    dict(
        id="sources",
        title="Sources",
        purpose="The videos, chapters and articles your lessons were written from.",
        style="table",
        fields=["Source", "From"],
    ),
)


def finished(db: Session, cat: Catalog, enrollment: Enrollment) -> list[Concept]:
    """The course's live concepts whose lesson this learner has finished, in course order."""
    done = {
        a.removeprefix("lesson:")
        for a in learn.completed_for(db, enrollment)
        if a.startswith("lesson:")
    }
    course = cat.course(enrollment.course_id)
    order = [f"{course.id}:{cid}" for m in course.modules for cid in m.concepts]
    return [
        cat.concept(key)
        for key in order
        if key in done and key in cat.concepts and cat.concept(key).status == "live"
    ]


def build(course: Course, concepts: list[Concept]) -> list[dict]:
    """Every section of the course with its entries grouped by lesson. The course's own
    sections come first and are listed even when empty (the learner sees what will fill
    them); a built-in section with nothing in it is left out."""
    own = [s.model_dump(mode="json") | {"built_in": False} for s in course.sections]
    known = {s["id"] for s in own}
    sections = own + [s | {"built_in": True} for s in BUILT_IN if s["id"] not in known]
    groups: dict[str, list[dict]] = {s["id"]: [] for s in sections}
    for concept in concepts:
        rows = _built_in(concept)
        for entry in concept.entries:
            if entry.section in known:
                rows.setdefault(entry.section, []).append({"values": list(entry.values)})
        for section_id, entries in rows.items():
            if entries and section_id in groups:
                groups[section_id].append(
                    dict(concept=f"{course.id}:{concept.id}", title=concept.title, entries=entries)
                )
    out = []
    for section in sections:
        mine = groups[section["id"]]
        if section["built_in"] and not mine:
            continue
        count = sum(len(g["entries"]) for g in mine)
        out.append(section | {"groups": mine, "count": count})
    return out


@router.get("")
def overview(request: Request):
    cat = catalog()
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = active(db, user)
        course = cat.course(enrollment.course_id)
        concepts = finished(db, cat, enrollment)
        return dict(
            course=course.title,
            lessons_done=len(concepts),
            lessons_total=sum(len(m.concepts) for m in course.modules),
            sections=build(course, concepts),
        )
