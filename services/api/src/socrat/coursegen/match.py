"""Match before build: does a course this learner may take already fit what they asked for?

Only courses the learner is allowed to see are ever compared: their own, and courses another
learner agreed to share with everyone (public, in good standing, with at least one released
lesson). A private course is never matched, so a match reveals nothing that the course list
does not already show. The comparison is code over two validated intents (the asker's and the
one the course was made from); no model is called. Off unless ``request_matching``.
"""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.coursegen.search import content_words
from socrat.models import Enrollment, GeneratedCourse, LearningRequest

MOST = 3  # matches shown
# Words about where a learner starts, not what the subject is ("algebra from zero").
FILLER = {"zero", "scratch", "fundamental", "essential"}
CHILD = {"little-kid", "kid", "teen"}  # registers that must match exactly
REGISTER_WORDS = {
    "little-kid": "a young child",
    "kid": "a child",
    "teen": "a teenager",
    "general": "a general reader",
    "university": "a university student",
    "professional": "a working professional",
}


def _stem(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def subject_key(subject: str) -> frozenset[str] | str:
    """What a subject is about, without filler words, order or plurals: "Introduction to
    fractions" and "fractions basics" are the same subject. A subject made only of short or
    filler words ("C", "Go") is compared as written."""
    words = frozenset(_stem(w) for w in content_words(subject)) - FILLER
    return words or re.sub(r"[^a-z0-9+#]+", " ", subject.lower()).strip()


def fit(wanted: dict, theirs: dict) -> tuple[str, list[str]] | None:
    """("exact" | "close", the differences in plain words), or None when the course is not
    this subject, not this language, or written for a different age of child."""
    if subject_key(str(wanted.get("subject", ""))) != subject_key(str(theirs.get("subject", ""))):
        return None
    if (wanted.get("language") or "en") != (theirs.get("language") or "en"):
        return None
    mine, other = wanted.get("register", "general"), theirs.get("register", "general")
    if mine != other and (mine in CHILD or other in CHILD):
        return None  # a child is never offered an adult's course, or the other way round
    differences = []
    if mine != other:
        differences.append(
            f"Written for {REGISTER_WORDS.get(other, other)}; "
            f"you asked as {REGISTER_WORDS.get(mine, mine)}."
        )
    level, their_level = wanted.get("desired_level"), theirs.get("desired_level")
    if level != their_level and their_level:
        differences.append(f"Goes to {their_level} level; you asked for {level}.")
    style = str(wanted.get("style_request") or "").strip().lower()
    if style and style != str(theirs.get("style_request") or "").strip().lower():
        differences.append("Taught in its own style, not the one you described.")
    return ("close" if differences else "exact"), differences


def find(db: Session, cat: Catalog, user_id: str, wanted: dict) -> list[dict]:
    """The courses that fit, best first: exact before close, the learner's own before others',
    then the ones with more lessons ready."""
    rows = db.scalars(
        select(GeneratedCourse).where(
            GeneratedCourse.owner_id.is_not(None),
            GeneratedCourse.status == "published",
            GeneratedCourse.moderation == "ok",
            (GeneratedCourse.visibility == "public") | (GeneratedCourse.owner_id == user_id),
        )
    ).all()
    found: list[dict] = []
    for row in rows:
        course = cat.courses.get(row.id)
        if course is None:
            continue
        ready = sum(c.status == "live" for c in course.concepts)
        if not ready:
            continue  # nothing released yet: there is nothing to start
        made = db.scalars(
            select(LearningRequest)
            .where(
                LearningRequest.course_id == row.id,
                LearningRequest.user_id == row.owner_id,
                LearningRequest.status == "confirmed",
            )
            .limit(1)
        ).first()
        if made is None:
            continue
        result = fit(wanted, made.intent)
        if result is None:
            continue
        enrolled = db.scalar(
            select(Enrollment.id)
            .where(Enrollment.user_id == user_id, Enrollment.course_id == row.id)
            .limit(1)
        )
        found.append(
            dict(
                course=row.id,
                title=course.title,
                tagline=course.tagline,
                fit=result[0],
                differences=result[1],
                lessons=len(course.concepts),
                ready=ready,
                mine=row.owner_id == user_id,
                by=row.credit_name if row.visibility == "public" else None,
                enrolled=enrolled is not None,
            )
        )
    found.sort(key=lambda m: (m["fit"] != "exact", not m["mine"], -m["ready"], m["course"]))
    return found[:MOST]
