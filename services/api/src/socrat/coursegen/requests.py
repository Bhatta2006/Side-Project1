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
from socrat.catalog.revisions import module_version
from socrat.coursegen import community, jobs, prefetch
from socrat.coursegen import intent as intents
from socrat.database import record_event
from socrat.learn.routes import catalog, engine, user_of
from socrat.models import Diagnostic, GeneratedCourse, GenerationJob, LearningRequest, now

router = APIRouter(prefix="/api/v1/learning-requests")
OPEN = ("parsed", "needs_clarification")
ENROLL_MINUTES = (15, 20, 30, 45, 60, 90, 120)  # what POST /enrollments accepts


class Create(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=3, max_length=2000)  # any subject, in the learner's words
    choices: list[str] = Field(default_factory=list, max_length=12)  # fixed picks: intent.PRESETS


class Share(BaseModel):
    model_config = ConfigDict(extra="forbid")
    consent: bool  # must be true: the learner agrees to share this course with everyone
    credit: str = Field(default="anonymous", pattern=r"^(anonymous|name)$")


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
        diagnostic="none",
        enroll=None,
        ready=0,
        total=0,
        community=None,
    )
    if row.course_id:
        stored = generated.course(db, row.course_id)
        meta = db.get(GeneratedCourse, row.course_id)
        check = db.scalar(select(Diagnostic).where(Diagnostic.request_id == row.id))
        diagnosed = check.result["level"] if check and check.result else None
        out["diagnostic"] = (
            "none" if check is None else "done" if check.result is not None else "ready"
        )
        out["published"] = bool(meta and meta.status == "published")
        if stored is not None:
            out["total"] = len(stored.concepts)
            out["ready"] = sum(c.status != "planned" for c in stored.concepts)
        if meta is not None and meta.owner_id == row.user_id and out["published"]:
            out["community"] = dict(
                shared=meta.visibility == "public",
                credit=meta.credit_name,
                **community.standing(db, meta),
            )
        if out["published"] and stored is not None:
            out["enroll"] = dict(  # what to send to POST /api/v1/enrollments
                course=row.course_id,
                language=stored.languages[0],
                level=diagnosed or stored.levels[0].id,
                # The planner's budgets start at 15; a 5-minute lesson length stays in the brief.
                minutes_per_day=next(
                    (m for m in ENROLL_MINUTES if m >= (row.intent.get("minutes_per_day") or 30)),
                    120,
                ),
                weekdays=list(range(7)),
            )
        if stored is not None:
            by_id = {c.id: c for c in stored.concepts}
            latest: dict[str, GenerationJob] = {}
            for j in db.scalars(
                select(GenerationJob)
                .where(GenerationJob.course_id == row.course_id, GenerationJob.kind == "package")
                .order_by(GenerationJob.created_at)
            ):
                latest[j.target] = j  # the newest job per concept wins
            out["blueprint"] = dict(
                title=stored.title,
                tagline=stored.tagline,
                modules=[
                    dict(
                        id=m.id,
                        title=m.title,
                        version=module_version(stored, m),
                        concepts=[
                            dict(
                                id=cid,
                                title=by_id[cid].title,
                                prerequisites=list(by_id[cid].prerequisites),
                                status=by_id[cid].status,
                                # Honest progress: planned, queued, generating, validating,
                                # published, failed, blocked (gave up after retries), cancelled.
                                generation=jobs.lifecycle(
                                    latest.get(cid.split(":", 1)[-1]), by_id[cid].status
                                ),
                                objectives=outline.objectives
                                if (outline := by_id[cid].outline)
                                else [],
                                minutes=by_id[cid].estimated_minutes,
                                category=outline.category if outline else None,
                                evidence=list(outline.evidence) if outline else [],
                                expected=outline.expected if outline else "",
                                related=list(outline.related) if outline else [],
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
            # What the architect assumed and could not settle, so the learner can check it.
            planned = [e for e in job.log if e.get("role") == "architect" and "concepts" in e]
            blueprint = out["blueprint"]
            if planned and isinstance(blueprint, dict):
                blueprint["assumptions"] = planned[-1].get("assumptions", [])
                blueprint["unresolved"] = planned[-1].get("unresolved", [])
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
    parsed = intents.apply_adapter(parsed, body.text)
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
            # The first lessons start now, so they are ready (or nearly) by the time the
            # learner enrols, instead of waiting for their first visit.
            check = db.scalar(select(Diagnostic).where(Diagnostic.request_id == row.id))
            level = check.result["level"] if check and check.result else None
            stored = generated.course(db, row.course_id)
            start = next(
                (lv.start_concept for lv in (stored.levels if stored else []) if lv.id == level),
                None,
            )
            prefetch.initial(db, row.course_id, start)
            record_event(db, user.id, "learning_request.published", row.id)
        db.flush()
        return view(db, row)


@router.post("/{request_id}/share")
def share(request_id: str, body: Share, request: Request):
    """Offer the learner's published course to every learner, if they agree. They may be
    credited by name or stay anonymous, and may stop sharing later. Perks: see ``community``."""
    _enabled(request)
    if not body.consent:
        raise HTTPException(422, "consent_required")
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        row = db.get(LearningRequest, request_id)
        course = db.get(GeneratedCourse, row.course_id) if row and row.course_id else None
        if row is None or row.user_id != user.id or course is None or course.owner_id != user.id:
            raise HTTPException(404, "not_found")
        if course.status != "published":
            raise HTTPException(409, "publish_first")
        if course.moderation != "ok":
            raise HTTPException(403, "sharing_not_allowed")
        stored = generated.course(db, course.id)
        if stored is None or not any(c.status == "live" for c in stored.concepts):
            # Only courses with at least one released (quality-checked) lesson can be shared.
            raise HTTPException(409, "nothing_ready_to_share")
        shared = db.scalar(
            select(func.count())
            .select_from(GeneratedCourse)
            .where(
                GeneratedCourse.owner_id == user.id,
                GeneratedCourse.visibility == "public",
                GeneratedCourse.id != course.id,
            )
        )
        if (shared or 0) >= request.app.state.settings.community_max_shared:
            raise HTTPException(429, "too_many_shared_courses")
        course.visibility = "public"
        course.shared_at = course.shared_at or now()
        course.credit_name = user.display_name[:80] if body.credit == "name" else None
        course.updated_at = max(now(), course.updated_at + 1)  # refresh the catalog cache
        record_event(db, user.id, "learning_request.shared", row.id)
        db.flush()
        return view(db, row)


@router.post("/{request_id}/unshare")
def unshare(request_id: str, request: Request):
    """Stop sharing. Learners who already started it keep their access and progress."""
    _enabled(request)
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        row = db.get(LearningRequest, request_id)
        course = db.get(GeneratedCourse, row.course_id) if row and row.course_id else None
        if row is None or row.user_id != user.id or course is None or course.owner_id != user.id:
            raise HTTPException(404, "not_found")
        course.visibility = "private"
        record_event(db, user.id, "learning_request.unshared", row.id)
        db.flush()
        return view(db, row)


def _owned_course(db: Session, request: Request, request_id: str):
    user = user_of(request, db, write=True)
    row = db.get(LearningRequest, request_id)
    if row is None or row.user_id != user.id or not row.course_id:
        raise HTTPException(404, "not_found")
    meta = db.get(GeneratedCourse, row.course_id)
    if meta is None or meta.owner_id != user.id:
        raise HTTPException(404, "not_found")
    if meta.status != "published":
        raise HTTPException(409, "outline_not_published")
    return user, row


@router.post("/{request_id}/concepts/{concept_id}/regenerate")
def regenerate(request_id: str, concept_id: str, request: Request):
    """The owner asks for one planned lesson again after it failed, gave up or was cancelled.
    A lesson that is queued, being written or already released is left alone (409)."""
    _enabled(request)
    with Session(engine(request)) as db, db.begin():
        user, row = _owned_course(db, request, request_id)
        stored = generated.course(db, row.course_id)
        local = concept_id.split(":", 1)[-1]
        if stored is None or local not in {c.id for c in stored.concepts}:
            raise HTTPException(404, "not_found")
        if stored.concept(local).status != "planned":
            raise HTTPException(409, "already_written")
        if jobs.active(db, row.course_id, local) is not None:
            raise HTTPException(409, "generation_in_progress")
        job = jobs.enqueue(db, "package", row.course_id, {"trigger": "owner"}, user.id, local)
        record_event(db, user.id, "learning_request.regenerate", f"{row.id}:{local}")
        db.flush()
        return view(db, row) | {"queued": job.id}


@router.post("/{request_id}/cancel")
def cancel(request_id: str, request: Request):
    """Stop lessons that have not started. A lesson being written finishes its current run (it
    cannot be interrupted safely mid-call) and is then released or not as usual."""
    _enabled(request)
    with Session(engine(request)) as db, db.begin():
        user, row = _owned_course(db, request, request_id)
        waiting = db.scalars(
            select(GenerationJob).where(
                GenerationJob.course_id == row.course_id, GenerationJob.state == "queued"
            )
        ).all()
        for job in waiting:
            job.state, job.updated_at = "cancelled", now()
            job.log = [*job.log, {"role": "owner", "event": "cancelled", "at": now()}]
        record_event(db, user.id, "learning_request.cancel", row.id)
        db.flush()
        return view(db, row) | {"cancelled": len(waiting)}


@router.get("/{request_id}/revisions")
def revisions(request_id: str, request: Request):
    """Every change made to this course's plan after it was published, newest first, and why."""
    _enabled(request)
    from socrat.coursegen import evolve

    with Session(engine(request)) as db:
        user = user_of(request, db)
        row = db.get(LearningRequest, request_id)
        if row is None or row.user_id != user.id or not row.course_id:
            raise HTTPException(404, "not_found")
        return dict(items=evolve.history(db, row.course_id))
