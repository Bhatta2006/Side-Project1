"""Admin API: only users on the SOCRAT_ADMIN_SUBJECTS allow-list may read it."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from socrat import billing, entitlements
from socrat.admin import drafts
from socrat.admin import service as admin
from socrat.database import record_event
from socrat.learn.routes import catalog, engine, is_admin, user_of
from socrat.models import ContentIssue, Evidence, LearningSession, Subscription, User, now

router = APIRouter(prefix="/api/v1/admin")


def require_admin(request: Request, db: Session, write: bool = False) -> User:
    """Allow-listed accounts only; `write` also enforces the CSRF token."""
    user = user_of(request, db, write=write)
    if not is_admin(request, user):
        raise HTTPException(403, "forbidden")
    return user


@router.get("/overview")
def overview(request: Request):
    cat = catalog()
    with Session(engine(request)) as db:
        require_admin(request, db)
        return admin.overview(db, cat, now())


@router.get("/ai-costs")
def ai_costs(request: Request):
    from socrat.assistant import budget

    with Session(engine(request)) as db:
        require_admin(request, db)
        return budget.summary(db, request.app.state.settings, now())


@router.get("/errors")
def error_reports(request: Request, status: Literal["open", "resolved"] = "open"):
    from socrat import errors

    with Session(engine(request)) as db:
        require_admin(request, db)
        return {
            "items": errors.recent(db, limit=100 if status == "resolved" else 50, status=status)
        }


@router.get("/reports/log")
def report_log(request: Request):
    """Learner reports per reporter: who reported how much, and how much of it was solved."""
    from socrat import errors

    with Session(engine(request)) as db:
        require_admin(request, db)
        return errors.reporter_log(db)


@router.post("/errors/{report_id}/resolve")
def resolve_error(report_id: str, request: Request):
    from socrat.models import ErrorReport

    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        row = db.get(ErrorReport, report_id)
        if row is None:
            raise HTTPException(404, "not_found")
        row.status = "resolved"
        row.resolved_at = now()
        row.resolved_by = user.id
        row.thanks_seen_at = None  # a fresh resolution earns a fresh thank-you
        record_event(db, user.id, "admin.error_resolved", report_id)
        return {"resolved": True}


@router.get("/learning-quality")
def learning_quality(request: Request):
    """Learning guardrails and closure, without optimizing time spent or reward clicks."""
    with Session(engine(request)) as db:
        require_admin(request, db)
        since = now() - 7 * 86400
        rows = list(db.scalars(select(LearningSession).where(LearningSession.created_at >= since)))
        evidence = list(db.scalars(select(Evidence).where(Evidence.created_at >= since)))
        code = [e for e in evidence if e.kind == "code"]
        completed = [s for s in rows if s.finished_at is not None]
        return dict(
            window_days=7,
            sessions_started=len(rows),
            sessions_completed=len(completed),
            summaries_viewed=sum(bool(s.payload.get("summary_viewed")) for s in completed),
            independent_code_successes=sum(e.score == 1 and e.assistance == 0 for e in code),
            code_evidence_items=len(code),
            high_hint_evidence_items=sum(e.assistance >= 3 for e in code),
            retention_checks=sum(e.kind == "review" for e in evidence),
            retention_successes=sum(e.kind == "review" and e.score >= 0.7 for e in evidence),
            content_issues=[
                dict(
                    concept=i.concept,
                    atom=i.atom_id,
                    version=i.version,
                    reason=i.reason,
                    note=i.note,
                    at=i.created_at,
                )
                for i in db.scalars(select(ContentIssue).where(ContentIssue.created_at >= since))
            ],
        )


# ---------------------------------------------------------------- content review queue


class Decision(BaseModel):
    notes: str = Field(default="", max_length=2000)


def _roots(request: Request) -> drafts.Roots:
    return drafts.Roots.from_settings(request.app.state.settings)


def _reviewer(user: User) -> str:
    return user.display_name or user.subject


@router.get("/drafts")
def draft_queue(request: Request):
    with Session(engine(request)) as db:
        require_admin(request, db)
    return drafts.queue(_roots(request))


@router.get("/drafts/{draft_id}")
def draft_detail(draft_id: str, request: Request):
    with Session(engine(request)) as db:
        require_admin(request, db)
    return drafts.detail(_roots(request), draft_id)


@router.post("/drafts/{draft_id}/validate")
def draft_validate(draft_id: str, request: Request):
    with Session(engine(request)) as db:
        require_admin(request, db, write=True)
    return drafts.run_validation(_roots(request), catalog(), draft_id)


@router.post("/drafts/{draft_id}/approve")
def draft_approve(draft_id: str, body: Decision, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        result = drafts.approve(_roots(request), draft_id, _reviewer(user), body.notes.strip())
        record_event(db, user.id, "content.draft_approved", draft_id)
    return result


@router.post("/drafts/{draft_id}/request-changes")
def draft_request_changes(draft_id: str, body: Decision, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        result = drafts.request_changes(_roots(request), draft_id, _reviewer(user), body.notes)
        record_event(db, user.id, "content.draft_changes_requested", draft_id)
    return result


# ---------------------------------------------------------------- learners and plans


class PlanGrant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan: Literal["free", "plus", "pro"]
    days: int = Field(default=30, ge=1, le=3660)


def plan_row(user: User, sub: Subscription | None, stamp: int) -> dict:
    live = (
        sub
        if sub is not None and sub.plan in entitlements.PLANS and sub.current_end > stamp
        else None
    )
    return dict(
        id=user.id,
        name=user.display_name,
        subject=user.subject,
        joined_at=user.created_at,
        plan=live.plan if live else "free",
        status=sub.status if sub else None,
        interval=live.interval if live else None,
        ends_at=live.current_end if live else None,
        cancelling=bool(live and live.cancel_at_period_end),
        comped=bool(sub and sub.razorpay_subscription_id.startswith("comp_")),
    )


@router.get("/users")
def users(request: Request, q: str = "", limit: int = 50):
    stamp = now()
    with Session(engine(request)) as db:
        require_admin(request, db)
        query = (
            select(User, Subscription)
            .outerjoin(Subscription, Subscription.user_id == User.id)
            .order_by(User.created_at.desc())
            .limit(max(1, min(limit, 200)))
        )
        needle = q.strip()[:80]
        if needle:
            like = f"%{needle}%"
            query = query.where(
                or_(User.display_name.ilike(like), User.subject.ilike(like), User.id == needle)
            )
        rows = [plan_row(u, s, stamp) for u, s in db.execute(query)]
        live = list(
            db.scalars(
                select(Subscription).where(
                    Subscription.current_end > stamp, Subscription.status == "active"
                )
            )
        )
        paying = [s for s in live if not s.razorpay_subscription_id.startswith("comp_")]
        # Monthly recurring revenue in INR paise; yearly plans count as a twelfth.
        mrr = sum(
            billing.PRICES[s.plan][s.interval]["INR"] // (12 if s.interval == "year" else 1)
            for s in paying
            if s.plan in billing.PRICES and s.currency == "INR"
        )
        return dict(
            items=rows,
            totals=dict(
                users=db.scalar(select(func.count()).select_from(User)) or 0,
                plus=sum(s.plan == "plus" for s in paying),
                pro=sum(s.plan == "pro" for s in paying),
                comped=len(live) - len(paying),
                mrr_inr=mrr,
            ),
        )


@router.post("/users/{user_id}/plan")
def set_plan(user_id: str, body: PlanGrant, request: Request):
    """Grant a free (comped) plan for some days, or end a plan now. Razorpay billing for a
    paying learner must still be cancelled in the Razorpay dashboard."""
    stamp = now()
    with Session(engine(request)) as db, db.begin():
        admin_user = require_admin(request, db, write=True)
        target = db.get(User, user_id)
        if target is None:
            raise HTTPException(404, "not_found")
        sub = db.get(Subscription, user_id)
        if body.plan == "free":
            if sub is not None:
                sub.current_end, sub.status, sub.updated_at = stamp, "revoked", stamp
        else:
            if sub is None:
                sub = Subscription(
                    user_id=user_id,
                    razorpay_subscription_id=f"comp_{user_id}",
                    interval="month",
                    currency="INR",
                )
                db.add(sub)
            sub.plan, sub.status, sub.pending = body.plan, "active", None
            sub.current_end = max(sub.current_end or 0, stamp) + body.days * 86400
            sub.cancel_at_period_end, sub.updated_at = False, stamp
        record_event(db, admin_user.id, "admin.plan_set", f"{user_id}:{body.plan}:{body.days}")
        db.flush()
        return plan_row(target, sub, stamp)
