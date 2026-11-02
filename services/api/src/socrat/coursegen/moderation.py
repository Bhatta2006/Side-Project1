"""Reports and takedowns for shared (community) courses.

A learner can report a shared course once. Enough distinct reporters hide it at once (held)
and queue it for an admin, who restores or removes it. A held or removed course stops showing
to others and cannot be joined; its perks stop accruing. Learners already inside keep their
own progress records.
"""

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.admin.routes import require_admin
from socrat.database import record_event
from socrat.learn.routes import engine, user_of
from socrat.models import CourseReport, GeneratedCourse, now

log = logging.getLogger(__name__)
learner = APIRouter(prefix="/api/v1/community/courses")
admin = APIRouter(prefix="/api/v1/admin/community/courses")


class Report(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: Literal["unsafe", "wrong", "offensive", "copied", "other"]
    note: str = Field(default="", max_length=500)


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["hold", "restore", "remove"]


def _shared(db: Session, course_id: str) -> GeneratedCourse:
    course = db.get(GeneratedCourse, course_id)
    if course is None or course.owner_id is None or course.visibility != "public":
        raise HTTPException(404, "not_found")
    return course


@learner.post("/{course_id}/report")
def report(course_id: str, body: Report, request: Request):
    settings = request.app.state.settings
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        course = _shared(db, course_id)
        if course.owner_id == user.id:
            raise HTTPException(422, "own_course")
        if db.get(CourseReport, (course_id, user.id)) is None:
            db.add(
                CourseReport(
                    course_id=course_id, user_id=user.id, reason=body.reason, note=body.note
                )
            )
            db.flush()
        reporters = db.scalar(
            select(func.count())
            .select_from(CourseReport)
            .where(CourseReport.course_id == course_id)
        )
        # "unsafe" counts double: a safety report should not wait for as many people.
        unsafe = db.scalar(
            select(func.count())
            .select_from(CourseReport)
            .where(CourseReport.course_id == course_id, CourseReport.reason == "unsafe")
        )
        held = (reporters or 0) + (unsafe or 0) >= settings.community_report_hold
        if held and course.moderation == "ok":
            course.moderation = "held"
            course.updated_at = max(now(), course.updated_at + 1)  # refresh the catalog cache
            log.error("shared course held after reports: %s", course_id)  # reaches /admin errors
            record_event(db, user.id, "community.course_held", course_id)
        return {"reported": True}


@admin.get("")
def queue(request: Request):
    """Held courses first, each with its reports."""
    with Session(engine(request)) as db:
        require_admin(request, db)
        rows = db.scalars(
            select(GeneratedCourse)
            .where(GeneratedCourse.owner_id.is_not(None), GeneratedCourse.moderation != "ok")
            .order_by(GeneratedCourse.updated_at.desc())
        ).all()
        out = []
        for c in rows:
            reports = db.scalars(select(CourseReport).where(CourseReport.course_id == c.id)).all()
            out.append(
                dict(
                    id=c.id,
                    title=c.payload.get("title"),
                    moderation=c.moderation,
                    reports=[dict(reason=r.reason, note=r.note) for r in reports],
                )
            )
        return {"items": out}


@admin.post("/{course_id}")
def act(course_id: str, body: Action, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        course = db.get(GeneratedCourse, course_id)
        if course is None or course.owner_id is None:
            raise HTTPException(404, "not_found")
        if body.action == "restore":
            course.moderation = "ok"
            for r in db.scalars(select(CourseReport).where(CourseReport.course_id == course_id)):
                db.delete(r)  # a restored course starts clean
        elif body.action == "hold":
            course.moderation = "held"
        else:
            course.moderation, course.visibility = "removed", "private"
        course.updated_at = max(now(), course.updated_at + 1)
        record_event(db, user.id, f"community.course_{body.action}", course_id)
        return {"id": course_id, "moderation": course.moderation}
