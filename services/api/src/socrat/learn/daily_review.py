"""The Daily Review (item 4 of docs/research/duolingo-teardown.md), behind
``daily_review_enabled``.

A short list, every day, of the concepts the learner has practised and is most likely to have
forgotten by now, ordered by the recall model (``learn/recall.py``). Each one opens the existing
``review:<concept>`` quiz, so the answers are scored and counted exactly as any review is. The
list itself counts nothing and changes no schedule.

Left out: concepts never practised, snoozed reviews (``learn/reviews.py``), concepts outside
the course or locked by the plan, and anything the learner still very likely remembers.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat import entitlements
from socrat.catalog.registry import Catalog
from socrat.learn import recall
from socrat.learn import service as learn
from socrat.learn.reviews import snoozed
from socrat.learn.routes import active, catalog, engine, user_of
from socrat.models import Enrollment, Evidence, QuizResponse, User, now
from socrat.planner.engine import MAX_REVIEWS_PER_DAY

router = APIRouter(prefix="/api/v1/daily-review", tags=["learn"])
FADED_BELOW = 0.9  # recall chance under this is worth a refresh


def _plain(chance: float) -> str:
    if chance < 0.5:
        return "probably faded"
    if chance < 0.75:
        return "fading"
    return "starting to fade"


def reason(item: recall.Recall, stamp: int) -> str:
    days = max(0, stamp - item.last_at) // recall.DAY
    when = "earlier today" if days == 0 else "yesterday" if days == 1 else f"{days} days ago"
    alone = (
        f"you have got it on your own {item.independent} "
        f"{'time' if item.independent == 1 else 'times'}"
        if item.independent
        else "you have not yet got it without help"
    )
    return f"Last practised {when}; {alone}."


def refreshed_today(db: Session, user: User, enrollment: Enrollment, stamp: int) -> int:
    """Distinct concepts reviewed today, by the fixed or the adaptive review quiz."""
    today = learn.local_day(user, stamp)
    since = stamp - 2 * recall.DAY
    fixed = db.execute(
        select(Evidence.concept, Evidence.created_at).where(
            Evidence.enrollment_id == enrollment.id,
            Evidence.activity_id.like("review:%"),
            Evidence.created_at >= since,
        )
    ).all()
    adaptive = db.execute(
        select(QuizResponse.concept, QuizResponse.created_at).where(
            QuizResponse.enrollment_id == enrollment.id,
            QuizResponse.mode == "review",
            QuizResponse.created_at >= since,
        )
    ).all()
    return len({q for q, at in [*fixed, *adaptive] if learn.local_day(user, at) == today})


def queue_for(
    db: Session, cat: Catalog, user: User, enrollment: Enrollment, stamp: int, limit: int
) -> list[dict]:
    scope = learn.curriculum(cat, enrollment)
    locked = entitlements.plan_locked(db, cat, user.id, stamp)
    held = {q for q, until in snoozed(enrollment).items() if until > stamp}
    picks = []
    for q, item in recall.for_enrollment(db, enrollment).items():
        if q not in cat.concepts or q not in scope or q in locked or q in held:
            continue
        chance = item.chance(stamp)
        if chance >= FADED_BELOW:
            continue
        picks.append((chance, q, item))
    picks.sort(key=lambda p: (p[0], p[1]))
    return [
        {
            "concept": q,
            "title": cat.concept(q).title,
            "activity": f"review:{q}",
            "recall": round(chance, 2),
            "state": _plain(chance),
            "half_life_days": round(item.half_life_days, 1),
            "reason": reason(item, stamp),
        }
        for chance, q, item in picks[:limit]
    ]


@router.get("")
def daily_review(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=MAX_REVIEWS_PER_DAY)] = MAX_REVIEWS_PER_DAY,
) -> dict:
    """Today's refresh list, most likely forgotten first."""
    if not request.app.state.settings.daily_review_enabled:
        raise HTTPException(404, "not_found")
    cat, stamp = catalog(), now()
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = active(db, user)
        items = queue_for(db, cat, user, enrollment, stamp, limit)
        return {
            "model": recall.MODEL,
            "daily_limit": MAX_REVIEWS_PER_DAY,
            "refreshed_today": refreshed_today(db, user, enrollment, stamp),
            "items": items,
        }
