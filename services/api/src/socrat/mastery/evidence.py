"""Evidence in the master prompt's terms (9.2) and a learner-facing stage per competency (9.3).

The mastery estimate (``mastery.model``) stays the one number that moves; this module reads the
same append-only evidence rows and says *what kind* of evidence stands behind it, so the engine
can tell recognising an answer from recalling, applying, transferring, explaining or performing
it, and separate a fresh success from one that held after a delay.

Stages, from evidence only (never from time on page or lesson completion):

- ``unknown``: no scored evidence.
- ``emerging``: some evidence, but the estimate is low or rests on recognition alone.
- ``developing``: application-level evidence, estimate not yet at the mastery bar.
- ``proficient``: at the mastery bar, but not yet shown independently at application level, or
  a full worked solution has not been followed by an unaided success, or nothing has held after
  a delay or in a new context.
- ``demonstrated``: at the mastery bar, an independent application-level success after any full
  solution, and either delayed retention or transfer.

``FULL_SOLUTION`` is the top of the hint ladder (``assistant.prompts.LEVELS``): the learner saw
a complete solution. Anything solved with that much help needs a later independent success
before the competency can be demonstrated (prompt 9.5).
"""

from dataclasses import dataclass, field

from socrat.mastery.model import DAY, ConceptState

FULL_SOLUTION = 5
DELAY = DAY  # a success counts as delayed retention after at least a day since the last one
PASS = 0.7  # a score at or above this is a success for the evidence summary

# Activity kind -> the evidence type it gives when successful.
TYPE = {
    "placement": "recognition",
    "quiz": "recognition",
    "testout": "application",
    "code": "application",
    "checkpoint": "application",
    "verified": "application",
    "external": "application",
    "guided": "application",
    "trace": "application",
    "debug": "application",
    "retrieval": "recall",
    "review": "recall",
    "transfer": "transfer",
    "explanation": "explanation",
    "explain": "explanation",
    "project": "performance",
    "performance": "performance",
    "tutor": "exposure",  # an observation, never a success on its own
}
APPLIED = {"application", "transfer", "performance"}
STAGES = ("unknown", "emerging", "developing", "proficient", "demonstrated")


@dataclass
class Summary:
    stage: str = "unknown"
    by_type: dict[str, int] = field(default_factory=dict)  # successes per evidence type
    independent: int = 0  # successes with no help at all
    assisted: int = 0
    delayed: int = 0  # successes a day or more after the previous success
    needs_follow_up: bool = False  # a full solution not yet followed by an unaided success
    reasons: list[str] = field(default_factory=list)


def summarise(rows: list, state: ConceptState, now: int) -> Summary:
    """``rows`` are Evidence rows (or objects with kind, score, assistance, created_at) for one
    competency, in any order."""
    out = Summary()
    if not rows and not state.evidence_count:
        return out
    last_success = None
    pending_follow_up = False
    for row in sorted(rows, key=lambda r: (r.created_at, getattr(r, "seq", 0))):
        kind = TYPE.get(row.kind, "application")
        success = row.score >= PASS and kind != "exposure"
        if row.assistance >= FULL_SOLUTION:
            pending_follow_up = True
        if not success:
            continue
        out.by_type[kind] = out.by_type.get(kind, 0) + 1
        if row.assistance == 0:
            out.independent += 1
            if kind in APPLIED:
                pending_follow_up = False
        else:
            out.assisted += 1
        if last_success is not None and row.created_at - last_success >= DELAY:
            out.delayed += 1
        last_success = row.created_at
    out.needs_follow_up = pending_follow_up
    applied_alone = any(
        r.score >= PASS and r.assistance == 0 and TYPE.get(r.kind, "application") in APPLIED
        for r in rows
    )
    if state.mastered(now):
        if not applied_alone:
            out.stage, why = "proficient", "Not yet shown without help on a real task."
        elif pending_follow_up:
            out.stage, why = (
                "proficient",
                "Solve one like it without help after the worked solution.",
            )
        elif not (out.delayed or out.by_type.get("transfer")):
            out.stage, why = "proficient", "Not yet shown to last or to work somewhere new."
        else:
            out.stage, why = "demonstrated", "Shown alone, and it held up."
        out.reasons.append(why)
    elif out.by_type.keys() & APPLIED and state.effective(now) >= 0.4:
        out.stage = "developing"
    else:
        out.stage = "emerging"
        if out.by_type and set(out.by_type) <= {"recognition"}:
            out.reasons.append("Only picked from options so far; recall or apply it next.")
    return out


def calibration(pairs: list[tuple[float, bool]]) -> dict | None:
    """Confidence against correctness (prompt 8.1, metacognitive calibration). ``pairs`` are
    (confidence 0-1, correct). Returns the mean confidence, accuracy, their gap (positive means
    over-confident) and a Brier score; None when nothing was rated."""
    if not pairs:
        return None
    n = len(pairs)
    confidence = sum(c for c, _ in pairs) / n
    accuracy = sum(1 for _, ok in pairs if ok) / n
    brier = sum((c - (1.0 if ok else 0.0)) ** 2 for c, ok in pairs) / n
    return dict(
        rated=n,
        confidence=round(confidence, 3),
        accuracy=round(accuracy, 3),
        gap=round(confidence - accuracy, 3),
        brier=round(brier, 3),
    )
