"""Learning outcomes (master prompt 16.2), measured from the append-only evidence.

Everything here is **observational**: it describes what learners did, it does not show that a
feature caused it. Causal claims need a controlled experiment with outcome measures, sample size
and analysis fixed in advance; ``experiment_note`` says so in every report. Time spent, streaks
and message counts are deliberately absent.
"""

from collections import defaultdict
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.mastery.evidence import APPLIED, PASS, TYPE
from socrat.models import (
    Diagnostic,
    Enrollment,
    Evidence,
    LearningRequest,
    QuizResponse,
    QuizSession,
)

DAY = 86_400


def _rate(rows: list) -> float | None:
    return round(sum(r.score >= PASS for r in rows) / len(rows), 3) if rows else None


def report(db: Session, course_id: str | None = None) -> dict:
    enrollments = select(Enrollment.id)
    if course_id:
        enrollments = enrollments.where(Enrollment.course_id == course_id)
    ids = set(db.scalars(enrollments))
    rows = [
        r
        for r in db.scalars(select(Evidence).order_by(Evidence.created_at, Evidence.seq))
        if r.enrollment_id in ids
    ]
    scored = [r for r in rows if TYPE.get(r.kind) != "exposure"]
    independent = [r for r in scored if r.assistance == 0]
    assisted = [r for r in scored if r.assistance > 0]
    reviews = [r for r in scored if r.kind in ("review", "retrieval")]
    transfer = [r for r in scored if r.kind == "transfer"]
    immediate = [r for r in scored if r.kind == "quiz"]

    # Hint dependence over time: mean help level in each learner's first and second half.
    by_learner: dict[str, list] = defaultdict(list)
    for r in scored:
        by_learner[r.enrollment_id].append(r)
    early, late = [], []
    for seq in by_learner.values():
        if len(seq) >= 4:
            half = len(seq) // 2
            early += [r.assistance for r in seq[:half]]
            late += [r.assistance for r in seq[half:]]

    # Misconceptions: share of answers tagged with one, early versus late.
    tagged_early = [
        bool((r.details or {}).get("misconception"))
        for s in by_learner.values()
        for r in s[: len(s) // 2]
    ]
    tagged_late = [
        bool((r.details or {}).get("misconception"))
        for s in by_learner.values()
        for r in s[len(s) // 2 :]
    ]

    # Time to a first unaided, applied success on a concept, from the first evidence on it.
    first: dict[tuple[str, str], int] = {}
    reached: dict[tuple[str, str], int] = {}
    for r in scored:
        key = (r.enrollment_id, r.concept)
        first.setdefault(key, r.created_at)
        if (
            key not in reached
            and r.assistance == 0
            and r.score >= PASS
            and TYPE.get(r.kind) in APPLIED
        ):
            reached[key] = r.created_at
    days = [(reached[k] - first[k]) / DAY for k in reached]

    # Baseline: diagnostics taken for learner-made courses.
    diagnostics = [d.result for d in db.scalars(select(Diagnostic)) if d.result]
    if course_id:
        requests = set(
            db.scalars(select(LearningRequest.id).where(LearningRequest.course_id == course_id))
        )
        diagnostics = [
            d.result
            for d in db.scalars(select(Diagnostic))
            if d.result and d.request_id in requests
        ]

    # Calibration from rated answers in these enrolments.
    pairs = [
        ((int(a["confidence"]) - 1) / 3, bool(a["correct"]))
        for s in db.scalars(select(QuizSession).where(QuizSession.enrollment_id.in_(ids or {""})))
        for a in (s.answers or {}).values()
        if isinstance(a, dict) and a.get("confidence") is not None
    ] + [
        ((int(c or 1) - 1) / 3, bool(ok))
        for c, ok in db.execute(
            select(QuizResponse.confidence, QuizResponse.correct).where(
                QuizResponse.enrollment_id.in_(ids or {""}), QuizResponse.confidence.is_not(None)
            )
        )
    ]
    from socrat.mastery.evidence import calibration

    return dict(
        course=course_id,
        learners=len(by_learner),
        evidence_rows=len(scored),
        baseline_diagnostic=dict(
            taken=len(diagnostics),
            mean_correct=round(
                sum(d.get("correct", 0) / max(1, d.get("total", 1)) for d in diagnostics)
                / len(diagnostics),
                3,
            )
            if diagnostics
            else None,
        ),
        immediate_check_success=_rate(immediate),
        independent_success=_rate(independent),
        assisted_success=_rate(assisted),
        delayed_retention=_rate(reviews),
        transfer_success=_rate(transfer),
        hint_level_early=round(sum(early) / len(early), 3) if early else None,
        hint_level_late=round(sum(late) / len(late), 3) if late else None,
        misconception_share_early=round(sum(tagged_early) / len(tagged_early), 3)
        if tagged_early
        else None,
        misconception_share_late=round(sum(tagged_late) / len(tagged_late), 3)
        if tagged_late
        else None,
        days_to_unaided_application=dict(
            concepts=len(days), median=round(median(days), 2) if days else None
        ),
        calibration=calibration(pairs),
        experiment_note=(
            "Observational: these numbers describe learners, they do not show that a feature "
            "caused a change. Use a controlled experiment with pre-registered measures for that."
        ),
    )
