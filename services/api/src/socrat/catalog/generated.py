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


def _assemble(payload: dict, concepts: list[dict]) -> Course:
    # Rows come back in key order; authoring (module) order breaks planner ties, so restore it.
    position = {
        cid: i for i, cid in enumerate(c for m in payload["modules"] for c in m["concepts"])
    }
    concepts = sorted(concepts, key=lambda c: position.get(c["id"], len(position)))
    return Course.model_validate({**payload, "concepts": concepts})


def course(db: Session, course_id: str) -> Course | None:
    row = db.get(GeneratedCourse, course_id)
    if row is None:
        return None
    concepts = db.scalars(select(GeneratedConcept).where(GeneratedConcept.course_id == course_id))
    return _assemble(row.payload, [c.payload for c in concepts])


def courses(db: Session, published_only: bool = True) -> list[Course]:
    """Learners only ever see published courses; outlines under review stay out."""
    query = select(GeneratedCourse).order_by(GeneratedCourse.id)
    if published_only:
        query = query.where(GeneratedCourse.status == "published")
    rows = db.scalars(query).all()
    by_course: dict[str, list[dict]] = {}
    for concept in db.scalars(
        select(GeneratedConcept).where(GeneratedConcept.course_id.in_([r.id for r in rows]))
    ):
        by_course.setdefault(concept.course_id, []).append(concept.payload)
    return [_assemble(row.payload, by_course.get(row.id, [])) for row in rows]


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
        stamps = db.execute(
            select(GeneratedCourse.id, GeneratedCourse.updated_at).where(
                GeneratedCourse.status == "published"
            )
        ).all()
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


def save_course(
    db: Session,
    base: Catalog,
    course: Course,
    status: str = "published",
    brief: dict | None = None,
) -> None:
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
        row = GeneratedCourse(id=course.id, created_at=stamp, updated_at=stamp)
        db.add(row)
    else:
        row.updated_at = max(stamp, row.updated_at + 1)
    row.payload = payload
    row.status = status
    if brief is not None:
        row.brief = brief
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


def publish(db: Session, base: Catalog, course_id: str) -> None:
    """Make a reviewed outline visible to learners, re-checked against today's catalog."""
    stored = course(db, course_id)
    if stored is None:
        raise CatalogError(f"unknown generated course {course_id}")
    save_course(db, base, stored, status="published")
