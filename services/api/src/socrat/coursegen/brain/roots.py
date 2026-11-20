"""Subject roots: the broad subject every generated course lives under.

Roots are created on demand for whatever a learner asks for; there is no fixed list. A few
common synonyms are folded together in code (``CANONICAL``) so "math", "maths" and
"mathematics" land on one root, and every name a root has been reached by is stored as an alias
so it resolves the same way next time. A duplicate root that slips through is merged by an
admin (``merged_into``); lookups follow the redirect.
"""

import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from socrat.coursegen.brain.spec import normalise
from socrat.models import SubjectAlias, SubjectRoot, now

# Synonyms folded into one root id. Not a list of allowed subjects: any other name becomes a
# root of its own.
CANONICAL = {
    "mathematics": "mathematics",
    "math": "mathematics",
    "maths": "mathematics",
    "algebra": "mathematics",
    "arithmetic": "mathematics",
    "calculus": "mathematics",
    "geometry": "mathematics",
    "trigonometry": "mathematics",
    "probability": "mathematics",
    "statistics": "mathematics",
    "linear algebra": "mathematics",
    "physics": "physics",
    "chemistry": "chemistry",
    "biology": "biology",
    "software": "computer-science",
    "programming": "computer-science",
    "coding": "computer-science",
    "computer science": "computer-science",
    "computing": "computer-science",
    "software engineering": "computer-science",
    "databases": "computer-science",
    "database": "computer-science",
    "data science": "computer-science",
    "machine learning": "computer-science",
    "economics": "economics",
    "music": "music",
    "history": "history",
}
# Intent.domain values that say nothing about the subject: the subject itself is used instead.
VAGUE = {"", "general", "other", "misc", "miscellaneous", "unknown", "learning"}


def alias_of(name: str) -> str:
    """Lowercase, synonyms folded, punctuation collapsed: the key an alias is stored under."""
    return re.sub(r"[^a-z0-9+#]+", " ", normalise(name)).strip()[:120]


def slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", alias_of(name)).strip("-")
    base = re.sub(r"^[^a-z]+", "", base)[:63].strip("-")
    return base or "general"


def name_for(intent: dict) -> str:
    """The broad subject of a request: the intent's domain when it names one, otherwise its
    subject (a request the parser could not place still gets a root of its own)."""
    domain = alias_of(str(intent.get("domain") or ""))
    if domain not in VAGUE:
        return domain
    subject = alias_of(str(intent.get("subject") or ""))
    for words, root in CANONICAL.items():  # "linear equations" -> nothing; "algebra 1" -> maths
        if re.search(rf"\b{re.escape(words)}\b", subject):
            return root
    return subject or "general"


def follow(db: Session, root_id: str) -> SubjectRoot | None:
    seen = set()
    root = db.get(SubjectRoot, root_id)
    while root is not None and root.merged_into and root.id not in seen:
        seen.add(root.id)
        root = db.get(SubjectRoot, root.merged_into)
    return root


def find(db: Session, name: str) -> SubjectRoot | None:
    """The root this name already resolves to, or None. Never writes."""
    key = alias_of(name)
    row = db.get(SubjectAlias, key)
    if row is not None:
        return follow(db, row.root_id)
    return follow(db, CANONICAL.get(key) or slug(key))


def resolve(db: Session, name: str, request_id: str | None = None) -> SubjectRoot:
    """The root for this name, created once if it does not exist yet. Safe under concurrency:
    the primary keys decide, and a loser of the race reads the winner's row."""
    found = find(db, name)
    key = alias_of(name) or "general"
    if found is None:
        root_id = CANONICAL.get(key) or slug(key)
        try:
            with db.begin_nested():
                db.add(
                    SubjectRoot(
                        id=root_id,
                        title=(root_id.replace("-", " ").title())[:120],
                        status="active",
                        created_by=request_id,
                        created_at=now(),
                    )
                )
                db.flush()
        except IntegrityError:
            pass  # another request created it first
        found = follow(db, root_id)
        assert found is not None
    if db.get(SubjectAlias, key) is None:
        try:
            with db.begin_nested():
                db.add(
                    SubjectAlias(alias=key, root_id=found.id, source="request", created_at=now())
                )
                db.flush()
        except IntegrityError:
            pass
    return found


def backfill(db: Session) -> int:
    """Give each learner course made before the brain a root (backlog 3.2), from its request's
    stored intent through the alias tables only (no model). Such a course is never served:
    ``serve = "private"``, except a community course (public), which keeps its sharing and only
    gains the root. Returns how many courses changed. No commit."""
    from socrat.models import GeneratedCourse, LearningRequest

    changed = 0
    rows = db.scalars(
        select(GeneratedCourse).where(
            GeneratedCourse.root_id.is_(None), GeneratedCourse.owner_id.is_not(None)
        )
    )
    for row in list(rows):
        req = db.scalars(
            select(LearningRequest)
            .where(LearningRequest.course_id == row.id)
            .order_by(LearningRequest.created_at)
        ).first()
        if req is None or not req.intent:
            continue
        row.root_id = resolve(db, name_for(req.intent), req.id).id
        if row.visibility != "public":
            row.serve = "private"
        changed += 1
    db.flush()
    return changed
