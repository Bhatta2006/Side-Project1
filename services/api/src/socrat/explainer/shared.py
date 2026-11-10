"""The shared visual cache: one generation per concept, depth and language, reused by everyone.

A learner pressing "See it" gets the saved visual for free. Only a miss runs the generator, once;
everyone who asks while it runs waits on that same job. The row is the index; this module holds
the rules that need no HTTP, and ``routes`` does the serving.
"""

import hashlib
import json

from sqlalchemy.orm import Session

from socrat.explainer.jobs import ACTIVE
from socrat.models import AssistantMessage, PlaygroundJob, SharedVisual, now

RETIRE_AFTER = 2  # distinct learners who must flag a visual before it stops being served


def prompt_for(concept) -> str:
    """The request the generator receives: built from the lesson, never from learner text."""
    points = "; ".join(concept.key_points[:5])
    return (
        f"Show how {concept.title} works, step by step, with an interactive visual. "
        f"{concept.summary} Key ideas: {points}"
    )[:4000]


PART_CHARS = 1800  # of one lesson page handed to the generator


def parts(lesson: str) -> list[tuple[str, str]]:
    """The lesson's pages as (title, text): one per ``## `` heading, the same split the
    lesson page uses (apps/web/src/lib/pages.ts), so page N here is page N there. Text
    before the first heading belongs to the first page; a heading inside a code fence is
    not a heading."""
    pages: list[tuple[str, list[str]]] = []
    lead: list[str] = []
    fenced = False
    for line in lesson.replace("\r\n", "\n").split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        if not fenced and line.startswith("##") and line[2:3].isspace():
            pages.append((line[2:].strip(), [] if pages else lead))
            lead = []
            continue
        (pages[-1][1] if pages else lead).append(line)
    if not pages:
        return [("", "\n".join(lead).strip())]
    return [(title, "\n".join(lines).strip()) for title, lines in pages]


def key_for(concept_id: str, section: int | None) -> str:
    """The cache key: the lesson, or one page of it."""
    return concept_id if section is None else f"{concept_id}#{section}"


def prompt_for_part(concept, title: str, text: str) -> str:
    """The request for one page of a lesson: built from the lesson's own text, never from
    anything a learner wrote."""
    return (
        f"Show this part of the lesson \u201c{concept.title}\u201d with an interactive visual, "
        f"step by step: {title or concept.title}. Stay on this part only.\n\n"
        f"The part, as the learner reads it:\n{text[:PART_CHARS]}"
    )[:4000]


def fingerprint_part(concept, title: str, text: str) -> str:
    """Changes when this page of the lesson changes."""
    return hashlib.sha256("|".join([concept.title, title, text]).encode()).hexdigest()[:32]


def fingerprint(concept) -> str:
    """Changes whenever the lesson it was made from changes, so a stale visual is rebuilt."""
    text = "|".join([concept.title, concept.summary, concept.lesson, *concept.key_points])
    return hashlib.sha256(text.encode()).hexdigest()[:32]


def settle(db: Session, row: SharedVisual) -> None:
    """Move a generating row on once its job has finished, whoever asks first."""
    if row.status != "generating":
        return
    job = db.get(PlaygroundJob, row.job_id) if row.job_id else None
    if job is not None and job.status == "ready":
        row.status, row.artifact_id, row.updated_at = "ready", job.id, now()
    elif job is None or job.status not in ACTIVE:
        row.status, row.updated_at = "failed", now()


def usable(row: SharedVisual | None, source: str) -> bool:
    return row is not None and row.status == "ready" and row.source_hash == source


def report(db: Session, row: SharedVisual, artifact: AssistantMessage, user_id: str, reason: str):
    """Flags from different learners add up; enough of them stop the visual being served."""
    if user_id not in row.reports:
        row.reports = [*row.reports, user_id]
    db.add(
        AssistantMessage(
            thread_id=artifact.thread_id,
            role="feedback",
            content=json.dumps(dict(artifact_id=artifact.id, reason=reason, reporter=user_id)),
        )
    )
    if len(row.reports) >= RETIRE_AFTER:
        row.status, row.updated_at = "retired", now()
        artifact.rating = -1  # the saved artifact itself stops being readable
