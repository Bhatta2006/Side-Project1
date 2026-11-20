"""Root units: reusable, validated teaching material under a subject root.

A unit covers one topic at one depth ("equation linear" at beginner). It is researched once,
by the ``research`` job, when the first request that needs it arrives; every later course on
that topic, under any frame or assessment style, is planned and written from it instead of
researching again. Creating a root researches nothing: units are pulled in by requests.

Units never hold learner text. Their queries and prompts are built from the canonical topic,
depth and language only.
"""

import hashlib
import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.coursegen.brain.roots import slug
from socrat.models import ConceptUnitPin, GenerationJob, RootUnit, Source, UnitSource, now

# Unit material older than this is still served, but a later request queues a refresh.
FRESH_SECONDS = 365 * 24 * 3600
# The research job for one unit: course id "root:<root id>", target the unit key. The open-job
# unique index (course_id, kind, target) means one unit is researched once, however many
# requests need it at the same moment.
KIND = "research"


def key_of(topic: str, depth: str) -> str:
    return f"{slug(topic)[:100]}.{depth}"[:120]


def ref(root_id: str, unit_key: str) -> str:
    return f"{root_id}/{unit_key}"


def parse_ref(value: str) -> tuple[str, str]:
    root_id, _, unit_key = value.partition("/")
    return root_id, unit_key


def job_course(root_id: str) -> str:
    return f"root:{root_id}"[:80]


def current(db: Session, root_id: str, unit_key: str) -> RootUnit | None:
    """The newest validated revision, or None."""
    return db.scalars(
        select(RootUnit)
        .where(
            RootUnit.root_id == root_id,
            RootUnit.unit_key == unit_key,
            RootUnit.status == "validated",
        )
        .order_by(RootUnit.revision.desc())
        .limit(1)
    ).first()


def research_job(db: Session, root_id: str, unit_key: str) -> GenerationJob | None:
    """The open research job for this unit if there is one (at most one, by the open-job
    index), else the most recent. Open first: two jobs can share a creation second."""
    from socrat.coursegen import jobs

    query = select(GenerationJob).where(
        GenerationJob.course_id == job_course(root_id),
        GenerationJob.kind == KIND,
        GenerationJob.target == unit_key[:80],
    )
    running = db.scalars(query.where(GenerationJob.state.in_(jobs.OPEN)).limit(1)).first()
    if running is not None:
        return running
    return db.scalars(query.order_by(GenerationJob.created_at.desc()).limit(1)).first()


def ensure(
    db: Session, root_id: str, unit_key: str, spec: dict, user_id: str | None
) -> tuple[RootUnit | None, GenerationJob | None]:
    """(the usable unit, None) when it exists and is fresh; otherwise queue its research once
    and return (stale unit or None, the research job). The job input carries only canonical
    fields of the spec, never learner text."""
    from socrat.coursegen import jobs

    unit = current(db, root_id, unit_key)
    if unit is not None and (unit.review_after or 0) > now():
        return unit, None
    latest = research_job(db, root_id, unit_key)
    if latest is not None and latest.state in jobs.OPEN:
        return unit, latest
    if unit is None and latest is not None and latest.state in ("failed", "dead"):
        return None, None  # tried and could not validate: build without; the admin retries it
    data = {
        "root": root_id,
        "unit_key": unit_key,
        "topic": spec.get("topic", ""),
        "depth": spec.get("depth", "intermediate"),
        "language": spec.get("language", "en"),
        "audience": spec.get("audience", "general"),
        "refresh": unit is not None,
    }
    job = jobs.enqueue_once(db, KIND, job_course(root_id), data, user_id, unit_key[:80])
    return unit, job or research_job(db, root_id, unit_key)


def waiting(db: Session, refs: list[str]) -> list[str]:
    """The unit refs worth waiting for: research is queued or running and there is no
    validated revision to use meanwhile. A routine refresh of a usable unit is not waited for;
    a correction is (the old revision was quarantined, so there is none to use)."""
    from socrat.coursegen import jobs

    out = []
    for value in refs:
        root_id, unit_key = parse_ref(value)
        job = research_job(db, root_id, unit_key)
        if job is None or job.state not in jobs.OPEN:
            continue
        if (job.input or {}).get("refresh") and current(db, root_id, unit_key) is not None:
            continue
        out.append(value)
    return out


def load(db: Session, refs: list[str]) -> list[RootUnit]:
    out = []
    for value in refs:
        unit = current(db, *parse_ref(value))
        if unit is not None:
            out.append(unit)
    return out


def sources_of(db: Session, unit: RootUnit) -> list[dict]:
    rows = db.execute(
        select(UnitSource, Source)
        .join(Source, Source.id == UnitSource.source_id)
        .where(UnitSource.unit_id == unit.id)
        .order_by(UnitSource.n)
    ).all()
    return [
        dict(n=link.n, title=src.title, url=src.url, role=link.role, supports=link.supports)
        for link, src in rows
    ]


def block(db: Session, units: list[RootUnit], limit: int = 12000) -> str:
    """The units as one prompt block: sourced material, marked as data."""
    if not units:
        return ""
    parts = []
    for unit in units:
        payload = {
            "unit": unit.unit_key,
            "revision": unit.revision,
            "concepts": unit.concepts,
            **{k: unit.content.get(k, []) for k in CONTENT_KEYS},
            "sources": sources_of(db, unit),
        }
        parts.append(json.dumps(payload, ensure_ascii=False))
    text = "\n".join(parts)[:limit]
    return f"<subject_material>\n{text}\n</subject_material>"


def misconceptions(units: list[RootUnit]) -> dict[str, str]:
    """id -> belief for the misconceptions the units hold (the ids quizzes may tag)."""
    out: dict[str, str] = {}
    for unit in units:
        for item in (unit.content or {}).get("misconceptions", []):
            if isinstance(item, dict) and item.get("id"):
                out.setdefault(str(item["id"]), str(item.get("belief", ""))[:200])
    return out


def pin(db: Session, course_id: str, concept_id: str, units: list[RootUnit]) -> None:
    """Record which unit revisions this lesson is written from. Idempotent. A lesson rewritten
    from a newer revision of the same unit drops its pin to the older one, so a corrected
    course stops counting as written from the withdrawn revision."""
    for unit in units:
        older = db.scalars(
            select(ConceptUnitPin)
            .join(RootUnit, RootUnit.id == ConceptUnitPin.unit_id)
            .where(
                ConceptUnitPin.course_id == course_id,
                ConceptUnitPin.concept_id == concept_id,
                RootUnit.root_id == unit.root_id,
                RootUnit.unit_key == unit.unit_key,
                RootUnit.id != unit.id,
            )
        ).all()
        for stale in older:
            db.delete(stale)
        if db.get(ConceptUnitPin, (course_id, concept_id, unit.id)) is None:
            db.add(ConceptUnitPin(course_id=course_id, concept_id=concept_id, unit_id=unit.id))
    db.flush()


def pinned_courses(db: Session, unit_id: str) -> list[tuple[str, str]]:
    """(course, concept) pairs written from this unit revision: who a correction touches."""
    return [
        (p.course_id, p.concept_id)
        for p in db.scalars(select(ConceptUnitPin).where(ConceptUnitPin.unit_id == unit_id))
    ]


def quarantine(db: Session, unit_id: str, reason: str) -> list[str]:
    """Withdraw a unit revision. Returns the courses that now fail eligibility for new learners
    (route.decide checks pins); existing enrollments keep their course."""
    unit = db.get(RootUnit, unit_id)
    if unit is None:
        return []
    unit.status = "quarantined"
    unit.quality = {**(unit.quality or {}), "quarantined": {"reason": reason[:300], "at": now()}}
    return sorted({course for course, _ in pinned_courses(db, unit_id)})


def correct(db: Session, base, unit_id: str, reason: str, user_id: str | None = None) -> dict:
    """A unit revision turned out wrong (a source was corrected, a learner or reviewer found an
    error). Withdraw it, research a new revision with the reason in hand, and rewrite every
    live lesson written from it. No commit; the caller owns it.

    New learners are not served courses on the withdrawn revision from this moment
    (``route.decide``). Learners already enrolled keep their course and their evidence; each
    affected lesson goes back to planned and is rewritten (``quality.quarantine``, the same path
    as a lesson learners reported), and the rewrite waits for the new revision."""
    from socrat.coursegen import jobs, quality
    from socrat.models import GeneratedConcept

    unit = db.get(RootUnit, unit_id)
    if unit is None:
        raise ValueError(f"unknown unit {unit_id}")
    courses = quarantine(db, unit_id, reason)
    data = {
        "root": unit.root_id,
        "unit_key": unit.unit_key,
        "topic": unit.topic,
        "depth": unit.depth,
        "language": unit.language,
        "audience": (unit.quality or {}).get("audience", "general"),
        "refresh": True,
        "correction": reason[:300],
    }
    job = jobs.enqueue_once(db, KIND, job_course(unit.root_id), data, user_id, unit.unit_key[:80])
    job = job or research_job(db, unit.root_id, unit.unit_key)
    rewrites = []
    for course_id, concept_id in pinned_courses(db, unit_id):
        row = db.get(GeneratedConcept, (course_id, concept_id))
        if row is None or (row.payload or {}).get("status") != "live":
            continue
        if jobs.active(db, course_id, concept_id) is not None:
            continue
        quality.quarantine(
            db, base, course_id, concept_id, "source_correction", [f"Source correction: {reason}"]
        )
        rewrites.append(f"{course_id}:{concept_id}")
    return {
        "unit": unit_id,
        "courses": courses,
        "rewrites": rewrites,
        "research_job": job.id if job else None,
    }


def courses_on_quarantined_units(db: Session, course_ids: list[str]) -> set[str]:
    if not course_ids:
        return set()
    rows = db.execute(
        select(ConceptUnitPin.course_id)
        .join(RootUnit, RootUnit.id == ConceptUnitPin.unit_id)
        .where(ConceptUnitPin.course_id.in_(course_ids), RootUnit.status == "quarantined")
    ).all()
    return {r[0] for r in rows}


CONTENT_KEYS = ("explanations", "worked_examples", "exercise_seeds", "misconceptions", "probes")


def next_revision(db: Session, root_id: str, unit_key: str) -> int:
    top = db.scalar(
        select(func.max(RootUnit.revision)).where(
            RootUnit.root_id == root_id, RootUnit.unit_key == unit_key
        )
    )
    return (top or 0) + 1


def digest(concepts: list, content: dict) -> str:
    return hashlib.sha256(
        json.dumps([concepts, content], sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
