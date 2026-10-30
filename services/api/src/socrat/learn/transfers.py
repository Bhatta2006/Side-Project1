"""Transfer checks for one learner: load their state, run the two steps, record the outcome.

State lives in the activity record ``transfer:<concept>`` (its ``outcome`` says pending, failed
or verified) and in append-only evidence, so nothing here needs a table of its own. The rules
are in ``socrat.mastery.transfer``.
"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat import entitlements
from socrat.catalog.registry import Catalog
from socrat.learn import service as learn
from socrat.mastery import model as mastery
from socrat.mastery import transfer
from socrat.mastery.transfer import Transfer
from socrat.models import ActivityRecord, AssistantThread, Enrollment, Evidence, Submission, User


def seen_problems(db: Session, enrollment: Enrollment) -> set[str]:
    """Anything the learner has submitted, run, talked to the tutor about, started, or been
    asked in an earlier check: a problem they have met cannot test transfer."""
    seen = set(
        db.scalars(select(Submission.problem_id).where(Submission.user_id == enrollment.user_id))
    )
    seen |= {
        t.scope.removeprefix("problem:")
        for t in db.scalars(
            select(AssistantThread).where(AssistantThread.user_id == enrollment.user_id)
        )
        if t.scope.startswith("problem:")
    }
    seen |= {
        a.removeprefix("problem:")
        for a in db.scalars(
            select(ActivityRecord.activity_id).where(
                ActivityRecord.enrollment_id == enrollment.id,
                ActivityRecord.activity_id.like("problem:%"),
            )
        )
    }
    asked = db.scalars(
        select(Evidence.details).where(
            Evidence.enrollment_id == enrollment.id, Evidence.kind == "transfer"
        )
    )
    return seen | {d["problem"] for d in asked if d.get("problem")}


def current(
    db: Session,
    catalog: Catalog,
    enrollment: Enrollment,
    states: dict[str, mastery.ConceptState],
    completed: set[str],
    now: int,
) -> Transfer:
    """Status of every concept with a check, and the modules a missing check holds shut."""
    scope = learn.curriculum(catalog, enrollment)
    outcomes = {
        r.activity_id.removeprefix("transfer:"): r.outcome or {}
        for r in db.scalars(
            select(ActivityRecord).where(
                ActivityRecord.enrollment_id == enrollment.id,
                ActivityRecord.activity_id.like("transfer:%"),
            )
        )
    }
    mastered = {c for c in scope if (s := states.get(c)) and s.mastered(now)}
    held_back = (
        entitlements.plan_locked(db, catalog, enrollment.user_id, now) if mastered else set()
    )
    known = {c for c, s in states.items() if s.evidence_count}
    seen: set[str] | None = None
    result: dict[str, str] = {}
    for concept in sorted((mastered | outcomes.keys()) & scope):
        verified = transfer.activity_id(concept) in completed
        outcome = outcomes.get(concept)
        available = False
        if not verified and concept in mastered and concept not in held_back:
            seen = seen_problems(db, enrollment) if seen is None else seen
            available = bool(transfer.unseen(catalog, concept, seen)) and (
                transfer.choices(catalog, concept, "", scope, known) is not None
            )
        mark = transfer.status(
            outcome, verified, states.get(concept, mastery.ConceptState()), available, now
        )
        if mark:
            result[concept] = mark
    blocking = transfer.blocking_modules(
        catalog, enrollment.course_id, result, states, completed, now
    )
    return Transfer(result, blocking)


def _seed(enrollment: Enrollment, concept: str) -> str:
    return f"{enrollment.id}|{concept}"


def _problem_card(catalog: Catalog, problem_id: str) -> dict:
    """What the learner may read before naming the technique: no title, no hints, no starter."""
    problem = catalog.problems[problem_id][1]
    return dict(
        id=problem.id,
        statement=problem.statement,
        input_format=problem.input_format,
        output_format=problem.output_format,
        constraints=problem.constraints,
        examples=[e.model_dump() for e in problem.examples],
    )


def view(db: Session, catalog: Catalog, enrollment: Enrollment, concept: str, now: int) -> dict:
    states = learn.states_for(db, enrollment)
    mark = current(
        db, catalog, enrollment, states, learn.completed_for(db, enrollment), now
    ).status.get(concept)
    base = dict(concept=concept, title=catalog.concept(concept).title, state="unavailable")
    record = db.get(ActivityRecord, (enrollment.id, transfer.activity_id(concept)))
    outcome = (record.outcome if record else None) or {}
    if mark == "verified":
        return {**base, "state": "verified"}
    if mark == "pending":
        return {**base, "state": "solve", "problem": outcome["problem"]}
    if mark == "wait":
        return {**base, "state": "wait", "retry_at": int(outcome["at"]) + transfer.COOLDOWN}
    if mark != "due":
        return base
    problem_id = transfer.pick(
        _seed(enrollment, concept), transfer.unseen(catalog, concept, seen_problems(db, enrollment))
    )
    scope = learn.curriculum(catalog, enrollment)
    options = transfer.choices(
        catalog,
        concept,
        problem_id or "",
        scope,
        {c for c, s in states.items() if s.evidence_count},
    )
    if problem_id is None or options is None:  # raced with the learner opening the problem
        return base
    return {
        **base,
        "state": "classify",
        "problem": _problem_card(catalog, problem_id),
        "choices": [dict(id=c, title=catalog.concept(c).title) for c in options],
    }


def classify(
    db: Session,
    catalog: Catalog,
    enrollment: Enrollment,
    concept: str,
    problem_id: str,
    choice: str,
    now: int,
) -> dict:
    """Step one. A right answer opens the solve; a wrong one ends the attempt."""
    shown = view(db, catalog, enrollment, concept, now)
    if shown["state"] != "classify":
        raise HTTPException(409, "transfer_not_due")
    if shown["problem"]["id"] != problem_id:
        raise HTTPException(409, "transfer_problem_changed")
    if choice not in {c["id"] for c in shown["choices"]}:
        raise HTTPException(422, "unknown_choice")
    aid = transfer.activity_id(concept)
    record = learn.start_activity(db, enrollment, aid, now)
    correct = choice == concept
    if correct:
        record.outcome = {"state": "pending", "problem": problem_id, "at": now}
        return dict(correct=True, state="solve", problem=problem_id)
    record.outcome = {"state": "failed", "stage": "classify", "problem": problem_id, "at": now}
    learn.record_evidence(
        db,
        enrollment,
        concept,
        "transfer",
        0.0,
        aid,
        now,
        details=dict(stage="classify", problem=problem_id, ok=False, choice=choice),
    )
    return dict(
        correct=False,
        state="wait",
        retry_at=now + transfer.COOLDOWN,
        answer=catalog.concept(concept).title,
    )


def on_solve(
    db: Session,
    catalog: Catalog,
    user: User,
    enrollment: Enrollment,
    problem_id: str,
    assistance: int,
    now: int,
) -> None:
    """Step two, called when the problem named in a pending check is accepted. Any tutor help
    on it (before or during) makes the solve a miss: the check is about unaided work."""
    course_id, problem = catalog.problems[problem_id]
    concept = f"{course_id}:{problem.concepts[0]}"
    aid = transfer.activity_id(concept)
    record = db.get(ActivityRecord, (enrollment.id, aid))
    outcome = (record.outcome if record else None) or {}
    if record is None or record.completed_at is not None:
        return
    if outcome.get("state") != "pending" or outcome.get("problem") != problem_id:
        return
    independent = assistance == 0
    learn.record_evidence(
        db,
        enrollment,
        concept,
        "transfer",
        1.0 if independent else transfer.ASSISTED_SCORE,
        aid,
        now,
        min(assistance, 5),
        details=dict(stage="solve", problem=problem_id, ok=independent),
    )
    if independent:
        learn.complete_activity(
            db,
            user,
            enrollment,
            aid,
            now,
            outcome={"state": "verified", "problem": problem_id, "at": now},
        )
    else:
        record.outcome = {"state": "failed", "stage": "solve", "problem": problem_id, "at": now}


def is_pending(db: Session, catalog: Catalog, enrollment: Enrollment, problem_id: str) -> bool:
    """True while ``problem_id`` is the problem of a transfer check that is still to be solved."""
    if problem_id not in catalog.problems:
        return False
    course_id, problem = catalog.problems[problem_id]
    record = db.get(
        ActivityRecord, (enrollment.id, transfer.activity_id(f"{course_id}:{problem.concepts[0]}"))
    )
    outcome = (record.outcome if record else None) or {}
    return (
        record is not None
        and record.completed_at is None
        and outcome.get("state") == "pending"
        and outcome.get("problem") == problem_id
    )
