"""Practice sets API: list topics, make a set for one, answer its questions."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.assistant import budget
from socrat.assistant.gateway import ProviderError, make_provider
from socrat.catalog import shape
from socrat.drills import bank, service
from socrat.learn import sections
from socrat.learn import service as learn
from socrat.learn.routes import active, catalog, engine, require_feature, user_of
from socrat.models import Enrollment, Evidence, GeneratedCourse, need, now
from socrat.workbench.routes import CONCEPT

router = APIRouter(prefix="/api/v1/drills")

PRACTICE_EVIDENCE_PER_DAY = 3  # answers per lesson a day that count as evidence
EVIDENCE_PREFIX = "practice:"


def kinds_for(db: Session, cat, course_id: str) -> list[str]:
    """The question kinds that suit this course (bank.plan), for the bank and the model."""
    course = cat.course(course_id)
    meta = db.get(GeneratedCourse, course_id)
    learner = ((meta.brief or {}).get("learner") or {}) if meta is not None else {}
    return bank.plan(course, shape.effective(course).studio, str(learner.get("register", "")))


def count_as_evidence(
    db: Session, enrollment: Enrollment, user, outcome: dict, index: int, right: bool, stamp: int
) -> bool:
    """One bank answer as recall evidence, within the day's limits. True when it counted."""
    question = outcome["questions"][index]
    ref = question.get("ref")
    if outcome.get("source") != "bank" or not ref:
        return False  # a model-written question was never checked: it proves nothing
    # A question the coach added from an earlier lesson is evidence about that lesson.
    concept = question.get("concept") or outcome["concept"]
    midnight = learn.local_now(user, stamp).replace(hour=0, minute=0, second=0, microsecond=0)
    today = (
        select(func.count())
        .select_from(Evidence)
        .where(
            Evidence.enrollment_id == enrollment.id,
            Evidence.created_at >= int(midnight.timestamp()),
        )
    )
    activity = f"{EVIDENCE_PREFIX}{ref}"
    if db.scalar(today.where(Evidence.activity_id == activity)):
        return False  # this question already counted today
    counted = db.scalar(
        today.where(
            Evidence.concept == concept,
            Evidence.activity_id.like(f"{EVIDENCE_PREFIX}%"),
        )
    )
    if (counted or 0) >= PRACTICE_EVIDENCE_PER_DAY:
        return False
    learn.record_evidence(
        db,
        enrollment,
        concept,
        "retrieval",
        1.0 if right else 0.0,
        activity,
        stamp,
        details={"source": "practice"},
    )
    return True


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
        kinds = kinds_for(db, cat, enrollment.course_id)
        if settings.practice_bank:
            # Enough checked material in the lesson itself: the set is ready now, at no cost.
            course = cat.course(enrollment.course_id)
            items = bank.pool(cat, course, body.concept, sections.finished(db, cat, enrollment))
            if len(items) >= bank.MIN_SET:
                right, missed = bank.history(service._records(db, enrollment))
                chosen = bank.choose(items, kinds, right, missed)
                record = service.store(db, enrollment, cat, body.concept, chosen, "bank", stamp)
                db.commit()
                return service.view(record)
        if service.made_since(db, enrollment, int(midnight.timestamp())) >= service.SETS_PER_DAY:
            raise HTTPException(429, "practice_sets_today")
        db.expunge(user)
        db.expunge(enrollment)
    provider = budget.Metered(
        make_provider(settings), engine(request), settings, user_id=user.id, feature="practice"
    )
    try:
        questions, source = await service.draft(
            provider, cat, enrollment, user, body.concept, stamp, kinds
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
    stamp = now()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        record = service.find(db, enrollment, set_id)
        if record is None:
            raise HTTPException(404, "not_found")
        try:
            result = service.answer(record, body.question, body.answer, stamp)
        except LookupError:
            raise HTTPException(404, "not_found") from None
        except ValueError:
            raise HTTPException(409, "already_answered") from None
        counted = request.app.state.settings.practice_evidence and count_as_evidence(
            db, enrollment, user, record.outcome, body.question, result["correct"], stamp
        )
        if not result["correct"]:
            # The coach's ladder: an easier question on the same idea, then one from a
            # lesson underneath it (bank sets only; drills/bank.follow_up).
            cat = catalog()
            extra = bank.follow_up(
                cat, record.outcome, body.question, sections.finished(db, cat, enrollment)
            )
            if extra is not None:
                outcome = dict(record.outcome)
                outcome["questions"] = [*outcome["questions"], extra]
                record.outcome = outcome
        return result | dict(set=service.view(record), counted=bool(counted))
