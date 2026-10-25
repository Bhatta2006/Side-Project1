"""Plans and what each allows: content, tutor chat and visual playground.

One table (`PLANS`) is the whole policy. Everything else asks `plan_of` and `enforce`.
Plan checks are off until SOCRAT_BILLING_ENABLED is set, so rollout is a switch.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.models import AssistantMessage, AssistantThread, Subscription, User, now

# ponytail: process-wide flag set by create_app; the concept guard has no settings handle.
ENABLED = False
PLAYGROUND_SCOPE = "playground:visual"
FREE_MODULES = 2  # per course

# feature -> (messages, window). 0 messages = locked.
PLANS = {
    "free": dict(chat=(5, "week"), playground=(0, "day")),
    "plus": dict(chat=(10, "day"), playground=(3, "day")),
    "pro": dict(chat=(50, "day"), playground=(15, "day")),
}


def plan_of(db: Session, user_id: str, stamp: int | None = None) -> str:
    """Paid access lasts until the end of the period that was paid for, cancelled or not."""
    sub = db.get(Subscription, user_id)
    if sub and sub.plan in PLANS and sub.current_end > (stamp or now()):
        return sub.plan
    return "free"


def free_concepts(catalog: Catalog) -> set[str]:
    return {
        f"{course_id}:{concept}"
        for course_id in catalog.courses
        for module in catalog.course(course_id).modules[:FREE_MODULES]
        for concept in module.concepts
    }


def require_concept(db: Session, catalog: Catalog, user_id: str, concept: str, stamp: int):
    if ENABLED and plan_of(db, user_id, stamp) == "free" and concept not in free_concepts(catalog):
        raise HTTPException(402, "upgrade_required")


def window_start(user: User | None, unit: str, stamp: int) -> int:
    """Start of the learner's calendar day, or of their week (Monday)."""
    local = datetime.fromtimestamp(stamp, ZoneInfo(user.timezone if user else "UTC"))
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    if unit == "week":
        start -= timedelta(days=start.weekday())
    return int(start.timestamp())


def used(db: Session, user_id: str, feature: str, since: int) -> int:
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
                playground if feature == "playground" else ~playground,
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
