import asyncio
import json
import logging
import secrets
import threading
import time
import uuid
from contextlib import asynccontextmanager

from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError
from starlette.middleware.sessions import SessionMiddleware

from socrat import errors
from socrat.adaptive.routes import router as adaptive_router
from socrat.admin.routes import router as admin_router
from socrat.assessments.routes import router as assessments_router
from socrat.auth import COOKIE, establish_session, require_csrf, require_session
from socrat.config import Settings
from socrat.database import make_engine, record_event
from socrat.explainer.routes import router as explainer_router
from socrat.learn.routes import router as learner_router
from socrat.learn.session_routes import router as session_router
from socrat.library import autosync
from socrat.library.routes import router as library_router
from socrat.models import User
from socrat.passport import router as passport_router
from socrat.quiz.routes import router as adaptive_quiz_router
from socrat.schema_revision import SCHEMA_REVISION
from socrat.trial import router as trial_router
from socrat.vitals import router as vitals_router

logger = logging.getLogger("socrat.requests")


class DevIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    display_name: str | None = Field(default=None, max_length=80)


def warm_quiz_bank() -> None:
    from socrat.catalog.registry import default_catalog
    from socrat.quiz import service as quiz_service

    quiz_service.bank(default_catalog())


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = make_engine(settings.database_url_value)

    @asynccontextmanager
    async def lifespan(app):
        background = None
        if settings.codeforces_autosync:
            background = asyncio.create_task(autosync.run_forever(engine))
        if settings.adaptive_quiz_enabled and settings.prewarm_content:
            await asyncio.to_thread(warm_quiz_bank)
        elif settings.adaptive_quiz_enabled and settings.environment != "test":
            # Building the item bank runs every generator (~20 s); do it before the first check.
            threading.Thread(target=warm_quiz_bank, daemon=True).start()
        yield
        if background is not None:
            background.cancel()
        engine.dispose()

    app = FastAPI(
        title="Socrat API",
        version="2.0.0",
        lifespan=lifespan,
        docs_url=None if settings.secure else "/api/docs",
        openapi_url=None if settings.secure else "/api/openapi.json",
    )
    app.state.engine = engine
    errors.install(engine, settings)
    app.state.settings = settings
    app.include_router(learner_router)
    app.include_router(adaptive_router)
    app.include_router(explainer_router)
    app.include_router(adaptive_quiz_router)
    app.include_router(session_router)
    app.include_router(library_router)
    app.include_router(assessments_router)
    app.include_router(admin_router)
    app.include_router(vitals_router)
    app.include_router(passport_router)
    app.include_router(trial_router)
    app.include_router(errors.router)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret.get_secret_value(),
        session_cookie="socrat_oidc",
        same_site="lax",
        https_only=settings.secure,
        max_age=600,
    )
    registry = CollectorRegistry()
    requests = Counter(
        "socrat_http_requests_total",
        "HTTP responses",
        ["method", "route", "status"],
        registry=registry,
    )
    latency = Histogram(
        "socrat_http_duration_seconds", "HTTP latency", ["route"], registry=registry
    )
    oauth = OAuth()
    if settings.oidc_issuer:
        oauth.register(
            "identity",
            client_id=settings.oidc_client_id,
            client_secret=settings.oidc_client_secret.get_secret_value(),
            server_metadata_url=f"{settings.oidc_issuer.rstrip('/')}/.well-known/openid-configuration",
            client_kwargs={"scope": "openid profile", "code_challenge_method": "S256"},
        )

    def error(code: str, status: int, request_id: str = ""):
        return JSONResponse({"error": {"code": code, "request_id": request_id}}, status_code=status)

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        worker_call = request.url.path.startswith("/api/v1/execution/worker/")
        if (
            request.method in {"POST", "PATCH", "PUT", "DELETE"}
            and not worker_call
            and request.headers.get("origin") != settings.public_origin
        ):
            response = error("origin_rejected", 403, request_id)
        else:
            try:
                response = await call_next(request)
            except Exception as exc:
                logger.exception(json.dumps({"event": "request_failed", "request_id": request_id}))
                route = getattr(request.scope.get("route"), "path", "unmatched")
                errors.capture_exception(app.state.engine, exc, route, request_id)
                response = error("internal_error", 500, request_id)
        response.headers.update(
            {
                "X-Request-ID": request_id,
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            }
        )
        response.headers.setdefault("Referrer-Policy", "same-origin")
        if settings.secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        route = getattr(request.scope.get("route"), "path", "unmatched")
        # Use templates, not raw paths: prevents PII leaks and unbounded metric labels.
        requests.labels(request.method, route, str(response.status_code)).inc()
        latency.labels(route).observe(time.perf_counter() - started)
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "route": route,
                    "status": response.status_code,
                }
            )
        )
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error(str(exc.detail), exc.status_code, request.state.request_id)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Never echo submitted values (code, messages, credentials) in errors.
        return error("validation_failed", 422, request.state.request_id)

    @app.exception_handler(StaleDataError)
    async def stale_write(request, exc):
        return error("concurrent_update_retry", 409, request.state.request_id)

    @app.get("/api/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/api/health/ready")
    def ready():
        try:
            with engine.connect() as connection:
                if (
                    connection.scalar(text("SELECT version_num FROM alembic_version"))
                    != SCHEMA_REVISION
                ):
                    raise ValueError("Schema mismatch")
        except Exception as exc:
            raise HTTPException(503, "database_not_ready") from exc
        return {"status": "ready"}

    @app.get("/api/metrics", include_in_schema=False)
    def metrics(request: Request):
        metrics_token = settings.metrics_token.get_secret_value()
        if not metrics_token or not secrets.compare_digest(
            request.headers.get("authorization", ""), f"Bearer {metrics_token}"
        ):
            raise HTTPException(404, "not_found")
        return Response(generate_latest(registry), media_type="text/plain; version=0.0.4")

    @app.get("/api/v1/features")
    def features():
        return {
            "dev_login": settings.dev_login_enabled,
            "oidc_login": bool(settings.oidc_issuer),
            "ai_provider": settings.ai_provider,
            "code_execution": settings.execution_enabled,
            "execution_backend": settings.execution_backend,
            "demo_mode": settings.demo_mode,
            "adaptive_quiz": settings.adaptive_quiz_enabled,
            "pattern_planner": settings.pattern_planner_enabled,
            "community_url": settings.community_whatsapp_url or None,
            "try_tutor": settings.try_tutor_enabled,
        }

    @app.post("/api/v1/auth/dev-login")
    def dev_login(body: DevIdentity, request: Request):
        if not settings.dev_login_enabled:
            raise HTTPException(404, "not_found")
        response = establish_session(
            request,
            JSONResponse({"authenticated": True}),
            "local-development",
            body.subject,
            body.display_name or "",
        )
        if body.display_name:
            with Session(engine) as db, db.begin():
                from sqlalchemy import select

                user = db.scalar(
                    select(User).where(
                        User.issuer == "local-development", User.subject == body.subject
                    )
                )
                if user is not None and not user.display_name:
                    user.display_name = body.display_name
        return response

    @app.get("/api/v1/auth/login")
    async def oidc_login(request: Request):
        if not settings.oidc_issuer:
            raise HTTPException(503, "identity_provider_not_configured")
        return await oauth.identity.authorize_redirect(
            request, f"{settings.public_origin}/api/v1/auth/callback"
        )

    @app.get("/api/v1/auth/callback")
    async def oidc_callback(request: Request):
        if not settings.oidc_issuer:
            raise HTTPException(503, "identity_provider_not_configured")
        try:
            token = await oauth.identity.authorize_access_token(request)
            identity = token["userinfo"]
            # Authlib validates signature, audience, expiry and nonce; pin issuer explicitly too.
            if identity.get("iss") != settings.oidc_issuer or not identity.get("sub"):
                raise ValueError("Invalid identity")
        except Exception as exc:
            request.session.clear()
            raise HTTPException(401, "identity_verification_failed") from exc
        request.session.clear()
        response = establish_session(
            request, RedirectResponse("/start", status_code=303), identity["iss"], identity["sub"]
        )
        name = str(identity.get("given_name") or identity.get("name") or "")[:80]
        if name:
            with Session(engine) as db, db.begin():
                from sqlalchemy import select

                user = db.scalar(
                    select(User).where(
                        User.issuer == identity["iss"], User.subject == identity["sub"]
                    )
                )
                if user is not None and not user.display_name:
                    user.display_name = name
        return response

    @app.post("/api/v1/auth/logout", status_code=204)
    def logout(request: Request):
        with Session(engine) as db, db.begin():
            session = require_session(request, db)
            require_csrf(request, session)
            record_event(db, session.user_id, "auth.logout")
            db.delete(session)
        response = Response(status_code=204)
        response.delete_cookie(
            COOKIE, path="/", secure=settings.secure, httponly=True, samesite="lax"
        )
        return response

    return app
