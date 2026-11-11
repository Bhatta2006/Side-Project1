"""How far along each lesson being written is, told to the learner (Today and the skill map).

Read from the job's own log, so it is the real step, not a timer: finding sources, writing,
checking facts and teaching, improving it after a check, and so on. A lesson that failed its
gates says so, and whether it is being written again (``jobs.retry_once``) or waits for the
course team, so nobody watches a loader that will never finish.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.models import GenerationJob

# A lesson takes about this long end to end with the current models (7 to 8 minutes measured
# on the live model in November 2026); only used to say roughly how long is left.
TYPICAL_SECONDS = 420
WRITE_AT = 0.3  # the first draft is written; the checks and revisions share the rest
CHECKS_SHARE = 0.6
CAP = 0.95  # never "done" before the lesson is actually released


def _round_pct(round_: int, rounds: int, checking: bool) -> float:
    """Round ``round_`` of ``rounds``: its check sits half way through its share, its
    revision at the end of it."""
    step = (2 * round_ - 1) if checking else (2 * round_)
    return WRITE_AT + CHECKS_SHARE * step / (2 * max(rounds, 1))


def of_job(job: GenerationJob | None, rounds: int, now: int) -> dict:
    """One lesson's progress: ``state`` is later, scheduled, queued, writing or stuck;
    ``progress`` is 0..1; ``label`` is what the learner reads."""
    if job is None:
        return dict(state="later", progress=0.0, label="Written when you get closer")
    retry = bool((job.input or {}).get("retry_of"))
    again = "Second try: " if retry else ""
    if job.state == "queued":
        if job.not_before and job.not_before > now:
            return dict(
                state="scheduled",
                progress=0.0,
                label="Scheduled",
                at=job.not_before,
            )
        return dict(state="queued", progress=0.02, label=f"{again}waiting its turn".capitalize())
    if job.state in ("failed", "dead", "cancelled"):
        return dict(
            state="stuck",
            progress=0.0,
            label="Didn't pass its checks yet; the course team has been told",
        )
    if job.state == "done":
        return dict(state="writing", progress=CAP, label="Finishing up")
    # Running: the last step in its log says where it is.
    label, pct = "Starting", 0.04
    for entry in job.log or []:
        role, event = entry.get("role"), entry.get("event")
        round_ = int(entry.get("round") or 1)
        if role == "search":
            label, pct = "Finding sources", 0.08
        elif role == "researcher":
            label, pct = "Reading the sources", 0.16
        elif role == "author":
            if round_ <= 1:
                label, pct = "Writing the lesson", WRITE_AT
            else:
                label, pct = "Improving it", _round_pct(round_ - 1, rounds, False)
        elif event == "validating":
            label = "Checking facts and teaching" if round_ <= 1 else "Checking it again"
            pct = _round_pct(round_, rounds, True)
        elif event == "revising":
            label, pct = "Improving it", _round_pct(round_, rounds, False)
        elif event == "polishing":
            label, pct = "Polishing", max(pct, 0.85)
    pct = min(CAP, pct)
    started = job.created_at or now
    left = max(30, int(TYPICAL_SECONDS * (1 - pct)))
    return dict(
        state="writing",
        progress=round(pct, 3),
        label=f"{again}{label[0].lower()}{label[1:]}" if retry else label,
        started_at=started,
        eta_seconds=left,
    )


def for_course(db: Session, course, rounds: int, now: int) -> list[dict]:
    """Every lesson of ``course`` that is not live yet, in course order, with its progress."""
    latest: dict[str, GenerationJob] = {}
    for job in db.scalars(
        select(GenerationJob)
        .where(GenerationJob.course_id == course.id, GenerationJob.kind == "package")
        .order_by(GenerationJob.created_at)
    ):
        latest[job.target] = job  # the newest job per concept wins
    by_id = {c.id: c for c in course.concepts}
    out: list[dict] = []
    for module in course.modules:
        for cid in module.concepts:
            concept = by_id.get(cid)
            if concept is None or concept.status == "live":
                continue
            out.append(
                dict(
                    concept=f"{course.id}:{cid}",
                    title=concept.title,
                    module=module.id,
                    **of_job(latest.get(cid), rounds, now),
                )
            )
    return out
