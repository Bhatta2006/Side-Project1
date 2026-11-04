"""Validation reports for generated lessons (master prompt 12).

Every round of a package job ends in a report with one of five states and the concrete findings
behind it, so "why was this not released?" and "what did the checks say about what was?" have
stored, structured answers instead of log lines.

- ``pass``: every deterministic gate passed, no fact claim was wrong or imprecise, the reviewer
  scored every dimension at the bar.
- ``pass_with_warnings``: released, but the fact checker called something imprecise or the
  reviewer left notes; the findings say what.
- ``needs_revision``: a gate failed, a fact was wrong, or the reviewer scored below the bar. The
  job revises; the learner never sees this version.
- ``human_review_required``: released and labelled, because automated checks cannot establish
  correctness for this subject (the domain adapter says verification is limited, the skill needs
  physical practice or an external evaluator, or the request carried safety notes). An LLM
  reviewer passing it is not proof (prompt 12.1). A named person clears it.
- ``rejected``: no version passed in the allowed rounds; nothing is released.

Deterministic code decides the state from the gate results and the checkers' structured replies.
"""

from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.engine.domains import Adapter
from socrat.models import ValidationReport, now

STATUSES = ("pass", "pass_with_warnings", "needs_revision", "human_review_required", "rejected")
RELEASED = {"pass", "pass_with_warnings", "human_review_required"}
LABEL = {
    "pass": "Checked automatically: every check passed.",
    "pass_with_warnings": "Checked automatically, with minor notes.",
    "needs_revision": "Being revised.",
    "human_review_required": (
        "Checked automatically, but this subject needs a person to confirm it. "
        "Treat it as a guide, not as verified."
    ),
    "rejected": "Not released: it did not pass its checks.",
}


@dataclass(frozen=True)
class Finding:
    source: str  # gates | facts | reviewer | domain | safety | human
    severity: str  # blocking | warning | info
    where: str
    problem: str
    fix: str = ""


def _facts(facts: dict | None) -> list[Finding]:
    if facts is None:
        return [Finding("facts", "blocking", "package", "The fact checker gave no usable reply.")]
    out = []
    for claim in facts.get("claims", []):
        if not isinstance(claim, dict) or claim.get("verdict") == "correct":
            continue
        out.append(
            Finding(
                "facts",
                "blocking" if claim.get("verdict") == "incorrect" else "warning",
                str(claim.get("where", "lesson"))[:120],
                str(claim.get("claim", ""))[:500],
                str(claim.get("correction", ""))[:500],
            )
        )
    return out


def _review(review: dict | None, scores: dict, bar: dict[str, int]) -> list[Finding]:
    out = [
        Finding("reviewer", "blocking", dim, f"Scored {scores.get(dim, 0)}, needs {need}.")
        for dim, need in bar.items()
        if scores.get(dim, 0) < need
    ]
    for dim, need in bar.items():  # not blocked, but under target: say so
        goal = 5 if dim == "correctness" else 4
        got = scores.get(dim, 0)
        if need <= got < goal:
            out.append(
                Finding(
                    "reviewer",
                    "warning",
                    dim,
                    f"Scored {got} of 5, target {goal}; released under the current floor.",
                )
            )
    for target in ("lesson", "quiz", "atoms"):
        out += [
            Finding("reviewer", "warning", target, str(n)[:500])
            for n in (review or {}).get(target, [])[:10]
            if n
        ]
    return out


def needs_person(adapter: Adapter, safety_notes: list[str]) -> list[Finding]:
    """Reasons automated checks cannot vouch for this subject on their own."""
    out = []
    if adapter.verifiable != "fully":
        out.append(
            Finding(
                "domain",
                "info",
                adapter.id,
                f"Automated verification for {adapter.name} is {adapter.verifiable}.",
            )
        )
    if adapter.needs_physical_practice or adapter.needs_external_evaluator:
        out.append(
            Finding(
                "domain",
                "info",
                adapter.id,
                "The skill is shown by doing it; a person must judge real performance.",
            )
        )
    out += [Finding("safety", "info", "request", n[:500]) for n in safety_notes]
    return out


def grounding(citations: list[dict]) -> list[Finding]:
    """Citations whose claim shares too little with the cited passage (master prompt 11.4).
    A warning, not a block: overlap of words is evidence of support, not proof against it."""
    return [
        Finding(
            "grounding",
            "warning",
            f"lesson@{c['offset']}",
            f'Citation [{c["n"]}] backs "{c["claim"][:200]}" but its '
            f"{'retrieved passage' if c['basis'] == 'retrieved' else 'summary'} shares little "
            "with it.",
            "Cite a source that states this, or reword the claim to what the source says.",
        )
        for c in citations
        if not c["supported"]
    ][:10]


def with_grounding(status: str, findings: list[Finding], citations: list[dict]):
    """Add grounding warnings to a released state: pass becomes pass_with_warnings."""
    extra = grounding(citations)
    if extra and status == "pass":
        status = "pass_with_warnings"
    return status, [*findings, *extra]


def assess(
    gates: list[str],
    facts: dict | None,
    review: dict | None,
    scores: dict,
    bar: dict[str, int],
    adapter: Adapter,
    safety_notes: list[str],
) -> tuple[str, list[Finding]]:
    """The state of one round. ``gates`` are deterministic gate problems (schema, math, code,
    links); when there are any the checkers were not consulted (facts and review are None)."""
    if gates:
        return "needs_revision", [Finding("gates", "blocking", "package", g[:500]) for g in gates]
    findings = _facts(facts) + _review(review, scores, bar)
    if any(f.severity == "blocking" for f in findings):
        return "needs_revision", findings
    person = needs_person(adapter, safety_notes)
    if person:
        return "human_review_required", findings + person
    return ("pass_with_warnings" if findings else "pass"), findings


def record(
    db: Session,
    course_id: str,
    concept_id: str,
    job_id: str | None,
    round_: int,
    status: str,
    findings: list[Finding],
    reviewer: str | None = None,
) -> ValidationReport:
    if status not in STATUSES:
        raise ValueError(f"unknown validation status {status}")
    row = ValidationReport(
        course_id=course_id,
        concept_id=concept_id,
        job_id=job_id,
        round=round_,
        status=status,
        findings=[asdict(f) for f in findings][:60],
        reviewer=reviewer,
        created_at=now(),
    )
    db.add(row)
    db.flush()
    return row


def latest(db: Session, course_id: str, concept_id: str) -> ValidationReport | None:
    return db.scalars(
        select(ValidationReport)
        .where(ValidationReport.course_id == course_id, ValidationReport.concept_id == concept_id)
        .order_by(ValidationReport.seq.desc())
    ).first()


def view(row: ValidationReport | None) -> dict | None:
    if row is None:
        return None
    return dict(
        status=row.status,
        label=LABEL[row.status],
        reviewer=row.reviewer,
        findings=row.findings,
        at=row.created_at,
    )


def awaiting_person(db: Session) -> list[dict]:
    """Released lessons whose newest report still says a person must confirm them."""
    newest: dict[tuple[str, str], ValidationReport] = {}
    for row in db.scalars(select(ValidationReport).order_by(ValidationReport.seq)):
        newest[(row.course_id, row.concept_id)] = row
    return [
        dict(course_id=c, concept_id=k, **(view(r) or {}))
        for (c, k), r in sorted(newest.items())
        if r.status == "human_review_required"
    ]


def confirm(
    db: Session, course_id: str, concept_id: str, reviewer: str, note: str
) -> ValidationReport:
    """A named person confirms a lesson that automated checks could not vouch for. Appends a
    ``pass`` report carrying their name; the earlier findings stay in the history."""
    current = latest(db, course_id, concept_id)
    if current is None or current.status != "human_review_required":
        raise ValueError("not_awaiting_review")
    finding = Finding("human", "info", "lesson", note[:500] or "Confirmed by a reviewer.")
    return record(db, course_id, concept_id, None, current.round, "pass", [finding], reviewer)
