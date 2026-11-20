"""The learner's own preferences across courses: the write side of the learner memory layer.

Stored on ``users.learner_profile`` (migration ``0052_learner_profile``), read by
``socrat.learner`` as one source among others (docs/implementation/learner-memory.md, section 3).
Shape, ``learner-profile/1``::

    {"schema": "learner-profile/1",
     "prefs":   {key: {"value", "source", "why", "at"}},
     "log":     [{"id", "at", "key", "value", "source", "why", "prev", "undone"}],  # newest last
     "pending": [{"id", "at", "key", "value", "why"}]}  # the tutor's suggestions

Rules: every value is validated against ``WRITABLE``; a weaker source never overwrites a
stronger one (``learner.SOURCES``); every write is logged and can be undone; a model only ever
adds a *pending* suggestion, which changes nothing until the learner accepts it.
Off until ``SOCRAT_LEARNER_PROFILE`` is set: then nothing is stored or served.
"""

import uuid
from collections.abc import Callable

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from socrat.models import User, now

SCHEMA = "learner-profile/1"
LOG_LIMIT = 60
PENDING_LIMIT = 5
WHY_CHARS = 200
WRITERS = ("learner", "mentor", "observed", "onboarding")  # "default" is never stored


def _one_of(*values: str) -> Callable[[object], bool]:
    return lambda v: v in values


def _text(limit: int) -> Callable[[object], bool]:
    return lambda v: isinstance(v, str) and 0 < len(v.strip()) <= limit


# Preferences about the person. Keys owned by another store (strictness: users.learning_mode,
# minutes: the enrollment) are not writable here, so there is one place for each fact.
WRITABLE: dict[str, Callable[[object], bool]] = {
    "analogy_domain": _text(80),
    "tone": _one_of("direct", "direct_and_encouraging", "curious_and_thorough"),
    "explanation_length": _one_of("short_3_sentences", "medium_one_page", "long_worked_examples"),
    "friction_limit": lambda v: isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 6,
    "pace": _one_of("fast", "medium", "slow"),
    "course_mode": _one_of("sprint", "builder", "explorer"),
}


def profile(user: User) -> dict:
    data = dict(user.learner_profile or {})
    data.setdefault("schema", SCHEMA)
    return data


def stored(user: User) -> dict[str, dict]:
    """Key -> {value, source, why, at}: what ``socrat.learner`` offers as preferences."""
    return {k: v for k, v in (profile(user).get("prefs") or {}).items() if k in WRITABLE}


def check(key: str, value: object) -> None:
    if key not in WRITABLE:
        raise ValueError(f"not a writable preference: {key!r}")
    if not WRITABLE[key](value):
        raise ValueError(f"invalid value for {key}")
    if isinstance(value, str) and ("<" in value or ">" in value):
        raise ValueError(f"invalid value for {key}")


def _rank(source: str) -> int:
    from socrat.learner import SOURCES

    return SOURCES.index(source)


def set_pref(
    user: User, key: str, value: object, source: str, why: str, at: int | None = None
) -> dict | None:
    """Store one preference. Returns the log entry, or None when a stronger source already set
    it (the learner's own choice is never overwritten by the mentor, behaviour or onboarding).
    Raises ValueError for an unknown key, a bad value or an unknown source."""
    if source not in WRITERS:
        raise ValueError(f"unknown source {source!r}")
    check(key, value)
    at = now() if at is None else at
    data = profile(user)
    prefs = dict(data.get("prefs") or {})
    current = prefs.get(key)
    if current and _rank(current["source"]) < _rank(source):
        return None
    log = list(data.get("log") or [])
    entry = dict(
        id="p" + uuid.uuid4().hex[:12],
        at=at,
        key=key,
        value=value,
        source=source,
        why=str(why)[:WHY_CHARS],
        prev=current,
        undone=False,
    )
    prefs[key] = dict(value=value, source=source, why=entry["why"], at=at)
    data.update(prefs=prefs, log=[*log, entry][-LOG_LIMIT:])
    user.learner_profile = data  # reassigned so the JSON column is written
    return entry


def undo(user: User, entry_id: str) -> dict | None:
    """Put a preference back to what it was before one write. None if there is no such write,
    it was undone already, or a later write to the same key stands on top of it."""
    data = profile(user)
    log = [dict(e) for e in data.get("log") or []]
    index = next((i for i, e in enumerate(log) if e["id"] == entry_id), None)
    if index is None or log[index]["undone"]:
        return None
    entry = log[index]
    if any(e["key"] == entry["key"] and not e["undone"] for e in log[index + 1 :]):
        return None
    prefs = dict(data.get("prefs") or {})
    if entry["prev"]:
        prefs[entry["key"]] = entry["prev"]
    else:
        prefs.pop(entry["key"], None)
    entry["undone"] = True
    data.update(prefs=prefs, log=log)
    user.learner_profile = data
    return entry


def suggest(user: User, key: str, value: object, why: str, at: int | None = None) -> dict:
    """A model's suggestion: stored as pending, applies nothing. One per key (the newest
    replaces an older one), at most ``PENDING_LIMIT``. Raises ValueError like ``set_pref``."""
    check(key, value)
    at = now() if at is None else at
    data = profile(user)
    pending = [p for p in data.get("pending") or [] if p["key"] != key]
    item = dict(
        id="s" + uuid.uuid4().hex[:12], at=at, key=key, value=value, why=str(why)[:WHY_CHARS]
    )
    data["pending"] = [*pending, item][-PENDING_LIMIT:]
    user.learner_profile = data
    return item


def decide(user: User, suggestion_id: str, accept: bool, at: int | None = None) -> dict | None:
    """The learner accepts (stored with source ``learner``) or declines a suggestion."""
    data = profile(user)
    pending = list(data.get("pending") or [])
    item = next((p for p in pending if p["id"] == suggestion_id), None)
    if item is None:
        return None
    data["pending"] = [p for p in pending if p["id"] != suggestion_id]
    user.learner_profile = data
    if not accept:
        return dict(item, accepted=False)
    entry = set_pref(user, item["key"], item["value"], "learner", f"Accepted: {item['why']}", at)
    return dict(item, accepted=True, entry=entry["id"] if entry else None)


def seed_from_lesson0(user: User, lesson0: dict | None, at: int | None = None) -> list[dict]:
    """Store what Lesson 0 suggested (``onboarding-handoff.md`` 3.2) as ``onboarding``
    preferences. Never overwrites anything stronger; a later Lesson 0 replaces an earlier one."""
    from socrat.learner import ONBOARDING

    entries = []
    for (section, name), key in ONBOARDING.items():
        value = ((lesson0 or {}).get(section) or {}).get(name)
        if key not in WRITABLE or value in (None, ""):
            continue
        try:
            entry = set_pref(user, key, value, "onboarding", "From your first lesson.", at)
        except ValueError:
            continue  # a value outside the allowed set is not stored, never half-used
        if entry:
            entries.append(entry)
    return entries


# ---------------------------------------------------------------- routes

router = APIRouter(prefix="/api/v1/learner")


class Value(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str | int


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accept: bool


def _enabled(request: Request) -> None:
    if not request.app.state.settings.learner_profile:
        raise HTTPException(404, "not_found")


def view(db: Session, user: User) -> dict:
    """What the learner sees: preferences in force (with who set them), the tutor's pending
    suggestions and the history they can undo. Never the stored ``prev`` values."""
    from socrat import learner
    from socrat.learn import service as learn

    enrollment = learn.active_enrollment(db, user.id)
    if enrollment is not None and enrollment.status == "active":
        resolved = learner.snapshot(db, enrollment, now(), user=user).prefs
        prefs = {k: dict(value=p.value, source=p.source) for k, p in resolved.items()}
    else:
        brief = learner.user_brief(db, user.id, now())
        prefs = {k: dict(value=v) for k, v in brief.get("delivery", {}).items()}
    data = profile(user)
    history = [
        {k: e[k] for k in ("id", "at", "key", "value", "source", "why", "undone")}
        for e in reversed(data.get("log") or [])
    ]
    return dict(prefs=prefs, pending=data.get("pending") or [], history=history)


@router.get("/profile")
def read(request: Request):
    from socrat.learn.routes import engine, user_of

    _enabled(request)
    with Session(engine(request)) as db:
        return view(db, user_of(request, db))


@router.put("/profile/{key}")
def choose(key: str, body: Value, request: Request):
    from socrat.learn.routes import engine, user_of

    _enabled(request)
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        try:
            set_pref(user, key, body.value, "learner", "You chose this.")
        except ValueError as exc:
            raise HTTPException(422, "invalid_preference") from exc
        return view(db, user)


@router.post("/profile/undo/{entry_id}")
def take_back(entry_id: str, request: Request):
    from socrat.learn.routes import engine, user_of

    _enabled(request)
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        if undo(user, entry_id) is None:
            raise HTTPException(409, "cannot_undo")
        return view(db, user)


@router.post("/profile/suggestions/{suggestion_id}")
def answer(suggestion_id: str, body: Decision, request: Request):
    from socrat.learn.routes import engine, user_of

    _enabled(request)
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        if decide(user, suggestion_id, body.accept) is None:
            raise HTTPException(404, "not_found")
        return view(db, user)
