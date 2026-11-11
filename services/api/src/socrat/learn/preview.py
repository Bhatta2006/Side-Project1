"""A learner's first lesson, readable while it is still being checked.

The first lesson of a new course is the longest wait a learner has: the lesson is written,
then its quiz and in-lesson checks, then a fact check and a review. Reading it takes minutes,
and the checks take about as long, so with ``gen_first_lesson_preview`` the draft is shown as
soon as it has passed the lesson gates, labelled as a draft. The real lesson replaces it when
the checks pass; if they fail, the draft is withdrawn and a new one is written.

What keeps this honest:
- only the course's owner, on their own private course, for the job marked as their first
  lesson; nobody else's course and no later lesson;
- read-only: no quiz, no progress, nothing is marked done from a draft;
- never for a course with safety notes, and never for a learner under 13 or in a child's
  register, where an unchecked sentence costs more than a minute of waiting.
"""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog import generated
from socrat.learn.routes import active, engine, user_of
from socrat.models import GeneratedCourse, GenerationJob

router = APIRouter(prefix="/api/v1/concepts")

CHILD_REGISTERS = {"little-kid", "kid"}
ADULT_FROM = 13


def allowed_for(brief: dict | None) -> bool:
    """False for a course whose brief asks for extra care: safety notes or a young learner."""
    brief = brief or {}
    if brief.get("safety"):
        return False
    learner = brief.get("learner") or {}
    age = learner.get("age")
    if isinstance(age, int) and age < ADULT_FROM:
        return False
    return learner.get("register") not in CHILD_REGISTERS


def draft(db: Session, course_id: str, concept_id: str) -> dict | None:
    """The first-lesson draft of a running job that is past the lesson gates, or None."""
    job = db.scalars(
        select(GenerationJob)
        .where(
            GenerationJob.course_id == course_id,
            GenerationJob.kind == "package",
            GenerationJob.target == concept_id,
            GenerationJob.state == "running",
        )
        .order_by(GenerationJob.created_at.desc())
    ).first()
    if job is None or job.input.get("trigger") != "first":
        return None
    if not any(e.get("event") == "preview_ready" for e in job.log or []):
        return None
    lesson = (job.output or {}).get("lesson")
    if not isinstance(lesson, dict) or not str(lesson.get("lesson", "")).strip():
        return None
    return lesson


@router.get("/{qualified}/writing")
def writing(qualified: str, request: Request):
    """When a lesson that is not written yet will be: for the learner who has reached it.
    Only while a daily lesson quota is set (``gen_lessons_per_day``); it says a time, never
    a cost."""
    from socrat.coursegen import jobs, prefetch
    from socrat.models import now

    if prefetch.LESSONS_PER_DAY <= 0:
        raise HTTPException(404, "not_found")
    course_id, _, concept_id = qualified.partition(":")
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = active(db, user)
        if enrollment.course_id != course_id or db.get(GeneratedCourse, course_id) is None:
            raise HTTPException(404, "not_found")
        job = db.scalars(
            select(GenerationJob)
            .where(
                GenerationJob.course_id == course_id,
                GenerationJob.kind == "package",
                GenerationJob.target == concept_id,
            )
            .order_by(GenerationJob.created_at.desc())
        ).first()
        if job is None:
            raise HTTPException(404, "not_found")
        stamp = now()
        waiting = job.state == "queued" and job.not_before > stamp
        return dict(
            state=jobs.lifecycle(job),
            per_day=prefetch.LESSONS_PER_DAY,
            at=job.not_before if waiting else None,  # when it will be written, if not yet
            seconds=job.not_before - stamp if waiting else 0,
        )


@router.get("/{qualified}/preview")
def preview(qualified: str, request: Request):
    if not request.app.state.settings.gen_first_lesson_preview:
        raise HTTPException(404, "not_found")
    course_id, _, concept_id = qualified.partition(":")
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = active(db, user)
        meta = db.get(GeneratedCourse, course_id)
        if (
            enrollment.course_id != course_id
            or meta is None
            or meta.owner_id != user.id
            or meta.visibility != "private"
            or meta.moderation != "ok"
            or not allowed_for(meta.brief)
        ):
            raise HTTPException(404, "not_found")
        course = generated.course(db, course_id)
        concept = (
            next(
                (c for c in course.concepts if c.id.split(":", 1)[-1] == concept_id),
                None,
            )
            if course is not None
            else None
        )
        if concept is None or concept.status != "planned":
            raise HTTPException(404, "not_found")  # released: the real lesson is the one to read
        lesson = draft(db, course_id, concept_id)
        if lesson is None:
            raise HTTPException(404, "not_found")

        def lines(key: str) -> list[str]:
            value = lesson.get(key)
            return (
                [str(x) for x in value if isinstance(x, str)][:12]
                if isinstance(value, list)
                else []
            )

        return dict(
            title=concept.title,
            lesson=str(lesson["lesson"]),
            key_points=lines("key_points"),
            pitfalls=lines("pitfalls"),
            checking=True,
        )
