"""Courses stored in the database, merged with the hand-authored packs in ``content/``.

The generation pipeline writes courses here instead of YAML. Learners, planner and mastery
see one ``Catalog``; nothing downstream knows where a course came from.
"""

import hashlib
import json
import logging
from collections.abc import Sequence
from dataclasses import replace

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from socrat.catalog.atoms import AtomPack
from socrat.catalog.projects import Project
from socrat.catalog.registry import Catalog, CatalogError, build
from socrat.catalog.schema import Concept, Course, Problem
from socrat.models import GeneratedConcept, GeneratedCourse, need, now

log = logging.getLogger(__name__)

_engine: Engine | None = None
_cache: dict[tuple, Catalog] = {}


def bind(engine: Engine) -> None:
    """Called by the app at startup; without it ``merged`` returns the file catalog."""
    global _engine
    _engine = engine
    _cache.clear()


def _assemble(payload: dict, concepts: list[dict], problems: Sequence[dict] = ()) -> Course:
    # Rows come back in key order; authoring (module) order breaks planner ties, so restore it.
    position = {
        cid: i for i, cid in enumerate(c for m in payload["modules"] for c in m["concepts"])
    }
    concepts = sorted(concepts, key=lambda c: position.get(c["id"], len(position)))
    return Course.model_validate({**payload, "concepts": concepts, "problems": list(problems)})


def course(db: Session, course_id: str) -> Course | None:
    row = db.get(GeneratedCourse, course_id)
    if row is None:
        return None
    concepts = list(
        db.scalars(select(GeneratedConcept).where(GeneratedConcept.course_id == course_id))
    )
    problems = [p for c in concepts for p in c.problems or []]
    return _assemble(row.payload, [c.payload for c in concepts], problems)


def courses(db: Session, published_only: bool = True) -> list[Course]:
    """Learners only ever see published courses; outlines under review stay out."""
    query = select(GeneratedCourse).order_by(GeneratedCourse.id)
    if published_only:
        query = query.where(GeneratedCourse.status == "published")
    rows = db.scalars(query).all()
    by_course: dict[str, list[dict]] = {}
    problems: dict[str, list[dict]] = {}
    for concept in db.scalars(
        select(GeneratedConcept).where(GeneratedConcept.course_id.in_([r.id for r in rows]))
    ):
        by_course.setdefault(concept.course_id, []).append(concept.payload)
        problems.setdefault(concept.course_id, []).extend(concept.problems or [])
    return [
        _assemble(row.payload, by_course.get(row.id, []), problems.get(row.id, [])) for row in rows
    ]


def atom_packs(db: Session) -> dict[str, AtomPack]:
    """Released atom packs of published courses, keyed ``course:concept`` like file packs."""
    rows = db.scalars(
        select(GeneratedConcept)
        .join(GeneratedCourse, GeneratedCourse.id == GeneratedConcept.course_id)
        .where(GeneratedCourse.status == "published")
    )
    # A JSON column stores None as JSON null, which SQL IS NULL does not match.
    return {
        f"{r.course_id}:{r.concept_id}": AtomPack.model_validate(r.atoms) for r in rows if r.atoms
    }


def projects(db: Session) -> dict[str, Project]:
    """Projects of published generated courses, keyed ``course:project`` like file projects."""
    rows = db.scalars(select(GeneratedCourse).where(GeneratedCourse.status == "published"))
    found = {}
    for row in rows:
        for raw in row.projects or []:
            project = Project.model_validate(raw)
            found[f"{project.course}:{project.id}"] = project
    return found


def extend(
    base: Catalog,
    extra: list[Course],
    packs: dict[str, AtomPack] | None = None,
    extra_projects: dict[str, Project] | None = None,
) -> Catalog:
    """The file catalog plus ``extra`` courses (and their atom packs and projects), validated
    as one graph."""
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
        atom_packs={**base.atom_packs, **(packs or {})},
        projects={**base.projects, **(extra_projects or {})},
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
            catalog = extend(base, courses(db), atom_packs(db), projects(db))
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
        # Problems are released one by one with execution-verified tests (store_problem).
        raise CatalogError("an outline carries no problems")
    # Released problems stay with their concepts; validate the course as it will be served.
    kept = {
        old.concept_id: old
        for old in db.scalars(
            select(GeneratedConcept).where(GeneratedConcept.course_id == course.id)
        )
    }
    shown = [
        Problem.model_validate(p)
        for c in course.concepts
        if c.id in kept
        for p in kept[c.id].problems or []
    ]
    extend(
        base,
        [
            *(c for c in courses(db) if c.id != course.id),
            course.model_copy(update={"problems": shown}),
        ],
    )
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
    # Generated atom packs and problems survive an outline save.
    atoms = {cid: old.atoms for cid, old in kept.items()}
    problems = {cid: old.problems for cid, old in kept.items()}
    for old in kept.values():
        db.delete(old)
    db.flush()
    for concept in course.concepts:
        db.add(
            GeneratedConcept(
                course_id=course.id,
                concept_id=concept.id,
                payload=concept.model_dump(mode="json"),
                atoms=atoms.get(concept.id),
                problems=problems.get(concept.id),
                updated_at=stamp,
            )
        )


def publish(db: Session, base: Catalog, course_id: str) -> None:
    """Make a reviewed outline visible to learners, re-checked against today's catalog."""
    stored = course(db, course_id)
    if stored is None:
        raise CatalogError(f"unknown generated course {course_id}")
    save_course(db, base, stored, status="published")


def store_concept(
    db: Session,
    base: Catalog,
    course_id: str,
    concept: Concept,
    atoms: AtomPack | None,
    problems: list[Problem] | None = None,
) -> None:
    """Replace one concept of a generated course (a release, a new problem, or a quarantine
    back to planned); checked against the whole catalog first. ``problems`` None keeps the
    concept's problems. No commit; the caller owns it."""
    stored = course(db, course_id)
    row = db.get(GeneratedConcept, (course_id, concept.id))
    if stored is None or row is None:
        raise CatalogError(f"unknown generated concept {course_id}:{concept.id}")
    if problems is None:
        problems = [Problem.model_validate(p) for p in row.problems or []]
    owned = {p["id"] for p in row.problems or []}
    updated = stored.model_copy(
        update={
            "concepts": [concept if c.id == concept.id else c for c in stored.concepts],
            "problems": [*(p for p in stored.problems if p.id not in owned), *problems],
        }
    )
    others = [c for c in courses(db) if c.id != course_id]
    extend(base, [*others, updated])
    row.payload = concept.model_dump(mode="json")
    row.atoms = atoms.model_dump(mode="json") if atoms else None
    row.problems = [p.model_dump(mode="json") for p in problems] or None
    row.updated_at = now()
    parent = need(db.get(GeneratedCourse, course_id))
    parent.updated_at = max(now(), parent.updated_at + 1)  # refreshes the merged catalog


def add_problem(db: Session, base: Catalog, course_id: str, concept_id: str, problem: Problem):
    """Release one more judged problem for a live concept. No commit."""
    row = need(db.get(GeneratedConcept, (course_id, concept_id)))
    concept = Concept.model_validate(row.payload)
    listed = concept.model_copy(update={"problems": [*concept.problems, problem.id]})
    own = [Problem.model_validate(p) for p in row.problems or []]
    pack = AtomPack.model_validate(row.atoms) if row.atoms else None
    store_concept(db, base, course_id, listed, pack, [*own, problem])


def store_project(db: Session, base: Catalog, project: Project) -> None:
    """Add or replace one project of a generated course. No commit."""
    row = db.get(GeneratedCourse, project.course)
    if row is None:
        raise CatalogError(f"unknown generated course {project.course}")
    stored = need(course(db, project.course))
    known = {f"{stored.id}:{c.id}" for c in stored.concepts} | set(base.concepts)
    unknown = [c for c in project.concepts if c not in known]
    if unknown:
        raise CatalogError(f"project {project.id}: unknown concepts {unknown}")
    if project.id in {p.id for k, p in base.projects.items() if p.course == project.course}:
        raise CatalogError(f"project {project.id} already exists in content/")
    others = [p for p in row.projects or [] if p["id"] != project.id]
    row.projects = [*others, project.model_dump(mode="json")]
    row.updated_at = max(now(), row.updated_at + 1)  # refreshes the merged catalog
