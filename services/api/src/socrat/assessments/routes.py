"""Weekly assessment API. Writes are CSRF-checked; answers are graded at the end."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from socrat import entitlements
from socrat.assessments import hard
from socrat.assessments import service as assessments
from socrat.learn.routes import active, catalog, engine, user_of
from socrat.models import WeeklyAssessment, now

router = APIRouter(prefix="/api/v1/assessments")


class StartInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timed: bool = True  # ignored: every weekly is a 30-minute exam


class AnswerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item: str = Field(pattern=r"^[a-z0-9][a-z0-9:._/-]{0,199}$")  # bank key, gen- key, legacy id
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
async def start(body: StartInput, request: Request):
    """Plans the exam from the bank, has the hardest questions written and proven by running
    them (up to about two minutes, outside any transaction), then creates the attempt."""
    cat = catalog()
    db_engine = engine(request)
    with Session(db_engine) as db, db.begin():
        user = user_of(request, db, write=True)
        entitlements.require(db, user.id, "assessment")
        enrollment = active(db, user)
        planned = assessments.plan(db, cat, user, enrollment, now())
        if isinstance(planned, WeeklyAssessment):
            return assessments.view(db, cat, user, planned, enrollment.language, now())
        user_id = user.id
    generated = await hard.generate(
        db_engine, request.app.state.settings, cat, planned.wanted(), planned.language, user_id
    )
    try:
        with Session(db_engine) as db, db.begin():
            user = user_of(request, db, write=True)
            enrollment = active(db, user)
            stamp = now()
            attempt = assessments.create(db, enrollment, planned, generated, stamp)
            return assessments.view(db, cat, user, attempt, enrollment.language, stamp)
    except IntegrityError:  # a second start (another tab) won the race: show that attempt
        with Session(db_engine) as db, db.begin():
            user = user_of(request, db)
            enrollment = active(db, user)
            stamp = now()
            existing = assessments.this_week(db, enrollment, planned.week)
            assert existing is not None  # the row that raised the conflict
            return assessments.view(db, cat, user, existing, enrollment.language, stamp)


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
