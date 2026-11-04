"""Keep the next few concepts on each learner's path written before they get there.

Called when a learner finishes something or is placed. Deterministic and cheap: it reads the
learner's position in the course order and queues a package job for each planned concept in
the next few positions. Content is shared, so the first learner to approach a concept pays
for it and everyone after finds it ready.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.models import Enrollment, GeneratedCourse, GenerationJob

AHEAD = 3  # the learner's current concept and the two after it are kept written
# Written as soon as a course is published, before anyone enrols: the concepts of the first
# INITIAL_MODULES modules, but never more than INITIAL_CONCEPTS (a large first module would
# otherwise cost minutes and dollars before the learner has read a line). A short course is
# written whole within the same cap.
INITIAL_MODULES = 3
INITIAL_CONCEPTS = 6
# A job in one of these states is on its way or needs a person (or the owner) to act; prefetch
# does not queue the concept again on every visit.
SETTLED = {"queued", "running", "failed", "dead", "cancelled"}


def upcoming(catalog, course_id: str, done: set[str], ahead: int) -> list[str]:
    """The next ``ahead`` concepts on the path that the learner has not finished or skipped."""
    path = catalog.closure(catalog.course_concepts(course_id))
    return [c for c in path if c not in done][:ahead]


def request(db: Session, enrollment: Enrollment, now: int, catalog=None) -> list:
    """Queue package jobs for planned concepts just ahead of this learner. No commit."""
    course = db.get(GeneratedCourse, enrollment.course_id)
    if course is None or course.status != "published":
        return []  # hand-authored courses are always fully written
    from socrat.catalog import generated
    from socrat.catalog.registry import default_catalog
    from socrat.coursegen import jobs
    from socrat.learn import service as learn

    catalog = catalog or generated.merged(default_catalog())
    if enrollment.course_id not in catalog.courses:
        return []
    states = learn.states_for(db, enrollment)
    completed = learn.completed_for(db, enrollment)
    done = {
        c for c, s in states.items() if s.mastered(now) or (s.assumed and s.evidence_count == 0)
    } | {a.removeprefix("lesson:") for a in completed if a.startswith("lesson:")}
    queued = []
    for concept in upcoming(catalog, enrollment.course_id, done, AHEAD):
        if catalog.concept(concept).status != "planned":
            continue
        local = concept.split(":", 1)[1]
        latest = db.scalars(
            select(GenerationJob)
            .where(
                GenerationJob.course_id == course.id,
                GenerationJob.target == local,
                GenerationJob.kind == "package",
            )
            .order_by(GenerationJob.created_at.desc())
        ).first()
        # Running or queued: already on its way. Failed: the owner retries it from /admin,
        # so a concept that cannot pass its gates does not burn budget on every visit.
        if latest is not None and latest.state in SETTLED:
            continue
        job = jobs.enqueue_once(db, "package", course.id, {"trigger": "prefetch"}, None, local)
        if job is not None:  # None: a concurrent page load queued it first
            queued.append(job)
    return queued


def initial_slice(course, start: str | None = None) -> list[str]:
    """Local ids of the concepts written at publish, in course order (see ``INITIAL_MODULES``).
    ``start`` is where this learner begins (their diagnosed level): concepts before it are
    ones they already know, so the slice starts there instead of at the very beginning."""
    by_id = {c.id: c for c in course.concepts}
    order = [(i, cid) for i, m in enumerate(course.modules) for cid in m.concepts]
    begin = next((n for n, (_, cid) in enumerate(order) if cid == start), 0)
    first_module = order[begin][0] if order else 0
    picked: list[str] = []
    for module, cid in order[begin:]:
        if module >= first_module + INITIAL_MODULES or len(picked) >= INITIAL_CONCEPTS:
            break
        if by_id[cid].status == "planned":
            picked.append(cid)
    return picked


def initial(db: Session, course_id: str, start: str | None = None) -> list:
    """Queue the first slice of a just-published generated course. Idempotent: a concept with
    any job already (queued, running, done or settled) is skipped. No commit."""
    from socrat.catalog import generated
    from socrat.coursegen import jobs

    course = generated.course(db, course_id)
    if course is None:
        return []
    queued = []
    for local in initial_slice(course, start):
        seen = db.scalar(
            select(GenerationJob.id).where(
                GenerationJob.course_id == course_id,
                GenerationJob.target == local,
                GenerationJob.kind == "package",
            )
        )
        if seen is None:
            job = jobs.enqueue_once(db, "package", course_id, {"trigger": "initial"}, None, local)
            if job is not None:
                queued.append(job)
    # Jobs are claimed oldest first and these share one second: stagger them backwards so the
    # learner's first lesson is always written first.
    for i, job in enumerate(queued):
        job.created_at -= len(queued) - i
    return queued
