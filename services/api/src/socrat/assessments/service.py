"""Weekly personalised assessments: the hardest exam of the week, on Sundays.

Each Sunday (learner's local day) a learner who studied at least two topics in the last
seven days gets a 30-minute exam built from exactly that study: the hardest questions the
item bank holds on those topics, weighted toward what they spent time on, a few older topics
that are due, and one or two coding tasks from Socrat's judge.

Every question is one the learner has never been shown: not in a concept check, a review, a
checkpoint, a test-out or an earlier weekly. Once used here, a question is held back from
every other quiz for ``QUARANTINE_DAYS``, so the next time it appears is long after.
Answers stay hidden until the end; the report shows per-topic results, mastery movement and
what to focus on next.
"""

import os
import random
from collections import Counter
from dataclasses import dataclass, field
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.catalog.schema import QuizItem
from socrat.learn import service as learn
from socrat.library import service as library
from socrat.mastery.model import DAY, ConceptState, band
from socrat.models import (
    ActivityRecord,
    Enrollment,
    Evidence,
    QuizEngineSession,
    QuizResponse,
    QuizSession,
    Submission,
    User,
    WeeklyAssessment,
)
from socrat.quiz import service as engine_service
from socrat.quiz.pools import Item

WINDOW_SECONDS = 7 * DAY
MIN_CONCEPTS = 2
QUESTIONS = 12
REVIEW_SLOTS = 3  # about 20-25% interleaved from older topics that are due
MAX_CODING = 2
TIME_LIMIT_SECONDS = 30 * 60
ACTIVE_SECONDS = 3 * 60 * 60  # how long an unfinished attempt pauses the tutor
STUDY_KINDS = ("quiz", "code", "checkpoint", "review", "external", "verified")
EXAM_WEEKDAY = 6  # Sunday (date.weekday())
QUARANTINE_DAYS = 180  # a weekly question is held back from every other quiz this long


def exam_day(user: User, now: int) -> bool:
    # Local demos only: SOCRAT_WEEKLY_ANY_DAY=1 opens the exam on any day for testing.
    if os.environ.get("SOCRAT_WEEKLY_ANY_DAY") == "1" and os.environ.get(
        "SOCRAT_ENVIRONMENT", "production"
    ) in {"development", "test"}:
        return True
    return learn.local_day(user, now).weekday() == EXAM_WEEKDAY


def next_exam_day(user: User, now: int) -> str:
    today = learn.local_day(user, now)
    return (today + timedelta(days=(EXAM_WEEKDAY - today.weekday()) % 7)).isoformat()


def key_of(concept: str, stored: str) -> str:
    """Bank key for a stored weekly item: new attempts store keys, old ones bare legacy ids."""
    return stored if ":" in stored or stored.startswith("gen-") else f"{concept}:{stored}"


def seen_keys(db: Session, enrollment: Enrollment) -> set[str]:
    """Every bank key this learner has been shown anywhere, ever."""
    seen = set(
        db.scalars(select(QuizResponse.item_id).where(QuizResponse.enrollment_id == enrollment.id))
    )
    for session in db.scalars(
        select(QuizSession).where(QuizSession.enrollment_id == enrollment.id)
    ):
        seen |= {f"{concept}:{item_id}" for concept, item_id in session.items}
    for row in db.scalars(
        select(QuizEngineSession).where(QuizEngineSession.enrollment_id == enrollment.id)
    ):
        pending = (row.state or {}).get("pending") or {}
        if pending.get("item"):
            seen.add(pending["item"])
    for attempt in db.scalars(
        select(WeeklyAssessment).where(WeeklyAssessment.enrollment_id == enrollment.id)
    ):
        seen |= {key_of(concept, stored) for concept, stored in attempt.items}
    return seen


def quarantined(db: Session, enrollment: Enrollment, now: int) -> set[str]:
    """Bank keys used in this learner's weeklies recently: other quizzes must not serve them."""
    since = now - QUARANTINE_DAYS * DAY
    keys: set[str] = set()
    for attempt in db.scalars(
        select(WeeklyAssessment).where(
            WeeklyAssessment.enrollment_id == enrollment.id,
            WeeklyAssessment.started_at >= since,
        )
    ):
        keys |= {key_of(concept, stored) for concept, stored in attempt.items}
    return keys


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


def _hardest(pool: list[Item], count: int, rng: random.Random) -> list[Item]:
    """The hardest ``count`` items, never-practised (assessment pool) first within a band,
    spread over patterns so one trick is not asked twice."""
    ranked = sorted(pool, key=lambda i: (-i.band, i.pool != "assessment", rng.random()))
    chosen: list[Item] = []
    used_patterns: set[str] = set()
    floor = ranked[0].band - 1 if ranked else 0
    for item in ranked:  # first pass: one per pattern, among the top two bands only
        if len(chosen) >= count or item.band < floor:
            break
        if item.pattern not in used_patterns or item.pattern == item.concept:
            chosen.append(item)
            used_patterns.add(item.pattern)
    for item in ranked:  # then fill by difficulty
        if len(chosen) >= count:
            break
        if item not in chosen:
            chosen.append(item)
    return sorted(chosen, key=lambda i: -i.band)


def compose(
    catalog: Catalog,
    bank: list[Item],
    language: str,
    states: dict[str, ConceptState],
    exposure: Counter,
    locked: set[str],
    solved: set[str],
    seen: set[str],
    now: int,
    seed: str,
) -> tuple[list[list[str]], list[list[str]], list[str]]:
    """(concepts with reasons, [concept, bank key] pairs, coding problem ids). Pure.

    Only items the learner has never seen, in their language, from the concepts they
    studied (plus a few due ones), hardest first.
    """
    rng = random.Random(seed)
    by_concept: dict[str, list[Item]] = {}
    for item in bank:
        if (
            item.status != "retired"
            and item.key not in seen
            and (not item.languages or language in item.languages)
        ):
            by_concept.setdefault(item.concept, []).append(item)
    weights = {
        c: n * (1.5 - states.get(c, ConceptState()).effective(now))
        for c, n in exposure.items()
        if c not in locked and by_concept.get(c)
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
            and by_concept.get(c)
        ),
        key=lambda c: states[c].next_review_at,
    )[:REVIEW_SLOTS]
    budget = QUESTIONS - len(due)
    total = sum(weights.values()) or 1.0
    # Largest-remainder allocation, at least one question per studied topic.
    share = {c: max(1.0, budget * w / total) for c, w in weights.items()}
    counts = {c: min(int(v), len(by_concept[c])) for c, v in share.items()}
    for c, _ in sorted(share.items(), key=lambda x: x[1] - int(x[1]), reverse=True):
        if sum(counts.values()) >= budget:
            break
        if counts[c] < len(by_concept[c]):
            counts[c] += 1
    # Topics with spare questions take the slots others could not fill.
    while sum(counts.values()) < budget:
        spare = [c for c in counts if counts[c] < len(by_concept[c])]
        if not spare:
            break
        counts[max(spare, key=lambda c: weights[c])] += 1
    items: list[list[str]] = []
    for c, n in counts.items():
        items += [[c, i.key] for i in _hardest(by_concept[c], n, rng)]
    for c in due:
        items += [[c, i.key] for i in _hardest(by_concept[c], 1, rng)]
    rng.shuffle(items)
    items = items[:QUESTIONS]
    coding: list[str] = []
    for c, _ in sorted(weights.items(), key=lambda x: -x[1]):
        problems = sorted(
            (p for p in catalog.concept(c).problems if p not in solved and p not in coding),
            key=lambda p: -_difficulty(catalog, p),
        )
        if problems:
            coding.append(problems[0])  # the hardest unsolved problem on the topic
        if len(coding) >= MAX_CODING:
            break
    concepts = [[c, "studied"] for c in weights] + [[c, "review"] for c in due]
    return concepts, items, coding


def _difficulty(catalog: Catalog, problem_id: str) -> int:
    entry = catalog.problems.get(problem_id)
    if entry is None:
        return 0
    value = getattr(entry[1], "difficulty", 0)
    order = {"easy": 1, "medium": 2, "hard": 3}
    return order.get(value, 0) if isinstance(value, str) else int(value or 0)


def status(db: Session, catalog: Catalog, user: User, enrollment: Enrollment, now: int) -> dict:
    week = iso_week(user, now)
    existing = this_week(db, enrollment, week)
    exposure = studied(db, catalog, enrollment, now)
    titles = [catalog.concept(c).title for c, _ in exposure.most_common(6)]
    if existing is not None:
        state = "done" if existing.finished_at else "in_progress"
        return dict(state=state, week=week, id=existing.id, topics=titles, needed=MIN_CONCEPTS)
    if not exam_day(user, now) and len(exposure) >= MIN_CONCEPTS:
        return dict(
            state="upcoming",
            week=week,
            id=None,
            topics=titles,
            needed=MIN_CONCEPTS,
            opens_on=next_exam_day(user, now),
            ready=len(exposure) >= MIN_CONCEPTS,
            time_limit_minutes=TIME_LIMIT_SECONDS // 60,
        )
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
    return dict(
        state="locked",
        week=week,
        id=None,
        topics=titles,
        needed=MIN_CONCEPTS,
        opens_on=next_exam_day(user, now),
    )


@dataclass
class Draft:
    """A weekly exam planned from the bank, before its hard questions are generated."""

    week: str
    language: str
    concepts: list[list[str]]
    items: list[list[str]]  # [concept, bank key]
    coding: list[str]
    bands: dict[str, int] = field(default_factory=dict)  # bank key -> band

    def wanted(self) -> dict[str, int]:
        """How many generated questions to ask for, per topic: one per planned question."""
        return dict(Counter(c for c, _ in self.items))


def plan(
    db: Session, catalog: Catalog, user: User, enrollment: Enrollment, now: int
) -> WeeklyAssessment | Draft:
    """This week's attempt when it exists, else the bank plan for a new one."""
    week = iso_week(user, now)
    existing = this_week(db, enrollment, week)
    if existing is not None:
        if existing.finished_at:
            raise HTTPException(409, "assessment_done")
        return existing
    if not exam_day(user, now):
        raise HTTPException(409, "assessment_not_today")
    exposure = studied(db, catalog, enrollment, now)
    if len(exposure) < MIN_CONCEPTS:
        raise HTTPException(409, "assessment_unavailable")
    bank = engine_service.items_for(db, catalog)
    concepts, items, coding = compose(
        catalog,
        bank,
        enrollment.language,
        learn.states_for(db, enrollment),
        exposure,
        set(learn.locked_concepts(db, catalog, enrollment, now)),
        library.native_solved(db, user.id),
        seen_keys(db, enrollment),
        now,
        f"{enrollment.id}:{week}",
    )
    if not items:
        raise HTTPException(409, "assessment_unavailable")
    bands = {i.key: i.band for i in bank}
    return Draft(
        week, enrollment.language, concepts, items, coding, {k: bands.get(k, 0) for _, k in items}
    )


def merge(draft: Draft, generated: list[dict]) -> tuple[list[list[str]], dict[str, dict]]:
    """Each topic keeps its question count; generated questions take the place of its
    easiest bank questions."""
    by_concept: dict[str, list[dict]] = {}
    for g in generated:
        by_concept.setdefault(g["concept"], []).append(g)
    items: list[list[str]] = []
    kept: dict[str, dict] = {}
    for concept, n in draft.wanted().items():
        fresh = by_concept.get(concept, [])[:n]
        bank = sorted(
            (k for c, k in draft.items if c == concept), key=lambda k: -draft.bands.get(k, 0)
        )[: n - len(fresh)]
        for g in fresh:
            kept[g["key"]] = {
                k: g[k] for k in ("prompt", "code", "options", "answer", "explanation", "edge")
            }
            items.append([concept, g["key"]])
        items += [[concept, k] for k in bank]
    # Hardest first is a tell; keep the planned order's shuffle instead.
    random.Random(draft.week + str(len(kept))).shuffle(items)
    return items, kept


def create(
    db: Session, enrollment: Enrollment, draft: Draft, generated: list[dict], now: int
) -> WeeklyAssessment:
    items, kept = merge(draft, generated)
    attempt = WeeklyAssessment(
        enrollment_id=enrollment.id,
        iso_week=draft.week,
        concepts=draft.concepts,
        items=items,
        coding=draft.coding,
        answers={},
        timed=True,
        started_at=now,
        deadline=now + TIME_LIMIT_SECONDS,
        report={},
        generated=kept or None,
    )
    db.add(attempt)
    db.flush()
    return attempt


def start(
    db: Session, catalog: Catalog, user: User, enrollment: Enrollment, now: int, timed: bool = True
) -> WeeklyAssessment:
    """Bank-only start (tests, and when generation is off). Every weekly is a 30-minute
    exam; ``timed`` is kept for old clients and ignored."""
    planned = plan(db, catalog, user, enrollment, now)
    if isinstance(planned, WeeklyAssessment):
        return planned
    return create(db, enrollment, planned, [], now)


def _item(catalog: Catalog, concept: str, item_id: str) -> QuizItem:
    return catalog.concept(concept).quiz_item(item_id)


def _shown(catalog: Catalog, attempt: WeeklyAssessment, concept: str, stored: str, language: str):
    """(prompt, code, options, answer position, explanation, difficulty, kind) for one item."""
    generated = (attempt.generated or {}).get(stored)
    if generated is not None:
        return dict(
            prompt=generated["prompt"],
            code=generated["code"],
            options=generated["options"],
            answer=generated["answer"],
            explanation=generated["explanation"]
            + (f" (Edge case: {generated['edge']}.)" if generated.get("edge") else ""),
            difficulty=7,
            kind="output",
        )
    if ":" not in stored:  # an attempt from before weeklies used the bank
        q = _item(catalog, concept, stored)
        shown = q.shown(attempt.id)
        return dict(
            prompt=q.prompt,
            code=q.snippet(language),
            options=shown["options"],
            answer=shown["answer"],
            explanation=q.explanation,
            difficulty=q.difficulty,
            kind=q.kind,
        )
    item = engine_service.item_by_key(catalog, stored)
    shown = engine_service.render(catalog, item, attempt.id, language)
    return dict(
        prompt=shown["prompt"],
        code=shown["code"],
        options=shown["options"],
        answer=shown["answer"],
        explanation=shown["explanation"],
        difficulty=item.band,
        kind=item.format,
    )


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
        shown = _shown(catalog, attempt, concept, item_id, language)
        answer = attempt.answers.get(item_id)
        entry = dict(
            id=item_id,
            concept=concept,
            concept_title=catalog.concept(concept).title,
            kind=shown["kind"],
            prompt=shown["prompt"],
            code=shown["code"],
            options=shown["options"],
            difficulty=shown["difficulty"],
            answered=answer is not None,
            choice=answer["choice"] if answer else None,
        )
        if finished and answer is not None:
            entry.update(
                correct=answer["correct"], answer=shown["answer"], explanation=shown["explanation"]
            )
        elif finished:
            entry.update(correct=False, answer=shown["answer"], explanation=shown["explanation"])
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
        server_now=now,
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
    shown = _shown(catalog, attempt, pair[0], item_id, enrollment.language)
    if not 0 <= choice < len(shown["options"]):
        raise HTTPException(422, "invalid_choice")
    if item_id in attempt.answers:
        raise HTTPException(409, "already_answered")
    attempt.answers = {
        **attempt.answers,
        item_id: {"choice": choice, "correct": choice == shown["answer"]},
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
