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
            .where(GenerationJob.course_id == course.id, GenerationJob.target == local)
            .order_by(GenerationJob.created_at.desc())
        ).first()
        # Running or queued: already on its way. Failed: the owner retries it from /admin,
        # so a concept that cannot pass its gates does not burn budget on every visit.
        if latest is not None and latest.state in {"queued", "running", "failed"}:
            continue
        queued.append(
            jobs.enqueue(db, "package", course.id, {"trigger": "prefetch"}, None, target=local)
        )
    return queued
