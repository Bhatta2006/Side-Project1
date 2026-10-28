"""Admin-only API to try learning styles: interpret a wish, pick a preset, set your own."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from socrat.admin.routes import require_admin
from socrat.database import record_event
from socrat.learn import service as learn
from socrat.learn.routes import engine
from socrat.style import access
from socrat.style import spec as styles

router = APIRouter(prefix="/api/v1/admin/style")


class Interpret(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request: str = Field(min_length=3, max_length=600)


class SetStyle(BaseModel):
    """One of: a preset key, a free-text request (interpreted), or a full style."""

    model_config = ConfigDict(extra="forbid")
    preset: str | None = None
    request: str | None = Field(default=None, min_length=3, max_length=600)
    style: styles.StyleSpec | None = None


def _admin(request: Request, db: Session, write: bool = False):
    user = require_admin(request, db, write=write)
    if not request.app.state.settings.style_engine_enabled:
        raise HTTPException(404, "not_found")
    return user


@router.get("/presets")
def presets(request: Request):
    with Session(engine(request)) as db:
        _admin(request, db)
    return {"items": [{"key": k, **v.model_dump(mode="json")} for k, v in styles.PRESETS.items()]}


@router.post("/interpret")
async def interpret(body: Interpret, request: Request):
    """Turn a free-text wish into a style without saving it (a preview)."""
    with Session(engine(request)) as db:
        user = _admin(request, db, write=True)
        user_id = user.id
    spec, source = await styles.interpret(
        engine(request), request.app.state.settings, body.request, user_id=user_id
    )
    return {"style": spec.model_dump(mode="json"), "source": source}


@router.get("/me")
def mine(request: Request):
    with Session(engine(request)) as db:
        user = _admin(request, db)
        enrollment = learn.active_enrollment(db, user.id)
        stored = (enrollment.adaptive or {}).get(styles.STYLE_KEY) if enrollment else None
        return {"style": stored, "enrolled": enrollment is not None}


@router.put("/me")
async def set_mine(body: SetStyle, request: Request):
    """Make the tutor teach this admin's active enrollment in the given style."""
    with Session(engine(request)) as db:
        user = _admin(request, db, write=True)
        user_id = user.id
    chosen = [x for x in (body.preset, body.request, body.style) if x]
    if len(chosen) != 1:
        raise HTTPException(422, "give_one_of_preset_request_style")
    source = "style"
    if body.preset:
        if body.preset not in styles.PRESETS:
            raise HTTPException(422, "unknown_preset")
        spec, source = styles.PRESETS[body.preset], "preset"
    elif body.request:
        spec, source = await styles.interpret(
            engine(request), request.app.state.settings, body.request, user_id=user_id
        )
    else:
        spec = body.style
    with Session(engine(request)) as db, db.begin():
        user = access_user(request, db)
        enrollment = learn.active_enrollment(db, user.id)
        if enrollment is None:
            raise HTTPException(409, "enroll_first")
        enrollment.adaptive = {
            **(enrollment.adaptive or {}),
            styles.STYLE_KEY: spec.model_dump(mode="json"),
        }
        record_event(db, user.id, "style.set", spec.name)
    return {"style": spec.model_dump(mode="json"), "source": source}


@router.delete("/me")
def clear_mine(request: Request):
    with Session(engine(request)) as db, db.begin():
        user = _admin(request, db, write=True)
        enrollment = learn.active_enrollment(db, user.id)
        if enrollment is not None:
            rest = {k: v for k, v in (enrollment.adaptive or {}).items() if k != styles.STYLE_KEY}
            enrollment.adaptive = rest
        record_event(db, user.id, "style.cleared", "")
    return {"style": None}


def access_user(request: Request, db: Session):
    """The admin again, inside the write transaction (no CSRF re-check: already passed)."""
    user = require_admin(request, db)
    if not access.enabled(request.app.state.settings, user):
        raise HTTPException(403, "forbidden")
    return user
