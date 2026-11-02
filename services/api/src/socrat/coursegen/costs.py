"""What generation costs, per course: the owner's answer to "can we afford more learners?".

Every model call is already metered into ``ai_usage`` and every job keeps its own ``cost_usd``.
This adds them up per course (and per role from ``ai_usage``) and divides by what the money
bought, the released concepts, so a course that burns budget without releasing is visible.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.models import AIUsage, GeneratedConcept, GeneratedCourse, GenerationJob


def by_course(db: Session, *, limit: int = 50) -> list[dict]:
    spend = {
        course_id: (jobs, cost or 0.0)
        for course_id, jobs, cost in db.execute(
            select(
                GenerationJob.course_id,
                func.count(),
                func.sum(GenerationJob.cost_usd),
            ).group_by(GenerationJob.course_id)
        )
    }
    released: dict[str, int] = {}
    for course_id, payload in db.execute(
        select(GeneratedConcept.course_id, GeneratedConcept.payload)
    ):
        if isinstance(payload, dict) and payload.get("status") == "live":
            released[str(course_id)] = released.get(str(course_id), 0) + 1
    courses = {c.id: c for c in db.scalars(select(GeneratedCourse))}
    rows: list[dict[str, Any]] = []
    for course_id, (jobs, cost) in spend.items():
        count = released.get(course_id, 0)
        course = courses.get(course_id)
        rows.append(
            dict(
                course_id=course_id,
                title=(course.payload.get("title") if course else None) or course_id,
                owner=("learner" if course and course.owner_id else "owner"),
                jobs=jobs,
                cost_usd=round(cost, 4),
                released_concepts=count,
                cost_per_released_concept_usd=round(cost / count, 4) if count else None,
            )
        )
    rows.sort(key=lambda r: r["cost_usd"], reverse=True)
    return rows[:limit]


def queue(db: Session, stamp: int) -> dict:
    """Generation jobs waiting or running, and how long the oldest has waited: the signal that
    the worker is down or too small. Paused courses are excluded (their jobs are meant to wait)."""
    paused = select(GeneratedCourse.id).where(GeneratedCourse.paused != "")
    waiting = GenerationJob.course_id.not_in(paused)
    queued, oldest = db.execute(
        select(func.count(), func.min(GenerationJob.created_at)).where(
            GenerationJob.state == "queued", waiting
        )
    ).one()
    running = db.scalar(select(func.count()).where(GenerationJob.state == "running"))
    return dict(
        queued=queued or 0,
        running=running or 0,
        oldest_queued_seconds=max(0, stamp - oldest) if oldest is not None else None,
    )


def by_role(db: Session, *, since_day: str) -> dict[str, dict]:
    """Per generation role (intent, architect, author, translator...) from the call ledger."""
    return {
        feature.removeprefix("coursegen."): dict(
            calls=calls, cost_usd=round(total or 0.0, 4), tokens=int(tokens or 0)
        )
        for feature, calls, total, tokens in db.execute(
            select(
                AIUsage.feature,
                func.count(),
                func.sum(AIUsage.cost_usd),
                func.sum(AIUsage.input_tokens + AIUsage.output_tokens),
            )
            .where(AIUsage.day >= since_day, AIUsage.feature.like("coursegen.%"))
            .group_by(AIUsage.feature)
        )
    }
