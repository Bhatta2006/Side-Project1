"""Weekly personalised assessments.

Once per (local) ISO week a learner who studied at least two topics in the last seven days
gets an assessment built from exactly that study: questions weighted toward what they spent
time on and what is still shaky, a few interleaved older topics that are due for review,
and one or two coding tasks from Socrat's judge. Answers stay hidden until the end; the
report shows per-topic results, mastery movement and what to focus on next.
"""

import random
from collections import Counter

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.catalog.schema import QuizItem
from socrat.learn import service as learn
from socrat.learn.quizzes import recent_items
from socrat.library import service as library
from socrat.mastery.model import DAY, ConceptState, band
from socrat.models import (
    ActivityRecord,
    Enrollment,
    Evidence,
    Submission,
    User,
    WeeklyAssessment,
)

WINDOW_SECONDS = 7 * DAY
MIN_CONCEPTS = 2
QUESTIONS = 12
REVIEW_SLOTS = 3  # about 20-25% interleaved from older topics that are due
MAX_CODING = 2
TIME_LIMIT_SECONDS = 30 * 60
ACTIVE_SECONDS = 3 * 60 * 60  # how long an unfinished attempt pauses the tutor
STUDY_KINDS = ("quiz", "code", "checkpoint", "review", "external", "verified")


def iso_week(user: User, now: int) -> str:
    year, week, _ = learn.local_day(user, now).isocalendar()
    return f"{year}-W{week:02d}"


def studied(db: Session, catalog: Catalog, enrollment: Enrollment, now: int) -> Counter:
    """Concept -> how many study events it had in the last seven days."""
    since = now - WINDOW_SECONDS
    exposure: Counter = Counter()
    for concept in db.scalars(
        select(Evidence.concept).where(
            Evidence.enrollment_id == enrollment.id,
            Evidence.created_at >= since,
            Evidence.kind.in_(STUDY_KINDS),
            ~Evidence.activity_id.like("assessment:%"),
        )
    ):
        exposure[concept] += 1
    for activity in db.scalars(
        select(ActivityRecord.activity_id).where(
            ActivityRecord.enrollment_id == enrollment.id,
            ActivityRecord.completed_at >= since,
            ActivityRecord.activity_id.like("lesson:%"),
        )
    ):
        exposure[activity.removeprefix("lesson:")] += 1
    return Counter({c: n for c, n in exposure.items() if c in catalog.concepts})


def this_week(db: Session, enrollment: Enrollment, week: str) -> WeeklyAssessment | None:
    return db.scalar(
        select(WeeklyAssessment).where(
            WeeklyAssessment.enrollment_id == enrollment.id, WeeklyAssessment.iso_week == week
        )
    )


def in_progress(db: Session, enrollment: Enrollment, now: int) -> WeeklyAssessment | None:
    """An unfinished attempt that is still live (pauses the tutor)."""
    attempt = db.scalar(
        select(WeeklyAssessment)
        .where(
            WeeklyAssessment.enrollment_id == enrollment.id,
            WeeklyAssessment.finished_at.is_(None),
            WeeklyAssessment.started_at >= now - ACTIVE_SECONDS,
        )
        .order_by(WeeklyAssessment.started_at.desc())
    )
    if attempt is not None and attempt.deadline and now > attempt.deadline:
        return None
    return attempt


def _target(state: ConceptState, now: int) -> int:
    """Difficulty to aim for: shaky topics get a fair check, strong ones get a stretch."""
    label = band(state, now)
    return {"not_started": 1, "needs_practice": 1, "developing": 2}.get(label, 5)


def _pick(
    pool: list[QuizItem], count: int, target: int, recent: set[str], rng: random.Random
) -> list[QuizItem]:
    ranked = sorted(pool, key=lambda q: (q.id in recent, abs(q.difficulty - target), rng.random()))
    return ranked[:count]


def compose(
    catalog: Catalog,
    states: dict[str, ConceptState],
    exposure: Counter,
    locked: set[str],
    solved: set[str],
    recent: set[str],
    now: int,
    seed: str,
) -> tuple[list[list[str]], list[list[str]], list[str]]:
    """(concepts with reasons, [concept, item] pairs, coding problem ids). Pure."""
    rng = random.Random(seed)
    weights = {
        c: n * (1.5 - states.get(c, ConceptState()).effective(now))
        for c, n in exposure.items()
        if c not in locked and catalog.concept(c).quiz
    }
    due = sorted(
        (
            c
            for c, s in states.items()
            if c not in weights
            and c not in locked
            and c in catalog.concepts
            and s.evidence_count
            and s.due(now)
            and catalog.concept(c).quiz
        ),
        key=lambda c: states[c].next_review_at,
    )[:REVIEW_SLOTS]
    budget = QUESTIONS - len(due)
    total = sum(weights.values()) or 1.0
    # Largest-remainder allocation, at least one question per studied topic.
    share = {c: max(1.0, budget * w / total) for c, w in weights.items()}
    counts = {c: min(int(v), len(catalog.concept(c).quiz)) for c, v in share.items()}
    for c, _ in sorted(share.items(), key=lambda x: x[1] - int(x[1]), reverse=True):
        if sum(counts.values()) >= budget:
            break
        if counts[c] < len(catalog.concept(c).quiz):
            counts[c] += 1
    items: list[list[str]] = []
    for c, n in counts.items():
        state = states.get(c, ConceptState())
        items += [
            [c, q.id] for q in _pick(catalog.concept(c).quiz, n, _target(state, now), recent, rng)
        ]
    for c in due:
        items += [[c, q.id] for q in _pick(catalog.concept(c).quiz, 1, 5, recent, rng)]
    rng.shuffle(items)
    items = items[:QUESTIONS]
    coding: list[str] = []
    for c, _ in sorted(weights.items(), key=lambda x: -x[1]):
        for problem_id in catalog.concept(c).problems:
            if problem_id not in solved and problem_id not in coding:
                coding.append(problem_id)
                break
        if len(coding) >= MAX_CODING:
            break
    concepts = [[c, "studied"] for c in weights] + [[c, "review"] for c in due]
    return concepts, items, coding


def status(db: Session, catalog: Catalog, user: User, enrollment: Enrollment, now: int) -> dict:
    week = iso_week(user, now)
    existing = this_week(db, enrollment, week)
    exposure = studied(db, catalog, enrollment, now)
    titles = [catalog.concept(c).title for c, _ in exposure.most_common(6)]
    if existing is not None:
        state = "done" if existing.finished_at else "in_progress"
        return dict(state=state, week=week, id=existing.id, topics=titles, needed=MIN_CONCEPTS)
    if len(exposure) >= MIN_CONCEPTS:
        return dict(
            state="available",
            week=week,
            id=None,
            topics=titles,
            questions=QUESTIONS,
            time_limit_minutes=TIME_LIMIT_SECONDS // 60,
            needed=MIN_CONCEPTS,
        )
    return dict(state="locked", week=week, id=None, topics=titles, needed=MIN_CONCEPTS)


def start(
    db: Session, catalog: Catalog, user: User, enrollment: Enrollment, now: int, timed: bool
) -> WeeklyAssessment:
    week = iso_week(user, now)
    existing = this_week(db, enrollment, week)
    if existing is not None:
        if existing.finished_at:
            raise HTTPException(409, "assessment_done")
        return existing
    exposure = studied(db, catalog, enrollment, now)
    if len(exposure) < MIN_CONCEPTS:
        raise HTTPException(409, "assessment_unavailable")
    concepts, items, coding = compose(
        catalog,
        learn.states_for(db, enrollment),
        exposure,
        set(learn.locked_concepts(db, catalog, enrollment, now)),
        library.native_solved(db, user.id),
        recent_items(db, enrollment, now),
        now,
        f"{enrollment.id}:{week}",
    )
    if not items:
        raise HTTPException(409, "assessment_unavailable")
    attempt = WeeklyAssessment(
        enrollment_id=enrollment.id,
        iso_week=week,
        concepts=concepts,
        items=items,
        coding=coding,
        answers={},
        timed=timed,
        started_at=now,
        deadline=now + TIME_LIMIT_SECONDS if timed else None,
        report={},
    )
    db.add(attempt)
    db.flush()
    return attempt


def _item(catalog: Catalog, concept: str, item_id: str) -> QuizItem:
    return next(q for q in catalog.concept(concept).quiz if q.matches(item_id))


def _coding_solved(db: Session, user_id: str, attempt: WeeklyAssessment) -> set[str]:
    if not attempt.coding:
        return set()
    return set(
        db.scalars(
            select(Submission.problem_id).where(
                Submission.user_id == user_id,
                Submission.problem_id.in_(attempt.coding),
                Submission.mode == "submit",
                Submission.verdict == "accepted",
                Submission.created_at >= attempt.started_at,
            )
        )
    )


def view(
    db: Session, catalog: Catalog, user: User, attempt: WeeklyAssessment, language: str, now: int
) -> dict:
    finished = attempt.finished_at is not None
    questions = []
    for concept, item_id in attempt.items:
        q = _item(catalog, concept, item_id)
        shown = q.shown(attempt.id)
        answer = attempt.answers.get(item_id)
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
        if finished and answer is not None:
            entry.update(
                correct=answer["correct"], answer=shown["answer"], explanation=q.explanation
            )
        elif finished:
            entry.update(correct=False, answer=shown["answer"], explanation=q.explanation)
        questions.append(entry)
    solved = _coding_solved(db, user.id, attempt)
    coding = []
    for problem_id in attempt.coding:
        course_id, problem = catalog.problems[problem_id]
        coding.append(
            dict(
                id=problem_id,
                title=problem.title,
                difficulty=problem.difficulty,
                concept=catalog.concept(f"{course_id}:{problem.concepts[0]}").title,
                solved=problem_id in solved,
            )
        )
    return dict(
        id=attempt.id,
        week=attempt.iso_week,
        timed=attempt.timed,
        started_at=attempt.started_at,
        deadline=attempt.deadline,
        seconds_left=max(0, attempt.deadline - now) if attempt.deadline and not finished else None,
        finished=finished,
        score=attempt.score,
        topics=[
            dict(id=c, title=catalog.concept(c).title, reason=reason)
            for c, reason in attempt.concepts
        ],
        questions=questions,
        coding=coding,
        report=attempt.report if finished else None,
    )


def answer(
    db: Session,
    catalog: Catalog,
    user: User,
    enrollment: Enrollment,
    attempt: WeeklyAssessment,
    item_id: str,
    choice: int,
    now: int,
) -> None:
    if attempt.finished_at is not None:
        raise HTTPException(409, "assessment_done")
    if attempt.deadline and now > attempt.deadline:
        finish(db, catalog, user, enrollment, attempt, now)
        return
    pair = next((p for p in attempt.items if p[1] == item_id), None)
    if pair is None:
        raise HTTPException(404, "not_found")
    q = _item(catalog, pair[0], item_id)
    if not 0 <= choice < len(q.options):
        raise HTTPException(422, "invalid_choice")
    if item_id in attempt.answers:
        raise HTTPException(409, "already_answered")
    attempt.answers = {
        **attempt.answers,
        item_id: {"choice": choice, "correct": q.is_correct(attempt.id, choice)},
    }


def finish(
    db: Session,
    catalog: Catalog,
    user: User,
    enrollment: Enrollment,
    attempt: WeeklyAssessment,
    now: int,
) -> None:
    if attempt.finished_at is not None:
        return
    before = learn.states_for(db, enrollment)
    results: dict[str, list[bool]] = {}
    for concept, item_id in attempt.items:
        results.setdefault(concept, []).append(
            bool(attempt.answers.get(item_id, {}).get("correct"))
        )
    for concept, marks in results.items():
        learn.record_evidence(
            db,
            enrollment,
            concept,
            "checkpoint",
            sum(marks) / len(marks),
            f"assessment:{attempt.iso_week}",
            now,
        )
    after = learn.states_for(db, enrollment)
    solved = _coding_solved(db, user.id, attempt)
    correct = sum(sum(marks) for marks in results.values())
    total = sum(len(marks) for marks in results.values()) + len(attempt.coding)
    attempt.score = round((correct + len(solved)) / total, 3) if total else 0.0
    attempt.finished_at = now
    ratios = {c: sum(m) / len(m) for c, m in results.items()}
    ordered = sorted(results, key=lambda c: ratios[c])
    topics = [
        dict(
            id=c,
            title=catalog.concept(c).title,
            correct=sum(results[c]),
            total=len(results[c]),
            before=round(before.get(c, ConceptState()).effective(now), 3),
            after=round(after.get(c, ConceptState()).effective(now), 3),
            band=band(after.get(c, ConceptState()), now),
        )
        for c in ordered
    ]
    previous = db.scalar(
        select(WeeklyAssessment.score)
        .where(
            WeeklyAssessment.enrollment_id == enrollment.id,
            WeeklyAssessment.finished_at.is_not(None),
            WeeklyAssessment.id != attempt.id,
        )
        .order_by(WeeklyAssessment.finished_at.desc())
    )
    minutes = max(1, round((now - attempt.started_at) / 60))
    attempt.report = dict(
        correct=correct,
        questions=sum(len(m) for m in results.values()),
        coding_solved=len(solved),
        coding_total=len(attempt.coding),
        minutes=minutes,
        previous_score=previous,
        topics=topics,
        strengths=[catalog.concept(c).title for c in ordered if ratios[c] >= 0.8],
        focus=[dict(id=c, title=catalog.concept(c).title) for c in ordered if ratios[c] < 0.6],
    )
    learn.bump_daily(db, user, now, minutes=minutes)


def history(db: Session, enrollment: Enrollment, limit: int = 12) -> list[dict]:
    rows = db.scalars(
        select(WeeklyAssessment)
        .where(
            WeeklyAssessment.enrollment_id == enrollment.id,
            WeeklyAssessment.finished_at.is_not(None),
        )
        .order_by(WeeklyAssessment.finished_at.desc())
        .limit(limit)
    )
    return [dict(id=r.id, week=r.iso_week, score=r.score, finished_at=r.finished_at) for r in rows]
