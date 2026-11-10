"""Gather the learner's adaptive signals from the database and sync suggestions.

Reads only; ``sync_suggestions`` is the one writer and it only stores *pending*
proposals. Callers pass ``today`` (the learner's local day) so this module stays free of
the learn service it feeds.
"""

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.adaptive import profile as profiles
from socrat.adaptive import proposals, suggest
from socrat.adaptive.stuck import Stuck, detect
from socrat.catalog.registry import Catalog
from socrat.mastery.model import DAY, ConceptState
from socrat.models import (
    ActivityRecord,
    DailyActivity,
    Enrollment,
    Evidence,
    LearnerAbility,
    LinkedAccount,
    PlanProposal,
    Submission,
)
from socrat.planner import engine
from socrat.planner.engine import Adaptive, Plan

ADHERENCE_DAYS = 28
REVIEW_WINDOW = 20
RUNG_OF = {"probe": "probe", "repair": "repair", "defer": "defer"}


def evidence_rows(db: Session, enrollment: Enrollment) -> dict[str, list[profiles.EvidenceRow]]:
    rows: dict[str, list[profiles.EvidenceRow]] = defaultdict(list)
    for e in db.scalars(
        select(Evidence)
        .where(Evidence.enrollment_id == enrollment.id)
        .order_by(Evidence.created_at, Evidence.seq)
    ):
        details = e.details or {}
        rows[e.concept].append(
            profiles.EvidenceRow(
                concept=e.concept,
                kind=e.kind,
                score=e.score,
                assistance=e.assistance,
                elapsed_seconds=e.elapsed_seconds,
                expected_seconds=e.expected_seconds,
                created_at=e.created_at,
                misconception=details.get("misconception"),
                before_band=details.get("before_band"),
                after_band=details.get("after_band"),
            )
        )
    return rows


def concept_ratings(db: Session, catalog: Catalog, enrollment: Enrollment) -> dict[str, float]:
    thetas: dict[str, list[float]] = defaultdict(list)
    for row in db.scalars(
        select(LearnerAbility).where(LearnerAbility.enrollment_id == enrollment.id)
    ):
        pattern = catalog.patterns.get(row.pattern)
        if pattern is not None:
            thetas[pattern.concept].append(row.theta)
    return {c: sum(v) / len(v) for c, v in thetas.items()}


def failed_verdicts(db: Session, catalog: Catalog, user_id: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for problem_id, verdict in db.execute(
        select(Submission.problem_id, Submission.verdict).where(
            Submission.user_id == user_id,
            Submission.mode == "submit",
            Submission.status == "done",
            Submission.verdict != "accepted",
        )
    ):
        if problem_id in catalog.problems:
            course_id, problem = catalog.problems[problem_id]
            out[f"{course_id}:{problem.concepts[0]}"].append(verdict or "")
    return out


def build_profiles(
    db: Session,
    catalog: Catalog,
    enrollment: Enrollment,
    states: dict[str, ConceptState],
    now: int,
) -> dict[str, profiles.SkillProfile]:
    rows = evidence_rows(db, enrollment)
    ratings = concept_ratings(db, catalog, enrollment)
    verdicts = failed_verdicts(db, catalog, enrollment.user_id)
    from socrat.learn import memory

    # How each lesson was read. Empty unless SOCRAT_LESSON_SIGNALS records them.
    reading = memory.signals(db, enrollment)
    concepts = set(states) | set(rows)
    return {
        c: profiles.build(
            c,
            states.get(c, ConceptState()),
            rows.get(c, []),
            now,
            ratings.get(c),
            verdicts.get(c),
            reading.get(c),
        )
        for c in sorted(concepts)
        if c in catalog.concepts
    }


def stuck_map(skill: dict[str, profiles.SkillProfile], now: int) -> dict[str, Stuck]:
    out = {}
    for concept, item in skill.items():
        found = detect(item, now)
        if found is not None:
            out[concept] = found
    return out


def tried(db: Session, enrollment: Enrollment) -> dict[str, frozenset[str]]:
    """Ladder rungs already used per concept: decided proposals (accepted or declined)."""
    used: dict[str, set[str]] = defaultdict(set)
    for row in db.scalars(
        select(PlanProposal).where(
            PlanProposal.enrollment_id == enrollment.id,
            PlanProposal.kind.in_(list(RUNG_OF)),
            PlanProposal.status.in_(["accepted", "declined"]),
        )
    ):
        concept = row.payload.get("for") or row.payload.get("concept")
        if concept:
            used[concept].add(RUNG_OF[row.kind])
    # In-concept support the learner already went through counts as a used rung too, so
    # proposals and the planner agree on where the ladder stands.
    for activity in db.scalars(
        select(ActivityRecord.activity_id).where(
            ActivityRecord.enrollment_id == enrollment.id,
            ActivityRecord.completed_at.is_not(None),
        )
    ):
        kind, _, concept = activity.partition(":")
        if kind in engine.SUPPORT_MINUTES and concept:
            used[concept].add(kind)
    return {c: frozenset(v) for c, v in used.items()}


def adherence_for(db: Session, enrollment: Enrollment, today: date) -> float:
    start = max(date.fromtimestamp(enrollment.created_at), today - timedelta(days=ADHERENCE_DAYS))
    days = [start + timedelta(days=i) for i in range((today - start).days)]
    planned = sum(enrollment.minutes_per_day for d in days if d.weekday() in enrollment.weekdays)
    done = sum(
        db.scalars(
            select(DailyActivity.minutes).where(
                DailyActivity.user_id == enrollment.user_id,
                DailyActivity.day >= start.isoformat(),
                DailyActivity.day < today.isoformat(),
            )
        )
    )
    enrolled = (today - date.fromtimestamp(enrollment.created_at)).days
    return profiles.adherence(done, planned, enrolled)


def review_scale_for(db: Session, enrollment: Enrollment) -> float:
    scores = list(
        db.scalars(
            select(Evidence.score)
            .where(Evidence.enrollment_id == enrollment.id, Evidence.kind == "review")
            .order_by(Evidence.created_at.desc())
            .limit(REVIEW_WINDOW)
        )
    )
    return profiles.review_scale(scores)


def overrides_with_mentor(data: dict) -> dict:
    """The learner's overrides, plus the pace the mentor set; what the learner said wins."""
    overrides = dict(data.get("overrides", {}))
    mentor_feel = data.get("mentor", {}).get("feel", {})
    if mentor_feel:
        overrides["feel"] = {**mentor_feel, **overrides.get("feel", {})}
    return overrides


def inputs(
    db: Session,
    catalog: Catalog,
    enrollment: Enrollment,
    states: dict[str, ConceptState],
    today: date,
    now: int,
) -> Adaptive:
    skill = build_profiles(db, catalog, enrollment, states, now)
    data = enrollment.adaptive or {}
    return Adaptive(
        course_id=enrollment.course_id,
        goal=dict(enrollment.goal or {}),
        style=data.get("style", "balanced"),
        overrides=overrides_with_mentor(data),
        stuck=stuck_map(skill, now),
        tried=tried(db, enrollment),
        adherence=adherence_for(db, enrollment, today),
    )


def recent_concepts(db: Session, enrollment: Enrollment, limit: int = 2) -> list[str]:
    seen: list[str] = []
    for concept in db.scalars(
        select(Evidence.concept)
        .where(Evidence.enrollment_id == enrollment.id)
        .order_by(Evidence.created_at.desc())
        .limit(30)
    ):
        if concept not in seen:
            seen.append(concept)
        if len(seen) >= limit:
            break
    return seen


def passed_checkpoint(db: Session, enrollment: Enrollment, now: int) -> tuple[str, float] | None:
    row = db.scalar(
        select(ActivityRecord)
        .where(
            ActivityRecord.enrollment_id == enrollment.id,
            ActivityRecord.activity_id.like("checkpoint:%"),
            ActivityRecord.completed_at >= now - 3 * DAY,
        )
        .order_by(ActivityRecord.completed_at.desc())
    )
    if row is None or not (row.outcome or {}).get("passed"):
        return None
    return row.activity_id.removeprefix("checkpoint:"), float(row.outcome.get("score", 0))


def sync_suggestions(
    db: Session,
    catalog: Catalog,
    enrollment: Enrollment,
    plan: Plan,
    adaptive: Adaptive,
    states: dict[str, ConceptState],
    today: date,
    days_away: int,
    now: int,
) -> list[PlanProposal]:
    signals = suggest.Signals(
        today=today,
        minutes_per_day=enrollment.minutes_per_day,
        weekdays=tuple(enrollment.weekdays),
        overrides=adaptive.overrides,
        stuck=adaptive.stuck,
        tried=adaptive.tried,
        days_away=days_away,
        recent_concepts=tuple(recent_concepts(db, enrollment)),
        passed_checkpoint=passed_checkpoint(db, enrollment, now),
        weak_prereqs={
            c: w
            for c in adaptive.stuck
            if (w := engine.weakest_prerequisite(catalog, c, states, now)) is not None
        },
    )
    return proposals.sync(db, enrollment, suggest.drafts(catalog, plan, signals), now)


def level_for(db: Session, user_id: str, library_rating: int, enrollment: Enrollment) -> dict:
    thetas = list(
        db.scalars(
            select(LearnerAbility.theta).where(LearnerAbility.enrollment_id == enrollment.id)
        )
    )
    account = db.scalar(select(LinkedAccount).where(LinkedAccount.user_id == user_id))
    rating = getattr(account, "rating", None) if account else None
    return profiles.level(library_rating, thetas, rating)
