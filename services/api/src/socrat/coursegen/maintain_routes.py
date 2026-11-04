"""Owner view of course maintenance: what needs a person, version history, rollback, run now."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from socrat.admin.routes import require_admin
from socrat.assistant.gateway import make_provider
from socrat.catalog.registry import default_catalog
from socrat.coursegen import maintain, validation
from socrat.database import record_event
from socrat.learn.routes import engine
from socrat.models import now

router = APIRouter(prefix="/api/v1/admin/maintenance")
http = None  # replaced in tests; None uses a real client
make = make_provider  # replaced in tests


class Rollback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str


class Confirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewer: str = Field(min_length=3, max_length=120)  # a person's full name
    note: str = Field(default="", max_length=500)


@router.get("/validation")
def awaiting_review(request: Request):
    """Released lessons that automated checks could not vouch for (see coursegen.validation)."""
    with Session(engine(request)) as db:
        require_admin(request, db)
        return dict(items=validation.awaiting_person(db))


@router.post("/validation/{course_id}/{concept_id}/confirm")
def confirm_review(course_id: str, concept_id: str, body: Confirm, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        if len(body.reviewer.split()) < 2:
            raise HTTPException(422, "reviewer_full_name_required")
        try:
            row = validation.confirm(db, course_id, concept_id, body.reviewer, body.note)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        record_event(db, user.id, "validation.confirmed", f"{course_id}:{concept_id}")
        return validation.view(row)


@router.get("")
def queue(request: Request):
    settings = request.app.state.settings
    with Session(engine(request)) as db:
        require_admin(request, db)
        return dict(
            enabled=settings.maintainer_enabled,
            **maintain.attention(db, now(), settings.maintainer_review_days),
        )


@router.post("/run")
async def run(request: Request):
    """One maintenance pass now (also runs on a schedule when the maintainer is enabled)."""
    with Session(engine(request)) as db:
        user = require_admin(request, db, write=True)
        user_id = user.id
    result = await maintain.sweep(
        engine(request), request.app.state.settings, default_catalog(), now(), http, make
    )
    with Session(engine(request)) as db, db.begin():
        record_event(db, user_id, "maintenance.run", str(result["checked"]))
    return result


@router.get("/{course_id}/{concept_id}/versions")
def versions(course_id: str, concept_id: str, request: Request):
    with Session(engine(request)) as db:
        require_admin(request, db)
        return {"items": maintain.history(db, course_id, concept_id)}


@router.post("/{course_id}/{concept_id}/rollback")
def rollback(course_id: str, concept_id: str, body: Rollback, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        try:
            done = maintain.rollback(db, default_catalog(), course_id, concept_id, body.version)
        except LookupError as exc:
            raise HTTPException(404, "not_found") from exc
        except RuntimeError as exc:
            raise HTTPException(409, "being_rewritten") from exc
        record_event(db, user.id, "maintenance.rollback", f"{course_id}:{concept_id}")
        return done
