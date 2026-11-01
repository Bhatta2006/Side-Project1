"""Work graded against a rubric: free-text answers to a concept's prompts, and project
milestones. Both become AI-graded evidence (``explain``, ``project``): lighter than judged
work and never enough to master a concept on their own.

The model is never called inside a database transaction: the request reads what it needs,
grades, then records the evidence in a fresh transaction.
"""

import re

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from socrat.assistant.gateway import ProviderError
from socrat.coursegen import grading, links
from socrat.learn import service as learn
from socrat.learn.graded import PASS, attempts_today, project_view
from socrat.learn.routes import active, catalog, engine, guard_instruction, user_of
from socrat.mastery import model as mastery
from socrat.models import Enrollment, need, now

router = APIRouter(prefix="/api/v1")
ATTEMPTS_PER_DAY = 3  # per prompt or milestone: grading is not a slot machine


class Answer(BaseModel):
    prompt_id: str = Field(min_length=1, max_length=64)
    answer: str = Field(min_length=1, max_length=8000)


class Milestone(BaseModel):
    work: str = Field(min_length=40, max_length=8000)
    link: str = Field(default="", max_length=500)
    checklist: list[bool] = Field(default_factory=list, max_length=10)


async def graded(request: Request, user_id: str, task: str, rubric, work: str, reference=""):
    try:
        return await grading.grade(
            engine(request), request.app.state.settings, user_id, task, rubric, work, reference
        )
    except ProviderError as exc:
        code = "ai_budget_reached" if "budget" in str(exc) else "grading_unavailable"
        raise HTTPException(503, code) from exc
    except grading.GradingFailed as exc:
        raise HTTPException(503, "grading_unavailable") from exc


@router.post("/concepts/{qualified}/answers")
async def answer(qualified: str, body: Answer, request: Request):
    cat = catalog()
    if qualified not in cat.concepts:
        raise HTTPException(404, "not_found")
    concept = cat.concept(qualified)
    prompt = next((p for p in concept.prompts if p.id == body.prompt_id), None)
    if prompt is None:
        raise HTTPException(404, "not_found")
    count = len(re.findall(r"\S+", body.answer))
    if not 10 <= count <= prompt.max_words:
        raise HTTPException(422, "answer_length")
    activity = f"answer:{qualified}:{prompt.id}"
    stamp = now()
    with Session(engine(request)) as db:
        user = user_of(request, db, write=True)
        guard_instruction(db, cat, user, qualified)
        enrollment = active(db, user)
        learn.require_unlocked(db, cat, enrollment, qualified, stamp)
        if attempts_today(db, enrollment, activity, qualified, stamp) >= ATTEMPTS_PER_DAY:
            raise HTTPException(429, "answer_attempts")
        user_id, enrollment_id = user.id, enrollment.id
    rubric = [c.model_dump() for c in prompt.rubric]
    grade = await graded(request, user_id, prompt.prompt, rubric, body.answer, prompt.model_answer)
    with Session(engine(request)) as db, db.begin():
        enrollment = need(db.get(Enrollment, enrollment_id))
        state = learn.record_evidence(
            db,
            enrollment,
            qualified,
            "explain",
            grade.score,
            activity,
            now(),
            details={"prompt": prompt.id, "answer": body.answer, "grade": grade.to_dict()},
        )
        return dict(
            grade=grade.to_dict(),
            model_answer=prompt.model_answer,
            band=mastery.band(state, now()),
        )


@router.get("/projects")
def projects(request: Request):
    cat = catalog()
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = active(db, user)
        keys = [k for k, p in cat.projects.items() if p.course == enrollment.course_id]
        return {"projects": [project_view(db, cat, enrollment, k) for k in keys]}


@router.get("/projects/{course_id}/{project_id}")
def project(course_id: str, project_id: str, request: Request):
    cat = catalog()
    key = f"{course_id}:{project_id}"
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = active(db, user)
        if key not in cat.projects or enrollment.course_id != course_id:
            raise HTTPException(404, "not_found")
        return project_view(db, cat, enrollment, key)


@router.post("/projects/{course_id}/{project_id}/milestones/{milestone_id}")
async def submit_milestone(
    course_id: str, project_id: str, milestone_id: str, body: Milestone, request: Request
):
    cat = catalog()
    key = f"{course_id}:{project_id}"
    stamp = now()
    with Session(engine(request)) as db:
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        if key not in cat.projects or enrollment.course_id != course_id:
            raise HTTPException(404, "not_found")
        view = project_view(db, cat, enrollment, key)
        milestone = next((m for m in view["milestones"] if m["id"] == milestone_id), None)
        if milestone is None:
            raise HTTPException(404, "not_found")
        if view["preparing"]:
            raise HTTPException(423, "concept_preparing")
        if not milestone["available"]:
            raise HTTPException(409, "milestone_locked")
        activity = f"project:{key}:{milestone_id}"
        counted = next(
            c for c in cat.projects[key].concepts if c in learn.curriculum(cat, enrollment)
        )
        if attempts_today(db, enrollment, activity, counted, stamp) >= ATTEMPTS_PER_DAY:
            raise HTTPException(429, "answer_attempts")
        user_id, enrollment_id = user.id, enrollment.id
    # Deterministic checks first: nothing is graded until they pass.
    if len(body.checklist) != len(milestone["checklist"]) or not all(body.checklist):
        raise HTTPException(422, "checklist_incomplete")
    if body.link and await links.broken([body.link]):
        raise HTTPException(422, "link_unreachable")
    project_spec = cat.projects[key]
    task = (
        f"Project: {project_spec.title}\n{project_spec.summary}\n"
        f"Constraints: {'; '.join(project_spec.constraints) or 'none'}\n"
        f"Milestone: {milestone['title']}\nIt must contain:\n- "
        + "\n- ".join(milestone["checklist"])
        + "\nGrade only this milestone's work."
    )
    rubric = [
        dict(criterion=r.criterion, points=r.weight, look_for=r.full_marks)
        for r in project_spec.rubric
    ]
    work = body.work + (f"\n\nLink: {body.link}" if body.link else "")
    grade = await graded(request, user_id, task, rubric, work)
    with Session(engine(request)) as db, db.begin():
        enrollment = need(db.get(Enrollment, enrollment_id))
        details = {"work": body.work, "link": body.link, "grade": grade.to_dict()}
        recorded = now()
        for concept in project_spec.concepts:
            if concept in learn.curriculum(cat, enrollment):
                learn.record_evidence(
                    db,
                    enrollment,
                    concept,
                    "project",
                    grade.score,
                    activity,
                    recorded,
                    details=details,
                )
        return dict(grade=grade.to_dict(), passed=grade.score >= PASS)
