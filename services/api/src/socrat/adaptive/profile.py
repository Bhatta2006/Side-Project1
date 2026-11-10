"""One skill profile per concept, built from every signal Socrat has about the learner.

Mastery stays the Beta-Bernoulli estimate (the only thing that gates progress). The profile
adds what the planner and tutor need to adapt: rating, speed, hint dependence, trend,
recurring mistakes and how the learner's code fails. Pure functions of plain values.
"""

import statistics
from collections import Counter
from dataclasses import asdict, dataclass, field

from socrat.mastery.model import DAY, ConceptState, band

BAND_ORDER = {
    "not_started": 0,
    "needs_practice": 1,
    "developing": 2,
    "likely_known": 2,
    "strong": 3,
}
SCORED = {"quiz", "code", "checkpoint", "review", "testout", "trace", "retrieval", "debug"}
TREND_DAYS = 7
PLATEAU_DAYS = 14
RECALL_TARGET = 0.85
MIN_REVIEWS = 4
# Submission verdict -> how the attempt failed (D4).
FAILURE_MODES = {
    "wrong_answer": "logic",
    "timeout": "performance",
    "memory_limit": "performance",
    "output_limit": "logic",
    "runtime_error": "implementation",
    "compile_error": "syntax",
}


@dataclass(frozen=True)
class EvidenceRow:
    concept: str
    kind: str
    score: float
    assistance: int = 0
    elapsed_seconds: int = 0
    expected_seconds: int = 0
    created_at: int = 0
    misconception: str | None = None
    before_band: str | None = None
    after_band: str | None = None


@dataclass(frozen=True)
class SkillProfile:
    concept: str
    mastery: float
    confidence: float
    band: str
    rating: float | None = None  # mean Elo theta over the concept's patterns
    speed: float | None = None  # median elapsed / expected; >1 is slower than planned
    hint_dependence: float = 0.0  # share of successes that needed help
    attempts: int = 0
    recent_failures: int = 0  # misses among the last five scored attempts
    trend: float | None = None  # mean score this week minus the week before
    plateau: bool = False  # many attempts lately, band has not moved
    first_seen_at: int = 0
    last_seen_at: int = 0
    active_days: int = 0
    misconceptions: dict[str, int] = field(default_factory=dict)  # unresolved, by count
    failure_modes: dict[str, int] = field(default_factory=dict)
    # How the lesson was read (learn/memory.py): counters, never scored.
    simpler_requests: int = 0  # taps on "explain it simpler"
    rereads: int = 0  # came back to a lesson already finished

    def to_dict(self) -> dict:
        return asdict(self)


def build(
    concept: str,
    state: ConceptState,
    rows: list[EvidenceRow],
    now: int,
    rating: float | None = None,
    verdicts: list[str] | None = None,
    reading: dict | None = None,
) -> SkillProfile:
    """``rows`` are this concept's evidence, oldest first; ``verdicts`` its failed submits."""
    scored = [r for r in rows if r.kind in SCORED]
    successes = [r for r in scored if r.score >= 0.7]
    ratios = [
        r.elapsed_seconds / r.expected_seconds
        for r in scored
        if r.elapsed_seconds > 0 and r.expected_seconds > 0
    ]
    week = [r.score for r in scored if r.created_at >= now - TREND_DAYS * DAY]
    before = [
        r.score
        for r in scored
        if now - 2 * TREND_DAYS * DAY <= r.created_at < now - TREND_DAYS * DAY
    ]
    window = [r for r in scored if r.created_at >= now - PLATEAU_DAYS * DAY]
    plateau = False
    if len(window) >= 5 and window[0].before_band and window[-1].after_band:
        start = BAND_ORDER.get(window[0].before_band, 0)
        plateau = BAND_ORDER.get(window[-1].after_band, 0) <= start and not state.mastered(now)
    return SkillProfile(
        concept=concept,
        mastery=round(state.effective(now), 3),
        confidence=round(state.confidence, 3),
        band=band(state, now),
        rating=round(rating, 1) if rating is not None else None,
        speed=round(statistics.median(ratios), 2) if len(ratios) >= 2 else None,
        hint_dependence=round(sum(1 for r in successes if r.assistance > 0) / len(successes), 2)
        if successes
        else 0.0,
        attempts=len(scored),
        recent_failures=sum(1 for r in scored[-5:] if r.score < 0.5),
        trend=round(statistics.mean(week) - statistics.mean(before), 2)
        if week and before
        else None,
        plateau=plateau,
        first_seen_at=rows[0].created_at if rows else 0,
        last_seen_at=rows[-1].created_at if rows else 0,
        active_days=len({r.created_at // DAY for r in rows}),
        misconceptions=unresolved(rows),
        failure_modes=dict(Counter(FAILURE_MODES.get(v, "other") for v in verdicts or [])),
        simpler_requests=int((reading or {}).get("simpler", 0)),
        rereads=int((reading or {}).get("reread", 0)),
    )


def unresolved(rows: list[EvidenceRow]) -> dict[str, int]:
    """Misconceptions missed more recently than they were last answered correctly (A3)."""
    misses: Counter[str] = Counter()
    for row in rows:
        if not row.misconception:
            continue
        if row.score >= 0.7:
            misses.pop(row.misconception, None)
        else:
            misses[row.misconception] += 1
    return dict(misses)


def review_scale(review_scores: list[float]) -> float:
    """The learner's own forgetting rate (A2), as a multiplier on review spacing.

    Recalling more than the target on spaced reviews stretches the gaps; forgetting more
    shrinks them. Too few reviews keeps the default schedule.
    """
    if len(review_scores) < MIN_REVIEWS:
        return 1.0
    recall = sum(1 for s in review_scores if s >= 0.7) / len(review_scores)
    return round(min(1.5, max(0.6, 1 + (recall - RECALL_TARGET) * 2)), 2)


def adherence(minutes_done: int, minutes_planned: int, days_enrolled: int) -> float:
    """How much of the planned study time the learner actually does (E2), 0.25-1.2."""
    if days_enrolled < 7 or minutes_planned <= 0:
        return 1.0
    return round(min(1.2, max(0.25, minutes_done / minutes_planned)), 2)


def level(
    library_rating: int, thetas: list[float], codeforces_rating: int | None
) -> dict[str, float | int | None]:
    """A single practice level from the three rating systems (A1, A5).

    The library rating already folds in solved problems; quiz Elo and a verified
    Codeforces rating pull it toward independent evidence when they exist.
    """
    parts: list[tuple[float, float]] = [(float(library_rating), 1.0)]
    if thetas:
        parts.append((statistics.mean(thetas), 0.5))
    if codeforces_rating:
        parts.append((float(codeforces_rating), 1.0))
    total = sum(w for _, w in parts)
    return dict(
        rating=round(sum(v * w for v, w in parts) / total),
        library=library_rating,
        quiz=round(statistics.mean(thetas)) if thetas else None,
        codeforces=codeforces_rating,
    )
