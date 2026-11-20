"""Achievements for real skill milestones, derived from learning data (nothing stored).

Each badge marks something a learner did, not time spent clicking: solving problems
(and solving them without hints), clearing checkpoints, finishing a weekly check, and
studying on consecutive days. Count badges report progress so the next one is visible.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.models import (
    ActivityRecord,
    Enrollment,
    Submission,
    User,
    WeeklyAssessment,
)
from socrat.planner import gates


@dataclass(frozen=True)
class Badge:
    id: str
    title: str
    description: str
    goal: int
    metric: str  # which fact the badge counts


BADGES = [
    Badge("first-lesson", "First lesson", "Finished your first lesson.", 1, "lessons"),
    Badge("first-solve", "First solve", "Solved your first problem.", 1, "solves"),
    Badge("hard-solve", "Hard problem", "Solved a problem rated hard.", 1, "hard"),
    Badge("solved-10", "Ten solved", "Solved 10 problems.", 10, "solves"),
    Badge("independent-10", "On your own", "Solved 10 Socrat problems with no hints.", 10, "own"),
    Badge("solved-50", "Fifty solved", "Solved 50 problems.", 50, "solves"),
    Badge("solved-100", "Hundred solved", "Solved 100 problems.", 100, "solves"),
    Badge("first-gate", "Checkpoint cleared", "Passed your first module checkpoint.", 1, "gates"),
    Badge(
        "course-cleared", "Course cleared", "Passed every checkpoint in your course.", 0, "gates"
    ),
    Badge("weekly-check", "Weekly check", "Finished a weekly assessment.", 1, "weekly"),
    Badge("streak-7", "Week in a row", "Studied 7 scheduled days in a row.", 7, "streak"),
    Badge("streak-30", "Month in a row", "Studied 30 scheduled days in a row.", 30, "streak"),
]


@dataclass
class Facts:
    """Timestamps of each counted event (sorted); the streak is a length, not events."""

    events: dict[str, list[int]] = field(default_factory=dict)
    longest_streak: int = 0
    gate_count: int = 0  # checkpoints in the learner's course


def evaluate(facts: Facts) -> list[dict]:
    out = []
    for badge in BADGES:
        goal = badge.goal or facts.gate_count
        if badge.metric == "streak":
            value, at = facts.longest_streak, None
        else:
            times = sorted(facts.events.get(badge.metric, []))
            value = len(times)
            at = times[goal - 1] if goal and value >= goal else None
        earned = goal > 0 and value >= goal
        out.append(
            dict(
                id=badge.id,
                title=badge.title,
                description=badge.description,
                goal=goal,
                value=min(value, goal),
                earned=earned,
                earned_at=at if earned else None,
            )
        )
    return out


def facts_for(
    db: Session, catalog: Catalog, user: User, enrollment: Enrollment, longest_streak: int
) -> Facts:
    enrollment_ids = list(db.scalars(select(Enrollment.id).where(Enrollment.user_id == user.id)))
    records: list[tuple[str, int]] = [
        (activity, at)
        for activity, at in db.execute(
            select(ActivityRecord.activity_id, ActivityRecord.completed_at).where(
                ActivityRecord.enrollment_id.in_(enrollment_ids),
                ActivityRecord.completed_at.is_not(None),
            )
        )
        if at is not None
    ]
    lessons = [at for activity, at in records if activity.startswith("lesson:")]
    course_gates = {gates.gate_id(k) for k in gates.module_keys(catalog, enrollment.course_id)}
    passed: dict[str, int] = {}
    for activity, at in records:
        if activity in course_gates:
            passed[activity] = min(passed.get(activity, at), at)

    # First accepted submit per Socrat problem, and whether any was without hints.
    first: dict[str, int] = {}
    own: dict[str, int] = {}
    accepted = db.execute(
        select(Submission.problem_id, Submission.created_at, Submission.assistance).where(
            Submission.user_id == user.id,
            Submission.mode == "submit",
            Submission.verdict == "accepted",
        )
    )
    for problem_id, at, assistance in accepted:
        first[problem_id] = min(first.get(problem_id, at), at)
        if not assistance:
            own[problem_id] = min(own.get(problem_id, at), at)
    hard = [
        at
        for pid, at in first.items()
        if pid in catalog.problems and catalog.problem(pid).difficulty == "hard"
    ]

    solves = list(first.values())

    weekly = db.scalars(
        select(WeeklyAssessment.finished_at).where(
            WeeklyAssessment.enrollment_id.in_(enrollment_ids),
            WeeklyAssessment.finished_at.is_not(None),
        )
    )
    return Facts(
        events=dict(
            lessons=lessons,
            solves=solves,
            own=list(own.values()),
            hard=hard,
            gates=list(passed.values()),
            weekly=[at for at in weekly if at is not None],
        ),
        longest_streak=longest_streak,
        gate_count=len(course_gates),
    )


def for_learner(
    db: Session, catalog: Catalog, user: User, enrollment: Enrollment, longest_streak: int
) -> list[dict]:
    return evaluate(facts_for(db, catalog, user, enrollment, longest_streak))
