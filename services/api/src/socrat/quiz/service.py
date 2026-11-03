"""Database side of the adaptive quiz: load state, call the engine, write results.

Each answer writes a ``QuizResponse``, updates the learner's θ for the pattern and (for
provisional items) the item's rating, and, when the mode and item allow it, records normal
mastery ``Evidence`` through ``learn.record_evidence`` → ``mastery.apply`` (D4): score 1 or
0, with hints as the assistance level. θ itself never changes mastery.
"""

import random
import threading
from dataclasses import asdict, replace
from typing import cast

from fastapi import HTTPException
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog, qualify
from socrat.catalog.schema import Language
from socrat.learn import service as learn
from socrat.models import (
    ActivityRecord,
    Enrollment,
    ItemCalibration,
    ItemRating,
    LearnerAbility,
    QuizEngineSession,
    QuizResponse,
)
from socrat.quiz import engine, modes, pools
from socrat.quiz.config import COURSE_TRACK, DEFAULT, TRACKS, EngineConfig, Mode, ModeSpec, Track
from socrat.quiz.pools import Item
from socrat.quiz.selection import Context, Outcome, Step

LEGACY_REASON = "assessment_pool_not_calibrated"
SEEN_DAYS = 14  # an answered item stays out of rotation this long
_BANKS: dict[str, list[Item]] = {}
_BANK_LOCK = threading.Lock()


def bank(cat: Catalog, cfg: EngineConfig = DEFAULT) -> list[Item]:
    """The item bank for this catalog, built once per catalog digest."""
    key = getattr(cat, "digest", "") or str(id(cat))
    # Generators are not thread-safe: two first requests at once must not build it together.
    with _BANK_LOCK:
        if key not in _BANKS:
            _BANKS.clear()
            _BANKS[key] = pools.bank(cat, cfg)
        return _BANKS[key]


def spec_of(session: QuizEngineSession, cfg: EngineConfig = DEFAULT) -> ModeSpec:
    return cfg.modes[cast(Mode, session.mode)]


def track_of(session: QuizEngineSession) -> Track:
    return cast(Track, session.track)


def approved(db: Session) -> dict[str, str]:
    """Statuses a named human approved (M7); they override the content file's status."""
    rows = db.scalars(select(ItemCalibration).where(ItemCalibration.approved_by.is_not(None)))
    return {row.item_id: row.status for row in rows}


def effective(items: list[Item], statuses: dict[str, str]) -> list[Item]:
    return [replace(i, status=statuses[i.key]) if i.key in statuses else i for i in items]


def items_for(db: Session, cat: Catalog, cfg: EngineConfig = DEFAULT) -> list[Item]:
    """The bank with approved calibrations applied: calibrated freezes d, retired is never served."""
    return effective(bank(cat, cfg), approved(db))


def track_for(enrollment: Enrollment) -> Track:
    chosen = (enrollment.goal or {}).get("track")
    if chosen in TRACKS:
        return chosen
    return COURSE_TRACK.get(enrollment.course_id, "interview")


# ---------------------------------------------------------------- item content


def render(cat: Catalog, item: Item, seed: str, language: str) -> dict:
    """What the learner sees, plus the server-side answer in display order."""
    if not item.family:
        q = next(q for q in cat.concept(item.concept).quiz if q.matches(item.item_id))
        order = q.order(seed)
        return dict(
            prompt=q.prompt,
            code=q.snippet(language),
            options=[q.options[i] for i in order],
            order=order,
            answer=order.index(q.answer),
            explanation=q.explanation,
            hints=[],
        )
    family = cat.quiz_families[item.family]
    if item.seed is not None:
        return render_generated(cat, item, seed, language)
    b = next(b for b in family.items if b.id == item.item_id)
    order = list(range(len(b.options)))
    random.Random(f"{seed}:{b.id}").shuffle(order)
    code = b.code.get(cast(Language, language)) or next(iter(b.code.values()), None)
    return dict(
        prompt=b.prompt,
        code=code,
        options=[b.options[i] for i in order],
        order=order,
        answer=order.index(b.answer),
        explanation=b.explanation,
        hints=list(family.hint_ladder),
    )


def render_generated(cat: Catalog, item: Item, seed: str, language: str) -> dict:
    from socrat.quiz.generate import framework

    family = cat.quiz_families[item.family]
    assert cat.quiz_root is not None and item.seed is not None
    made = framework.draft(cat.quiz_root, family, item.seed)
    order = list(range(len(made.options)))
    random.Random(f"{seed}:{item.key}").shuffle(order)
    code = made.code.get(cast(Language, language)) or next(iter(made.code.values()))
    return dict(
        prompt=made.prompt,
        code=code,
        options=[made.option_text(i, language) for i in order],
        order=order,
        answer=order.index(made.answer),
        explanation=made.explanation,
        hints=list(family.hint_ladder),
    )


# ---------------------------------------------------------------- state


def steps_of(session: QuizEngineSession) -> list[Step]:
    return [Step(**s) for s in session.state.get("steps", [])]


def scope_items(items: list[Item], concepts: list[str]) -> list[Item]:
    wanted = set(concepts)
    return [i for i in items if i.concept in wanted]


def max_band(
    db: Session,
    cat: Catalog,
    enrollment: Enrollment,
    concepts: list[str],
    now: int,
    cfg: EngineConfig = DEFAULT,
) -> int:
    """7, or the prerequisite cap while any prerequisite is neither mastered nor assumed."""
    states = learn.states_for(db, enrollment)
    for concept in concepts:
        course = concept.split(":", 1)[0]
        for ref in cat.concept(concept).prerequisites:
            state = states.get(qualify(course, ref))
            if state is None or not (state.mastered(now) or state.assumed):
                return cfg.prerequisite_cap_band
    return 7


def thetas(
    db: Session,
    enrollment: Enrollment,
    patterns: list[str],
    items: list[Item],
    track: Track,
    cfg: EngineConfig = DEFAULT,
) -> tuple[dict[str, float], dict[str, int]]:
    rows = {
        r.pattern: r
        for r in db.scalars(
            select(LearnerAbility).where(
                LearnerAbility.enrollment_id == enrollment.id,
                LearnerAbility.pattern.in_(patterns),
            )
        )
    }
    states = learn.states_for(db, enrollment)
    concept_of = {i.pattern: i.concept for i in items}
    values, counts = {}, {}
    for p in patterns:
        if p in rows:
            values[p], counts[p] = rows[p].theta, rows[p].n
            continue
        state = states.get(concept_of.get(p, p))
        prior = state.mean if state and (state.evidence_count or state.assumed) else None
        values[p], counts[p] = modes.initial_theta(track, prior, cfg), 0
    return values, counts


def exposure(
    db: Session, concepts: list[str], now: int, cfg: EngineConfig = DEFAULT
) -> dict[str, float]:
    """Share of this week's learners on these concepts who saw each item."""
    since = now - cfg.exposure_window_s
    where = (QuizResponse.created_at >= since, QuizResponse.concept.in_(concepts))
    eligible = db.scalar(select(func.count(distinct(QuizResponse.enrollment_id))).where(*where))
    if not eligible or eligible < cfg.exposure_min_learners:
        return {}
    rows = db.execute(
        select(QuizResponse.item_id, func.count(distinct(QuizResponse.enrollment_id)))
        .where(*where)
        .group_by(QuizResponse.item_id)
    )
    return {item_id: n / eligible for item_id, n in rows}


def context(
    db: Session,
    cat: Catalog,
    enrollment: Enrollment,
    session: QuizEngineSession,
    now: int,
    cfg: EngineConfig = DEFAULT,
) -> tuple[Context, list[Item], int]:
    items = scope_items(items_for(db, cat, cfg), session.concepts)
    spec = spec_of(session, cfg)
    patterns = sorted({i.pattern for i in items})
    track = track_of(session)
    values, _ = thetas(db, enrollment, patterns, items, track, cfg)
    ratings = {
        r.item_id: r.d_current
        for r in db.scalars(
            select(ItemRating).where(ItemRating.item_id.in_([i.key for i in items]))
        )
    }
    # Items come back after a while, so a small bank never runs a learner dry.
    seen = frozenset(
        db.scalars(
            select(QuizResponse.item_id).where(
                QuizResponse.enrollment_id == enrollment.id,
                QuizResponse.created_at > now - SEEN_DAYS * 86_400,
            )
        )
    )
    if session.mode != "weekly":  # weekly questions stay out of every other quiz for months
        from socrat.assessments.service import quarantined

        seen = seen | quarantined(db, enrollment, now)
    top = max_band(db, cat, enrollment, session.concepts, now, cfg)
    ctx = Context(
        track=track,
        mode=spec,
        patterns=tuple(patterns),
        language=enrollment.language,
        thetas=values,
        seed=session.id,
        ratings=ratings,
        seen=seen,
        exposure=exposure(db, session.concepts, now, cfg),
        max_band=top,
        micro_shown=bool(session.state.get("micro_shown")),
    )
    if spec.paced:
        # A test-out must reach the hardest band this learner can be served on the concept.
        fit = [
            i
            for i in items
            if i.status != "retired" and (not i.languages or enrollment.language in i.languages)
        ]
        return ctx, items, min(top, max((i.band for i in fit), default=1))
    pool = [i for i in items if i.pool == spec.pool]
    return ctx, items, modes.ceiling(track, pool, top, cfg)


def item_reviewed(cat: Catalog, key: str, cfg: EngineConfig = DEFAULT) -> bool:
    item = next((i for i in bank(cat, cfg) if i.key == key), None)
    return bool(item and item.reviewed)


def advance(
    db: Session,
    cat: Catalog,
    enrollment: Enrollment,
    session: QuizEngineSession,
    now: int,
    cfg: EngineConfig = DEFAULT,
) -> None:
    """Pick the next item, or finish the session with the stop reason."""
    ctx, items, ceiling_band = context(db, cat, enrollment, session, now, cfg)
    choice = engine.next_choice(items, steps_of(session), ctx, ceiling_band, cfg)
    state = dict(session.state)
    if choice.item is None:
        state.update(pending=None, stop=choice.reason)
        session.completed_at = now
        if session.mode == "concept_check" and len(session.concepts) == 1:
            # The adaptive check closes the same plan activity as the fixed one.
            from socrat.learn import quizzes
            from socrat.models import User

            done = [s for s in steps_of(session) if s.outcome != "skipped"]
            score = sum(s.outcome == "correct" for s in done) / len(done) if done else 0.0
            user = db.get(User, enrollment.user_id)
            if user is None:
                raise HTTPException(401, "authentication_required")
            concept = session.concepts[0]
            if done and not any(item_reviewed(cat, s.item, cfg) for s in done):
                # No answer here counted per item (content not yet reviewed), yet the result
                # still decides the plan: one session-level row lets support and stuck
                # detection see a missed check without inflating mastery item by item.
                learn.record_evidence(
                    db,
                    enrollment,
                    concept,
                    "quiz",
                    score,
                    f"adaptive:concept_check:{concept}",
                    now,
                    details={"engine_session": session.id, "unreviewed": True, "items": len(done)},
                )
            state["passed"] = quizzes.settle_check(
                db, user, enrollment, f"quiz:{concept}", score, now
            )
            state["score"] = round(score, 3)
        elif session.mode == "testout":
            state.update(settle_testout(db, cat, enrollment, session, ceiling_band, now, cfg))
    else:
        state["pending"] = dict(
            item=choice.item.key,
            hints=0,
            served_at=now,
            reason=choice.reason,
            micro=choice.micro,
        )
        if choice.micro:
            state["micro_shown"] = True
    session.state = state


def settle_testout(
    db: Session,
    cat: Catalog,
    enrollment: Enrollment,
    session: QuizEngineSession,
    ceiling_band: int,
    now: int,
    cfg: EngineConfig = DEFAULT,
) -> dict:
    """Decide a finished test-out and write its evidence once.

    Passing needs enough answers to mean something (the mode's ``min_items``), at most
    ``max_wrong - 1`` misses, ``testout_pass`` accuracy and ``testout_hard_needed``
    unaided corrects at the hardest band on offer. A concept whose bank is too thin to ask
    ``min_items`` questions cannot be proven here: the learner is sent to a transfer check.
    """
    from socrat.learn import quizzes
    from socrat.models import User

    spec = spec_of(session, cfg)
    done = [s for s in steps_of(session) if s.outcome != "skipped"]
    right = sum(s.outcome == "correct" for s in done)
    wrong = len(done) - right
    hard = sum(1 for s in done if s.independent and s.band >= ceiling_band)
    accuracy = right / len(done) if done else 0.0
    enough = len(done) >= spec.min_items
    strong = (
        bool(done)
        and wrong < (spec.max_wrong or 10**6)
        and accuracy >= cfg.testout_pass
        and hard >= cfg.testout_hard_needed
    )
    passed = strong and enough
    user = db.get(User, enrollment.user_id)
    if user is None:
        raise HTTPException(401, "authentication_required")
    by_key = {i.key: i.concept for i in bank(cat, cfg)}
    per_concept: dict[str, list[bool]] = {}
    for s in done:
        per_concept.setdefault(by_key.get(s.item, session.concepts[0]), []).append(
            s.outcome == "correct"
        )
    activity = session.state.get("activity") or f"testout:{session.concepts[0]}"
    quizzes.settle_testout(db, cat, user, enrollment, activity, per_concept, passed, accuracy, now)
    return dict(
        passed=passed,
        score=round(accuracy, 3),
        hard_band=ceiling_band,
        hard_correct=hard,
        hard_needed=cfg.testout_hard_needed,
        needs_transfer=strong and not enough,
    )


# ---------------------------------------------------------------- actions


def start(
    db: Session,
    cat: Catalog,
    enrollment: Enrollment,
    mode: str,
    concepts: list[str],
    now: int,
    cfg: EngineConfig = DEFAULT,
) -> QuizEngineSession | None:
    """A new session, or None when an assessment mode must fall back to legacy (D3)."""
    if mode not in cfg.modes:
        raise HTTPException(404, "not_found")
    spec = cfg.modes[cast(Mode, mode)]
    concepts = sorted(set(concepts))
    for concept in concepts:
        learn.require_unlocked(db, cat, enrollment, concept, now)
    activity = None
    if mode == "testout":
        if len(concepts) != 1:
            raise HTTPException(422, "one_concept_per_testout")
        activity = f"testout:{concepts[0]}"
        # One attempt: a finished test-out shows its result instead of starting over.
        record = db.get(ActivityRecord, (enrollment.id, activity))
        if record is not None and record.completed_at is not None:
            earlier = next(
                (
                    row
                    for row in db.scalars(
                        select(QuizEngineSession)
                        .where(
                            QuizEngineSession.enrollment_id == enrollment.id,
                            QuizEngineSession.mode == "testout",
                            QuizEngineSession.completed_at.is_not(None),
                        )
                        .order_by(QuizEngineSession.created_at.desc())
                    )
                    if list(row.concepts) == concepts
                ),
                None,
            )
            if earlier is not None:
                return earlier
    if not modes.available(spec, concepts, items_for(db, cat, cfg), cfg):
        return None
    session = QuizEngineSession(
        enrollment_id=enrollment.id,
        mode=mode,
        track=track_for(enrollment),
        concepts=concepts,
        state={"steps": [], "pending": None, **({"activity": activity} if activity else {})},
        created_at=now,
    )
    db.add(session)
    db.flush()
    if activity:
        learn.start_activity(db, enrollment, activity, now)
    advance(db, cat, enrollment, session, now, cfg)
    return session


def owned(db: Session, enrollment: Enrollment, session_id: str) -> QuizEngineSession:
    session = db.get(QuizEngineSession, session_id)
    if session is None or session.enrollment_id != enrollment.id:
        raise HTTPException(404, "not_found")
    return session


def item_by_key(cat: Catalog, key: str, cfg: EngineConfig = DEFAULT) -> Item:
    return next(i for i in bank(cat, cfg) if i.key == key)


def hint(cat: Catalog, session: QuizEngineSession, cfg: EngineConfig = DEFAULT) -> dict:
    pending = session.state.get("pending")
    if session.completed_at is not None or not pending:
        raise HTTPException(409, "quiz_already_completed")
    if not spec_of(session, cfg).hints:
        raise HTTPException(409, "hints_unavailable")
    ladder = render(cat, item_by_key(cat, pending["item"], cfg), session.id, "python")["hints"]
    level = pending["hints"]
    if level >= len(ladder):
        raise HTTPException(409, "no_hint_available")
    session.state = {**session.state, "pending": {**pending, "hints": level + 1}}
    return dict(level=level + 1, hint=ladder[level], remaining=len(ladder) - level - 1)


def answer(
    db: Session,
    cat: Catalog,
    enrollment: Enrollment,
    session: QuizEngineSession,
    item_key: str,
    choice: int | None,
    time_s: int,
    now: int,
    cfg: EngineConfig = DEFAULT,
    confidence: int | None = None,
) -> dict:
    """Grade the pending item (``choice=None`` means "not seen this"), then move on."""
    pending = session.state.get("pending")
    if session.completed_at is not None or not pending:
        raise HTTPException(409, "quiz_already_completed")
    if pending["item"] != item_key:
        raise HTTPException(409, "not_current_item")
    item = effective([item_by_key(cat, item_key, cfg)], approved(db))[0]
    shown = render(cat, item, session.id, enrollment.language)
    if choice is not None and not 0 <= choice < len(shown["options"]):
        raise HTTPException(422, "invalid_choice")
    hints = int(pending["hints"])
    spec = spec_of(session, cfg)
    if pending.get("served_at"):  # the client's clock cannot claim more speed than the server saw
        time_s = min(time_s, max(0, now - int(pending["served_at"])))
    outcome: Outcome
    authored: int | None = None
    if choice is None and spec.paced:
        outcome, tag = "wrong", None  # a test-out has no "not learned yet": that is a miss
    elif choice is None:
        outcome, tag = "skipped", None
    else:
        outcome = "correct" if choice == shown["answer"] else "wrong"
        authored = shown["order"][choice]
        tag = item.misconceptions[authored] if item.misconceptions else None
    ability = db.get(LearnerAbility, (enrollment.id, item.pattern))
    if ability is None:
        values, _ = thetas(db, enrollment, [item.pattern], [item], track_of(session))
        ability = LearnerAbility(
            enrollment_id=enrollment.id, pattern=item.pattern, theta=values[item.pattern], n=0
        )
        db.add(ability)
    rating = db.get(ItemRating, item.key)
    d = rating.d_current if rating else item.d_prior
    top = max_band(db, cat, enrollment, session.concepts, now, cfg)
    step, change = engine.score(
        item,
        outcome,
        hints,
        tag,
        ability.theta,
        d,
        ability.n,
        rating.n_responses if rating else 0,
        top,
        cfg,
    )
    step = replace(step, seconds=max(0, time_s))
    if change is not None:
        ability.theta, ability.n, ability.updated_at = change.theta, ability.n + 1, now
        if item.status != "calibrated":
            if rating is None:
                rating = ItemRating(item_id=item.key, d_current=change.d, n_responses=0)
                db.add(rating)
            rating.d_current, rating.updated_at = change.d, now
            rating.n_responses = (rating.n_responses or 0) + 1
        db.add(
            QuizResponse(
                enrollment_id=enrollment.id,
                item_id=item.key,
                family=item.family,
                pattern=item.pattern,
                concept=item.concept,
                mode=session.mode,
                pool=item.pool,
                session_id=session.id,
                correct=outcome == "correct",
                score=change.score,
                hint_level=hints,
                time_s=max(0, time_s),
                choice=authored,
                confidence=confidence if choice is not None else None,
                created_at=now,
            )
        )
        if spec.evidence and item.reviewed:
            learn.record_evidence(
                db,
                enrollment,
                item.concept,
                spec.evidence,
                1.0 if outcome == "correct" else 0.0,
                f"adaptive:{session.mode}:{item.concept}",
                now,
                assistance=min(hints, 5),
                elapsed_seconds=max(0, time_s),
                details={
                    "item": item.key,
                    "band": item.band,
                    "engine_session": session.id,
                    **({"misconception": tag} if tag else {}),
                },
            )
    session.state = {
        **session.state,
        "steps": [*session.state.get("steps", []), asdict(step)],
        "pending": None,
    }
    advance(db, cat, enrollment, session, now, cfg)
    if spec.paced:  # graded at the end: no answer key mid-test
        return dict(outcome="recorded", answer=None, explanation=None, misconception=None)
    return dict(
        outcome=outcome,
        answer=shown["answer"],
        explanation=shown["explanation"] if outcome != "skipped" else None,
        misconception=tag,
    )


# ---------------------------------------------------------------- views


def view(cat: Catalog, session: QuizEngineSession, language: str, cfg: EngineConfig = DEFAULT):
    spec = spec_of(session, cfg)
    pending = session.state.get("pending")
    current = None
    if pending:
        item = item_by_key(cat, pending["item"], cfg)
        shown = render(cat, item, session.id, language)
        current = dict(
            item=item.key,
            concept=item.concept,
            pattern=item.pattern,
            format=item.format,
            band=item.band,
            prompt=shown["prompt"],
            code=shown["code"],
            options=shown["options"],
            reason=pending.get("reason"),
            hints_used=pending["hints"],
            hints_available=len(shown["hints"]) if spec.hints else 0,
            micro_lesson=(
                {"pattern": pending["micro"], "concept": item.concept} if pending["micro"] else None
            ),
        )
    steps = steps_of(session)
    return dict(
        id=session.id,
        engine="adaptive",
        mode=session.mode,
        track=session.track,
        concepts=session.concepts,
        served=len(steps),
        max_items=spec.max_items,
        current=current,
        finished=session.completed_at is not None,
        stop_reason=session.state.get("stop"),
        score=session.state.get("score"),
        passed=session.state.get("passed"),
        hard_band=session.state.get("hard_band"),
        hard_correct=session.state.get("hard_correct"),
        hard_needed=session.state.get("hard_needed"),
        needs_transfer=session.state.get("needs_transfer"),
        # Per-answer trail once finished, so a reloaded result page can still draw it.
        results=(
            [
                dict(band=s.band, correct=s.outcome == "correct", seconds=s.seconds)
                for s in steps
                if s.outcome != "skipped"
            ]
            if session.completed_at is not None
            else None
        ),
    )


def summary(
    db: Session,
    cat: Catalog,
    enrollment: Enrollment,
    session: QuizEngineSession,
    cfg: EngineConfig = DEFAULT,
) -> dict:
    steps = steps_of(session)
    result = modes.summarise(steps)
    items = scope_items(bank(cat, cfg), session.concepts)
    patterns = sorted({i.pattern for i in items})
    values, counts = thetas(db, enrollment, patterns, items, track_of(session), cfg)
    concept_of = {i.pattern: i.concept for i in items}
    abilities = {
        c: modes.concept_ability({p: values[p] for p in patterns if concept_of[p] == c})
        for c in session.concepts
    }
    return dict(
        id=session.id,
        finished=session.completed_at is not None,
        stop_reason=session.state.get("stop"),
        headline=result.headline,
        evidence=asdict(result),
        patterns=[dict(pattern=p, theta=round(values[p]), answers=counts[p]) for p in patterns],
        concept_ability={c: round(v) if v is not None else None for c, v in abilities.items()},
    )
