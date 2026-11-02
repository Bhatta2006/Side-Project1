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
from socrat.catalog.registry import CatalogError, default_catalog
from socrat.coursegen import intent as intents
from socrat.coursegen import jobs
from socrat.database import record_event
from socrat.learn.routes import catalog, engine, user_of
from socrat.models import GeneratedCourse, GenerationJob, LearningRequest, now

router = APIRouter(prefix="/api/v1/learning-requests")
OPEN = ("parsed", "needs_clarification")
ENROLL_MINUTES = (15, 20, 30, 45, 60, 90, 120)  # what POST /enrollments accepts


class Create(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=3, max_length=2000)  # any subject, in the learner's words
    choices: list[str] = Field(default_factory=list, max_length=12)  # fixed picks: intent.PRESETS


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
        published=False,
        enroll=None,
    )
    if row.course_id:
        stored = generated.course(db, row.course_id)
        meta = db.get(GeneratedCourse, row.course_id)
        out["published"] = bool(meta and meta.status == "published")
        if out["published"] and stored is not None:
            out["enroll"] = dict(  # what to send to POST /api/v1/enrollments
                course=row.course_id,
                language=stored.languages[0],
                level=stored.levels[0].id,
                # The planner's budgets start at 15; a 5-minute lesson length stays in the brief.
                minutes_per_day=next(
                    (m for m in ENROLL_MINUTES if m >= (row.intent.get("minutes_per_day") or 30)),
                    120,
                ),
                weekdays=list(range(7)),
            )
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


@router.get("/options")
def options(request: Request):
    """Suggested subjects (free text is always allowed) and the fixed choices."""
    _enabled(request)
    return intents.options()


@router.post("")
async def create(body: Create, request: Request):
    _enabled(request)
    settings, eng = request.app.state.settings, engine(request)
    try:
        picks = intents.check_choices(body.choices)
    except ValueError as exc:
        raise HTTPException(422, "invalid_choice") from exc
    key = intents.request_key(intents.normalise(body.text) + "|" + ",".join(picks))
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
    parsed = intents.apply_choices(parsed, picks)
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


@router.post("/{request_id}/publish")
def publish(request_id: str, request: Request):
    """Release the learner's own outline (after they have inspected it) so they can enrol.
    The course stays private to them. Idempotent."""
    _enabled(request)
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        row = db.get(LearningRequest, request_id)
        if row is None or row.user_id != user.id or not row.course_id:
            raise HTTPException(404, "not_found")
        course = db.get(GeneratedCourse, row.course_id)
        if course is None:
            raise HTTPException(409, "outline_not_ready")
        if course.owner_id != user.id:
            raise HTTPException(404, "not_found")
        if course.status == "review":
            try:
                generated.publish(db, default_catalog(), row.course_id)
            except (ValueError, CatalogError) as exc:
                raise HTTPException(422, "outline_invalid") from exc
            record_event(db, user.id, "learning_request.published", row.id)
        db.flush()
        return view(db, row)
