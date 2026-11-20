"""Keep one learner's private details out of a course other learners are served.

Two guards, both code:

1. ``shared_intent``: a course the brain may share is generated from the request with the
   learner-only parts removed. The Lesson 0 door ("introduce each idea through: <their
   scenario>") and the gaps one onboarding snag suggested belong to that learner's sessions
   (they are in their overlay), not to lessons everyone reads. Their age and deadline likewise.
2. ``leaks``: before a course is marked shareable, and again before it is served, its learner-
   visible text (outline, lessons, quizzes) is compared with what its maker typed and who they
   are. Any 8-word run of their own words, their email, or their full name keeps it private.
"""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.models import (
    GeneratedConcept,
    GeneratedCourse,
    LearningRequest,
    OnboardingDraft,
    User,
)

SHINGLE = 8  # words in a run that counts as copied
# Sentences onboarding.shaped_intent adds that describe one learner, not the course.
LEARNER_ONLY = (
    re.compile(r"Introduce each new idea through this everyday scenario:[^.]*\.\s*"),
    re.compile(r"Patch these gaps early:[^.]*\.\s*"),
)
_WORD = re.compile(r"[a-z0-9']+")


def shared_intent(intent: dict) -> dict:
    """The intent a shareable course is generated from: learner-only parts removed."""
    style = str(intent.get("style_request") or "")
    for pattern in LEARNER_ONLY:
        style = pattern.sub("", style)
    out = dict(intent, style_request=style.strip())
    out.pop("age", None)
    out["deadline"] = None
    out["hours_per_week"] = None
    return out


def _words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def shingles(text: str, n: int = SHINGLE) -> set[tuple[str, ...]]:
    words = _words(text)
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def private_texts(db: Session, course_id: str) -> tuple[list[str], list[str]]:
    """(free text the maker wrote, identifiers of the maker) for the course's requests."""
    row = db.get(GeneratedCourse, course_id)
    if row is None or row.owner_id is None:
        return [], []
    requests = db.scalars(
        select(LearningRequest).where(
            LearningRequest.course_id == course_id, LearningRequest.user_id == row.owner_id
        )
    ).all()
    texts: list[str] = []
    for req in requests:
        texts.extend([req.text, req.material or ""])
        draft = db.scalar(select(OnboardingDraft).where(OnboardingDraft.request_id == req.id))
        if draft is not None:
            texts.append(draft.text)
    ids: list[str] = []
    user = db.get(User, row.owner_id)
    if user is not None:
        email = getattr(user, "email", None)
        if email:
            ids.append(email.lower())
        name = (getattr(user, "display_name", "") or "").strip()
        if len(name.split()) >= 2:  # one first name ("Ada") is too common to be a finding
            ids.append(name.lower())
    return [t for t in texts if t], ids


def course_text(db: Session, course_id: str) -> str:
    """Everything a learner of the course can read, as one string."""
    row = db.get(GeneratedCourse, course_id)
    parts = [str(row.payload) if row else ""]
    for concept in db.scalars(
        select(GeneratedConcept).where(GeneratedConcept.course_id == course_id)
    ):
        parts.append(str(concept.payload))
        if concept.problems:
            parts.append(str(concept.problems))
    return "\n".join(parts)


def leaks(db: Session, course_id: str) -> list[str]:
    """Why this course must stay private, or [] when nothing of its maker shows in it."""
    texts, ids = private_texts(db, course_id)
    if not texts and not ids:
        return []
    visible = course_text(db, course_id)
    lowered = visible.lower()
    found = [f"maker identifier {i!r} appears" for i in ids if i and i in lowered]
    theirs: set[tuple[str, ...]] = set()
    for text in texts:
        theirs |= shingles(text)
    copied = theirs & shingles(visible)
    if copied:
        sample = " ".join(sorted(copied)[0])
        found.append(f"{len(copied)} run(s) of the maker's own words, e.g. {sample!r}")
    return found
