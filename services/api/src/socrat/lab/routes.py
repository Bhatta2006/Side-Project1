"""Lab API (admins only while the studios are tested)."""

import re

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from socrat.lab import service
from socrat.learn import service as learn
from socrat.learn.graded import attempts_today
from socrat.learn.graded_routes import ATTEMPTS_PER_DAY, graded
from socrat.learn.routes import active, catalog, engine, user_of
from socrat.models import Enrollment, now
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
    values: dict[str, float] = Field(min_length=1, max_length=8)


class Explanation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    concept: str = Field(pattern=CONCEPT)
    experiment: str = Field(min_length=1, max_length=64)
    answer: str = Field(min_length=1, max_length=2000)


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
                | dict(
                    done=service.recorded(db, enrollment, qualified, e) is not None,
                    explained=service.recorded(db, enrollment, qualified, e, "lab-explain")
                    is not None,
                )
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
    """Change any parameters and re-run; only after the learner has predicted."""
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
        return service.vary(experiment, body.values)


@router.post("/explain")
async def explain(body: Explanation, request: Request):
    """Grade the learner's written explanation of the result against the experiment's rubric."""
    cat = catalog()
    experiment = service.find(cat, body.concept, body.experiment)
    if experiment is None:
        raise HTTPException(404, "not_found")
    if not 10 <= len(re.findall(r"\S+", body.answer)) <= 150:
        raise HTTPException(422, "answer_length")
    stamp = now()
    activity = f"lab-explain:{body.concept}:{experiment.id}"
    with Session(engine(request)) as db:
        user = user_of(request, db, write=True)
        _allowed(request, user)
        enrollment = active(db, user)
        learn.require_unlocked(db, cat, enrollment, body.concept, stamp)
        prediction = service.recorded(db, enrollment, body.concept, experiment)
        if prediction is None:
            raise HTTPException(409, "predict_first")
        if attempts_today(db, enrollment, activity, body.concept, stamp) >= ATTEMPTS_PER_DAY:
            raise HTTPException(429, "answer_attempts")
        user_id, enrollment_id = user.id, enrollment.id
        predicted = str(prediction.details.get("predicted", ""))
    truth = service.simulate(experiment)
    if not truth.ok:
        raise HTTPException(503, "lab_unavailable")
    result = truth.output["outputs"][experiment.predict]
    rubric = [c.model_dump() for c in service.rubric_of(experiment)]
    task = service.task_for(experiment, predicted, result)
    grade = await graded(request, user_id, task, rubric, body.answer, experiment.explanation)
    with Session(engine(request)) as db, db.begin():
        learn.record_evidence(
            db,
            db.get(Enrollment, enrollment_id),
            body.concept,
            "explain",
            grade.score,
            activity,
            now(),
            details=dict(
                studio="lab",
                experiment=experiment.id,
                answer=body.answer,
                grade=grade.to_dict(),
            ),
        )
    return dict(grade=grade.to_dict(), model_answer=experiment.explanation)
