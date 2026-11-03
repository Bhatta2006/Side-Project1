"""Adaptive quiz API. Every route answers 404 unless ``adaptive_quiz_enabled`` is set."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from socrat.learn.routes import active, catalog, engine, guard_instruction, user_of
from socrat.models import now
from socrat.quiz import service

Concept = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{0,63}:[a-z][a-z0-9-]{0,63}$")]


class StartInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: str = Field(pattern=r"^[a-z_]{1,24}$")
    concepts: list[Concept] = Field(min_length=1, max_length=8)


class AnswerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item: str = Field(min_length=3, max_length=200)
    choice: int | None = Field(default=None, ge=0, le=9)  # None: "I haven't seen this"
    time_s: int = Field(default=0, ge=0, le=7200)
    confidence: int | None = Field(default=None, ge=1, le=4)  # optional, for calibration


def enabled(request: Request) -> None:
    if not request.app.state.settings.adaptive_quiz_enabled:
        raise HTTPException(404, "not_found")


# The flag check runs before body validation, so a disabled engine is invisible.
router = APIRouter(prefix="/api/v1/adaptive-quiz", dependencies=[Depends(enabled)])


@router.post("/sessions")
def start(body: StartInput, request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        guard_instruction(db, cat, user)
        enrollment = active(db, user)
        for concept in body.concepts:
            if concept not in cat.concepts:
                raise HTTPException(404, "not_found")
        session = service.start(db, cat, enrollment, body.mode, body.concepts, now())
        if session is None:
            return {"engine": "legacy", "reason": service.LEGACY_REASON, "mode": body.mode}
        return service.view(cat, session, enrollment.language)


@router.get("/sessions/{session_id}/next")
def next_item(session_id: str, request: Request):
    cat = catalog()
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = active(db, user)
        return service.view(cat, service.owned(db, enrollment, session_id), enrollment.language)


@router.post("/sessions/{session_id}/hint")
def hint(session_id: str, request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        return service.hint(cat, service.owned(db, enrollment, session_id))


@router.post("/sessions/{session_id}/answer")
def submit_answer(session_id: str, body: AnswerInput, request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        session = service.owned(db, enrollment, session_id)
        result = service.answer(
            db,
            cat,
            enrollment,
            session,
            body.item,
            body.choice,
            body.time_s,
            now(),
            confidence=body.confidence,
        )
        return {**result, "session": service.view(cat, session, enrollment.language)}


@router.get("/sessions/{session_id}/summary")
def session_summary(session_id: str, request: Request):
    cat = catalog()
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = active(db, user)
        return service.summary(db, cat, enrollment, service.owned(db, enrollment, session_id))
