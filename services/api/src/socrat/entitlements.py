"""Plans and what each allows: content, tutor chat and visual playground.

One table (`PLANS`) is the whole policy. Everything else asks `plan_of` and `enforce`.
Plan checks are off until SOCRAT_BILLING_ENABLED is set, so rollout is a switch.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.models import (
    AssistantMessage,
    AssistantThread,
    LaunchGrant,
    PlaygroundJob,
    Subscription,
    User,
    now,
)

# ponytail: process-wide flag set by create_app; the concept guard has no settings handle.
ENABLED = False
PLAYGROUND_SCOPE = "playground:visual"
FREE_MODULES = 2  # per course
PLAN_GATE = "plan"  # the gate `learn.locked_concepts` reports for content outside the plan
RANK = {"free": 0, "plus": 1, "pro": 2}
# Features beyond lessons and chat: feature -> the lowest plan that includes it.
TIER = {"assessment": "plus", "companies": "pro"}

# feature -> (messages, window). 0 messages = locked.
PLANS = {
    "free": dict(chat=(5, "week"), playground=(0, "day")),
    "plus": dict(chat=(10, "day"), playground=(3, "day")),
    "pro": dict(chat=(50, "day"), playground=(15, "day")),
}


# Set from SOCRAT_LAUNCH_PROMO_* at startup: how many first signups get free Plus, for how long.
LAUNCH_PROMO_SLOTS = 0
LAUNCH_PROMO_DAYS = 30
# Test and local sign-ins never use up a launch slot.
NO_PROMO_ISSUERS = {"local-development", "eval"}


def plan_of(db: Session, user_id: str, stamp: int | None = None) -> str:
    """Paid access lasts until the end of the period that was paid for, cancelled or not.
    A launch grant gives Plus until it expires; a paid plan above it still wins."""
    at = stamp or now()
    sub = db.get(Subscription, user_id)
    paid = sub.plan if sub and sub.plan in PLANS and sub.current_end > at else "free"
    if paid == "free":
        grant = db.scalar(select(LaunchGrant).where(LaunchGrant.user_id == user_id))
        if grant and grant.expires_at > at:
            return "plus"
    return paid


def grant_launch_promo(
    db: Session, user: User, device: str, stamp: int | None = None
) -> LaunchGrant | None:
    """Give a brand-new account one of the launch slots, if any are left. Call it only where an
    account is created, never on sign-in, so existing learners are not eligible.

    Each attempt claims the next slot number inside a savepoint; if another signup took that
    number first, the primary key rejects it and we try the next. Slots above the cap are never
    written, so the cap holds under concurrent signups.

    ``device`` is the hash of the browser's device cookie: a device that already holds a grant
    gets no second one, whichever account signs up on it."""
    if LAUNCH_PROMO_SLOTS <= 0 or user.issuer in NO_PROMO_ISSUERS:
        return None
    if db.scalar(select(LaunchGrant.slot).where(LaunchGrant.device_hash == device)) is not None:
        return None
    at = stamp or now()
    for _ in range(5):
        taken = db.scalar(select(func.max(LaunchGrant.slot))) or 0
        if taken >= LAUNCH_PROMO_SLOTS:
            return None
        grant = LaunchGrant(
            slot=taken + 1,
            user_id=user.id,
            granted_at=at,
            expires_at=at + LAUNCH_PROMO_DAYS * 86400,
            device_hash=device,
        )
        try:
            with db.begin_nested():
                db.add(grant)
                db.flush()
            return grant
        except IntegrityError:
            # Another signup claimed that slot (look again), or this device just got a grant
            # in a racing request (the next look finds it and stops).
            if db.scalar(select(LaunchGrant.slot).where(LaunchGrant.device_hash == device)):
                return None
            continue
    return None


def free_concepts(catalog: Catalog) -> set[str]:
    return {
        f"{course_id}:{concept}"
        for course_id in catalog.courses
        for module in catalog.course(course_id).modules[:FREE_MODULES]
        for concept in module.concepts
    }


def plan_locked(db: Session, catalog: Catalog, user_id: str, stamp: int) -> set[str]:
    """Concepts the learner's plan does not include."""
    if not ENABLED or plan_of(db, user_id, stamp) != "free":
        return set()
    return set(catalog.concepts) - free_concepts(catalog)


def require_concept(db: Session, catalog: Catalog, user_id: str, concept: str, stamp: int):
    if concept in plan_locked(db, catalog, user_id, stamp):
        raise HTTPException(402, "upgrade_required")


def has(db: Session, user_id: str, feature: str, stamp: int | None = None) -> bool:
    return not ENABLED or RANK[plan_of(db, user_id, stamp)] >= RANK[TIER[feature]]


def require(db: Session, user_id: str, feature: str, stamp: int | None = None):
    if not has(db, user_id, feature, stamp):
        raise HTTPException(402, "pro_required" if TIER[feature] == "pro" else "upgrade_required")


def window_start(user: User | None, unit: str, stamp: int) -> int:
    """Start of the learner's calendar day, or of their week (Monday)."""
    local = datetime.fromtimestamp(stamp, ZoneInfo(user.timezone if user else "UTC"))
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    if unit == "week":
        start -= timedelta(days=start.weekday())
    return int(start.timestamp())


def used(db: Session, user_id: str, feature: str, since: int) -> int:
    if feature == "playground":
        # Generations that failed or were cancelled are not charged to the learner's allowance.
        return (
            db.scalar(
                select(func.count())
                .select_from(PlaygroundJob)
                .where(
                    PlaygroundJob.user_id == user_id,
                    PlaygroundJob.status.in_(("queued", "running", "ready")),
                    PlaygroundJob.created_at >= since,
                    PlaygroundJob.shared.is_(False),  # cache fills belong to everyone
                )
            )
            or 0
        )
    playground = AssistantThread.scope == PLAYGROUND_SCOPE
    return (
        db.scalar(
            select(func.count())
            .select_from(AssistantMessage)
            .join(AssistantThread, AssistantThread.id == AssistantMessage.thread_id)
            .where(
                AssistantThread.user_id == user_id,
                AssistantMessage.role == "user",
                AssistantMessage.created_at >= since,
                ~playground,
            )
        )
        or 0
    )


def enforce(db: Session, user_id: str, feature: str, stamp: int):
    if not ENABLED:
        return
    limit, unit = PLANS[plan_of(db, user_id, stamp)][feature]
    if limit == 0:
        raise HTTPException(402, "upgrade_required")
    since = window_start(db.get(User, user_id), unit, stamp)
    if used(db, user_id, feature, since) >= limit:
        raise HTTPException(429, f"{feature}_{unit}_limit")


def usage(db: Session, user_id: str, stamp: int) -> dict:
    plan = plan_of(db, user_id, stamp)
    user = db.get(User, user_id)
    out = {}
    for feature, (limit, unit) in PLANS[plan].items():
        spent = used(db, user_id, feature, window_start(user, unit, stamp)) if limit else 0
        out[feature] = dict(limit=limit, used=spent, window=unit)
    return out
