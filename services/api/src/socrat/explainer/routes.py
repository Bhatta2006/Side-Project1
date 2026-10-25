import asyncio
import json
import uuid
from urllib.parse import urlencode, urlparse

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.assistant import budget
from socrat.assistant import service as assistant
from socrat.assistant.gateway import ProviderError, make_provider
from socrat.database import record_event
from socrat.explainer import generator
from socrat.explainer.artifact import compile_document
from socrat.learn.routes import active, catalog, engine, guard_instruction, user_of
from socrat.models import AssistantMessage, AssistantThread, User, now

router = APIRouter(prefix="/api/v1/playground")
SCOPE = "playground:visual"
GENERATION_SECONDS = 300


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


@router.post("/generate")
async def create(body: CreateInput, request: Request):
    settings = request.app.state.settings
    running = getattr(request.app.state, "explainer_running", None)
    if running is None:
        running = request.app.state.explainer_running = set()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        guard_instruction(db, catalog(), user, body.concept)
        available(settings)
        user_id, language = user.id, enrollment.language
        # Bind the idempotency identity to the authenticated learner, never to a body user_id.
        artifact_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"visual:{user_id}:{body.request_id}"))
        previous = db.get(AssistantMessage, artifact_id)
        if previous:
            if (
                json.loads(previous.content).get("request") != body.prompt
                or json.loads(previous.content).get("level") != body.level
            ):
                raise HTTPException(409, "playground_idempotency_conflict")
            cached = public(owned(db, artifact_id, user_id), settings, user_id)
            if "text/event-stream" in request.headers.get("accept", ""):
                return StreamingResponse(
                    iter(
                        [
                            f"event: ready\ndata: {json.dumps(dict(event='ready', artifact=cached))}\n\n"
                        ]
                    ),
                    media_type="text/event-stream",
                )
            return cached
        thread = assistant.thread_for(db, user_id, SCOPE)
        db.flush()
        thread = db.scalars(
            select(AssistantThread).where(AssistantThread.id == thread.id).with_for_update()
        ).one()
        pending = thread.ladder.get("pending", {})
        if user_id in running or pending.get("until", 0) > now():
            raise HTTPException(409, "playground_request_in_progress")
        if len(running) >= settings.explainer_concurrent_limit:
            raise HTTPException(503, "playground_busy")
        assistant.check_quota(db, settings, user_id, now(), "playground")
        used = (
            db.scalar(
                select(func.count())
                .select_from(AssistantMessage)
                .where(
                    AssistantMessage.thread_id == thread.id,
                    AssistantMessage.role == "user",
                    AssistantMessage.created_at >= now() - 86400,
                )
            )
            or 0
        )
        if used >= settings.explainer_daily_messages:
            raise HTTPException(429, "playground_daily_limit")
        thread.ladder = dict(
            thread.ladder, pending=dict(id=artifact_id, until=now() + GENERATION_SECONDS)
        )
        db.add(
            AssistantMessage(
                thread_id=thread.id, role="user", content=body.prompt, created_at=now()
            )
        )
        thread_id = thread.id
        record_event(db, user_id, "explainer.requested", artifact_id)
    running.add(user_id)

    async def events():
        try:
            async with asyncio.timeout(GENERATION_SECONDS):
                provider_settings = settings
                if settings.explainer_model:
                    key = "openai_model" if settings.ai_provider == "openai" else "ai_model"
                    provider_settings = settings.model_copy(update={key: settings.explainer_model})
                provider = budget.Metered(
                    make_provider(
                        provider_settings,
                        chat_template_kwargs=settings.explainer_chat_template_kwargs,
                    ),
                    engine(request),
                    provider_settings,
                    user_id=user_id,
                    feature="playground",
                )
                async for event in generator.generate(
                    provider, provider_settings, body.prompt, language, body.level
                ):
                    if event["event"] != "document":
                        yield event
                        continue
                    with Session(engine(request)) as db, db.begin():
                        learner = db.get(User, user_id)
                        if learner is None:
                            raise HTTPException(401, "authentication_required")
                        guard_instruction(db, catalog(), learner)
                        row = AssistantMessage(
                            id=artifact_id,
                            thread_id=thread_id,
                            role="assistant",
                            content=json.dumps(event["document"]),
                            provider=settings.ai_provider,
                            created_at=now(),
                        )
                        db.add(row)
                        db.flush()
                        record_event(db, user_id, "explainer.created", artifact_id)
                        result = public(row, settings, user_id)
                    yield dict(event="ready", artifact=result)
        except TimeoutError:
            yield dict(event="error", code="playground_generation_timeout")
        except ProviderError as exc:
            yield dict(event="error", code=str(exc))
        except HTTPException as exc:
            yield dict(event="error", code=str(exc.detail))
        finally:
            running.discard(user_id)
            with Session(engine(request)) as db, db.begin():
                thread = db.get(AssistantThread, thread_id)
                if thread and thread.ladder.get("pending", {}).get("id") == artifact_id:
                    thread.ladder = {
                        key: value for key, value in thread.ladder.items() if key != "pending"
                    }

    if "text/event-stream" in request.headers.get("accept", ""):

        async def stream_events():
            async for event in events():
                yield f"event: {event['event']}\ndata: {json.dumps(event)}\n\n"

        return StreamingResponse(
            stream_events(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"}
        )
    async for event in events():
        if event["event"] == "ready":
            return event["artifact"]
        if event["event"] == "error":
            code = event["code"]
            raise HTTPException(504 if code.endswith("timeout") else 502, code)
    raise HTTPException(502, "playground_generation_invalid")


@router.get("/artifacts")
def history(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        guard_instruction(db, catalog(), user)
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
            ]
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
