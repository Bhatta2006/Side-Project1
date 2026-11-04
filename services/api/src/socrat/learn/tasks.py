"""Tasks a quiz cannot judge (master prompt 4, 9.4, 12.2): submit, wait for a person, get graded.

A learner submits text and, where the work lives elsewhere (a recording, a drawing, a repo), one
https link. Reflections and case studies are self-checked against the rubric: stored, shown back,
never counted as evidence. Oral, performance, portfolio and practical work waits for a person;
only a named person's rubric grade becomes evidence (kind ``performance``). Nothing here claims
a physical skill was verified by software (prompt 6).
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.admin.routes import require_admin
from socrat.database import record_event
from socrat.learn import service as learn
from socrat.learn.routes import active, catalog, engine, user_of
from socrat.models import Enrollment, TaskSubmission, now

router = APIRouter(prefix="/api/v1/tasks")
admin = APIRouter(prefix="/api/v1/admin/tasks")
MAX_OPEN = 3  # submissions waiting for a person, per task


class Submit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=10, max_length=4000)
    link: str = Field(default="", max_length=500, pattern=r"^(https://\S+)?$")
    # Self-checked tasks: which rubric criteria the learner believes they met.
    met: list[str] = Field(default_factory=list, max_length=6)


class Grade(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewer: str = Field(min_length=3, max_length=120)
    points: dict[str, int]  # criterion -> points awarded
    feedback: str = Field(default="", max_length=2000)


def _task(qualified: str, task_id: str):
    cat = catalog()
    if qualified not in cat.concepts:
        raise HTTPException(404, "not_found")
    task = next((t for t in cat.concepts[qualified].tasks if t.id == task_id), None)
    if task is None:
        raise HTTPException(404, "not_found")
    return task


def view(row: TaskSubmission) -> dict:
    return dict(
        id=row.id,
        task=row.task_id,
        status=row.status,
        text=row.text,
        link=row.link or None,
        met=row.met or [],
        score=row.score,
        reviewer=row.reviewer,
        feedback=row.feedback or None,
        created_at=row.created_at,
    )


def mine(db: Session, enrollment: Enrollment | None, qualified: str) -> dict[str, dict]:
    """The newest submission per task of this concept, for the lesson view."""
    if enrollment is None:
        return {}
    rows = db.scalars(
        select(TaskSubmission)
        .where(TaskSubmission.enrollment_id == enrollment.id, TaskSubmission.concept == qualified)
        .order_by(TaskSubmission.created_at)
    )
    return {r.task_id: view(r) for r in rows}


@router.post("/{qualified}/{task_id}")
def submit(qualified: str, task_id: str, body: Submit, request: Request):
    task = _task(qualified, task_id)
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        learn.require_unlocked(db, catalog(), enrollment, qualified, now())
        waiting = db.scalars(
            select(TaskSubmission).where(
                TaskSubmission.enrollment_id == enrollment.id,
                TaskSubmission.concept == qualified,
                TaskSubmission.task_id == task_id,
                TaskSubmission.status == "awaiting_person",
            )
        ).all()
        if len(waiting) >= MAX_OPEN:
            raise HTTPException(429, "too_many_waiting")
        criteria = {c.criterion for c in task.rubric}
        row = TaskSubmission(
            enrollment_id=enrollment.id,
            concept=qualified,
            task_id=task_id,
            kind=task.kind,
            text=body.text,
            link=body.link,
            met=[m for m in body.met if m in criteria] if task.evaluator == "self" else [],
            status="self_checked" if task.evaluator == "self" else "awaiting_person",
            created_at=now(),
        )
        db.add(row)
        db.flush()
        record_event(db, user.id, "task.submitted", f"{qualified}:{task_id}")
        return view(row)


@admin.get("")
def awaiting(request: Request):
    with Session(engine(request)) as db:
        require_admin(request, db)
        rows = db.scalars(
            select(TaskSubmission)
            .where(TaskSubmission.status == "awaiting_person")
            .order_by(TaskSubmission.created_at)
            .limit(100)
        )
        cat = catalog()
        out = []
        for r in rows:
            task = next((t for t in cat.concepts[r.concept].tasks if t.id == r.task_id), None)
            rubric = [c.model_dump() for c in task.rubric] if task else []
            out.append(view(r) | dict(concept=r.concept, kind=r.kind, rubric=rubric))
        return dict(items=out)


@admin.post("/{submission_id}/grade")
def grade(submission_id: str, body: Grade, request: Request):
    """A named person grades real work against the rubric; that grade is the evidence."""
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        if len(body.reviewer.split()) < 2:
            raise HTTPException(422, "reviewer_full_name_required")
        row = db.get(TaskSubmission, submission_id)
        if row is None or row.status != "awaiting_person":
            raise HTTPException(404, "not_found")
        task = _task(row.concept, row.task_id)
        rubric = {c.criterion: c.points for c in task.rubric}
        if set(body.points) != set(rubric) or any(
            not 0 <= body.points[c] <= rubric[c] for c in rubric
        ):
            raise HTTPException(422, "points_must_cover_the_rubric")
        score = sum(body.points.values()) / sum(rubric.values())
        row.status, row.score, row.reviewer = "graded", round(score, 3), body.reviewer
        row.feedback, row.graded_at = body.feedback, now()
        enrollment = db.get(Enrollment, row.enrollment_id)
        if enrollment is not None:
            learn.record_evidence(
                db,
                enrollment,
                row.concept,
                "performance",
                score,
                f"task:{row.concept}:{row.task_id}",
                now(),
                details={"reviewer": body.reviewer, "points": body.points},
            )
        record_event(db, user.id, "task.graded", row.id)
        return view(row)
