"""Courses stored in the database, merged with the hand-authored packs in ``content/``.

The generation pipeline writes courses here instead of YAML. Learners, planner and mastery
see one ``Catalog``; nothing downstream knows where a course came from.
"""

import hashlib
import json
import logging
from dataclasses import replace

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog, CatalogError, build
from socrat.catalog.schema import Course
from socrat.models import GeneratedConcept, GeneratedCourse, now

log = logging.getLogger(__name__)

_engine: Engine | None = None
_cache: dict[tuple, Catalog] = {}


def bind(engine: Engine) -> None:
    """Called by the app at startup; without it ``merged`` returns the file catalog."""
    global _engine
    _engine = engine
    _cache.clear()


def courses(db: Session) -> list[Course]:
    rows = db.scalars(select(GeneratedConcept)).all()
    by_course: dict[str, list[dict]] = {}
    for row in rows:
        by_course.setdefault(row.course_id, []).append(row.payload)
    return [
        Course.model_validate({**row.payload, "concepts": by_course.get(row.id, [])})
        for row in db.scalars(select(GeneratedCourse).order_by(GeneratedCourse.id))
    ]


def extend(base: Catalog, extra: list[Course]) -> Catalog:
    """The file catalog plus ``extra`` courses, validated as one graph."""
    if not extra:
        return base
    graph = build([*base.courses.values(), *extra])
    payload = json.dumps([c.model_dump(mode="json") for c in extra], sort_keys=True)
    return replace(
        base,
        courses=graph.courses,
        concepts=graph.concepts,
        owner=graph.owner,
        prerequisites=graph.prerequisites,
        problems=graph.problems,
        order=graph.order,
        digest=hashlib.sha256(f"{base.digest}:{payload}".encode()).hexdigest(),
    )


def merged(base: Catalog) -> Catalog:
    if _engine is None:
        return base
    with Session(_engine) as db:
        # shortcut: one small query per catalog() call; cache the key briefly if it shows up
        # in request latency.
        stamps = db.execute(select(GeneratedCourse.id, GeneratedCourse.updated_at)).all()
        key = (base.digest, *map(tuple, stamps))
        if key in _cache:
            return _cache[key]
        try:
            catalog = extend(base, courses(db))
        except (CatalogError, ValueError):
            # One bad generated course must not take the hand-authored courses down with it.
            log.exception("generated courses skipped: invalid catalog")
            catalog = base
    _cache.clear()
    _cache[key] = catalog
    return catalog


def save_course(db: Session, base: Catalog, course: Course) -> None:
    """Insert or replace a generated course. Validates against the live catalog first, so
    a stored course can never make ``merged`` fail. No commit; the caller owns it."""
    if course.id in base.courses:
        raise CatalogError(f"course {course.id} already exists in content/")
    if course.problems:
        # shortcut: judged problems need generated tests from the execution service; G4.
        raise CatalogError("generated courses cannot carry problems yet")
    extend(base, [*(c for c in courses(db) if c.id != course.id), course])
    stamp = now()
    row = db.get(GeneratedCourse, course.id)
    payload = course.model_dump(mode="json", exclude={"concepts", "problems"})
    if row is None:
        db.add(GeneratedCourse(id=course.id, payload=payload, created_at=stamp, updated_at=stamp))
    else:
        row.payload = payload
        row.updated_at = max(stamp, row.updated_at + 1)
    for old in db.scalars(select(GeneratedConcept).where(GeneratedConcept.course_id == course.id)):
        db.delete(old)
    db.flush()
    for concept in course.concepts:
        db.add(
            GeneratedConcept(
                course_id=course.id,
                concept_id=concept.id,
                payload=concept.model_dump(mode="json"),
                updated_at=stamp,
            )
        )
