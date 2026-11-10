"""What Socrat remembers about how a learner studies, for the coach, the tutor and the learner.

Scored evidence says what a learner got right. It says nothing about the reading: a
generated course's lesson could be opened five times, re-explained three times and asked
about twice, and the coach saw none of it. Two things are added here.

Lesson signals: the app reports, per lesson, the furthest page reached, taps on "explain it
simpler" or "go deeper", rereads and questions asked from the lesson. They are counters on
one record per lesson, never scored and never evidence: they cannot move mastery. The stuck
detector reads them as weak signals next to its others (``adaptive/stuck.py``).

The memory: one short list, built by code from the signals and the practice sets, that the
tutor is given and the learner can read (``GET /api/v1/memory``). The planner and tutor
already share the skill profile; this adds what the profile cannot see. Nothing a learner
typed is in it, so nothing in it can instruct the tutor.

Off until ``SOCRAT_LESSON_SIGNALS`` is set.
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.learn import service as learn
from socrat.learn.routes import active, catalog, engine, user_of
from socrat.models import ActivityRecord, Enrollment, now

router = APIRouter(prefix="/api/v1")

PREFIX = "signal:"
DRILL = "drill:"
COUNTERS = ("simpler", "deeper", "reread", "question", "visual")
MOST = 99  # a counter stops here: a stuck button is not a thousand signals
MANY = 2  # taps or rereads on one lesson that count as a sign of trouble
LINES = 8  # the memory is short, so it is read


class Signal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["page", "simpler", "deeper", "reread", "question", "visual"]
    page: int | None = Field(default=None, ge=1, le=60)


def note(db: Session, enrollment: Enrollment, qualified: str, signal: Signal, stamp: int) -> dict:
    """Add one signal to the lesson's record. Never completed, so plan progress, streaks
    and achievements, which read completed records, never count it."""
    key = f"{PREFIX}{qualified}"
    record = db.get(ActivityRecord, (enrollment.id, key))
    if record is None:
        record = ActivityRecord(
            enrollment_id=enrollment.id, activity_id=key, started_at=stamp, outcome={}
        )
        db.add(record)
    seen = dict(record.outcome or {})
    if signal.kind == "page":
        seen["pages"] = max(int(seen.get("pages", 0)), signal.page or 1)
    else:
        seen[signal.kind] = min(MOST, int(seen.get(signal.kind, 0)) + 1)
    seen["last_at"] = stamp
    record.outcome = seen  # reassign so the JSON column is written
    return seen


def signals(db: Session, enrollment: Enrollment) -> dict[str, dict]:
    """Lesson -> its counters, for every lesson of this enrolment that has any."""
    rows = db.scalars(
        select(ActivityRecord).where(
            ActivityRecord.enrollment_id == enrollment.id,
            ActivityRecord.activity_id.like(f"{PREFIX}%"),
        )
    )
    return {r.activity_id.removeprefix(PREFIX): dict(r.outcome or {}) for r in rows}


def practice(db: Session, enrollment: Enrollment) -> dict[str, dict]:
    """Lesson -> its latest finished practice set: how many right, of how many."""
    latest: dict[str, dict] = {}
    rows = db.scalars(
        select(ActivityRecord)
        .where(
            ActivityRecord.enrollment_id == enrollment.id,
            ActivityRecord.activity_id.like(f"{DRILL}%"),
        )
        .order_by(ActivityRecord.started_at)
    )
    for record in rows:
        outcome = record.outcome or {}
        questions, answers = outcome.get("questions", []), outcome.get("answers", {})
        if not questions or len(answers) < len(questions) or "concept" not in outcome:
            continue
        right = sum(1 for a in answers.values() if a.get("correct"))
        latest[outcome["concept"]] = dict(correct=right, questions=len(questions))
    return latest


def remembered(db: Session, cat: Catalog, enrollment: Enrollment) -> list[dict]:
    """The memory as short plain statements, most telling first. Each has a ``kind`` (what
    it is about) and the lesson it concerns."""

    def title(concept: str) -> str | None:
        return cat.concept(concept).title if concept in cat.concepts else None

    items: list[tuple[int, dict]] = []
    for concept, seen in signals(db, enrollment).items():
        name = title(concept)
        if name is None:
            continue
        if seen.get("simpler", 0) >= MANY:
            text = f"Asked for a simpler explanation of {name} {seen['simpler']} times."
            items.append((seen["simpler"] * 3, dict(kind="simpler", concept=concept, text=text)))
        if seen.get("reread", 0) >= MANY:
            text = f"Came back to reread {name} {seen['reread']} times."
            items.append((seen["reread"] * 2, dict(kind="reread", concept=concept, text=text)))
        if seen.get("question", 0) >= MANY:
            text = f"Asked the tutor about {name} {seen['question']} times."
            items.append((seen["question"] * 2, dict(kind="question", concept=concept, text=text)))
        if seen.get("visual", 0) >= MANY:
            text = f"Opened the visual for {name} {seen['visual']} times."
            items.append((seen["visual"], dict(kind="visual", concept=concept, text=text)))
        if seen.get("deeper", 0) >= MANY:
            text = f"Asked to go deeper into {name} {seen['deeper']} times."
            items.append((seen["deeper"], dict(kind="deeper", concept=concept, text=text)))
    for concept, result in practice(db, enrollment).items():
        name = title(concept)
        if name is None:
            continue
        right, total = result["correct"], result["questions"]
        if right * 2 <= total:
            text = f"Last practice on {name}: {right} of {total} right."
            items.append((4 + total - right, dict(kind="practice", concept=concept, text=text)))
        elif right == total:
            text = f"Last practice on {name}: all {total} right."
            items.append((1, dict(kind="practice", concept=concept, text=text)))
    items.sort(key=lambda pair: (-pair[0], pair[1]["text"]))
    return [item for _, item in items[:LINES]]


def tutor_block(db: Session, cat: Catalog, enrollment: Enrollment) -> str:
    """The memory for the tutor's context; empty when there is nothing to say, and empty
    until lesson signals are being recorded (the flag is off): then nothing changes."""
    if not signals(db, enrollment):
        return ""
    return "\n".join(item["text"] for item in remembered(db, cat, enrollment))


def _enabled(request: Request) -> None:
    if not request.app.state.settings.lesson_signals:
        raise HTTPException(404, "not_found")


@router.post("/concepts/{qualified}/signals", status_code=204)
def record(qualified: str, body: Signal, request: Request):
    _enabled(request)
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        if qualified not in learn.curriculum(cat, enrollment):
            raise HTTPException(404, "not_found")
        if cat.concept(qualified).status != "live":
            raise HTTPException(404, "not_found")
        note(db, enrollment, qualified, body, now())


@router.get("/memory")
def memory(request: Request):
    """What Socrat has noticed about how this learner studies, in the words the tutor sees."""
    _enabled(request)
    cat = catalog()
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = active(db, user)
        return dict(items=remembered(db, cat, enrollment))
