"""Learner API for "teach me X": type a wish, inspect the parsed intent, edit it, confirm.

Confirming queues the same outline job an owner's brief does. The learner then sees the
planned course (modules, concepts, prerequisites) as it is prepared; nothing here shows
unfinished content as ready. Off unless ``learning_requests_enabled``.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.catalog import generated
from socrat.coursegen import intent as intents
from socrat.coursegen import jobs
from socrat.database import record_event
from socrat.learn.routes import catalog, engine, user_of
from socrat.models import GenerationJob, LearningRequest, now

router = APIRouter(prefix="/api/v1/learning-requests")
OPEN = ("parsed", "needs_clarification")


class Create(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=3, max_length=2000)


class Confirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent: dict | None = None  # the learner's edits, validated as a whole Intent


def _enabled(request: Request) -> None:
    if not request.app.state.settings.learning_requests_enabled:
        raise HTTPException(404, "not_found")


def view(db: Session, row: LearningRequest) -> dict:
    out = dict(
        id=row.id,
        text=row.text,
        status=row.status,
        source=row.source,
        intent=row.intent,
        course_id=row.course_id,
        created_at=row.created_at,
        blueprint=None,
        job=None,
    )
    if row.course_id:
        stored = generated.course(db, row.course_id)
        if stored is not None:
            by_id = {c.id: c for c in stored.concepts}
            out["blueprint"] = dict(
                title=stored.title,
                tagline=stored.tagline,
                modules=[
                    dict(
                        id=m.id,
                        title=m.title,
                        concepts=[
                            dict(
                                id=cid,
                                title=by_id[cid].title,
                                prerequisites=list(by_id[cid].prerequisites),
                                status=by_id[cid].status,
                                objectives=outline.objectives
                                if (outline := by_id[cid].outline)
                                else [],
                            )
                            for cid in m.concepts
                        ],
                    )
                    for m in stored.modules
                ],
            )
        job = db.scalars(
            select(GenerationJob)
            .where(GenerationJob.course_id == row.course_id, GenerationJob.kind == "outline")
            .order_by(GenerationJob.created_at.desc())
        ).first()
        if job is not None:
            out["job"] = dict(state=job.state, error=job.error)
    return out


@router.post("")
async def create(body: Create, request: Request):
    _enabled(request)
    settings, eng = request.app.state.settings, engine(request)
    key = intents.request_key(body.text)
    with Session(eng) as db:
        user = user_of(request, db, write=True)
        user_id = user.id
        same = db.scalars(
            select(LearningRequest).where(
                LearningRequest.user_id == user_id, LearningRequest.key == key
            )
        ).first()
        if same is not None:
            return view(db, same)  # a retry or double submit is the same request
        open_count = db.scalar(
            select(func.count())
            .select_from(LearningRequest)
            .where(LearningRequest.user_id == user_id, LearningRequest.status.in_(OPEN))
        )
        if (open_count or 0) >= settings.learning_requests_max_open:
            raise HTTPException(429, "too_many_open_requests")
    parsed, source = await intents.parse(eng, settings, body.text, user_id)
    status = (
        "blocked"
        if parsed.blocked
        else "needs_clarification"
        if parsed.clarifications
        else "parsed"
    )
    with Session(eng) as db, db.begin():
        row = LearningRequest(
            user_id=user_id,
            key=key,
            text=intents.normalise(body.text),
            intent=parsed.model_dump(mode="json"),
            source=source,
            status=status,
        )
        db.add(row)
        record_event(db, user_id, "learning_request.created", row.id)
        db.flush()
        return view(db, row)


@router.get("")
def mine(request: Request):
    _enabled(request)
    with Session(engine(request)) as db:
        user = user_of(request, db)
        rows = db.scalars(
            select(LearningRequest)
            .where(LearningRequest.user_id == user.id)
            .order_by(LearningRequest.created_at.desc())
            .limit(50)
        )
        return {"items": [view(db, r) for r in rows]}


@router.get("/{request_id}")
def one(request_id: str, request: Request):
    _enabled(request)
    with Session(engine(request)) as db:
        user = user_of(request, db)
        row = db.get(LearningRequest, request_id)
        if row is None or row.user_id != user.id:
            raise HTTPException(404, "not_found")
        return view(db, row)


@router.post("/{request_id}/confirm")
def confirm(request_id: str, body: Confirm, request: Request):
    """Start the course from the (optionally edited) intent. Idempotent: a confirmed request
    returns as it is."""
    _enabled(request)
    settings, cat = request.app.state.settings, catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        row = db.get(LearningRequest, request_id)
        if row is None or row.user_id != user.id:
            raise HTTPException(404, "not_found")
        if row.status == "confirmed":
            return view(db, row)
        if row.status == "blocked":
            raise HTTPException(422, "request_blocked")
        try:
            parsed = intents.Intent.model_validate(body.intent or row.intent)
        except ValidationError as exc:
            raise HTTPException(422, "invalid_intent") from exc
        if parsed.blocked:
            raise HTTPException(422, "request_blocked")
        course_id = intents.slug(parsed.subject, user.id, row.key)
        if course_id in cat.courses or jobs.active(db, course_id) is not None:
            raise HTTPException(409, "generation_in_progress")
        brief = intents.to_brief(parsed, course_id, settings.learning_request_budget_usd)
        jobs.enqueue(
            db,
            "outline",
            course_id,
            {"brief": brief.model_dump(mode="json"), "learning_request": row.id},
            user.id,
        )
        row.intent = parsed.model_dump(mode="json")
        row.course_id, row.status, row.updated_at = course_id, "confirmed", now()
        record_event(db, user.id, "learning_request.confirmed", row.id)
        db.flush()
        return view(db, row)
