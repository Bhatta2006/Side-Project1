"""Admin control over accounts: one learner's record and activity, deleting an account, signing
it out everywhere, sending notes, and the log of generations that failed.

Every change here is written to the audit log under the admin who made it.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import CursorResult, delete, func, select
from sqlalchemy.orm import Session

from socrat import entitlements
from socrat.admin.routes import plan_row, require_admin
from socrat.database import record_event
from socrat.learn.routes import engine, is_admin
from socrat.models import (
    AuditEvent,
    DeliveredEvent,
    Enrollment,
    ErrorReport,
    Evidence,
    GenerationJob,
    LaunchGrant,
    LearningSession,
    LoginSession,
    OutboxEvent,
    PlaygroundJob,
    Subscription,
    User,
    UserNotification,
    now,
)

router = APIRouter(prefix="/api/v1/admin")

DAY = 86400


class Note(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(default="", max_length=120)
    body: str = Field(min_length=1, max_length=2000)


def _target(db: Session, user_id: str) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "not_found")
    return user


def _note_view(row: UserNotification) -> dict:
    return dict(
        id=row.id, title=row.title, body=row.body, created_at=row.created_at, seen_at=row.seen_at
    )


@router.get("/users/{user_id}")
def user_detail(user_id: str, request: Request):
    """Everything the admin needs about one account, on one screen."""
    stamp = now()
    with Session(engine(request)) as db:
        require_admin(request, db)
        user = _target(db, user_id)
        enrollments = db.scalars(
            select(Enrollment).where(Enrollment.user_id == user.id).order_by(Enrollment.id)
        ).all()
        ids = [e.id for e in enrollments]
        evidence = (
            db.execute(
                select(func.count(), func.max(Evidence.created_at)).where(
                    Evidence.enrollment_id.in_(ids)
                )
            ).one()
            if ids
            else (0, None)
        )
        sessions = (
            db.scalar(
                select(func.count())
                .select_from(LearningSession)
                .where(LearningSession.enrollment_id.in_(ids))
            )
            if ids
            else 0
        )
        events = db.scalars(
            select(AuditEvent)
            .where(AuditEvent.actor_id == user.id)
            .order_by(AuditEvent.created_at.desc())
            .limit(60)
        ).all()
        jobs = db.scalars(
            select(PlaygroundJob)
            .where(PlaygroundJob.user_id == user.id)
            .order_by(PlaygroundJob.created_at.desc())
            .limit(15)
        ).all()
        notes = db.scalars(
            select(UserNotification)
            .where(UserNotification.user_id == user.id)
            .order_by(UserNotification.created_at.desc())
            .limit(20)
        ).all()
        grant = db.scalar(select(LaunchGrant).where(LaunchGrant.user_id == user.id))
        reports = db.scalar(
            select(func.count()).select_from(ErrorReport).where(ErrorReport.user_id == user.id)
        )
        last = max(
            [t for t in (evidence[1], events[0].created_at if events else None) if t], default=None
        )
        return dict(
            **plan_row(user, db.get(Subscription, user.id), stamp),
            email=user.email or user.admin_email,
            sign_in="Email and password" if user.issuer == "email" else "Google",
            timezone=user.timezone,
            admin=is_admin(request, user),
            effective_plan=entitlements.plan_of(db, user.id, stamp),
            launch_offer=dict(slot=grant.slot, ends_at=grant.expires_at) if grant else None,
            last_active_at=last,
            signed_in_devices=db.scalar(
                select(func.count())
                .select_from(LoginSession)
                .where(LoginSession.user_id == user.id, LoginSession.expires_at > stamp)
            )
            or 0,
            enrollments=[
                dict(course=e.course_id, language=e.language, level=e.level_id, status=e.status)
                for e in enrollments
            ],
            counts=dict(evidence=evidence[0] or 0, study_days=sessions or 0, reports=reports or 0),
            activity=[dict(kind=e.kind, at=e.created_at) for e in events],
            generations=[
                dict(
                    id=j.id,
                    prompt=j.prompt[:160],
                    mode=j.mode,
                    status=j.status,
                    error=j.error,
                    at=j.created_at,
                )
                for j in jobs
            ],
            notifications=[_note_view(n) for n in notes],
        )


@router.delete("/users/{user_id}", status_code=200)
def delete_user(user_id: str, request: Request):
    """Delete an account and everything it owns. Cannot be undone. An admin cannot delete their
    own account here (Settings does that), nor another admin's."""
    with Session(engine(request)) as db, db.begin():
        admin_user = require_admin(request, db, write=True)
        user = _target(db, user_id)
        if user.id == admin_user.id:
            raise HTTPException(409, "cannot_delete_self")
        if is_admin(request, user):
            raise HTTPException(409, "cannot_delete_admin")
        events = select(OutboxEvent.id).where(
            OutboxEvent.payload["actor_id"].as_string() == user.id
        )
        db.execute(delete(DeliveredEvent).where(DeliveredEvent.event_id.in_(events)))
        db.execute(
            delete(OutboxEvent).where(OutboxEvent.payload["actor_id"].as_string() == user.id)
        )
        db.execute(delete(AuditEvent).where(AuditEvent.actor_id == user.id))
        db.delete(user)  # Everything else cascades from the user row.
        # The id only: nothing about the deleted person is kept.
        record_event(db, admin_user.id, "admin.user_deleted", user_id)
        return dict(deleted=True)


@router.post("/users/{user_id}/sign-out")
def sign_out_user(user_id: str, request: Request):
    """End every session of this account; they must sign in again on every device."""
    with Session(engine(request)) as db, db.begin():
        admin_user = require_admin(request, db, write=True)
        user = _target(db, user_id)
        result = db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
        ended = result.rowcount if isinstance(result, CursorResult) else 0
        record_event(db, admin_user.id, "admin.user_signed_out", user_id)
        return dict(ended=ended or 0)


@router.post("/users/{user_id}/notify")
def notify_user(user_id: str, body: Note, request: Request):
    """Send one learner a note; it shows in their app the next time they open it."""
    with Session(engine(request)) as db, db.begin():
        admin_user = require_admin(request, db, write=True)
        user = _target(db, user_id)
        row = UserNotification(
            user_id=user.id, title=body.title.strip(), body=body.body.strip(), sent_by=admin_user.id
        )
        db.add(row)
        record_event(db, admin_user.id, "admin.user_notified", user_id)
        db.flush()
        return _note_view(row)


@router.post("/notifications/broadcast")
def notify_everyone(body: Note, request: Request):
    """Send the same note to every account."""
    with Session(engine(request)) as db, db.begin():
        admin_user = require_admin(request, db, write=True)
        ids = db.scalars(select(User.id)).all()
        db.add_all(
            UserNotification(
                user_id=uid, title=body.title.strip(), body=body.body.strip(), sent_by=admin_user.id
            )
            for uid in ids
        )
        record_event(db, admin_user.id, "admin.broadcast_sent", str(len(ids)))
        return dict(sent=len(ids))


@router.get("/generations/failed")
def failed_generations(request: Request, limit: int = 100):
    """Every generation that failed, newest first: playground visuals (kept by the worker with
    the reason it gave up) and course-generation jobs."""
    stamp = now()
    with Session(engine(request)) as db:
        require_admin(request, db)
        cap = max(1, min(limit, 300))
        visuals = db.execute(
            select(PlaygroundJob, User)
            .outerjoin(User, User.id == PlaygroundJob.user_id)
            .where(PlaygroundJob.status == "failed")
            .order_by(PlaygroundJob.created_at.desc())
            .limit(cap)
        ).all()
        courses = db.scalars(
            select(GenerationJob)
            .where(GenerationJob.state == "failed")
            .order_by(GenerationJob.updated_at.desc())
            .limit(cap)
        ).all()

        def tally(since: int) -> dict:
            rows = dict(
                db.execute(
                    select(PlaygroundJob.status, func.count())
                    .where(PlaygroundJob.created_at >= since)
                    .group_by(PlaygroundJob.status)
                ).all()
            )
            return dict(failed=rows.get("failed", 0), total=sum(rows.values()))

        reasons = db.execute(
            select(PlaygroundJob.error, func.count())
            .where(PlaygroundJob.status == "failed", PlaygroundJob.created_at >= stamp - 30 * DAY)
            .group_by(PlaygroundJob.error)
            .order_by(func.count().desc())
        ).all()
        return dict(
            playground=[
                dict(
                    id=job.id,
                    user=dict(id=user.id, name=user.display_name or user.subject) if user else None,
                    prompt=job.prompt[:300],
                    mode=job.mode,
                    level=job.level,
                    error=job.error or "unknown",
                    tries=job.tries,
                    shared=job.shared,
                    at=job.created_at,
                )
                for job, user in visuals
            ],
            courses=[
                dict(
                    id=j.id,
                    kind=j.kind,
                    course=j.course_id,
                    target=j.target,
                    error=j.error or "unknown",
                    at=j.updated_at,
                )
                for j in courses
            ],
            summary=dict(
                last_day=tally(stamp - DAY),
                last_week=tally(stamp - 7 * DAY),
                reasons=[dict(error=e or "unknown", count=c) for e, c in reasons],
            ),
        )
