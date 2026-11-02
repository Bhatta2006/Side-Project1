"""Owner view of course maintenance: what needs a person, version history, rollback, run now."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from socrat.admin.routes import require_admin
from socrat.catalog.registry import default_catalog
from socrat.coursegen import maintain
from socrat.database import record_event
from socrat.learn.routes import engine
from socrat.models import now

router = APIRouter(prefix="/api/v1/admin/maintenance")
http = None  # replaced in tests; None uses a real client


class Rollback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str


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
        engine(request), request.app.state.settings, default_catalog(), now(), http
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
