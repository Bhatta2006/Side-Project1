"""Grade a workbench answer with the harness and write evidence only when it means something.

A correct answer counts once (hints used are recorded as assistance, which lowers its weight in
mastery); giving up counts as a miss and shows the worked solution. Wrong or unreadable tries
are feedback only, so practising cannot drag mastery down.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat import harness
from socrat.catalog.registry import Catalog
from socrat.catalog.schema import Exercise
from socrat.learn import service as learn
from socrat.models import Enrollment, Evidence

EXPECTED_SECONDS = 180


def public(exercise: Exercise) -> dict:
    """What the learner may see before solving: no answer and no worked solution."""
    return dict(
        id=exercise.id,
        prompt=exercise.prompt,
        check=exercise.check,
        unit=exercise.unit,
        hints=exercise.hints,
        plot=exercise.plot,
        difficulty=exercise.difficulty,
    )


def find(catalog: Catalog, concept: str, exercise_id: str) -> Exercise | None:
    if concept not in catalog.concepts:
        return None
    return next((e for e in catalog.concept(concept).exercises if e.id == exercise_id), None)


def request_for(exercise: Exercise, given: str | None, lines: list[str] | None) -> dict:
    if exercise.check == "steps":
        return {
            "op": "steps",
            "lines": lines or ([given] if given else []),
            "expected": exercise.expected,
        }
    if exercise.check == "numeric":
        return {
            "op": "numeric",
            "expected": exercise.expected,
            "given": given or "",
            "unit": exercise.unit,
        }
    return {"op": exercise.check, "expected": exercise.expected, "given": given or ""}


def _recorded(db: Session, enrollment: Enrollment, activity: str) -> Evidence | None:
    return db.scalar(
        select(Evidence)
        .where(Evidence.enrollment_id == enrollment.id, Evidence.activity_id == activity)
        .order_by(Evidence.created_at.desc())
        .limit(1)
    )


def check(
    db: Session,
    catalog: Catalog,
    enrollment: Enrollment,
    concept: str,
    exercise: Exercise,
    given: str | None,
    lines: list[str] | None,
    hints_used: int,
    now: int,
) -> dict:
    result = harness.call("math.check", request_for(exercise, given, lines))
    if not result.ok:
        return dict(verdict="unreadable", reason=result.error, hint="", evidence=False)
    out = dict(result.output, evidence=False)
    if out.get("verdict") != "correct":
        return out
    activity = f"workbench:{concept}:{exercise.id}"
    if _recorded(db, enrollment, activity) is None:
        learn.record_evidence(
            db,
            enrollment,
            concept,
            "quiz",
            1.0,
            activity,
            now,
            assistance=min(hints_used, len(exercise.hints)),
            expected_seconds=EXPECTED_SECONDS,
            details={"studio": "workbench", "exercise": exercise.id, "check": exercise.check},
        )
        out["evidence"] = True
    out["explanation"] = exercise.explanation
    return out


def give_up(
    db: Session,
    enrollment: Enrollment,
    concept: str,
    exercise: Exercise,
    hints_used: int,
    now: int,
) -> dict:
    activity = f"workbench:{concept}:{exercise.id}"
    recorded = _recorded(db, enrollment, activity)
    if recorded is None:
        learn.record_evidence(
            db,
            enrollment,
            concept,
            "quiz",
            0.0,
            activity,
            now,
            assistance=min(hints_used, len(exercise.hints)),
            expected_seconds=EXPECTED_SECONDS,
            details={"studio": "workbench", "exercise": exercise.id, "gave_up": True},
        )
    return dict(
        expected=exercise.expected, explanation=exercise.explanation, evidence=recorded is None
    )
