import json
import uuid
from typing import Any
from urllib.parse import urlencode, urlparse

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from socrat import entitlements
from socrat.assistant import budget
from socrat.assistant import service as assistant
from socrat.assistant.gateway import ProviderError
from socrat.database import record_event
from socrat.explainer import jobs, shared
from socrat.explainer.artifact import compile_document
from socrat.explainer.jobs import playground_code
from socrat.learn import transfers
from socrat.learn.routes import active, catalog, engine, guard_instruction, user_of
from socrat.models import (
    AssistantMessage,
    AssistantThread,
    PlaygroundJob,
    SharedVisual,
    User,
    now,
)

router = APIRouter(prefix="/api/v1/playground")
SCOPE = "playground:visual"


class CreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    prompt: str = Field(
        min_length=5, max_length=4000, validation_alias=AliasChoices("prompt", "confusion")
    )
    level: str = Field(default="standard", pattern=r"^(simple|standard|deep)$")
    # auto lets the prompt alone decide; the worker resolves it to sketch or 3d before generating.
    mode: str = Field(default="auto", pattern=r"^(auto|sketch|3d)$")
    request_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    concept: str | None = Field(
        default=None, pattern=r"^[a-z][a-z0-9-]{0,63}:[a-z][a-z0-9-]{0,63}$"
    )


class ReportInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reason: str = Field(min_length=5, max_length=1000)


def signer(settings):
    return URLSafeTimedSerializer(
        settings.session_secret.get_secret_value(), salt="socrat-visual-frame-v1"
    )


def available(settings):
    if not settings.explainer_enabled:
        raise HTTPException(503, "playground_unavailable")
    if settings.ai_provider == "offline":
        raise HTTPException(503, "playground_generation_unavailable")
    if settings.secure:
        app = urlparse(settings.public_origin)
        sandbox = urlparse(settings.explainer_sandbox_origin)
        # Conservative: reject shared suffix pairs, including shared multi-label public suffixes.
        if (
            sandbox.scheme != "https"
            or not sandbox.hostname
            or sandbox.path not in {"", "/"}
            or sandbox.query
            or sandbox.fragment
            or sandbox.username
            or sandbox.password
            or ".".join(sandbox.hostname.split(".")[-2:])
            == ".".join((app.hostname or "").split(".")[-2:])
        ):
            raise HTTPException(503, "playground_sandbox_unavailable")
        if (
            not settings.explainer_checker_url
            or len(settings.explainer_checker_secret.get_secret_value()) < 32
        ):
            raise HTTPException(503, "playground_checker_unavailable")


def owned(db, artifact_id, user_id):
    row = db.scalar(
        select(AssistantMessage)
        .join(AssistantThread)
        .where(
            AssistantMessage.id == artifact_id,
            AssistantMessage.role == "assistant",
            AssistantThread.scope == SCOPE,
            # Your own saved visuals, and any visual the whole site shares.
            or_(
                AssistantThread.user_id == user_id,
                AssistantMessage.id.in_(
                    select(SharedVisual.artifact_id).where(SharedVisual.status == "ready")
                ),
            ),
        )
    )
    if row is None:
        raise HTTPException(404, "not_found")
    if row.rating == -1:
        raise HTTPException(410, "playground_artifact_reported")
    return row


def public(row, settings, user_id):
    data = json.loads(row.content)
    token = signer(settings).dumps(dict(artifact=row.id, user=user_id))
    origin = settings.explainer_sandbox_origin.rstrip("/") or "http://127.0.0.1:8000"
    return {
        key: value
        for key, value in dict(
            data,
            id=row.id,
            created_at=row.created_at,
            frame_url=f"{origin}/api/v1/playground/artifacts/{row.id}/frame?{urlencode({'token': token})}",
        ).items()
        if key != "html"
    }


def view(db, job, settings):
    """A job's status for the polling client; a finished job carries its artifact."""
    data = dict(
        id=job.id,
        status=job.status,
        progress=job.progress,
        error=job.error or None,
        request=job.prompt,
        level=job.level,
        mode=job.mode or "sketch",
        created_at=job.created_at,
    )
    if job.status == "ready":
        data["artifact"] = public(owned(db, job.id, job.user_id), settings, job.user_id)
    return data


def job_of(db, job_id, user_id):
    job = db.get(PlaygroundJob, job_id)
    if job is None or job.user_id != user_id:
        raise HTTPException(404, "not_found")
    return job


def enqueue(db, settings, user_id, language, prompt, level, job_id, shared=False, mode="sketch"):
    """Queue one generation for ``user_id``, after the checks every generation passes.

    A ``shared`` one fills the cache for every learner, so it skips that learner's own plan
    allowance and chat count; a daily cap still bounds how many one learner can start."""
    thread = assistant.thread_for(db, user_id, SCOPE)
    db.flush()
    # Locking the learner's thread serializes their concurrent requests.
    thread = db.scalars(
        select(AssistantThread).where(AssistantThread.id == thread.id).with_for_update()
    ).one()
    if db.scalar(
        select(PlaygroundJob.id).where(
            PlaygroundJob.user_id == user_id, PlaygroundJob.status.in_(jobs.ACTIVE)
        )
    ):
        raise HTTPException(409, "playground_request_in_progress")
    if shared:
        fills = db.scalar(
            select(func.count())
            .select_from(PlaygroundJob)
            .where(
                PlaygroundJob.user_id == user_id,
                PlaygroundJob.shared.is_(True),
                PlaygroundJob.created_at >= now() - 86400,
            )
        )
        if (fills or 0) >= settings.explainer_daily_messages:
            raise HTTPException(429, "playground_daily_limit")
    else:
        assistant.check_quota(db, settings, user_id, now(), "playground")
        # Server-wide safety cap, counted like the plan allowance (failures are not charged).
        if (
            entitlements.used(db, user_id, "playground", now() - 86400)
            >= settings.explainer_daily_messages
        ):
            raise HTTPException(429, "playground_daily_limit")
    # Fail now, not minutes into the job, when AI is paused or the site-wide budget is spent.
    try:
        budget.check(db, settings, None, now(), "playground")
    except ProviderError as exc:
        raise HTTPException(503, playground_code(str(exc))) from exc
    if not shared:  # a cache fill is not something the learner typed, nor counted against them
        db.add(AssistantMessage(thread_id=thread.id, role="user", content=prompt, created_at=now()))
    job = PlaygroundJob(
        id=job_id,
        user_id=user_id,
        thread_id=thread.id,
        prompt=prompt,
        level=level,
        mode=mode,
        language=language,
        status="queued",
        progress={},
        error="",
        tries=0,
        heartbeat_at=0,
        created_at=now(),
        shared=shared,
    )
    db.add(job)
    record_event(db, user_id, "explainer.requested", job_id)
    db.flush()
    return job


@router.post("/generate", status_code=202)
def create(body: CreateInput, request: Request):
    settings = request.app.state.settings
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        guard_instruction(db, catalog(), user, body.concept)
        available(settings)
        user_id = user.id
        allowed_3d = jobs.may_use_3d(settings, user)
        if body.mode == "3d" and not allowed_3d:
            raise HTTPException(403, "playground_3d_restricted")
        # Auto never picks 3D for an account that may not use it.
        mode = body.mode if allowed_3d or body.mode != "auto" else "sketch"
        # Bind the idempotency identity to the authenticated learner, never to a body user_id.
        job_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"visual:{user_id}:{body.request_id}"))
        previous = db.get(PlaygroundJob, job_id)
        if previous:
            if (
                previous.prompt != body.prompt
                or previous.level != body.level
                # An auto request matches whichever medium the router resolved it to.
                or body.mode not in ("auto", previous.mode)
            ):
                raise HTTPException(409, "playground_idempotency_conflict")
            return view(db, previous, settings)
        return view(
            db,
            enqueue(
                db,
                settings,
                user_id,
                enrollment.language,
                body.prompt,
                body.level,
                job_id,
                mode=mode,
            ),
            settings,
        )


class SharedInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    concept: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}:[a-z][a-z0-9-]{0,63}$")
    level: str = Field(default="standard", pattern=r"^(simple|standard|deep)$")
    # The problem the learner is on, so a check that must be unaided never offers a visual.
    problem: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{0,127}$")
    # One page of the lesson (0-based, as the lesson page numbers them): "show me this part".
    section: int | None = Field(default=None, ge=0, le=59)


def serve_shared(db, settings, user, enrollment, body: SharedInput, start: bool):
    """The shared visual for a concept: served from the index, or (on a miss) generated once."""
    cat = catalog()
    guard_instruction(db, cat, user, body.concept)
    if body.problem and transfers.is_pending(db, cat, enrollment, body.problem):
        raise HTTPException(423, "independent_work_in_progress")
    concept = cat.concept(body.concept)
    if body.section is None:
        source, prompt = shared.fingerprint(concept), shared.prompt_for(concept)
    else:
        if not settings.explainer_section_visuals:
            raise HTTPException(404, "not_found")
        pages = shared.parts(concept.lesson)
        if body.section >= len(pages) or not pages[body.section][1]:
            raise HTTPException(404, "not_found")
        title, text = pages[body.section]
        source = shared.fingerprint_part(concept, title, text)
        prompt = shared.prompt_for_part(concept, title, text)
    key = (shared.key_for(body.concept, body.section), body.level, enrollment.language)
    row = db.get(SharedVisual, key, with_for_update=True)
    if row is not None:
        shared.settle(db, row)
    if shared.usable(row, source):
        available(settings)
        if start:
            row.hits += 1
        artifact = public(owned(db, row.artifact_id, user.id), settings, user.id)
        return dict(state="ready", artifact=artifact)
    job = db.get(PlaygroundJob, row.job_id) if row is not None and row.job_id else None
    if row is not None and row.status == "generating" and row.source_hash == source:
        return dict(
            state="generating",
            progress=job.progress if job else {},
            mine=bool(job and job.user_id == user.id),
        )
    if not start:
        failed = row is not None and row.status == "failed" and row.source_hash == source
        return dict(state="failed" if failed else "none", error=(job.error if job else "") or None)
    available(settings)
    job_id = str(uuid.uuid4())
    fresh = dict(status="generating", job_id=job_id, artifact_id=None, source_hash=source)
    if row is None:
        row = SharedVisual(
            concept=key[0],
            level=body.level,
            language=enrollment.language,
            reports=[],
            hits=0,
            created_at=now(),
            updated_at=now(),
            **fresh,
        )
        db.add(row)
        db.flush()  # a learner who got here first wins; the other attaches to their job
    else:
        values: dict[str, Any] = dict(fresh, reports=[], updated_at=now())
        for name, value in values.items():
            setattr(row, name, value)
    # Whoever asks first starts the one generation; it is not charged to their plan.
    enqueue(
        db,
        settings,
        user.id,
        enrollment.language,
        prompt,
        body.level,
        job_id,
        shared=True,
    )
    return dict(state="generating", progress={}, mine=True)


@router.post("/shared")
def shared_start(body: SharedInput, request: Request):
    settings = request.app.state.settings
    for attempt in (1, 2):
        try:
            with Session(engine(request)) as db, db.begin():
                user = user_of(request, db, write=True)
                return serve_shared(db, settings, user, active(db, user), body, start=True)
        except IntegrityError:
            if attempt == 2:
                raise HTTPException(409, "playground_request_in_progress") from None


@router.get("/shared")
def shared_state(
    request: Request,
    concept: str = Query(pattern=r"^[a-z][a-z0-9-]{0,63}:[a-z][a-z0-9-]{0,63}$"),
    level: str = Query(default="standard", pattern=r"^(simple|standard|deep)$"),
    problem: str | None = Query(default=None, pattern=r"^[a-z0-9][a-z0-9-]{0,127}$"),
    section: int | None = Query(default=None, ge=0, le=59),
):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        body = SharedInput(concept=concept, level=level, problem=problem, section=section)
        return serve_shared(
            db, request.app.state.settings, user, active(db, user), body, start=False
        )


# ponytail: clients poll every ~1.5 s; push (LISTEN/NOTIFY + SSE) if polling load ever matters.
@router.get("/jobs/{job_id}")
def job_status(job_id: str, request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        guard_instruction(db, catalog(), user)
        return view(db, job_of(db, job_id, user.id), request.app.state.settings)


@router.post("/jobs/{job_id}/cancel")
def cancel(job_id: str, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        job = job_of(db, job_id, user.id)
        if job.status in jobs.ACTIVE:
            job.status = "cancelled"
        return dict(status=job.status)


@router.get("/artifacts")
def history(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        guard_instruction(db, catalog(), user)
        # A generation still running (the learner reloaded or came back) is resumed by the page.
        pending = db.scalars(
            select(PlaygroundJob)
            .where(PlaygroundJob.user_id == user.id, PlaygroundJob.status.in_(jobs.ACTIVE))
            .limit(1)
        ).first()
        rows = db.scalars(
            select(AssistantMessage)
            .join(AssistantThread)
            .where(
                AssistantThread.user_id == user.id,
                AssistantThread.scope == SCOPE,
                AssistantMessage.role == "assistant",
                AssistantMessage.rating.is_distinct_from(-1),
            )
            .order_by(AssistantMessage.seq.desc())
            .limit(20)
        )
        return dict(
            # Whether the mode picker (Auto, Sketch, 3D) is offered to this account.
            three_d=jobs.may_use_3d(request.app.state.settings, user),
            items=[
                dict(id=row.id, title=json.loads(row.content)["title"], created_at=row.created_at)
                for row in rows
            ],
            pending=view(db, pending, request.app.state.settings) if pending else None,
        )


@router.get("/artifacts/{artifact_id}")
def detail(artifact_id: str, request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        guard_instruction(db, catalog(), user)
        return public(owned(db, artifact_id, user.id), request.app.state.settings, user.id)


@router.post("/artifacts/{artifact_id}/report")
def report(artifact_id: str, body: ReportInput, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        guard_instruction(db, catalog(), user)
        row = owned(db, artifact_id, user.id)
        flagged = db.scalar(select(SharedVisual).where(SharedVisual.artifact_id == artifact_id))
        if flagged is not None:  # a shared visual is retired by several learners, not one
            shared.report(db, flagged, row, user.id, body.reason)
            record_event(db, user.id, "explainer.reported", artifact_id)
            return dict(reported=True)
        row.rating = -1
        db.add(
            AssistantMessage(
                thread_id=row.thread_id,
                role="feedback",
                content=json.dumps(dict(artifact_id=artifact_id, reason=body.reason)),
            )
        )
        record_event(db, user.id, "explainer.reported", artifact_id)
    return dict(reported=True)


@router.get("/artifacts/{artifact_id}/frame")
def frame(
    artifact_id: str,
    token: str,
    request: Request,
    theme: str = Query(default="light", pattern=r"^(light|dark)$"),
):
    settings = request.app.state.settings
    available(settings)
    if settings.secure and request.url.netloc != urlparse(settings.explainer_sandbox_origin).netloc:
        raise HTTPException(404, "not_found")
    try:
        identity = signer(settings).loads(token, max_age=3600)
    except BadSignature as exc:
        raise HTTPException(403, "playground_frame_expired") from exc
    if identity.get("artifact") != artifact_id:
        raise HTTPException(403, "playground_frame_expired")
    with Session(engine(request)) as db:
        user = db.get(User, identity.get("user"))
        if user is None:
            raise HTTPException(404, "not_found")
        guard_instruction(db, catalog(), user)
        row = owned(db, artifact_id, user.id)
        content = json.loads(row.content)
        # Older artifacts predate the mode field; they are always sketch documents.
        document, csp = compile_document(
            content["html"],
            artifact_id,
            settings.public_origin,
            theme,
            mode=content.get("mode", "sketch"),
        )
    return HTMLResponse(
        document,
        headers={
            "Content-Security-Policy": csp,
            "Referrer-Policy": "no-referrer",
            "Origin-Agent-Cluster": "?1",
            "X-DNS-Prefetch-Control": "off",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=(), clipboard-read=(), clipboard-write=(), payment=(), usb=(), fullscreen=()",
        },
    )
