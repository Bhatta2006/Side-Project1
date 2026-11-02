"""Quarantine: a released generated concept that learners report goes back to planned and
is rewritten with their reports in hand. Learners keep their evidence; nobody is served
the reported version meanwhile."""

import logging
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog import generated
from socrat.catalog.atoms import AtomPack
from socrat.catalog.registry import Catalog
from socrat.catalog.schema import Concept
from socrat.coursegen import jobs
from socrat.models import ContentIssue, ErrorReport, GeneratedConcept, GeneratedCourse, need

log = logging.getLogger(__name__)
LESSON_ROUTE = re.compile(r"^/learn/([a-z][a-z0-9-]*)/([a-z][a-z0-9-]*)/?$")


def reports_since(db: Session, course_id: str, concept_id: str, since: int) -> list[tuple]:
    """(learner, text) for content reports on this concept made after its release."""
    lesson = db.execute(
        select(ErrorReport.user_id, ErrorReport.message).where(
            ErrorReport.source == "learner",
            ErrorReport.route == f"/learn/{course_id}/{concept_id}",
            ErrorReport.first_at >= since,
        )
    ).all()
    atoms = db.execute(
        select(ContentIssue.user_id, ContentIssue.note).where(
            ContentIssue.concept == f"{course_id}:{concept_id}",
            ContentIssue.created_at >= since,
        )
    ).all()
    return [(user, text) for user, text in [*lesson, *atoms] if user]


def quarantine(
    db: Session, base: Catalog, course_id: str, concept_id: str, reason: str, notes: list[str]
) -> None:
    """Take a live concept back to planned and queue its rewrite. No commit."""
    row = need(db.get(GeneratedConcept, (course_id, concept_id)))
    live = Concept.model_validate(row.payload)
    if live.status != "live":
        raise ValueError(f"{course_id}:{concept_id} is not live")
    planned = Concept.model_validate(
        {
            **live.model_dump(mode="json"),
            "status": "planned",
            "lesson": "",
            "key_points": [],
            "pitfalls": [],
            "resources": [],
            "quiz": [],
            "prompts": [],
            "problems": [],
        }
    )
    pack = AtomPack.model_validate({**row.atoms, "status": "quarantined"}) if row.atoms else None
    previous = {"concept": row.payload, "atoms": row.atoms, "problems": row.problems}
    generated.store_concept(db, base, course_id, planned, pack, problems=[], reason="quarantine")
    jobs.enqueue(
        db,
        "package",
        course_id,
        {"trigger": "quarantine", "reason": reason, "reports": notes[:20], "previous": previous},
        None,
        target=concept_id,
    )


def announce(course_id: str, concept_id: str, reason: str) -> None:
    """An ERROR log becomes an /admin error report, so the owner hears of every quarantine.
    Call it after the commit: the report is written in its own transaction."""
    log.error("generated concept quarantined: %s:%s (%s)", course_id, concept_id, reason)


def check_reports(engine, base: Catalog, route: str, threshold: int) -> bool:
    """After a learner report: quarantine the concept once enough distinct learners agree."""
    match = LESSON_ROUTE.match(route) or None
    if match is None:
        return False
    return check_concept(engine, base, match.group(1), match.group(2), threshold)


def check_concept(engine, base: Catalog, course_id: str, concept_id: str, threshold: int) -> bool:
    with Session(engine) as db, db.begin():
        course = db.get(GeneratedCourse, course_id)
        row = db.get(GeneratedConcept, (course_id, concept_id))
        if course is None or row is None or row.payload.get("status") != "live":
            return False
        found = reports_since(db, course_id, concept_id, row.updated_at)
        if len({user for user, _ in found}) < threshold:
            return False
        notes = [text for _, text in found if text]
        reason = f"{threshold}+ learner reports"
        quarantine(db, base, course_id, concept_id, reason, notes)
    announce(course_id, concept_id, reason)
    return True


def after_report(engine, threshold: int, *, route: str = "", concept: str = "") -> None:
    """Hook for the report endpoints. Never raises: a report must always be accepted."""
    from socrat.catalog.registry import default_catalog

    try:
        if concept and ":" in concept:
            course_id, concept_id = concept.split(":", 1)
            check_concept(engine, default_catalog(), course_id, concept_id, threshold)
        elif route:
            check_reports(engine, default_catalog(), route, threshold)
    except Exception:
        log.exception("quarantine check failed")
