"""Practice sets API: list topics, make a set for one, answer its questions."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from socrat.assistant import budget
from socrat.assistant.gateway import ProviderError, make_provider
from socrat.drills import service
from socrat.learn import service as learn
from socrat.learn.routes import active, catalog, engine, require_feature, user_of
from socrat.models import Enrollment, need, now
from socrat.workbench.routes import CONCEPT

router = APIRouter(prefix="/api/v1/drills")


class NewSet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    concept: str = Field(pattern=CONCEPT)


class Reply(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: int = Field(ge=0, le=20)
    answer: str = Field(min_length=1, max_length=200)


@router.get("")
def overview(request: Request):
    """The course's topics (unlocked ones can be practised) and the learner's recent sets."""
    cat = catalog()
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = active(db, user)
        require_feature(db, user, "drills")
        locked = learn.locked_concepts(db, cat, enrollment, now())
        return dict(
            course=cat.course(enrollment.course_id).title,
            concepts=service.concepts(cat, enrollment.course_id, locked),
            sets=service.history(db, enrollment),
            per_day=service.SETS_PER_DAY,
        )


@router.post("")
async def make(body: NewSet, request: Request):
    cat = catalog()
    settings = request.app.state.settings
    stamp = now()
    with Session(engine(request)) as db:
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        require_feature(db, user, "drills")
        # Only the learner's own course: another course's topics are not practised here.
        if body.concept not in cat.concepts or not body.concept.startswith(
            f"{enrollment.course_id}:"
        ):
            raise HTTPException(404, "not_found")
        if cat.concept(body.concept).status != "live":
            raise HTTPException(404, "not_found")
        learn.require_unlocked(db, cat, enrollment, body.concept, stamp)
        midnight = learn.local_now(user, stamp).replace(hour=0, minute=0, second=0, microsecond=0)
        if service.made_since(db, enrollment, int(midnight.timestamp())) >= service.SETS_PER_DAY:
            raise HTTPException(429, "practice_sets_today")
        db.expunge(user)
        db.expunge(enrollment)
    provider = budget.Metered(
        make_provider(settings), engine(request), settings, user_id=user.id, feature="practice"
    )
    try:
        questions, source = await service.draft(
            provider, cat, enrollment, user, body.concept, stamp
        )
    except ProviderError as exc:
        code = "ai_budget_reached" if "budget" in str(exc) else "practice_unavailable"
        raise HTTPException(503, code) from exc
    with Session(engine(request)) as db, db.begin():
        record = service.store(
            db, need(db.get(Enrollment, enrollment.id)), cat, body.concept, questions, source, stamp
        )
        return service.view(record)


@router.get("/{set_id}")
def one(set_id: str, request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        record = service.find(db, active(db, user), set_id)
        if record is None:
            raise HTTPException(404, "not_found")
        return service.view(record)


@router.post("/{set_id}/answers")
def reply(set_id: str, body: Reply, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        record = service.find(db, active(db, user), set_id)
        if record is None:
            raise HTTPException(404, "not_found")
        try:
            result = service.answer(record, body.question, body.answer, now())
        except LookupError:
            raise HTTPException(404, "not_found") from None
        except ValueError:
            raise HTTPException(409, "already_answered") from None
        return result | dict(set=service.view(record))
