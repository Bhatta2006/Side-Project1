"""Learner API for the starting-level check of a learner-requested course."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.assistant.gateway import ProviderError
from socrat.catalog import generated
from socrat.catalog.schema import Course
from socrat.coursegen import diagnostic
from socrat.coursegen.requests import _enabled
from socrat.database import record_event
from socrat.learn.routes import engine, user_of
from socrat.models import Diagnostic, LearningRequest, now

router = APIRouter(prefix="/api/v1/learning-requests")


class Answers(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answers: list[int | None] = Field(max_length=diagnostic.MAX_ITEMS)


def _view(row: Diagnostic) -> dict:
    out = dict(
        id=row.id,
        questions=diagnostic.public(row.items),
        done=row.result is not None,
        result=None,
        note="A short check to choose where to start. It does not count as mastery and you can start anywhere.",
    )
    if row.result is not None:
        out["result"] = row.result
    return out


def _owned(db: Session, request: Request, request_id: str) -> tuple[LearningRequest, Course]:
    user = user_of(request, db)
    row = db.get(LearningRequest, request_id)
    if row is None or row.user_id != user.id or not row.course_id:
        raise HTTPException(404, "not_found")
    course = generated.course(db, row.course_id)
    if course is None:
        raise HTTPException(409, "outline_not_ready")
    return row, course


@router.post("/{request_id}/diagnostic")
async def start(request_id: str, request: Request):
    """Create the check (once) from the course outline. Same call again returns it."""
    _enabled(request)
    settings, eng = request.app.state.settings, engine(request)
    with Session(eng) as db:
        row, course = _owned(db, request, request_id)
        user_of(request, db, write=True)
        existing = db.scalar(select(Diagnostic).where(Diagnostic.request_id == row.id))
        if existing is not None:
            return _view(existing)
        user_id, claimed = row.user_id, str(row.intent.get("starting_level", "unknown"))
    try:
        items, model = await diagnostic.generate(
            eng,
            settings,
            course,
            claimed,
            request_id,
            user_id,
        )
    except ProviderError as exc:
        raise HTTPException(503, "diagnostic_unavailable") from exc
    except ValueError as exc:
        raise HTTPException(502, "diagnostic_failed") from exc
    with Session(eng) as db, db.begin():
        again = db.scalar(select(Diagnostic).where(Diagnostic.request_id == request_id))
        if again is not None:  # a parallel call won; keep one check per request
            return _view(again)
        made = Diagnostic(request_id=request_id, user_id=user_id, items=items, model=model)
        db.add(made)
        record_event(db, user_id, "diagnostic.created", request_id)
        db.flush()
        return _view(made)


@router.get("/{request_id}/diagnostic")
def get(request_id: str, request: Request):
    _enabled(request)
    with Session(engine(request)) as db:
        row, _ = _owned(db, request, request_id)
        found = db.scalar(select(Diagnostic).where(Diagnostic.request_id == row.id))
        if found is None:
            raise HTTPException(404, "not_found")
        return _view(found)


@router.post("/{request_id}/diagnostic/answer")
def answer(request_id: str, body: Answers, request: Request):
    """Score the answers once; the result carries the suggested starting level."""
    _enabled(request)
    with Session(engine(request)) as db, db.begin():
        user_of(request, db, write=True)
        row, course = _owned(db, request, request_id)
        found = db.scalar(select(Diagnostic).where(Diagnostic.request_id == row.id))
        if found is None:
            raise HTTPException(404, "not_found")
        if found.result is not None:
            return _view(found)
        try:
            result = diagnostic.score(course, found.items, body.answers)
        except ValueError as exc:
            raise HTTPException(422, "answer_every_question") from exc
        found.answers, found.result = body.answers, result
        record_event(db, row.user_id, "diagnostic.answered", request_id)
        row.updated_at = now()
        db.flush()
        return _view(found)
