"""Quiz-style activities: concept checks, spaced reviews, refreshers and module checkpoints.

Answers stay server-side. Learning quizzes give feedback per question. Checkpoints are the
gates between modules: an adaptive staircase whose questions get harder with each correct
answer, graded only at the end. Passing completes the gate and unlocks the next module;
failing schedules a short cooldown with targeted reviews.
"""

import random

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat import entitlements
from socrat.catalog.registry import Catalog
from socrat.catalog.schema import QuizItem
from socrat.learn import service as learn
from socrat.mastery.model import EvidenceKind
from socrat.models import ActivityRecord, Enrollment, QuizSession, User
from socrat.planner import gates

KINDS: dict[str, EvidenceKind] = {
    "quiz": "quiz",
    "review": "review",
    "remedial": "quiz",
    "checkpoint": "checkpoint",
    "probe": "quiz",
    "testout": "testout",
    "moduletest": "testout",
}
# Test-outs are graded at the end, like checkpoints: no per-question feedback to game.
TESTOUTS = {"testout", "moduletest"}
TESTOUT_PASS = 0.8
CHECK_PASS = 0.8  # a concept check counts as done at 4 of 5
TESTOUT_CONCEPT_PASS = 0.75
PROBE_PREREQS = 3


def item(catalog: Catalog, concept: str, item_id: str) -> QuizItem:
    return next(q for q in catalog.concept(concept).quiz if q.matches(item_id))


def fitting(catalog: Catalog, concept: str, language: str) -> list[QuizItem]:
    """The concept's items minus those about another language; all of them if none fit."""
    quiz = catalog.concept(concept).quiz
    return [q for q in quiz if q.fits(language)] or list(quiz)


OPEN_TEST_SECONDS = 20 * 60  # a check touched this recently still counts as being taken


def open_test(db: Session, enrollment: Enrollment, now: int) -> bool:
    """Whether the learner is in the middle of a graded check or test right now.

    The tutor steps back while one is open, so a question cannot be answered by asking Soc.
    An abandoned check stops counting after ``OPEN_TEST_SECONDS``.
    """
    from socrat.models import QuizEngineSession

    since = now - OPEN_TEST_SECONDS
    legacy = db.scalar(
        select(QuizSession.id).where(
            QuizSession.enrollment_id == enrollment.id,
            QuizSession.completed_at.is_(None),
            QuizSession.created_at >= since,
            ~QuizSession.activity_id.like("review:%"),
        )
    )
    if legacy is not None:
        return True
    for row in db.scalars(
        select(QuizEngineSession).where(
            QuizEngineSession.enrollment_id == enrollment.id,
            QuizEngineSession.completed_at.is_(None),
            QuizEngineSession.mode.in_(("concept_check", "testout", "checkpoint", "weekly")),
        )
    ):
        pending = (row.state or {}).get("pending") or {}
        if int(pending.get("served_at") or row.created_at) >= since:
            return True
    return False


# ---------------------------------------------------------------- gates


def gate_pool(catalog: Catalog, module_key: str, language: str) -> list[tuple[str, QuizItem]]:
    return [
        (c, q)
        for c in gates.module_concepts(catalog, module_key)
        for q in fitting(catalog, c, language)
    ]


def recent_items(db: Session, enrollment: Enrollment, now: int, exclude: str = "") -> set[str]:
    rows = db.scalars(
        select(QuizSession).where(
            QuizSession.enrollment_id == enrollment.id,
            QuizSession.created_at >= now - gates.RECENT_SECONDS,
            QuizSession.id != exclude,
        )
    )
    recent = {item_id for s in rows for _, item_id in s.items}
    # Questions used in a weekly exam stay out of practice for months (bare legacy ids here).
    from socrat.assessments.service import quarantined

    for key in quarantined(db, enrollment, now):
        recent.add(key.rsplit(":", 1)[-1])
    return recent


def next_gate_item(
    pool: list[tuple[str, QuizItem]],
    used: list[list[str]],
    recent: set[str],
    level: int,
    rng: random.Random,
) -> list[str] | None:
    """Closest unused item to `level`, preferring fresh items and concepts asked least."""
    taken = {item_id for _, item_id in used}
    candidates = [(c, q) for c, q in pool if q.id not in taken]
    if not candidates:
        return None
    fresh = [x for x in candidates if x[1].id not in recent] or candidates
    gap = min(abs(q.difficulty - level) for _, q in fresh)
    near = [x for x in fresh if abs(x[1].difficulty - level) == gap]
    asked: dict[str, int] = {}
    for concept, _ in used:
        asked[concept] = asked.get(concept, 0) + 1
    least = min(asked.get(c, 0) for c, _ in near)
    choices = sorted((x for x in near if asked.get(x[0], 0) == least), key=lambda x: x[1].id)
    concept, q = rng.choice(choices)
    return [concept, q.id]


def gate_state(
    catalog: Catalog, session: QuizSession, language: str, exhausted: bool = False
) -> gates.GateResult:
    module_key = session.activity_id.removeprefix("checkpoint:")
    pool = gate_pool(catalog, module_key, language)
    levels = sorted({q.difficulty for _, q in pool})
    hard_available = sum(1 for _, q in pool if q.difficulty == levels[-1]) if levels else 0
    answers = [
        (item(catalog, concept, item_id).difficulty, bool(session.answers[item_id]["correct"]))
        for concept, item_id in session.items
        if item_id in session.answers
    ]
    return gates.evaluate(answers, levels, hard_available, exhausted)


def gate_rng(enrollment: Enrollment, session_key: str, step: int) -> random.Random:
    return random.Random(f"{enrollment.id}:{session_key}:{step}")


# ---------------------------------------------------------------- sessions


def choose_items(
    catalog: Catalog,
    enrollment: Enrollment,
    activity_id: str,
    seed: int,
    recent: set[str] | None = None,
) -> list[list[str]]:
    kind, _, target = activity_id.partition(":")
    rng = random.Random(f"{enrollment.id}:{activity_id}:{seed}")
    if kind == "quiz":
        # A retake leads with questions the learner hasn't just seen, easiest first.
        seen = recent or set()
        quiz = sorted(
            fitting(catalog, target, enrollment.language),
            key=lambda q: (q.id in seen, q.difficulty, rng.random()),
        )
        return [[target, q.id] for q in quiz[:5]]
    if kind in {"review", "remedial"}:
        quiz = list(fitting(catalog, target, enrollment.language))
        rng.shuffle(quiz)
        return [[target, q.id] for q in quiz[: 3 if kind == "review" else 4]]
    if kind == "probe":
        # The concept plus its direct prerequisites, two mid-difficulty items each.
        items = []
        for concept in [target, *catalog.prerequisites[target][:PROBE_PREREQS]]:
            quiz = sorted(
                fitting(catalog, concept, enrollment.language),
                key=lambda q: (abs(q.difficulty - 3), q.id),
            )
            items += [[concept, q.id] for q in quiz[:2]]
        return items
    if kind == "testout":
        hardest = sorted(
            fitting(catalog, target, enrollment.language), key=lambda q: (-q.difficulty, q.id)
        )
        return [[target, q.id] for q in hardest[:4]]
    if kind == "moduletest":
        items = []
        for concept in gates.module_concepts(catalog, target):
            hardest = sorted(
                fitting(catalog, concept, enrollment.language), key=lambda q: (-q.difficulty, q.id)
            )
            items += [[concept, q.id] for q in hardest[:2]]
        return items[: gates.MAX_ITEMS]
    if kind == "checkpoint":
        course_id, module_id = target.split(":", 1)
        course = catalog.course(course_id)
        if not any(m.id == module_id for m in course.modules):
            raise HTTPException(404, "not_found")
        pool = gate_pool(catalog, target, enrollment.language)
        levels = sorted({q.difficulty for _, q in pool})
        if not levels:
            raise HTTPException(404, "not_found")
        start = gates.evaluate([], levels, 0).next_level
        first = next_gate_item(pool, [], recent or set(), start, rng)
        return [first] if first else []
    raise HTTPException(404, "not_found")


def open_session(
    db: Session, catalog: Catalog, enrollment: Enrollment, activity_id: str, now: int
) -> QuizSession:
    kind, _, target = activity_id.partition(":")
    if kind not in KINDS:
        raise HTTPException(404, "not_found")
    scope = learn.curriculum(catalog, enrollment)
    modular = kind in {"checkpoint", "moduletest"}
    if modular:
        course_id, _, module_id = target.partition(":")
        if course_id not in catalog.courses or not any(
            m.id == module_id for m in catalog.course(course_id).modules
        ):
            raise HTTPException(404, "not_found")
    elif target not in catalog.concepts:
        raise HTTPException(404, "not_found")
    targets = gates.module_concepts(catalog, target) if modular else [target]
    if not any(concept in scope for concept in targets):
        raise HTTPException(404, "not_found")
    # Before reusing an open session: one started earlier is no way around the plan.
    entitlements.require_concept(db, catalog, enrollment.user_id, targets[0], now)
    session = db.scalar(
        select(QuizSession)
        .where(
            QuizSession.enrollment_id == enrollment.id,
            QuizSession.activity_id == activity_id,
            QuizSession.completed_at.is_(None),
        )
        .order_by(QuizSession.created_at.desc())
    )
    if session is not None:
        return session
    locked = learn.locked_concepts(db, catalog, enrollment, now)
    if kind == "checkpoint":
        if gates.module_concepts(catalog, target)[0] in locked:
            raise learn.lock_error(locked[gates.module_concepts(catalog, target)[0]])
        record = db.get(ActivityRecord, (enrollment.id, activity_id))
        retry_at = int((record.outcome or {}).get("retry_at", 0)) if record else 0
        if record is not None and record.completed_at is None and retry_at > now:
            # Cooling down after a miss: show the last attempt's results instead.
            last = db.scalar(
                select(QuizSession)
                .where(
                    QuizSession.enrollment_id == enrollment.id,
                    QuizSession.activity_id == activity_id,
                )
                .order_by(QuizSession.created_at.desc())
            )
            if last is not None:
                return last
    elif kind == "moduletest":
        if targets[0] in locked:
            raise learn.lock_error(locked[targets[0]])
        if _finished(db, enrollment, activity_id):
            return _latest(db, enrollment, activity_id)
    elif target in locked:
        raise learn.lock_error(locked[target])
    elif kind in {"testout", "probe"} and _finished(db, enrollment, activity_id):
        return _latest(db, enrollment, activity_id)
    session = QuizSession(
        enrollment_id=enrollment.id,
        activity_id=activity_id,
        items=choose_items(
            catalog,
            enrollment,
            activity_id,
            now // 86400 if kind != "checkpoint" else now,
            recent_items(db, enrollment, now) if kind in {"checkpoint", "quiz"} else None,
        ),
        answers={},
        created_at=now,
    )
    db.add(session)
    db.flush()
    learn.start_activity(db, enrollment, activity_id, now)
    return session


def _finished(db: Session, enrollment: Enrollment, activity_id: str) -> bool:
    """A one-off check already taken; it shows its result instead of starting over."""
    record = db.get(ActivityRecord, (enrollment.id, activity_id))
    return (
        record is not None
        and record.completed_at is not None
        and _latest(db, enrollment, activity_id) is not None
    )


def _latest(db: Session, enrollment: Enrollment, activity_id: str) -> QuizSession:
    row = db.scalar(
        select(QuizSession)
        .where(QuizSession.enrollment_id == enrollment.id, QuizSession.activity_id == activity_id)
        .order_by(QuizSession.created_at.desc())
    )
    if row is None:
        raise HTTPException(404, "not_found")
    return row


def gate_view(db: Session, catalog: Catalog, session: QuizSession, language: str) -> dict:
    module_key = session.activity_id.removeprefix("checkpoint:")
    state = gate_state(catalog, session, language)
    record = db.get(ActivityRecord, (session.enrollment_id, session.activity_id))
    outcome = (record.outcome or {}) if record else {}
    course_id = module_key.split(":", 1)[0]
    keys = gates.module_keys(catalog, course_id)
    position = keys.index(module_key)
    unlocks = keys[position + 1] if position + 1 < len(keys) else None
    pool = gate_pool(catalog, module_key, language)
    return dict(
        max_items=gates.MAX_ITEMS,
        max_strikes=gates.MAX_STRIKES,
        strikes=state.strikes,
        levels=sorted({q.difficulty for _, q in pool}),
        level=state.next_level,
        hard_level=state.hard_level,
        hard_needed=state.hard_needed,
        hard_correct=state.hard_correct,
        pass_score=gates.PASS_SCORE,
        score=state.score if session.completed_at else None,
        passed=bool(record and record.completed_at) if session.completed_at else None,
        retry_at=outcome.get("retry_at") if record and record.completed_at is None else None,
        attempts=int(outcome.get("attempts", 0)),
        module=gates_title(catalog, module_key),
        unlocks=gates_title(catalog, unlocks) if unlocks else None,
    )


def gates_title(catalog: Catalog, module_key: str) -> str:
    course_id, module_id = module_key.split(":", 1)
    return next(m.title for m in catalog.course(course_id).modules if m.id == module_id)


def session_view(
    catalog: Catalog,
    session: QuizSession,
    language: str,
    db: Session | None = None,
    locale: str = "en",
) -> dict:
    kind = session.activity_id.partition(":")[0]
    checkpoint = kind == "checkpoint"
    graded = (not checkpoint and kind not in TESTOUTS) or session.completed_at is not None
    questions = []
    for concept, item_id in session.items:
        q = item(catalog, concept, item_id)
        if db is not None and locale != "en":
            from socrat.localize import service as localized

            q = localized.quiz_item(db, concept, catalog.concept(concept), locale, q)
        answer = session.answers.get(item_id)
        shown = q.shown(session.id)
        entry = dict(
            id=q.id,
            concept=concept,
            concept_title=catalog.concept(concept).title,
            kind=q.kind,
            prompt=q.prompt,
            code=q.snippet(language),
            options=shown["options"],
            difficulty=q.difficulty,
            answered=answer is not None,
            choice=answer["choice"] if answer else None,
        )
        if answer is not None and graded:
            entry.update(
                correct=answer["correct"], answer=shown["answer"], explanation=q.explanation
            )
        questions.append(entry)
    view = dict(
        id=session.id,
        activity_id=session.activity_id,
        questions=questions,
        completed=session.completed_at is not None,
        score=score_of(catalog, session, language) if session.completed_at else None,
        feedback="at_end" if checkpoint or kind in TESTOUTS else "immediate",
    )
    if checkpoint and db is not None:
        view["gate"] = gate_view(db, catalog, session, language)
    if kind in TESTOUTS and db is not None and session.completed_at is not None:
        record = db.get(ActivityRecord, (session.enrollment_id, session.activity_id))
        outcome = (record.outcome or {}) if record else {}
        view["testout"] = dict(passed=bool(outcome.get("passed")), score=outcome.get("score"))
    return view


def score_of(catalog: Catalog, session: QuizSession, language: str) -> float:
    if session.activity_id.startswith("checkpoint:"):
        return gate_state(catalog, session, language).score
    if not session.items:
        return 0.0
    return sum(1 for a in session.answers.values() if a["correct"]) / len(session.items)


def answer(
    db: Session,
    catalog: Catalog,
    user: User,
    enrollment: Enrollment,
    session: QuizSession,
    item_id: str,
    choice: int,
    now: int,
    confidence: int | None = None,
) -> dict:
    if session.completed_at is not None:
        raise HTTPException(409, "quiz_already_completed")
    pair = next((p for p in session.items if p[1] == item_id), None)
    if pair is None:
        raise HTTPException(404, "not_found")
    q = item(catalog, pair[0], item_id)
    if not 0 <= choice < len(q.options):
        raise HTTPException(422, "invalid_choice")
    if item_id in session.answers:
        raise HTTPException(409, "already_answered")
    correct = q.is_correct(session.id, choice)  # choice is a display position
    entry = {"choice": choice, "correct": correct}
    if confidence is not None:
        entry["confidence"] = confidence
    session.answers = {**session.answers, item_id: entry}
    if session.activity_id.startswith("checkpoint:"):
        state = gate_state(catalog, session, enrollment.language)
        if not state.done:
            module_key = session.activity_id.removeprefix("checkpoint:")
            following = next_gate_item(
                gate_pool(catalog, module_key, enrollment.language),
                session.items,
                recent_items(db, enrollment, now, exclude=session.id),
                state.next_level,
                gate_rng(enrollment, session.id, len(session.items)),
            )
            if following is None:
                state = gate_state(catalog, session, enrollment.language, exhausted=True)
            else:
                session.items = [*session.items, following]
        finished = state.done
    else:
        finished = len(session.answers) == len(session.items)
    if finished:
        finish(db, catalog, user, enrollment, session, now)
    return dict(finished=finished, correct=correct)


def finish(
    db: Session,
    catalog: Catalog,
    user: User,
    enrollment: Enrollment,
    session: QuizSession,
    now: int,
):
    session.completed_at = now
    kind = KINDS[session.activity_id.partition(":")[0]]
    elapsed = learn.elapsed(db, enrollment, session.activity_id, now)
    expected = learn.expected_seconds(catalog, session.activity_id, enrollment)
    per_concept: dict[str, list[bool]] = {}
    for concept, item_id in session.items:
        if item_id in session.answers:
            per_concept.setdefault(concept, []).append(bool(session.answers[item_id]["correct"]))
    if session.activity_id.partition(":")[0] in TESTOUTS:
        return finish_testout(db, catalog, user, enrollment, session, per_concept, now)
    rated: dict[str, list[int]] = {}
    for concept, item_id in session.items:
        if (c := (session.answers.get(item_id) or {}).get("confidence")) is not None:
            rated.setdefault(concept, []).append(int(c))
    for concept, results in per_concept.items():
        sure = rated.get(concept, [])
        learn.record_evidence(
            db,
            enrollment,
            concept,
            kind,
            sum(results) / len(results),
            session.activity_id,
            now,
            elapsed_seconds=elapsed,
            expected_seconds=expected,
            # Mean stated confidence on a 0-1 scale, when the learner rated their answers.
            details={"confidence": round((sum(sure) / len(sure) - 1) / 3, 3), "rated": len(sure)}
            if sure
            else None,
        )
    if session.activity_id.startswith("checkpoint:"):
        state = gate_state(catalog, session, enrollment.language, exhausted=True)
        record = learn.start_activity(db, enrollment, session.activity_id, now)
        attempts = int((record.outcome or {}).get("attempts", 0)) + 1
        if state.passed:
            learn.complete_activity(
                db,
                user,
                enrollment,
                session.activity_id,
                now,
                outcome={"score": state.score, "passed": True, "attempts": attempts},
            )
        elif record.completed_at is None:  # a failed retake never re-locks a passed gate
            record.outcome = {
                "score": state.score,
                "passed": False,
                "attempts": attempts,
                "retry_at": now + gates.COOLDOWN_SECONDS,
            }
            learn.bump_daily(db, user, now, minutes=round(elapsed / 60))
    elif session.activity_id.startswith("quiz:"):
        settle_check(
            db,
            user,
            enrollment,
            session.activity_id,
            score_of(catalog, session, enrollment.language),
            now,
        )
    elif session.activity_id.startswith(("remedial:", "probe:")):
        learn.complete_activity(
            db,
            user,
            enrollment,
            session.activity_id,
            now,
            outcome={"score": score_of(catalog, session, enrollment.language)},
        )
    else:  # Reviews recur on a schedule; count the effort without completing them forever.
        learn.bump_daily(db, user, now, minutes=round(elapsed / 60))


def settle_check(
    db: Session, user: User, enrollment: Enrollment, activity_id: str, score: float, now: int
) -> bool:
    """Close a concept check, whichever engine served it. Returns whether it passed."""
    passed = score >= CHECK_PASS
    if passed:
        learn.complete_activity(db, user, enrollment, activity_id, now, outcome={"score": score})
    else:
        # A missed check is not done: the plan adds a different explanation and a fresh check.
        record = learn.start_activity(db, enrollment, activity_id, now)
        if record.completed_at is None:
            record.outcome = {"score": score, "passed": False}
        elapsed = learn.elapsed(db, enrollment, activity_id, now)
        learn.bump_daily(db, user, now, minutes=round(elapsed / 60))
    # Taking the check means the lesson was read.
    learn.complete_activity(
        db,
        user,
        enrollment,
        "lesson:" + activity_id.removeprefix("quiz:"),
        now,
        outcome={"via": "concept_check"},
    )
    return passed


def finish_testout(
    db: Session,
    catalog: Catalog,
    user: User,
    enrollment: Enrollment,
    session: QuizSession,
    per_concept: dict[str, list[bool]],
    now: int,
):
    """Passing proves the concept (or the whole module) and skips it. Missing costs nothing
    beyond honest quiz evidence, and the normal path carries on."""
    elapsed = learn.elapsed(db, enrollment, session.activity_id, now)
    expected = learn.expected_seconds(catalog, session.activity_id, enrollment)
    score = score_of(catalog, session, enrollment.language)
    fractions = {c: sum(r) / len(r) for c, r in per_concept.items()}
    passed = (
        score >= TESTOUT_PASS
        and bool(fractions)
        and all(f >= 0.5 for f in fractions.values())
        and (len(fractions) > 1 or min(fractions.values()) >= TESTOUT_CONCEPT_PASS)
    )
    for concept, fraction in fractions.items():
        proven = passed and fraction >= TESTOUT_CONCEPT_PASS
        learn.record_evidence(
            db,
            enrollment,
            concept,
            "testout" if proven else "quiz",
            1.0 if proven else fraction,
            session.activity_id,
            now,
            elapsed_seconds=elapsed,
            expected_seconds=expected,
        )
    outcome = {"score": score, "passed": passed}
    learn.complete_activity(db, user, enrollment, session.activity_id, now, outcome=outcome)
    if passed and session.activity_id.startswith("moduletest:"):
        gate = gates.gate_id(session.activity_id.removeprefix("moduletest:"))
        learn.complete_activity(
            db, user, enrollment, gate, now, outcome={**outcome, "via": "test_out"}
        )


def settle_testout(
    db: Session,
    catalog: Catalog,
    user: User,
    enrollment: Enrollment,
    activity_id: str,
    per_concept: dict[str, list[bool]],
    passed: bool,
    score: float,
    now: int,
) -> None:
    """Close a test-out the adaptive engine ran; ``passed`` is the engine's decision."""
    elapsed = learn.elapsed(db, enrollment, activity_id, now)
    expected = learn.expected_seconds(catalog, activity_id, enrollment)
    for concept, results in per_concept.items():
        fraction = sum(results) / len(results)
        learn.record_evidence(
            db,
            enrollment,
            concept,
            "testout" if passed else "quiz",
            1.0 if passed else fraction,
            activity_id,
            now,
            elapsed_seconds=elapsed,
            expected_seconds=expected,
        )
    outcome = {"score": round(score, 3), "passed": passed, "engine": "adaptive"}
    learn.complete_activity(db, user, enrollment, activity_id, now, outcome=outcome)


def rated_answers(db: Session, user_id: str) -> list[tuple[float, bool]]:
    """(confidence 0-1, correct) for every quiz answer this learner rated, across courses."""

    sessions = db.scalars(
        select(QuizSession)
        .join(Enrollment, Enrollment.id == QuizSession.enrollment_id)
        .where(Enrollment.user_id == user_id)
    )
    standard = [
        ((int(a["confidence"]) - 1) / 3, bool(a["correct"]))
        for s in sessions
        for a in (s.answers or {}).values()
        if isinstance(a, dict) and a.get("confidence") is not None
    ]
    from socrat.models import QuizResponse

    adaptive = db.execute(
        select(QuizResponse.confidence, QuizResponse.correct)
        .join(Enrollment, Enrollment.id == QuizResponse.enrollment_id)
        .where(Enrollment.user_id == user_id, QuizResponse.confidence.is_not(None))
    )
    return standard + [((int(c or 1) - 1) / 3, bool(ok)) for c, ok in adaptive]
