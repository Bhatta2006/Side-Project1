"""The learner's review queue (master prompt 9.6): what is due, why, and control over it.

Reviews are scheduled by the mastery model (expanding intervals after a success, shorter after a
failure). This module shows them with a plain reason and lets the learner snooze one (it stays
off the plan until then) or bring it back. A snooze is a learner-owned plan override
(``Enrollment.adaptive["overrides"]["snoozed"]``); it never touches the evidence or the mastery
estimate, so the schedule itself is unchanged when the snooze ends.

``?scope=all`` lists reviews from every course the learner has started, not only the active one
(prompt 9.6, cumulative review across courses). A concept scheduled in two enrolments appears
once, at its earliest due date. A review from another course that the current course builds on
(a cross-course prerequisite) says so and sorts ahead of others due at the same time. A daily
limit is stated so the queue never asks for more than the planner would schedule.
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.learn import service as learn
from socrat.learn.routes import active, catalog, engine, user_of
from socrat.mastery.model import DAY, REVIEW_DAYS, ConceptState
from socrat.models import Enrollment, User, now
from socrat.planner.engine import MAX_REVIEWS_PER_DAY

router = APIRouter(prefix="/api/v1/reviews")
MAX_SNOOZE_DAYS = 14


class Snooze(BaseModel):
    model_config = ConfigDict(extra="forbid")
    days: int = Field(ge=1, le=MAX_SNOOZE_DAYS)


def snoozed(enrollment: Enrollment) -> dict[str, int]:
    return dict(((enrollment.adaptive or {}).get("overrides") or {}).get("snoozed") or {})


def _set_snoozed(enrollment: Enrollment, value: dict[str, int]) -> None:
    data = dict(enrollment.adaptive or {})
    overrides = dict(data.get("overrides") or {})
    if value:
        overrides["snoozed"] = value
    else:
        overrides.pop("snoozed", None)
    data["overrides"] = overrides
    enrollment.adaptive = data  # reassigned so the JSON change is saved


def reason(state: ConceptState, at: int) -> str:
    """Why this review, in plain words, from the schedule's own numbers."""
    days = REVIEW_DAYS[max(0, min(state.review_step, len(REVIEW_DAYS)) - 1)]
    since = max(0, (at - state.last_evidence_at) // DAY) if state.last_evidence_at else None
    when = f"You last practised it {since} day{'s' if since != 1 else ''} ago. " if since else ""
    if state.failures and state.review_step <= 1:
        return f"{when}You missed it last time, so it comes back soon."
    return f"{when}Each success spaces the next review further apart; this one is at {days} days."


def builds_on(cat: Catalog, course_id: str) -> set[str]:
    """Concepts of other courses that ``course_id``'s concepts list as prerequisites."""
    own = [q for q, c in cat.owner.items() if c == course_id]
    return {p for q in own for p in cat.prerequisites.get(q, []) if cat.owner.get(p) != course_id}


def _enrollments(db: Session, user: User, current: Enrollment) -> list[Enrollment]:
    others = db.scalars(
        select(Enrollment)
        .where(Enrollment.user_id == user.id, Enrollment.id != current.id)
        .order_by(Enrollment.created_at)
    ).all()
    return [current, *others]


def items_for(
    db: Session, cat: Catalog, user: User, current: Enrollment, stamp: int, everywhere: bool
) -> list[dict]:
    chosen = _enrollments(db, user, current) if everywhere else [current]
    needed = builds_on(cat, current.course_id) if everywhere else set()
    merged: dict[str, dict] = {}
    for enrollment in chosen:
        held = snoozed(enrollment)
        for q, s in learn.states_for(db, enrollment).items():
            if not s.next_review_at or q not in cat.concepts:
                continue
            course = cat.owner[q]
            entry = merged.get(q)
            if entry is not None:  # the same concept scheduled in two enrolments: overlap
                entry["courses"] = sorted({*entry["courses"], enrollment.course_id})
                if s.next_review_at >= entry["due_at"]:
                    continue
            text = reason(s, stamp)
            if q in needed and course != current.course_id:
                text += f" {cat.course(current.course_id).title} builds on this."
            merged[q] = dict(
                concept=q,
                title=cat.concept(q).title,
                course=course,
                course_title=cat.course(course).title,
                courses=entry["courses"] if entry else [enrollment.course_id],
                current_course=enrollment.id == current.id,
                builds_on=q in needed,
                due_at=s.next_review_at,
                due=s.next_review_at <= stamp,
                snoozed_until=held[q] if held.get(q, 0) > stamp else None,
                reason=text,
            )
    return sorted(merged.values(), key=lambda i: (i["due_at"], not i["builds_on"], i["concept"]))


@router.get("")
def queue(request: Request, scope: Literal["course", "all"] = Query("course")):
    """Scheduled reviews, soonest first, with their reason and any snooze: the active course,
    or (``scope=all``) every course the learner has started."""
    cat, stamp = catalog(), now()
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = active(db, user)
        items = items_for(db, cat, user, enrollment, stamp, scope == "all")
        return dict(
            items=items,
            scope=scope,
            max_snooze_days=MAX_SNOOZE_DAYS,
            daily_limit=MAX_REVIEWS_PER_DAY,
            due_now=sum(1 for i in items if i["due"] and not i["snoozed_until"]),
        )


def _scheduled(db: Session, user: User, current: Enrollment, qualified: str) -> Enrollment:
    """The enrolment that schedules this review: the active course first, then the others."""
    for enrollment in _enrollments(db, user, current):
        state = learn.states_for(db, enrollment).get(qualified)
        if state is not None and state.next_review_at:
            return enrollment
    raise HTTPException(404, "no_review_scheduled")


@router.post("/{qualified}/snooze")
def snooze(qualified: str, body: Snooze, request: Request):
    stamp = now()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = _scheduled(db, user, active(db, user), qualified)
        held = {k: v for k, v in snoozed(enrollment).items() if v > stamp}  # drop expired ones
        held[qualified] = stamp + body.days * DAY
        _set_snoozed(enrollment, held)
        return dict(concept=qualified, snoozed_until=held[qualified])


@router.delete("/{qualified}/snooze")
def unsnooze(qualified: str, request: Request):
    """Bring a snoozed review back onto the plan now, in whichever course holds it."""
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        current = active(db, user)
        for enrollment in _enrollments(db, user, current):
            held = snoozed(enrollment)
            if qualified in held:
                held.pop(qualified)
                _set_snoozed(enrollment, held)
        return dict(concept=qualified, snoozed_until=None)
