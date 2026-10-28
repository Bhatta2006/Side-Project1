"""Mentor API (admins only while the adaptive engine is tested): see the why-log, run, undo."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from socrat.learn.routes import active, catalog, engine, user_of
from socrat.mentor import service
from socrat.models import now
from socrat.style import access

router = APIRouter(prefix="/api/v1/mentor")


class Undo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=40)


def _allowed(request: Request, user) -> None:
    if not access.enabled(request.app.state.settings, user):
        raise HTTPException(404, "not_found")


@router.get("")
def mentor(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        _allowed(request, user)
        return service.view(active(db, user))


@router.post("/refresh")
def refresh(request: Request):
    """Let the mentor look at the latest results and adjust (bounded; every move is logged)."""
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        _allowed(request, user)
        enrollment = active(db, user)
        service.refresh(db, catalog(), user, enrollment, now())
        return service.view(enrollment)


@router.post("/undo")
def undo(body: Undo, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        _allowed(request, user)
        enrollment = active(db, user)
        if service.undo(db, catalog(), user, enrollment, body.id, now()) is None:
            raise HTTPException(404, "not_found")
        return service.view(enrollment)
