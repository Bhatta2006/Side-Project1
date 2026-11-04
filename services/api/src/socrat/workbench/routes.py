"""Workbench API, for learners whose course is practised on the workbench (and admins)."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from socrat.learn import service as learn
from socrat.learn.routes import active, catalog, engine, user_of
from socrat.models import now
from socrat.style import access
from socrat.workbench import service

router = APIRouter(prefix="/api/v1/workbench")
CONCEPT = r"^[a-z][a-z0-9-]{0,63}:[a-z0-9-]{1,64}$"


class Attempt(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    concept: str = Field(pattern=CONCEPT)
    exercise: str = Field(min_length=1, max_length=64)
    given: str | None = Field(default=None, max_length=200)
    lines: list[str] | None = Field(default=None, max_length=25)
    hints_used: int = Field(default=0, ge=0, le=3)
    give_up: bool = False


def studio_allowed(request: Request, db: Session, user, studio: str) -> bool:
    """A learner whose course is practised in this studio, or an admin testing it."""
    from socrat.catalog import shape

    if access.enabled(request.app.state.settings, user):
        return True
    enrollment = learn.active_enrollment(db, user.id)
    course = catalog().courses.get(enrollment.course_id) if enrollment else None
    return course is not None and shape.effective(course).studio == studio


def _allowed(request: Request, user, db: Session) -> None:
    if not studio_allowed(request, db, user, "workbench"):
        raise HTTPException(404, "not_found")


@router.get("/{course}/{concept}")
def exercises(course: str, concept: str, request: Request):
    """The concept's exercises without their answers."""
    qualified = f"{course}:{concept}"
    with Session(engine(request)) as db:
        user = user_of(request, db)
        _allowed(request, user, db)
        cat = catalog()
        if qualified not in cat.concepts:
            raise HTTPException(404, "not_found")
        learn.require_unlocked(db, cat, active(db, user), qualified, now())
        return dict(
            concept=qualified,
            title=cat.concept(qualified).title,
            exercises=[service.public(e) for e in cat.concept(qualified).exercises],
        )


@router.post("/check")
def check(body: Attempt, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        _allowed(request, user, db)
        cat = catalog()
        exercise = service.find(cat, body.concept, body.exercise)
        enrollment = active(db, user)
        if exercise is None:
            raise HTTPException(404, "not_found")
        learn.require_unlocked(db, cat, enrollment, body.concept, now())
        if body.give_up:
            return service.give_up(db, enrollment, body.concept, exercise, body.hints_used, now())
        return service.check(
            db,
            cat,
            enrollment,
            body.concept,
            exercise,
            body.given,
            body.lines,
            body.hints_used,
            now(),
        )
