"""How likely a learner is to recall each concept now (item 4 of
docs/research/duolingo-teardown.md), behind ``daily_review_enabled``.

A half-life model in the shape of Settles and Meeder (2016, half-life regression): each
concept has a half-life ``h`` in days, and the chance of recall after ``t`` days without
practice is ``p = 2 ** (-t / h)``. The half-life grows with work done without help, a little
with work done with help, and shrinks with misses:

    log2(h) = BIAS + RIGHT * sqrt(1 + independent)
                   + ASSISTED * (sqrt(1 + assisted) - 1)
                   - WRONG * (sqrt(1 + misses) - 1)

then it is scaled by the learner's own forgetting rate (``adaptive.review_scale_for``).

The weights are hand-set starting values (``MODEL = "hlr-v0"``), chosen so one success holds
about a day and a half, three about five days and six about three weeks. They are not fitted:
fitting them needs logged recall outcomes, which the Daily Review produces.

Inputs are every scored answer, not only mastery evidence: the adaptive quiz writes
evidence only for human-reviewed items, but an answer to an unreviewed item is still practice
the learner did, and a memory estimate that ignored it would keep asking for the same topic.
So adaptive answers come from ``QuizResponse`` and everything else from ``Evidence`` (rows
the adaptive quiz wrote there are skipped, so nothing is counted twice).

This is read-only. It orders the Daily Review and explains it; mastery, the review schedule
and the evidence are unchanged, and nothing here counts as evidence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.models import Enrollment, Evidence, QuizResponse

MODEL = "hlr-v0"
BIAS = -3.66
RIGHT = 3.0
ASSISTED = 1.5
WRONG = 1.5
SUCCESS = 0.7  # the mastery model's own success line
MIN_HALF_LIFE, MAX_HALF_LIFE = 0.25, 180.0  # days
DAY = 86_400
IGNORED = {"tutor"}  # tutor observations only flag gaps; they are not practice


@dataclass(frozen=True)
class Recall:
    concept: str
    independent: int
    assisted: int
    misses: int
    last_at: int
    half_life_days: float

    def chance(self, now: int) -> float:
        days = max(0, now - self.last_at) / DAY
        return 2 ** (-days / self.half_life_days)


def half_life(independent: int, assisted: int, misses: int, scale: float = 1.0) -> float:
    exponent = (
        BIAS
        + RIGHT * math.sqrt(1 + independent)
        + ASSISTED * (math.sqrt(1 + assisted) - 1)
        - WRONG * (math.sqrt(1 + misses) - 1)
    )
    days = 2**exponent * min(1.5, max(0.5, scale))
    return min(MAX_HALF_LIFE, max(MIN_HALF_LIFE, days))


def fold(rows, scale: float = 1.0) -> dict[str, Recall]:
    """Rows with concept, kind, score, assistance and created_at -> one Recall per concept."""
    counts: dict[str, list[int]] = {}
    for row in rows:
        if row.kind in IGNORED:
            continue
        c = counts.setdefault(row.concept, [0, 0, 0, 0])
        if row.score >= SUCCESS:
            c[0 if row.assistance == 0 else 1] += 1
        else:
            c[2] += 1
        c[3] = max(c[3], row.created_at)
    return {
        q: Recall(q, i, a, m, last, half_life(i, a, m, scale))
        for q, (i, a, m, last) in counts.items()
    }


ADAPTIVE = "adaptive:"  # activity ids of evidence the adaptive quiz wrote


def answers(db: Session, enrollment: Enrollment) -> list:
    """Every scored answer for the enrolment, each once, as (concept, kind, score,
    assistance, created_at)."""
    evidence = db.execute(
        select(
            Evidence.concept,
            Evidence.kind,
            Evidence.score,
            Evidence.assistance,
            Evidence.created_at,
        ).where(
            Evidence.enrollment_id == enrollment.id,
            ~Evidence.activity_id.startswith(ADAPTIVE),
        )
    ).all()
    responses = db.execute(
        select(
            QuizResponse.concept,
            QuizResponse.mode,
            QuizResponse.correct,
            QuizResponse.hint_level,
            QuizResponse.created_at,
        ).where(QuizResponse.enrollment_id == enrollment.id)
    ).all()
    return [*evidence, *(_Answer(q, m, 1.0 if ok else 0.0, h, at) for q, m, ok, h, at in responses)]


@dataclass(frozen=True)
class _Answer:
    concept: str
    kind: str
    score: float
    assistance: int
    created_at: int


def for_enrollment(db: Session, enrollment: Enrollment) -> dict[str, Recall]:
    from socrat.adaptive import service as adaptive

    return fold(answers(db, enrollment), adaptive.review_scale_for(db, enrollment))
