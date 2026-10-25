"""Weekly assessment API. Writes are CSRF-checked; answers are graded at the end."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from socrat import entitlements
from socrat.assessments import service as assessments
from socrat.learn.routes import active, catalog, engine, user_of
from socrat.models import WeeklyAssessment, now

router = APIRouter(prefix="/api/v1/assessments")


class StartInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timed: bool = False


class AnswerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    choice: int = Field(ge=0, le=9)


def owned(db: Session, enrollment_id: str, assessment_id: str) -> WeeklyAssessment:
    attempt = db.get(WeeklyAssessment, assessment_id)
    if attempt is None or attempt.enrollment_id != enrollment_id:
        raise HTTPException(404, "not_found")
    return attempt


@router.get("")
def overview(request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        enrollment = active(db, user)
        stamp = now()
        return {
            "current": assessments.status(db, cat, user, enrollment, stamp),
            "history": assessments.history(db, enrollment),
            "locked": not entitlements.has(db, user.id, "assessment", stamp),
        }


@router.post("/start")
def start(body: StartInput, request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        entitlements.require(db, user.id, "assessment")
        enrollment = active(db, user)
        stamp = now()
        attempt = assessments.start(db, cat, user, enrollment, stamp, body.timed)
        return assessments.view(db, cat, user, attempt, enrollment.language, stamp)


@router.get("/{assessment_id}")
def detail(assessment_id: str, request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        enrollment = active(db, user)
        attempt = owned(db, enrollment.id, assessment_id)
        stamp = now()
        if attempt.finished_at is None and attempt.deadline and stamp > attempt.deadline:
            assessments.finish(db, cat, user, enrollment, attempt, stamp)
        return assessments.view(db, cat, user, attempt, enrollment.language, stamp)


@router.post("/{assessment_id}/answer")
def answer(assessment_id: str, body: AnswerInput, request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        attempt = owned(db, enrollment.id, assessment_id)
        stamp = now()
        assessments.answer(db, cat, user, enrollment, attempt, body.item, body.choice, stamp)
        return assessments.view(db, cat, user, attempt, enrollment.language, stamp)


@router.post("/{assessment_id}/finish")
def finish(assessment_id: str, request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        attempt = owned(db, enrollment.id, assessment_id)
        stamp = now()
        assessments.finish(db, cat, user, enrollment, attempt, stamp)
        return assessments.view(db, cat, user, attempt, enrollment.language, stamp)
