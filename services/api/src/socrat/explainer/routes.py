import json
import uuid
from urllib.parse import urlencode, urlparse

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat import entitlements
from socrat.assistant import budget
from socrat.assistant import service as assistant
from socrat.assistant.gateway import ProviderError
from socrat.database import record_event
from socrat.explainer import jobs
from socrat.explainer.artifact import compile_document
from socrat.explainer.jobs import playground_code
from socrat.learn.routes import active, catalog, engine, guard_instruction, user_of
from socrat.models import AssistantMessage, AssistantThread, PlaygroundJob, User, now

router = APIRouter(prefix="/api/v1/playground")
SCOPE = "playground:visual"


class CreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    prompt: str = Field(
        min_length=5, max_length=4000, validation_alias=AliasChoices("prompt", "confusion")
    )
    level: str = Field(default="standard", pattern=r"^(simple|standard|deep)$")
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
            AssistantThread.user_id == user_id,
            AssistantThread.scope == SCOPE,
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


@router.post("/generate", status_code=202)
def create(body: CreateInput, request: Request):
    settings = request.app.state.settings
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        guard_instruction(db, catalog(), user, body.concept)
        available(settings)
        user_id = user.id
        # Bind the idempotency identity to the authenticated learner, never to a body user_id.
        job_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"visual:{user_id}:{body.request_id}"))
        previous = db.get(PlaygroundJob, job_id)
        if previous:
            if previous.prompt != body.prompt or previous.level != body.level:
                raise HTTPException(409, "playground_idempotency_conflict")
            return view(db, previous, settings)
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
        db.add(
            AssistantMessage(
                thread_id=thread.id, role="user", content=body.prompt, created_at=now()
            )
        )
        job = PlaygroundJob(
            id=job_id,
            user_id=user_id,
            thread_id=thread.id,
            prompt=body.prompt,
            level=body.level,
            language=enrollment.language,
            status="queued",
            progress={},
            error="",
            tries=0,
            heartbeat_at=0,
            created_at=now(),
        )
        db.add(job)
        record_event(db, user_id, "explainer.requested", job_id)
        db.flush()
        return view(db, job, settings)


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
        document, csp = compile_document(
            json.loads(row.content)["html"], artifact_id, settings.public_origin, theme
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
