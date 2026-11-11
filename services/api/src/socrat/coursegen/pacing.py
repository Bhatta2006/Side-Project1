"""Pacing: a course is written lesson by lesson, at a cost that follows real use.

Two rules, both plain arithmetic over the job table (no model, no new tables):

- **A budget that is earned.** A learner's course starts with its base budget. With
  ``gen_budget_per_lesson_usd`` set, every released lesson adds that much to what the course
  may spend, so a long course that keeps releasing lessons never stops itself, while one
  that burns money without releasing still pauses where it always did.
- **A daily quota, not a pause.** With ``gen_lessons_per_day`` set, at most that many lessons
  are written for a course in any 24 hours. A lesson over the quota is still queued, with
  the time it will be written, so it arrives by itself and the learner is told when.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.models import GenerationJob

DAY = 86400


def released(db: Session, course_id: str) -> int:
    """Lessons of this course that passed every gate and were released."""
    return (
        db.scalar(
            select(func.count(func.distinct(GenerationJob.target))).where(
                GenerationJob.course_id == course_id,
                GenerationJob.kind == "package",
                GenerationJob.state == "done",
            )
        )
        or 0
    )


def ceiling(db: Session, course_id: str, base_usd: float, per_lesson_usd: float) -> float:
    """What the course may spend in all: its base budget plus what its released lessons earned."""
    if per_lesson_usd <= 0:
        return base_usd
    return base_usd + per_lesson_usd * released(db, course_id)


def slot(db: Session, course_id: str, per_day: int, stamp: int) -> int:
    """When the next lesson of this course may be written: 0 for now, else the time a place
    in the last 24 hours frees up. Every lesson counts once, at the time it was (or will be)
    written; cancelled ones do not count."""
    if per_day <= 0:
        return 0
    slots = sorted(
        max(created, wait)
        for created, wait in db.execute(
            select(GenerationJob.created_at, GenerationJob.not_before).where(
                GenerationJob.course_id == course_id,
                GenerationJob.kind == "package",
                GenerationJob.state != "cancelled",
            )
        )
        if max(created, wait) > stamp - DAY
    )
    if len(slots) < per_day:
        return 0
    return slots[len(slots) - per_day] + DAY
