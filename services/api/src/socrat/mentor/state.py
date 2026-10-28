"""The mentor's saved state and why-log, in ``Enrollment.adaptive["mentor"]`` (no schema change)."""

from socrat.assistant.engine import STYLES
from socrat.mastery.model import DAY
from socrat.mentor import policy
from socrat.mentor.policy import Move

KEY = "mentor"
LOG_LIMIT = 60


def read(adaptive: dict | None) -> dict:
    return dict((adaptive or {}).get(KEY, {}))


def apply(state: dict, move: Move, now: int) -> dict:
    """Make the move and log it. Returns the log entry (with what is needed to undo it)."""
    prev: dict = {}
    if move.kind in {"pace_down", "pace_up", "pace_reset"}:
        feel = dict(state.get("feel", {}))
        prev = {"feel": feel.get(move.concept)}
        if move.value:
            feel[move.concept] = move.value
        else:
            feel.pop(move.concept, None)
        state["feel"] = feel
    elif move.kind == "explain":
        explain = dict(state.get("explain", {}))
        prev = {"explain": explain.get(move.concept)}
        explain[move.concept] = move.value
        state["explain"] = explain
    elif move.kind == "recall":
        recall = list(state.get("recall", []))
        prev = {"recall": list(recall)}
        recall.append(move.concept)
        state["recall"] = recall
    state["locked"] = {
        **state.get("locked", {}),
        f"{move.kind}:{move.concept}": now + policy.COOLDOWN_DAYS * DAY,
    }
    entry = dict(
        id=f"m{now}-{len(state.get('log', []))}",
        at=now,
        kind=move.kind,
        concept=move.concept,
        title=move.title,
        why=move.why,
        auto=True,
        undone=False,
        prev=prev,
    )
    state["log"] = [*state.get("log", []), entry][-LOG_LIMIT:]
    return entry


def undo(state: dict, entry_id: str, now: int) -> dict | None:
    """Reverse one move and keep the mentor from redoing it for a while."""
    log = [dict(e) for e in state.get("log", [])]
    entry = next((e for e in log if e["id"] == entry_id and not e["undone"]), None)
    if entry is None:
        return None
    prev, concept = entry["prev"], entry["concept"]
    if "feel" in prev:
        feel = dict(state.get("feel", {}))
        if prev["feel"]:
            feel[concept] = prev["feel"]
        else:
            feel.pop(concept, None)
        state["feel"] = feel
    if "explain" in prev:
        explain = dict(state.get("explain", {}))
        if prev["explain"] is None:
            explain.pop(concept, None)
        else:
            explain[concept] = prev["explain"]
        state["explain"] = explain
    if "recall" in prev:
        state["recall"] = prev["recall"]
    state["locked"] = {
        **state.get("locked", {}),
        f"{entry['kind']}:{concept}": now + policy.UNDO_LOCK_DAYS * DAY,
    }
    entry["undone"] = True
    state["log"] = log
    return entry


def note(state: dict, concept: str | None, titles: dict[str, str]) -> str:
    """What the tutor is told about this learner's mentor settings (empty when none apply)."""
    lines = []
    if concept and state.get("feel", {}).get(concept) == "hard":
        lines.append("Use smaller steps and one new idea at a time; check before moving on.")
    if concept and state.get("feel", {}).get(concept) == "easy":
        lines.append("This learner is fast here: skip the basics, go deeper, raise the challenge.")
    if concept and state.get("explain", {}).get(concept) is not None:
        style = STYLES[state["explain"][concept] % len(STYLES)]
        lines.append(f"The usual explanation did not land. Explain it this way instead: {style}.")
    recall = [titles.get(c, c) for c in state.get("recall", [])]
    if recall:
        lines.append(f"Open with one short recall question on: {', '.join(recall)}.")
    return " ".join(lines)
