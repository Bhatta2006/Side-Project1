"""Session API consumed independently of the existing learner UI."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from socrat.database import record_event
from socrat.learn import sessions
from socrat.learn.routes import active, catalog, engine, user_of
from socrat.models import ContentIssue, now

router = APIRouter(prefix="/api/v1/learning-sessions")


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Start(Input):
    minutes: Literal[10, 15, 20, 30, 45, 60, 90, 120] | None = None


class Answer(Input):
    block: int = Field(ge=0, le=40)
    step: int = Field(ge=0, le=11)
    choice: int = Field(ge=0, le=5)


class Advance(Input):
    block: int = Field(ge=0, le=40)
    reflection: (
        Literal["clear", "syntax", "strategy", "boundaries", "tired", "need-example"] | None
    ) = None


class Issue(Input):
    block: int = Field(ge=0, le=40)
    reason: Literal["incorrect", "unclear", "language", "accessibility"]
    note: str = Field(default="", max_length=1000)


@router.get("/current")
def current(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = active(db, user)
        row = sessions.current(db, user, enrollment, now())
        return {
            "session": sessions.view(db, catalog(), user, row, enrollment, now()) if row else None
        }


@router.post("")
def start(body: Start, request: Request):
    try:
        with Session(engine(request)) as db, db.begin():
            user = user_of(request, db, write=True)
            enrollment = active(db, user)
            row = sessions.start(
                db,
                catalog(),
                user,
                enrollment,
                now(),
                body.minutes,
                allow_drafts=not request.app.state.settings.secure,
                pattern_planner=request.app.state.settings.pattern_planner_enabled,
            )
            return sessions.view(db, catalog(), user, row, enrollment, now())
    except IntegrityError:
        with Session(engine(request)) as db:
            user = user_of(request, db)
            enrollment = active(db, user)
            concurrent_row = sessions.current(db, user, enrollment, now())
            if concurrent_row is None:
                raise
            return sessions.view(db, catalog(), user, concurrent_row, enrollment, now())


@router.get("/{session_id}")
def detail(session_id: str, request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        row, enrollment = sessions.owned(db, user, session_id, now())
        return sessions.view(db, catalog(), user, row, enrollment, now())


@router.post("/{session_id}/answer")
def answer(session_id: str, body: Answer, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        row, enrollment = sessions.owned(db, user, session_id, now())
        sessions.answer(
            db, catalog(), user, row, enrollment, body.block, body.step, body.choice, now()
        )
        return sessions.view(db, catalog(), user, row, enrollment, now())


@router.post("/{session_id}/advance")
def advance(session_id: str, body: Advance, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        row, enrollment = sessions.owned(db, user, session_id, now())
        sessions.advance(db, catalog(), user, row, enrollment, body.block, now(), body.reflection)
        return sessions.view(db, catalog(), user, row, enrollment, now())


@router.post("/{session_id}/summary-viewed")
def summary_viewed(session_id: str, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        row, _ = sessions.owned(db, user, session_id, now())
        if row.finished_at is None:
            raise HTTPException(409, "session_not_completed")
        if not row.payload.get("summary_viewed"):
            row.payload = {**row.payload, "summary_viewed": now()}
            record_event(db, user.id, "learning.summary_viewed", row.id)
        return {"recorded": True}


@router.post("/{session_id}/issues")
def report_issue(session_id: str, body: Issue, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        row, _ = sessions.owned(db, user, session_id, now())
        if body.block >= len(row.payload["blocks"]) or body.block > row.payload["index"]:
            raise HTTPException(404, "not_found")
        block = row.payload["blocks"][body.block]
        if block["kind"] != "atom":
            raise HTTPException(409, "not_a_content_atom")
        issue = ContentIssue(
            user_id=user.id,
            concept=block["concept"],
            atom_id=block["atom"]["id"],
            version=block["version"],
            reason=body.reason,
            note=body.note,
            created_at=now(),
        )
        db.add(issue)
        db.flush()
        record_event(db, user.id, "content.issue_reported", issue.id)
        issue_id = issue.id
    from socrat.coursegen import quality

    threshold = request.app.state.settings.gen_quarantine_reports
    quality.after_report(engine(request), threshold, concept=block["concept"])
    return {"id": issue_id}
