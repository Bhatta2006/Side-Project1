"""Lab API (admins only while the studios are tested)."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from socrat.lab import service
from socrat.learn import service as learn
from socrat.learn.routes import active, catalog, engine, user_of
from socrat.models import now
from socrat.style import access
from socrat.workbench.routes import CONCEPT

router = APIRouter(prefix="/api/v1/lab")


class Prediction(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    concept: str = Field(pattern=CONCEPT)
    experiment: str = Field(min_length=1, max_length=64)
    given: str = Field(min_length=1, max_length=60)
    hints_used: int = Field(default=0, ge=0, le=3)


class Variation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    concept: str = Field(pattern=CONCEPT)
    experiment: str = Field(min_length=1, max_length=64)
    value: float = Field(ge=-1e9, le=1e9)


def _allowed(request: Request, user) -> None:
    if not access.enabled(request.app.state.settings, user):
        raise HTTPException(404, "not_found")


@router.get("/{course}/{concept}")
def experiments(course: str, concept: str, request: Request):
    """The concept's experiments with their setup and no results."""
    qualified = f"{course}:{concept}"
    with Session(engine(request)) as db:
        user = user_of(request, db)
        _allowed(request, user)
        cat = catalog()
        if qualified not in cat.concepts:
            raise HTTPException(404, "not_found")
        enrollment = active(db, user)
        learn.require_unlocked(db, cat, enrollment, qualified, now())
        found = cat.concept(qualified)
        return dict(
            concept=qualified,
            title=found.title,
            experiments=[
                service.public(e)
                | dict(done=service.recorded(db, enrollment, qualified, e) is not None)
                for e in found.experiments
            ],
        )


@router.post("/predict")
def predict(body: Prediction, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        _allowed(request, user)
        cat = catalog()
        experiment = service.find(cat, body.concept, body.experiment)
        if experiment is None:
            raise HTTPException(404, "not_found")
        enrollment = active(db, user)
        learn.require_unlocked(db, cat, enrollment, body.concept, now())
        return service.predict(
            db, enrollment, body.concept, experiment, body.given, body.hints_used, now()
        )


@router.post("/vary")
def vary(body: Variation, request: Request):
    """Change the adjustable parameter and re-run; only after the learner has predicted."""
    with Session(engine(request)) as db:
        user = user_of(request, db)
        _allowed(request, user)
        cat = catalog()
        experiment = service.find(cat, body.concept, body.experiment)
        if experiment is None:
            raise HTTPException(404, "not_found")
        enrollment = active(db, user)
        learn.require_unlocked(db, cat, enrollment, body.concept, now())
        if service.recorded(db, enrollment, body.concept, experiment) is None:
            raise HTTPException(409, "predict_first")
        return service.vary(experiment, body.value)
