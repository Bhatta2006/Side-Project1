"""The end of a session (item 3 of docs/research/duolingo-teardown.md), behind
``session_end_enabled``.

The server picks and orders the screens so the arrangement can be tested, as Duolingo does
with its session-end screens. The order is fixed by the peak-end idea, adapted to Socrat:
what the learner proved comes first, then the habit, then the next step.

- ``evidence`` always leads: the concept's state as the mastery model sees it now.
- ``streak`` once a day, on the first session that ends after studying today.
- ``badge`` once ever, for a badge earned in the last few minutes.
- ``next`` closes: the next planned step, or a note that today's goal is met.

Showing a screen changes nothing that counts; it only records that the streak or a badge
was shown, so they are not shown again.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.database import record_event
from socrat.learn import achievements
from socrat.learn import service as learn
from socrat.models import AuditEvent, DailyActivity, Enrollment, User

ARRANGEMENT = "evidence-first-v1"
BADGE_WINDOW = 15 * 60  # a badge earned this recently is news
STREAK_SHOWN = "session_end.streak"
BADGE_SHOWN = "session_end.badge."
MILESTONES = (3, 7, 14, 30, 50, 100, 200, 365)


def concept_of(catalog: Catalog, activity_id: str) -> str | None:
    """`quiz:zero:loops` -> `zero:loops` when that is a concept in the catalogue."""
    _, _, rest = activity_id.partition(":")
    if not rest:
        return None
    try:
        catalog.concept(rest)
    except Exception:  # noqa: BLE001  (unknown ids simply have no concept screen)
        return None
    return rest


def evidence_screen(
    db: Session, catalog: Catalog, enrollment: Enrollment, activity_id: str, now: int
) -> dict:
    concept = concept_of(catalog, activity_id)
    if concept is None:
        return {"kind": "evidence", "concept": None, "title": None, "status": None}
    state = learn.states_for(db, enrollment).get(concept)
    independent = state.independent_successes if state else 0
    assisted = state.assisted_successes if state else 0
    if state and state.mastered(now):
        status = "mastered"
    elif independent:
        status = "shown_alone"
    else:
        status = "building"
    return {
        "kind": "evidence",
        "concept": concept,
        "title": catalog.concept(concept).title,
        "status": status,
        "independent": independent,
        "assisted": assisted,
    }


def _shown(db: Session, user: User, kind: str, since: int | None = None) -> list[int]:
    query = select(AuditEvent.created_at).where(
        AuditEvent.actor_id == user.id, AuditEvent.kind == kind
    )
    if since is not None:
        query = query.where(AuditEvent.created_at >= since)
    return list(db.scalars(query))


def week_of(db: Session, user: User, enrollment: Enrollment, today: date) -> list[dict]:
    """Monday to Sunday of this week: studied, a study day, or still ahead."""
    studied = {
        day
        for (day,) in db.execute(select(DailyActivity.day).where(DailyActivity.user_id == user.id))
    }
    monday = today - timedelta(days=today.weekday())
    days = [monday + timedelta(days=i) for i in range(7)]
    return [
        {
            "day": d.isoformat(),
            "studied": d.isoformat() in studied,
            "scheduled": d.weekday() in set(enrollment.weekdays),
            "today": d == today,
        }
        for d in days
    ]


def streak_screen(db: Session, user: User, enrollment: Enrollment, now: int) -> dict | None:
    streak = learn.streak(db, user, enrollment, now)
    if not streak["studied_today"] or streak["current"] < 1:
        return None
    today = learn.local_day(user, now)
    recent = _shown(db, user, STREAK_SHOWN, since=now - 2 * 86_400)
    if any(learn.local_day(user, at) == today for at in recent):
        return None
    record_event(db, user.id, STREAK_SHOWN)
    current = streak["current"]
    return {
        "kind": "streak",
        "current": current,
        "longest": streak["longest"],
        "freezes": streak["freezes"],
        "first_day": current == 1,
        "milestone": current in MILESTONES,
        "week": week_of(db, user, enrollment, today),
    }


def badge_screens(
    db: Session, catalog: Catalog, user: User, enrollment: Enrollment, now: int
) -> list[dict]:
    longest = learn.streak(db, user, enrollment, now)["longest"]
    out = []
    for badge in achievements.for_learner(db, catalog, user, enrollment, longest):
        at = badge["earned_at"]
        if not badge["earned"] or at is None or now - at > BADGE_WINDOW:
            continue
        kind = f"{BADGE_SHOWN}{badge['id']}"[:80]
        if _shown(db, user, kind):
            continue
        record_event(db, user.id, kind)
        out.append(
            {
                "kind": "badge",
                "id": badge["id"],
                "title": badge["title"],
                "description": badge["description"],
            }
        )
    return out


def next_screen(today: dict) -> dict:
    nxt = today.get("next")
    minutes = today.get("minutes") or {}
    return {
        "kind": "next",
        "goal_reached": bool(minutes.get("reached")),
        "minutes_done": minutes.get("done", 0),
        "minutes_goal": minutes.get("goal", 0),
        "activity": (
            {k: nxt.get(k) for k in ("id", "kind", "concept", "title", "minutes", "reason")}
            if nxt
            else None
        ),
    }


def arrange(
    db: Session, catalog: Catalog, user: User, enrollment: Enrollment, activity_id: str, now: int
) -> dict:
    from socrat.learn import views

    screens = [evidence_screen(db, catalog, enrollment, activity_id, now)]
    streak = streak_screen(db, user, enrollment, now)
    if streak:
        screens.append(streak)
    screens.extend(badge_screens(db, catalog, user, enrollment, now))
    screens.append(next_screen(views.today_view(db, catalog, user, enrollment, now)))
    return {"arrangement": ARRANGEMENT, "screens": screens}
