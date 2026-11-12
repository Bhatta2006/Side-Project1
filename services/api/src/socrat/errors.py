"""Error reporting without a third-party script: server exceptions, browser crashes and
learner problem reports land in ``error_reports``, grouped by fingerprint, for /admin.

When ``SOCRAT_SENTRY_DSN`` is set, server exceptions also go to Sentry (or a self-hosted,
Sentry-compatible GlitchTip). Reports never carry request bodies, code, cookies or query
strings; browser reports carry a message, a trimmed stack and the page path only.
"""

import hashlib
import json
import logging
import time
import traceback
from collections import defaultdict, deque
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Engine, case, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from socrat.auth import require_csrf, require_session
from socrat.config import Settings
from socrat.models import ErrorReport, User, now

log = logging.getLogger("socrat.errors")
router = APIRouter(prefix="/api/v1")

STACK_LIMIT = 4000
MESSAGE_LIMIT = 500
# Per-IP browser reports per minute; a crash loop must not flood the table.
BROWSER_PER_MINUTE = 20
_recent: dict[str, deque] = defaultdict(deque)


def fingerprint(source: str, message: str, route: str, where: str = "") -> str:
    first = message.strip().splitlines()[0][:200] if message.strip() else ""
    return hashlib.sha256(f"{source}|{first}|{route}|{where}".encode()).hexdigest()


def store(
    engine: Engine,
    *,
    source: str,
    message: str,
    route: str = "",
    detail: dict | None = None,
    user_id: str | None = None,
    where: str = "",
) -> None:
    """Record or count one occurrence. Never raises: reporting must not cause errors."""
    key = fingerprint(source, message, route, where if source != "learner" else str(time.time_ns()))
    try:
        with Session(engine) as db, db.begin():
            row = db.scalar(select(ErrorReport).where(ErrorReport.fingerprint == key))
            stamp = now()
            if row is None:
                db.add(
                    ErrorReport(
                        source=source,
                        fingerprint=key,
                        message=message[: MESSAGE_LIMIT * 4],
                        route=route[:120],
                        detail=detail or {},
                        user_id=user_id,
                        first_at=stamp,
                        last_at=stamp,
                    )
                )
            else:
                row.count += 1
                row.last_at = stamp
                row.detail = detail or row.detail
                if row.status == "resolved":
                    row.status = "open"  # it came back
                    row.resolved_at = None
                    row.resolved_by = None
    except SQLAlchemyError:
        log.warning(json.dumps({"event": "error_report_not_stored"}))


class StoreHandler(logging.Handler):
    """ERROR logs from Socrat's own loggers (budget alarms, job failures) become reports.

    Request failures are captured with their exception by the middleware instead.
    """

    def __init__(self, engine: Engine):
        super().__init__(logging.ERROR)
        self.engine = engine

    def emit(self, record: logging.LogRecord):
        if record.name in {"socrat.requests", "socrat.errors"}:
            return
        store(
            self.engine,
            source="server",
            message=f"{record.name}: {record.getMessage()[:MESSAGE_LIMIT]}",
            where=f"{record.pathname.rsplit('socrat', 1)[-1]}:{record.lineno}",
        )


def install(engine: Engine, settings: Settings):
    root = logging.getLogger("socrat")
    for handler in root.handlers:
        if isinstance(handler, StoreHandler):
            handler.engine = engine  # the newest app owns reporting (tests build several)
            break
    else:
        root.addHandler(StoreHandler(engine))
    configure_sentry(settings)


def configure_sentry(settings: Settings) -> bool:
    if not settings.sentry_dsn:
        return False
    try:
        import sentry_sdk
    except ImportError:
        log.warning(json.dumps({"event": "sentry_sdk_missing"}))
        return False
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=settings.release or None,
        send_default_pii=False,
        traces_sample_rate=0.0,
        max_request_body_size="never",
    )
    return True


def capture_exception(engine: Engine, exc: BaseException, route: str, request_id: str):
    frames = traceback.extract_tb(exc.__traceback__)
    where = next(
        (
            f"{f.filename.rsplit('socrat', 1)[-1]}:{f.lineno}"
            for f in reversed(frames)
            if "socrat" in f.filename
        ),
        "",
    )
    store(
        engine,
        source="server",
        message=f"{type(exc).__name__}: {str(exc)[:MESSAGE_LIMIT]}",
        route=route,
        detail=dict(
            request_id=request_id,
            stack="".join(traceback.format_exception(exc))[-STACK_LIMIT:],
        ),
        where=where,
    )
    try:
        import sentry_sdk

        sentry_sdk.capture_exception(exc)
    except ImportError:
        pass


class BrowserError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["error", "unhandledrejection", "render", "runner"]
    message: str = Field(min_length=1, max_length=MESSAGE_LIMIT)
    stack: str = Field(default="", max_length=STACK_LIMIT)
    route: str = Field(max_length=120, pattern=r"^/[^?#]*$")
    release: str = Field(default="", max_length=40)


@router.post("/client-errors", status_code=204)
async def client_error(request: Request):
    """Browser crash reports (no sign-in needed): same-origin and rate-limited per IP."""
    settings = request.app.state.settings
    if request.headers.get("origin") != settings.public_origin.rstrip("/"):
        raise HTTPException(403, "origin_rejected")
    ip = request.client.host if request.client else "unknown"
    window = _recent[ip]
    stamp = time.monotonic()
    while window and stamp - window[0] > 60:
        window.popleft()
    if len(window) >= BROWSER_PER_MINUTE:
        return
    window.append(stamp)
    try:
        report = BrowserError.model_validate_json(await request.body())
    except ValueError as exc:
        raise HTTPException(422, "invalid_report") from exc
    store(
        request.app.state.engine,
        source="browser",
        message=f"{report.kind}: {report.message}",
        route=report.route,
        detail=dict(stack=report.stack, release=report.release),
    )


class ProblemReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=3, max_length=2000)
    route: str = Field(max_length=120, pattern=r"^/[^?#]*$")
    category: Literal["bug", "content", "idea", "feedback", "other"] = "bug"


@router.post("/problem-reports")
def problem_report(body: ProblemReport, request: Request):
    """A signed-in learner tells us something is wrong (or could be better)."""
    engine = request.app.state.engine
    with Session(engine) as db:
        session = require_session(request, db)
        require_csrf(request, session)
        user_id = session.user_id
        recent = db.scalars(
            select(ErrorReport.id).where(
                ErrorReport.user_id == user_id,
                ErrorReport.source == "learner",
                ErrorReport.first_at > now() - 3600,
            )
        ).all()
        if len(recent) >= 10:
            raise HTTPException(429, "too_many_reports")
    store(
        engine,
        source="learner",
        message=f"[{body.category}] {body.message}",
        route=body.route,
        detail=dict(category=body.category),
        user_id=user_id,
    )
    if body.category == "content":
        from socrat.coursegen import quality

        threshold = request.app.state.settings.gen_quarantine_reports
        quality.after_report(engine, threshold, route=body.route)
    return {"received": True}


def _person(user: User | None) -> dict | None:
    if user is None:
        return None
    return dict(
        id=user.id, name=user.display_name or "Learner", email=user.email or user.admin_email
    )


def category_of(row: ErrorReport) -> str | None:
    return (row.detail or {}).get("category") if row.source == "learner" else None


def learner_text(row: ErrorReport) -> str:
    """The learner's own words, without the "[bug] " prefix the queue shows."""
    category = category_of(row)
    prefix = f"[{category}] " if category else ""
    return row.message[len(prefix) :] if prefix and row.message.startswith(prefix) else row.message


def recent(db: Session, limit: int = 50, status: str = "open") -> list[dict]:
    """The admin queue: open items newest first, or resolved ones by when they were resolved."""
    query = select(ErrorReport).where(ErrorReport.status == status)
    if status == "resolved":
        query = query.order_by(
            ErrorReport.resolved_at.desc().nulls_last(), ErrorReport.last_at.desc()
        )
    else:
        query = query.order_by(ErrorReport.last_at.desc())
    rows = list(db.scalars(query.limit(limit)))
    ids = {r.user_id for r in rows if r.user_id} | {r.resolved_by for r in rows if r.resolved_by}
    people = {u.id: u for u in db.scalars(select(User).where(User.id.in_(ids)))} if ids else {}
    return [
        dict(
            id=r.id,
            source=r.source,
            category=category_of(r),
            message=r.message,
            route=r.route,
            count=r.count,
            first_at=r.first_at,
            last_at=r.last_at,
            request_id=(r.detail or {}).get("request_id"),
            stack=(r.detail or {}).get("stack", "")[:1500],
            reporter=_person(people.get(r.user_id)) if r.user_id else None,
            resolved_at=r.resolved_at,
            resolved_by=_person(people.get(r.resolved_by)) if r.resolved_by else None,
            thanks_seen_at=r.thanks_seen_at,
        )
        for r in rows
    ]


def _count(value: Any) -> int:
    """A SQL count or sum as an int (a sum over no rows is NULL)."""
    return int(value or 0)


def reporter_log(db: Session) -> dict:
    """Learner reports per reporter: how many they sent and how many were solved."""
    solved = func.sum(case((ErrorReport.status == "resolved", 1), else_=0))
    rows = db.execute(
        select(
            ErrorReport.user_id,
            func.count(ErrorReport.id),
            solved,
            func.max(ErrorReport.first_at),
        )
        .where(ErrorReport.source == "learner", ErrorReport.user_id.is_not(None))
        .group_by(ErrorReport.user_id)
        .order_by(func.count(ErrorReport.id).desc(), func.max(ErrorReport.first_at).desc())
    ).all()
    ids = [r[0] for r in rows]
    people = {u.id: u for u in db.scalars(select(User).where(User.id.in_(ids)))} if ids else {}
    reporters = [
        dict(
            reporter=_person(people.get(user_id)),
            reported=_count(reported),
            solved=_count(done),
            open=_count(reported) - _count(done),
            last_reported_at=last,
        )
        for user_id, reported, done, last in rows
        if user_id in people
    ]
    return dict(
        reporters=reporters,
        totals=dict(
            reporters=len(reporters),
            reported=sum(r["reported"] for r in reporters),
            solved=sum(r["solved"] for r in reporters),
            open=sum(r["open"] for r in reporters),
        ),
    )


@router.get("/problem-reports/thanks")
def thanks(request: Request):
    """The signed-in learner's resolved reports they have not yet been thanked for."""
    if not request.app.state.settings.report_thanks_enabled:
        return {"items": []}
    with Session(request.app.state.engine) as db:
        session = require_session(request, db)
        rows = db.scalars(
            select(ErrorReport)
            .where(
                ErrorReport.user_id == session.user_id,
                ErrorReport.source == "learner",
                ErrorReport.status == "resolved",
                ErrorReport.thanks_seen_at.is_(None),
            )
            .order_by(ErrorReport.resolved_at.desc().nulls_last())
            .limit(5)
        )
        return {
            "items": [
                dict(
                    id=r.id,
                    category=category_of(r),
                    message=learner_text(r)[:200],
                    resolved_at=r.resolved_at,
                )
                for r in rows
            ]
        }


class ThanksSeen(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ids: list[str] = Field(min_length=1, max_length=20)


@router.post("/problem-reports/thanks/seen")
def thanks_seen(body: ThanksSeen, request: Request):
    """The learner closed the thank-you note: only their own reports are marked."""
    with Session(request.app.state.engine) as db, db.begin():
        session = require_session(request, db)
        require_csrf(request, session)
        rows = db.scalars(
            select(ErrorReport).where(
                ErrorReport.id.in_(body.ids),
                ErrorReport.user_id == session.user_id,
                ErrorReport.status == "resolved",
            )
        )
        stamp = now()
        marked = 0
        for row in rows:
            row.thanks_seen_at = stamp
            marked += 1
        return {"marked": marked}
