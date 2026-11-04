"""Weighted Beta-Bernoulli mastery with spaced review.

The estimate is deliberately simple and inspectable: each scored piece of evidence
adds weighted pseudo-observations. Assistance lowers the weight of a success but
never softens a failure, so help cannot manufacture mastery.
"""

import hashlib
import json
import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass, fields, replace
from typing import Literal

DAY = 86_400
EvidenceKind = Literal[
    "placement",
    "quiz",
    "code",
    "checkpoint",
    "review",
    "external",
    "verified",
    "guided",
    "trace",
    "retrieval",
    "debug",
    "explanation",
    "testout",
    "tutor",
    "explain",  # a free-text answer graded by AI against a released rubric
    "project",  # a project milestone graded by AI against the project rubric
    "transfer",
    "performance",  # real work graded by a named person against a rubric (learn.tasks)
]
WEIGHTS: dict[str, float] = {
    "placement": 1.0,
    "quiz": 0.6,
    "code": 1.2,
    "checkpoint": 1.6,
    "review": 1.4,
    "external": 0.4,  # self-reported solve on another site
    "verified": 0.9,  # accepted on Codeforces, confirmed through its public API
    "guided": 0.25,
    "trace": 0.6,
    "retrieval": 0.6,
    "debug": 0.6,
    "explanation": 0.6,
    # A passed test-out is strong, deliberate proof: enough on its own to clear a concept.
    "testout": 8.0,
    # A tutor observation can only flag a gap (score <= 0.5), never manufacture mastery.
    "tutor": 0.15,
    # AI-graded work counts, but less than judged work, moves the estimate in smaller steps,
    # and can never master a concept on its own (``ConceptState.mastered``).
    "explain": 0.4,
    "project": 0.8,
    # Independent solve of a problem never seen before, after naming the technique unaided.
    "transfer": 1.2,
    "performance": 1.0,
}
AI_GRADED = {"explain", "project"}
# Socratic assistance level 0–5 → how much a success still counts.
ASSISTANCE = (1.0, 0.85, 0.7, 0.5, 0.3, 0.1)
REVIEW_DAYS = (1, 3, 7, 14, 30, 60)
MAX_STEP = 0.15
# A learner with a clean independent record may move faster (C5), and a test-out further.
FAST_STEP = 0.25
TESTOUT_STEP = 0.5
TUTOR_MAX_SCORE = 0.5
GRADED_STEP = 0.08  # explain answers
MASTERED = 0.8
MIN_CONFIDENCE = 0.55
PRIOR = 2.0  # alpha + beta of the default prior


# The scoring policy's version (master prompt 9.1, 9.3): a digest of every number above, so any
# change to weights, assistance, spacing or thresholds is a new version without anyone having
# to remember to bump it. Each state records the policy that produced it.
def policy_digest(parts: list) -> str:
    return "beta-" + hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:12]


POLICY_PARTS = [
    WEIGHTS,
    ASSISTANCE,
    REVIEW_DAYS,
    MAX_STEP,
    FAST_STEP,
    TESTOUT_STEP,
    TUTOR_MAX_SCORE,
    GRADED_STEP,
    MASTERED,
    MIN_CONFIDENCE,
    PRIOR,
]
POLICY = policy_digest(POLICY_PARTS)


@dataclass(frozen=True)
class ConceptState:
    alpha: float = 1.0
    beta: float = 1.0
    evidence_count: int = 0
    independent_successes: int = 0
    assisted_successes: int = 0
    failures: int = 0
    review_step: int = 0
    last_evidence_at: int = 0
    next_review_at: int = 0
    assumed: bool = False  # Placed as known; confirmed later by a light review.
    graded: int = 0  # evidence graded by AI (explain, project)
    policy: str = ""  # the scoring policy (POLICY) that last updated this state; "" before it

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def confidence(self) -> float:
        observed = max(0.0, self.alpha + self.beta - PRIOR)
        return min(0.95, 1 - math.exp(-observed / 5))

    def effective(self, now: int) -> float:
        """Mastery discounted when a scheduled review is overdue."""
        if not self.next_review_at or now <= self.next_review_at:
            return self.mean
        overdue_days = (now - self.next_review_at) / DAY
        return self.mean * max(0.7, 1 - 0.01 * overdue_days)

    def mastered(self, now: int) -> bool:
        # At least one judged or placed piece of evidence: AI grades alone never suffice.
        judged = self.evidence_count > self.graded or self.assumed
        return judged and self.effective(now) >= MASTERED and self.confidence >= MIN_CONFIDENCE

    def due(self, now: int) -> bool:
        return bool(self.next_review_at) and now >= self.next_review_at

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict | None) -> "ConceptState":
        if not value:
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in value.items() if k in known})

    @property
    def current(self) -> bool:
        """Whether this state was produced by the scoring policy in force now."""
        return self.policy == POLICY


def placed(known: bool, now: int) -> ConceptState:
    """Placement seeds a prior; it is never treated as verified mastery."""
    if known:
        return ConceptState(
            alpha=4.2, beta=1.0, assumed=True, review_step=1, next_review_at=now + 2 * DAY
        )
    return ConceptState(alpha=1.0, beta=2.0)


def apply(
    state: ConceptState,
    kind: EvidenceKind,
    score: float,
    now: int,
    assistance: int = 0,
    interval_scale: float = 1.0,
) -> ConceptState:
    """Fold one piece of evidence in. ``interval_scale`` stretches or shrinks review spacing
    to the learner's own forgetting rate (see ``socrat.adaptive.profile.review_scale``)."""
    if not 0 <= score <= 1:
        raise ValueError("score must be within [0, 1]")
    if kind == "tutor" and score > TUTOR_MAX_SCORE:
        raise ValueError("tutor observations can only flag gaps")
    if not 0 <= assistance < len(ASSISTANCE):
        raise ValueError("assistance level out of range")
    weight = WEIGHTS[kind] * (ASSISTANCE[assistance] if score >= 0.5 else 1.0)
    alpha = state.alpha + weight * score
    beta = state.beta + weight * (1 - score)
    # Cap one event's influence on the estimate.
    before, after = state.mean, alpha / (alpha + beta)
    cap = step_cap(state, kind, score, assistance)
    if abs(after - before) > cap:
        target = before + math.copysign(cap, after - before)
        total = alpha + beta
        alpha, beta = target * total, (1 - target) * total
    success = score >= 0.7
    independent = success and assistance == 0
    if success:
        step = min(state.review_step + 1, len(REVIEW_DAYS))
    else:
        step = 0
    scale = min(1.5, max(0.5, interval_scale))
    review_at = now + int(REVIEW_DAYS[max(0, step - 1)] * DAY * scale)
    return replace(
        state,
        alpha=alpha,
        beta=beta,
        evidence_count=state.evidence_count + 1,
        independent_successes=state.independent_successes + int(independent),
        assisted_successes=state.assisted_successes + int(success and not independent),
        failures=state.failures + int(not success),
        review_step=step,
        last_evidence_at=now,
        next_review_at=review_at,
        assumed=state.assumed and success,
        graded=state.graded + int(kind in AI_GRADED),
        policy=POLICY,
    )


def replay(
    events: Iterable, start: ConceptState | None = None, interval_scale: float = 1.0
) -> ConceptState:
    """Rebuild a state from append-only evidence (rows or objects with kind, score,
    assistance, created_at), oldest first, under the current policy. ``start`` is the
    placement prior, if any. Tutor observations above the cap are skipped, as ``apply``
    refuses them."""
    state = start or ConceptState()
    for e in sorted(events, key=lambda e: (e.created_at, getattr(e, "seq", 0))):
        if e.kind == "tutor" and e.score > TUTOR_MAX_SCORE:
            continue
        state = apply(state, e.kind, e.score, e.created_at, e.assistance, interval_scale)
    return state


def step_cap(state: ConceptState, kind: str, score: float, assistance: int) -> float:
    if kind == "testout":
        return TESTOUT_STEP
    if kind == "explain":
        return GRADED_STEP
    clean = state.independent_successes >= 2 and state.failures == 0
    if clean and score >= 0.7 and assistance == 0:
        return FAST_STEP
    return MAX_STEP


def band(state: ConceptState, now: int) -> str:
    """Learner-facing wording; never a fake-precise percentage."""
    if state.evidence_count == 0 and not state.assumed:
        return "not_started"
    if state.mastered(now):
        return "strong"
    if state.assumed and state.evidence_count == 0:
        return "likely_known"
    if state.effective(now) >= 0.6:
        return "developing"
    return "needs_practice"
