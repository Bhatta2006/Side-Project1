"""The learner's review queue (master prompt 9.6): what is due, why, and control over it.

Reviews are scheduled by the mastery model (expanding intervals after a success, shorter after a
failure). This module shows them with a plain reason and lets the learner snooze one (it stays
off the plan until then) or bring it back. A snooze is a learner-owned plan override
(``Enrollment.adaptive["overrides"]["snoozed"]``); it never touches the evidence or the mastery
estimate, so the schedule itself is unchanged when the snooze ends.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from socrat.learn import service as learn
from socrat.learn.routes import active, catalog, engine, user_of
from socrat.mastery.model import DAY, REVIEW_DAYS, ConceptState
from socrat.models import Enrollment, now

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


@router.get("")
def queue(request: Request):
    """Every scheduled review on this course, soonest first, with its reason and any snooze."""
    cat, stamp = catalog(), now()
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = active(db, user)
        states = learn.states_for(db, enrollment)
        held = snoozed(enrollment)
        scheduled = sorted(
            ((s.next_review_at, q, s) for q, s in states.items()),
            key=lambda t: t[0],
        )
        items = [
            dict(
                concept=q,
                title=cat.concept(q).title,
                due_at=at,
                due=at <= stamp,
                snoozed_until=held[q] if held.get(q, 0) > stamp else None,
                reason=reason(s, stamp),
            )
            for at, q, s in scheduled
            if at and q in cat.concepts
        ]
        return dict(items=items, max_snooze_days=MAX_SNOOZE_DAYS)


def _scheduled(db: Session, enrollment: Enrollment, qualified: str) -> ConceptState:
    state = learn.states_for(db, enrollment).get(qualified)
    if state is None or not state.next_review_at:
        raise HTTPException(404, "no_review_scheduled")
    return state


@router.post("/{qualified}/snooze")
def snooze(qualified: str, body: Snooze, request: Request):
    stamp = now()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        _scheduled(db, enrollment, qualified)
        held = {k: v for k, v in snoozed(enrollment).items() if v > stamp}  # drop expired ones
        held[qualified] = stamp + body.days * DAY
        _set_snoozed(enrollment, held)
        return dict(concept=qualified, snoozed_until=held[qualified])


@router.delete("/{qualified}/snooze")
def unsnooze(qualified: str, request: Request):
    """Bring a snoozed review back onto the plan now."""
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        held = snoozed(enrollment)
        held.pop(qualified, None)
        _set_snoozed(enrollment, held)
        return dict(concept=qualified, snoozed_until=None)
