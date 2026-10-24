"""Turn evidence into learner state, plans, streaks and today's agenda.

All writes here happen inside the caller's transaction; nothing commits on its own.
"""

import hashlib
import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from socrat.catalog.registry import Catalog
from socrat.database import record_event
from socrat.learn import streaks
from socrat.mastery import model as mastery
from socrat.models import (
    ActivityRecord,
    DailyActivity,
    Enrollment,
    Evidence,
    LearningSession,
    PlanRevision,
    User,
)
from socrat.models import ConceptState as ConceptRow
from socrat.planner import gates
from socrat.planner.engine import Adaptive, Plan, build_plan, concept_activities

MAX_ACTIVITY_SECONDS = 90 * 60


def local_now(user: User, now: int) -> datetime:
    return datetime.fromtimestamp(now, ZoneInfo(user.timezone))


def local_day(user: User, now: int) -> date:
    return local_now(user, now).date()


def active_enrollment(db: Session, user_id: str) -> Enrollment | None:
    return db.scalar(
        select(Enrollment)
        .where(Enrollment.user_id == user_id, Enrollment.active.is_(True))
        .order_by(Enrollment.created_at.desc())
    )


def require_enrollment(db: Session, user_id: str) -> Enrollment:
    enrollment = active_enrollment(db, user_id)
    if enrollment is None:
        raise HTTPException(404, "no_active_enrollment")
    return enrollment


def states_for(db: Session, enrollment: Enrollment) -> dict[str, mastery.ConceptState]:
    rows = db.scalars(select(ConceptRow).where(ConceptRow.enrollment_id == enrollment.id))
    return {row.concept: mastery.ConceptState.from_dict(row.state) for row in rows}


def completed_for(db: Session, enrollment: Enrollment) -> set[str]:
    return set(
        db.scalars(
            select(ActivityRecord.activity_id).where(
                ActivityRecord.enrollment_id == enrollment.id,
                ActivityRecord.completed_at.is_not(None),
            )
        )
    )


def history_for(db: Session, enrollment: Enrollment, limit: int = 40) -> list[dict]:
    rows = list(
        db.scalars(
            select(Evidence)
            .where(Evidence.enrollment_id == enrollment.id)
            .order_by(Evidence.created_at.desc(), Evidence.id.desc())
            .limit(limit)
        )
    )
    return [
        dict(
            kind=row.kind,
            score=row.score,
            assistance=row.assistance,
            elapsed_seconds=row.elapsed_seconds,
            expected_seconds=row.expected_seconds,
            concept=row.concept,
        )
        for row in reversed(rows)
    ]


def set_state(
    db: Session, enrollment: Enrollment, concept: str, state: mastery.ConceptState, now: int
):
    row = db.get(ConceptRow, (enrollment.id, concept))
    if row is None:
        db.add(ConceptRow(enrollment_id=enrollment.id, concept=concept, state=state.to_dict()))
    else:
        row.state = state.to_dict()
        row.updated_at = now


def record_evidence(
    db: Session,
    enrollment: Enrollment,
    concept: str,
    kind: mastery.EvidenceKind,
    score: float,
    activity_id: str,
    now: int,
    assistance: int = 0,
    elapsed_seconds: int = 0,
    expected_seconds: int = 0,
    details: dict | None = None,
) -> mastery.ConceptState:
    from socrat.adaptive import service as adaptive

    row = db.get(ConceptRow, (enrollment.id, concept))
    before = mastery.ConceptState.from_dict(row.state if row else None)
    scale = adaptive.review_scale_for(db, enrollment)
    after = mastery.apply(before, kind, score, now, assistance, interval_scale=scale)
    user = db.get(User, enrollment.user_id)
    learning_session = (
        db.scalar(
            select(LearningSession).where(
                LearningSession.enrollment_id == enrollment.id,
                LearningSession.day == local_day(user, now).isoformat(),
                LearningSession.finished_at.is_(None),
            )
        )
        if user
        else None
    )
    set_state(db, enrollment, concept, after, now)
    evidence = Evidence(
        enrollment_id=enrollment.id,
        concept=concept,
        kind=kind,
        score=score,
        assistance=assistance,
        activity_id=activity_id,
        elapsed_seconds=elapsed_seconds,
        expected_seconds=expected_seconds,
        created_at=now,
        details={
            "session_id": learning_session.id if learning_session else None,
            **(details or {}),
            "before_band": mastery.band(before, now),
            "after_band": mastery.band(after, now),
        },
    )
    db.add(evidence)
    db.flush()
    if kind == "code" and score == 1 and assistance == 0:
        user_id = enrollment.user_id
        record_event(db, user_id, "learning.independent_solve", evidence.id)
    if mastery.band(before, now) != mastery.band(after, now):
        record_event(db, enrollment.user_id, "learning.band_changed", evidence.id)
    return after


def start_activity(
    db: Session, enrollment: Enrollment, activity_id: str, now: int
) -> ActivityRecord:
    record = db.get(ActivityRecord, (enrollment.id, activity_id))
    if record is None:
        record = ActivityRecord(
            enrollment_id=enrollment.id, activity_id=activity_id, started_at=now
        )
        db.add(record)
        db.flush()
    elif record.completed_at is None and now - record.started_at > MAX_ACTIVITY_SECONDS:
        record.started_at = now  # A stale attempt restarts the clock.
    return record


def elapsed(db: Session, enrollment: Enrollment, activity_id: str, now: int) -> int:
    record = db.get(ActivityRecord, (enrollment.id, activity_id))
    if record is None:
        return 0
    return max(0, min(MAX_ACTIVITY_SECONDS, now - record.started_at))


def expected_seconds(catalog: Catalog, activity_id: str, enrollment: Enrollment) -> int:
    kind, _, target = activity_id.partition(":")
    if kind in {"review", "remedial"}:
        return 5 * 60 if kind == "review" else 15 * 60
    if kind in {"checkpoint", "moduletest"}:
        return 15 * 60
    if kind in {"probe", "testout"}:
        return 10 * 60
    if kind in {"example", "explain", "checkin", "stretch"}:
        return {"checkin": 5, "stretch": 20}.get(kind, 10) * 60
    if kind == "problem":
        course_id, problem = catalog.problems[target]
        concept = f"{course_id}:{problem.concepts[0]}"
    else:
        concept = target
    for activity in concept_activities(catalog, concept, mastery.ConceptState(), "steady"):
        if activity.id == activity_id:
            return activity.minutes * 60
    return 15 * 60


def complete_activity(
    db: Session,
    user: User,
    enrollment: Enrollment,
    activity_id: str,
    now: int,
    outcome: dict | None = None,
    solved: bool = False,
) -> bool:
    """Mark complete once; returns False when it was already complete."""
    record = start_activity(db, enrollment, activity_id, now)
    if record.completed_at is not None:
        return False
    record.completed_at = now
    record.outcome = outcome or {}
    minutes = max(1, round(min(MAX_ACTIVITY_SECONDS, now - record.started_at) / 60))
    bump_daily(db, user, now, minutes=minutes, solved=int(solved))
    record_event(db, user.id, "activity.completed")
    return True


def bump_daily(db: Session, user: User, now: int, minutes: int = 0, solved: int = 0):
    day = local_day(user, now).isoformat()
    row = db.get(DailyActivity, (user.id, day))
    if row is None:
        row = DailyActivity(user_id=user.id, day=day, activities=0, minutes=0, solved=0)
        db.add(row)
    row.activities += 1
    row.minutes += minutes
    row.solved += solved


def minutes_by_day(db: Session, user: User) -> dict[date, int]:
    rows = db.execute(
        select(DailyActivity.day, DailyActivity.minutes).where(DailyActivity.user_id == user.id)
    )
    return {date.fromisoformat(day): minutes or 0 for day, minutes in rows}


def streak(db: Session, user: User, enrollment: Enrollment, now: int) -> dict:
    """Consecutive scheduled study days with activity; earned freezes cover missed days."""
    return streaks.compute(
        minutes_by_day(db, user),
        local_day(user, now),
        set(enrollment.weekdays),
        date.fromtimestamp(enrollment.created_at) - timedelta(days=1),
        enrollment.minutes_per_day,
    )


def days_away(db: Session, user: User, enrollment: Enrollment, now: int) -> int:
    return streaks.days_away(
        set(minutes_by_day(db, user)),
        local_day(user, now),
        set(enrollment.weekdays),
        date.fromtimestamp(enrollment.created_at),
    )


def gate_cooldowns(db: Session, enrollment: Enrollment) -> dict[str, int]:
    """Failed, not-yet-passed gates -> when the next attempt opens."""
    rows = db.scalars(
        select(ActivityRecord).where(
            ActivityRecord.enrollment_id == enrollment.id,
            ActivityRecord.activity_id.like("checkpoint:%"),
            ActivityRecord.completed_at.is_(None),
        )
    )
    return {r.activity_id: int(r.outcome.get("retry_at", 0)) for r in rows if r.outcome}


def locked_concepts(
    db: Session, catalog: Catalog, enrollment: Enrollment, now: int
) -> dict[str, str]:
    """Concept -> the gate that must be passed first. Empty when nothing is locked."""
    return gates.locked_concepts(
        catalog,
        enrollment.course_id,
        states_for(db, enrollment),
        completed_for(db, enrollment),
        now,
    )


def require_unlocked(
    db: Session, catalog: Catalog, enrollment: Enrollment, concept: str, now: int
) -> None:
    if concept not in curriculum(catalog, enrollment):
        raise HTTPException(404, "not_found")
    if catalog.concept(concept).status == "planned":
        raise HTTPException(423, "concept_preparing")
    if concept in locked_concepts(db, catalog, enrollment, now):
        raise HTTPException(423, "concept_locked")


def curriculum(catalog: Catalog, enrollment: Enrollment | None) -> set[str]:
    return (
        set(catalog.closure(catalog.course_concepts(enrollment.course_id)))
        if enrollment is not None
        else set()
    )


def practice_topics(
    db: Session, catalog: Catalog, enrollment: Enrollment | None, now: int
) -> set[str]:
    """Completed lessons and demonstrated knowledge, within the active course and its bridges."""
    if enrollment is None or enrollment.status != "active":
        return set()
    completed = completed_for(db, enrollment)
    states = states_for(db, enrollment)
    locked = locked_concepts(db, catalog, enrollment, now)
    return {
        c
        for c in curriculum(catalog, enrollment)
        if c not in locked
        and (
            f"lesson:{c}" in completed
            or mastery.band(states.get(c, mastery.ConceptState()), now)
            in {"likely_known", "strong"}
        )
    }


def plan_for(
    db: Session,
    catalog: Catalog,
    user: User,
    enrollment: Enrollment,
    now: int,
    record: bool = True,
) -> Plan:
    """The learner's plan; with `record`, a changed plan is logged as a PlanRevision and
    new roadmap suggestions are stored as pending proposals for the learner to decide.

    Pure readers (tutor tools, recommendations) pass record=False so they never write.
    """
    from socrat.adaptive import service as adaptive_service

    states = states_for(db, enrollment)
    today = local_day(user, now)
    plan, adaptive = build_for(db, catalog, user, enrollment, now, states)
    if not record or enrollment.status != "active":
        return plan
    adaptive_service.sync_suggestions(
        db,
        catalog,
        enrollment,
        plan,
        adaptive,
        states,
        today,
        days_away(db, user, enrollment, now),
        now,
    )
    signature = hashlib.sha256(
        json.dumps(
            [plan.pace, plan.style, [a.id for a in plan.queue[:12]]], sort_keys=True
        ).encode()
    ).hexdigest()
    if signature != enrollment.plan_signature and _claim(db, enrollment, signature):
        previous = db.scalar(
            select(PlanRevision)
            .where(PlanRevision.enrollment_id == enrollment.id)
            .order_by(PlanRevision.created_at.desc())
        )
        reasons = list(plan.reasons)
        if previous is None:
            reasons = ["Your personalised path is ready.", *reasons]
        elif previous.pace != plan.pace:
            reasons = [plan.pace_reason, *reasons]
        snapshot = [[a.id, a.title] for a in plan.queue]
        db.add(
            PlanRevision(
                enrollment_id=enrollment.id,
                pace=plan.pace,
                reasons=reasons or ["Plan adjusted to your latest progress."],
                remaining_minutes=plan.remaining_minutes,
                projected_finish=plan.projected_finish,
                created_at=now,
                snapshot=snapshot,
                changes=plan_changes(
                    previous.snapshot if previous else None,
                    snapshot,
                    completed_for(db, enrollment),
                ),
            )
        )
    return plan


def build_for(
    db: Session,
    catalog: Catalog,
    user: User,
    enrollment: Enrollment,
    now: int,
    states: dict[str, mastery.ConceptState] | None = None,
    style: str | None = None,
) -> tuple[Plan, Adaptive]:
    """Build the plan without recording anything; ``style`` previews another path style."""
    from dataclasses import replace

    from socrat.adaptive import service as adaptive_service

    states = states if states is not None else states_for(db, enrollment)
    today = local_day(user, now)
    adaptive = adaptive_service.inputs(db, catalog, enrollment, states, today, now)
    if style is not None:
        adaptive = replace(adaptive, style=style)
    plan = build_plan(
        catalog,
        catalog.course_concepts(enrollment.course_id),
        states,
        completed_for(db, enrollment),
        history_for(db, enrollment),
        today,
        now,
        set(enrollment.weekdays),
        enrollment.minutes_per_day,
        course_id=enrollment.course_id,
        cooldowns=gate_cooldowns(db, enrollment),
        adaptive=adaptive,
    )
    return plan, adaptive


def plan_changes(before: list | None, after: list, completed: set[str]) -> dict:
    """What a revision added to or removed from the queue (E4). Finished work leaving the
    queue and reviews coming and going are progress, not changes."""
    if not before:
        return {}

    def keep(activity_id: str) -> bool:
        return not activity_id.startswith("review:") and activity_id not in completed

    old = {a: t for a, t in before if keep(a)}
    new = {a: t for a, t in after if keep(a)}
    return dict(
        added=[t for a, t in new.items() if a not in old][:12],
        removed=[t for a, t in old.items() if a not in new][:12],
    )


def revise(
    db: Session, catalog: Catalog, user: User, enrollment: Enrollment, now: int, reason: str
) -> PlanRevision | None:
    """Re-plan now and log the revision with ``reason`` first (a learner decision)."""
    if enrollment.status != "active":
        return None
    earlier = dict(
        db.execute(
            select(PlanRevision.id, PlanRevision.created_at).where(
                PlanRevision.enrollment_id == enrollment.id
            )
        ).all()
    )
    enrollment.plan_signature = ""  # Force a fresh, explained revision.
    plan_for(db, catalog, user, enrollment, now)
    db.flush()
    revision = db.scalar(
        select(PlanRevision).where(
            PlanRevision.enrollment_id == enrollment.id,
            PlanRevision.id.not_in(list(earlier)),
        )
    )
    if revision is not None:
        # Revisions sort by whole seconds; keep this one strictly latest.
        revision.created_at = max([revision.created_at, *(t + 1 for t in earlier.values())])
        revision.reasons = [reason] + [
            r for r in revision.reasons if r != "Your personalised path is ready."
        ]
    return revision


def _claim(db: Session, enrollment: Enrollment, signature: str) -> bool:
    """Compare-and-swap the plan signature so concurrent page loads log one revision.

    Only the request whose UPDATE still sees the old signature records the change; the
    others (Postgres re-checks the WHERE after the winner commits) skip it.
    """
    current = enrollment.plan_signature
    same = (
        Enrollment.plan_signature.is_(None)
        if current is None
        else Enrollment.plan_signature == current
    )
    result = db.execute(
        update(Enrollment)
        .where(Enrollment.id == enrollment.id, same)
        .values(plan_signature=signature)
        .execution_options(synchronize_session=False)
    )
    claimed = result.rowcount if isinstance(result, CursorResult) else 0
    set_committed_value(enrollment, "plan_signature", signature)
    return claimed == 1


def latest_revisions(db: Session, enrollment: Enrollment, limit: int = 5) -> list[dict]:
    rows = db.scalars(
        select(PlanRevision)
        .where(PlanRevision.enrollment_id == enrollment.id)
        .order_by(PlanRevision.created_at.desc())
        .limit(limit)
    )
    return [
        dict(
            pace=row.pace,
            reasons=row.reasons,
            projected_finish=row.projected_finish,
            remaining_minutes=row.remaining_minutes,
            at=row.created_at,
            changes=row.changes or {},
        )
        for row in rows
    ]


def completed_today(db: Session, user: User, enrollment: Enrollment, now: int) -> list[str]:
    midnight = local_now(user, now).replace(hour=0, minute=0, second=0, microsecond=0)
    return list(
        db.scalars(
            select(ActivityRecord.activity_id)
            .where(
                ActivityRecord.enrollment_id == enrollment.id,
                ActivityRecord.completed_at >= int(midnight.timestamp()),
            )
            .order_by(ActivityRecord.completed_at)
        )
    )


def evidence_counts(db: Session, enrollment: Enrollment) -> dict:
    rows = db.execute(
        select(Evidence.kind, Evidence.assistance, Evidence.score, func.count())
        .where(Evidence.enrollment_id == enrollment.id)
        .group_by(Evidence.kind, Evidence.assistance, Evidence.score)
    ).all()
    independent = sum(c for kind, a, s, c in rows if kind == "code" and s >= 1 and a == 0)
    assisted = sum(c for kind, a, s, c in rows if kind == "code" and s >= 1 and a > 0)
    return {"independent_solves": independent, "assisted_solves": assisted}
