"""Adaptive course evolution (master prompt 10.4): a generated course changes with the learner's
evidence, visibly, never silently.

A bridge unit is a new planned concept inserted just before the one a learner keeps struggling
with, aimed at the prerequisite that looks shaky. It is built by code from that prerequisite
(no model decides the plan change): its objective is to use the prerequisite in the setting of
the struggling concept, and the struggling concept now depends on it. The objectives and
assessment standard of every existing concept stay as they were. Only the learner who owns the
course can add one, through a proposal they accept; every change is a ``CourseRevision`` the
learner can read. The package job writes the bridge like any other planned concept.
"""

import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.catalog import generated
from socrat.catalog.registry import Catalog
from socrat.catalog.schema import Concept
from socrat.coursegen import jobs
from socrat.models import CourseRevision, GeneratedCourse, now

MAX_BRIDGES = 6  # per course: past this, the course needs a new outline, not more patches


def _title(catalog: Catalog, ref: str) -> str:
    return catalog.concepts[ref].title if ref in catalog.concepts else ref.split(":")[-1]


def record(
    db: Session, course_id: str, change: str, reason: str, user_id: str | None
) -> CourseRevision:
    version = (
        db.scalar(
            select(func.max(CourseRevision.version)).where(CourseRevision.course_id == course_id)
        )
        or 0
    ) + 1
    row = CourseRevision(
        course_id=course_id,
        version=version,
        change=change[:300],
        reason=reason[:500],
        user_id=user_id,
        created_at=now(),
    )
    db.add(row)
    db.flush()
    return row


def history(db: Session, course_id: str) -> list[dict]:
    rows = db.scalars(
        select(CourseRevision)
        .where(CourseRevision.course_id == course_id)
        .order_by(CourseRevision.version.desc())
    )
    return [
        dict(version=r.version, change=r.change, reason=r.reason, at=r.created_at) for r in rows
    ]


def insert_bridge(
    db: Session,
    base: Catalog,
    catalog: Catalog,
    course_id: str,
    struggling: str,
    weak: str,
    reason: str,
    user_id: str,
) -> str:
    """Add a bridge concept before ``struggling`` (qualified) for the shaky ``weak`` prerequisite
    (qualified). Returns the bridge's local id. Raises ValueError when not allowed."""
    meta = db.get(GeneratedCourse, course_id)
    course = generated.course(db, course_id)
    if meta is None or course is None or meta.owner_id != user_id:
        raise ValueError("not_your_course")
    target = struggling.split(":", 1)[1]
    if struggling.split(":", 1)[0] != course_id or target not in {c.id for c in course.concepts}:
        raise ValueError("unknown_concept")
    if sum(c.id.startswith("bridge-") for c in course.concepts) >= MAX_BRIDGES:
        raise ValueError("too_many_bridges")
    stem = re.sub(r"[^a-z0-9-]", "-", weak.split(":")[-1])[:40].strip("-")
    local = f"bridge-{stem}-for-{target}"[:64].rstrip("-")
    if local in {c.id for c in course.concepts}:
        raise ValueError("bridge_exists")
    after = course.concept(target)
    weak_title, target_title = _title(catalog, weak), after.title
    weak_ref = weak.split(":", 1)[1] if weak.startswith(f"{course_id}:") else weak
    bridge = Concept.model_validate(
        {
            "id": local,
            "title": f"Bridge: {weak_title}"[:100],
            "summary": f"{weak_title} again, in the setting of {target_title}, to close the gap."[
                :300
            ],
            "module": after.module,
            "prerequisites": [weak_ref],
            "difficulty": max(1, after.difficulty - 1),
            "estimated_minutes": min(after.estimated_minutes, 30),
            "status": "planned",
            "outline": {
                "depth": "overview",
                "objectives": [
                    f"Apply {weak_title} correctly in problems from {target_title}"[:200]
                ],
                "misconceptions": list(after.outline.misconceptions[:3]) if after.outline else [],
                "assessment": ["quiz"],
                "category": "both",
                "evidence": ["application"],
                "expected": f"Uses {weak_title} without help on a {target_title} task."[:300],
                "practice": ["worked-example", "retrieval"],
            },
        }
    )
    concepts = []
    for c in course.concepts:
        if c.id == target:
            concepts.append(bridge)
            c = c.model_copy(update={"prerequisites": [*c.prerequisites, local]})
        concepts.append(c)
    modules = [
        m.model_copy(
            update={
                "concepts": [
                    x for cid in m.concepts for x in ((local, cid) if cid == target else (cid,))
                ]
            }
        )
        if m.id == after.module
        else m
        for m in course.modules
    ]
    updated = course.model_copy(update={"concepts": concepts, "modules": modules})
    generated.save_course(db, base, updated, status=meta.status)
    jobs.enqueue(db, "package", course_id, {"trigger": "bridge"}, user_id, target=local)
    record(
        db,
        course_id,
        f"Added a bridge lesson, {bridge.title}, before {target_title}.",
        reason,
        user_id,
    )
    return local
