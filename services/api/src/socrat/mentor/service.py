"""Run the mentor for an enrollment and keep the learner able to see and undo what it did."""

from sqlalchemy.orm import Session

from socrat.adaptive import service as adaptive
from socrat.catalog.registry import Catalog
from socrat.learn import service as learn
from socrat.mentor import policy
from socrat.mentor import state as saved
from socrat.models import Enrollment, User

PACE_KINDS = {"pace_down", "pace_up", "pace_reset"}


def view(enrollment: Enrollment) -> dict:
    """What the learner sees: the newest moves first, with their reasons."""
    state = saved.read(enrollment.adaptive)
    log = [
        {k: e[k] for k in ("id", "at", "kind", "concept", "title", "why", "undone")}
        for e in reversed(state.get("log", []))
    ]
    return dict(log=log, recall=state.get("recall", []))


def refresh(
    db: Session, catalog: Catalog, user: User, enrollment: Enrollment, now: int
) -> list[dict]:
    """Decide and apply new moves. Only changes how things are taught, never what (see policy)."""
    states = learn.states_for(db, enrollment)
    skill = adaptive.build_profiles(db, catalog, enrollment, states, now)
    stuck = adaptive.stuck_map(skill, now)
    data = dict(enrollment.adaptive or {})
    state = saved.read(data)
    # A recall warm-up is done once the learner has worked on the concept again.
    last = {e["concept"]: e["at"] for e in state.get("log", []) if e["kind"] == "recall"}
    state["recall"] = [
        c
        for c in state.get("recall", [])
        if c in skill and skill[c].last_seen_at <= last.get(c, 0) and skill[c].mastery < 0.6
    ]
    titles = {c: catalog.concept(c).title for c in skill}
    learner_feel = dict(data.get("overrides", {}).get("feel", {}))
    moves = policy.decide(skill, stuck, state, titles, now, learner_feel)
    entries = [saved.apply(state, move, now) for move in moves]
    state["last_run"] = now
    data[saved.KEY] = state
    enrollment.adaptive = data
    paced = [m for m in moves if m.kind in PACE_KINDS]
    if paced:
        learn.revise(db, catalog, user, enrollment, now, paced[0].why)
    return entries


def undo(
    db: Session, catalog: Catalog, user: User, enrollment: Enrollment, entry_id: str, now: int
) -> dict | None:
    data = dict(enrollment.adaptive or {})
    state = saved.read(data)
    entry = saved.undo(state, entry_id, now)
    if entry is None:
        return None
    data[saved.KEY] = state
    enrollment.adaptive = data
    if entry["kind"] in PACE_KINDS:
        learn.revise(db, catalog, user, enrollment, now, f"You undid: {entry['title']}.")
    return entry


def tutor_note(enrollment: Enrollment | None, catalog: Catalog, scope: str) -> str:
    """The mentor's standing instructions for the tutor on this screen."""
    if enrollment is None:
        return ""
    state = saved.read(enrollment.adaptive)
    if not state:
        return ""
    concept = scope.removeprefix("concept:") if scope.startswith("concept:") else None
    titles = {c: catalog.concept(c).title for c in state.get("recall", []) if c in catalog.concepts}
    return saved.note(state, concept, titles)
