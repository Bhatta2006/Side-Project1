"""What the mentor may do on its own, and why. Rules decide; no model is involved.

Bounds (the "auto within bounds" decision): the mentor only changes *how* a concept is taught
(pace, explanation style, a recall warm-up). It never drops topics, changes the goal or the
course shape; those stay proposals the learner accepts (see ``adaptive.proposals``). Every move
carries a plain-words reason, is undoable, and is rate-limited per concept.
"""

from dataclasses import dataclass

from socrat.adaptive.profile import SkillProfile
from socrat.adaptive.stuck import Stuck
from socrat.assistant.engine import STYLES
from socrat.mastery.model import DAY

MAX_MOVES = 3  # new moves per run
COOLDOWN_DAYS = 3  # per concept and kind, after a move or an undo
UNDO_LOCK_DAYS = 14
RECALL_AFTER_DAYS = 10
RECALL_BELOW = 0.6
MIN_ATTEMPTS = 3
MAX_RECALL = 3
EXPLAIN_FROM = 2  # stuck severity that earns a new way of explaining


@dataclass(frozen=True)
class Move:
    kind: str  # pace_down | pace_up | pace_reset | explain | recall
    concept: str
    title: str
    why: str
    value: str | int | None = None


def _locked(state: dict, kind: str, concept: str, now: int) -> bool:
    return state.get("locked", {}).get(f"{kind}:{concept}", 0) > now


def _pace(p: SkillProfile, name: str, current: str | None, state: dict, now: int) -> Move | None:
    concept = p.concept
    hard = p.recent_failures >= 3 or (p.hint_dependence >= 0.6 and p.band != "strong")
    easy = (
        p.band in {"strong", "likely_known"}
        and p.hint_dependence == 0
        and p.recent_failures == 0
        and p.speed is not None
        and p.speed <= 0.8
        and (p.trend is None or p.trend >= 0)
    )
    if hard and current != "hard" and not _locked(state, "pace_down", concept, now):
        cause = (
            "Several recent attempts missed"
            if p.recent_failures >= 3
            else "Most of your successes needed hints"
        )
        return Move(
            "pace_down",
            concept,
            f"Smaller steps on {name}",
            f"{cause}, so {name} now goes in smaller steps.",
            "hard",
        )
    if easy and current != "easy" and not _locked(state, "pace_up", concept, now):
        why = f"You are quick and accurate on {name} without hints, so it moves faster."
        return Move("pace_up", concept, f"Faster through {name}", why, "easy")
    if current and not hard and not easy and not _locked(state, "pace_reset", concept, now):
        why = f"Your results on {name} are steady again, so the extra support or speed is removed."
        return Move("pace_reset", concept, f"Back to the normal pace on {name}", why, None)
    return None


def decide(
    skill: dict[str, SkillProfile],
    stuck: dict[str, Stuck],
    state: dict,
    titles: dict[str, str],
    now: int,
    learner_feel: dict[str, str] | None = None,
) -> list[Move]:
    """New moves for this moment, most useful first, never more than ``MAX_MOVES``.
    ``learner_feel`` is what the learner said themselves: it always wins."""
    learner_feel = learner_feel or {}
    feel = state.get("feel", {})
    explained = state.get("explain", {})
    moves: list[Move] = []
    for concept, p in sorted(skill.items()):
        name = titles.get(concept, concept)
        if concept in learner_feel or p.attempts < MIN_ATTEMPTS:
            continue
        pace = _pace(p, name, feel.get(concept), state, now)
        if pace is not None:
            moves.append(pace)
        s = stuck.get(concept)
        if (
            s is not None
            and s.severity >= EXPLAIN_FROM
            and not _locked(state, "explain", concept, now)
        ):
            nxt = (explained.get(concept, -1) + 1) % len(STYLES)
            how = STYLES[nxt].split(",")[0]
            why = f"{s.summary} Soc will explain {name} another way: {how}."
            moves.append(Move("explain", concept, f"A different way to explain {name}", why, nxt))
    recalled = list(state.get("recall", []))
    for concept, p in sorted(skill.items()):
        if len(recalled) >= MAX_RECALL:
            break
        if (
            concept not in recalled
            and p.band in {"strong", "likely_known", "developing"}
            and p.mastery < RECALL_BELOW
            and p.last_seen_at
            and now - p.last_seen_at >= RECALL_AFTER_DAYS * DAY
            and not _locked(state, "recall", concept, now)
        ):
            name = titles.get(concept, concept)
            why = (
                f"It has been over {RECALL_AFTER_DAYS} days and your recall of {name} has "
                "faded, so a short recall warm-up comes first."
            )
            moves.append(Move("recall", concept, f"Quick recall of {name}", why))
            recalled.append(concept)
    return moves[:MAX_MOVES]
