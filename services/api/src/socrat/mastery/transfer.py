"""Transfer verification: can the learner use a mastered concept on a problem they have never seen?

A check has two steps, both without help. First the learner reads an unseen problem and names the
technique it needs (one of four concepts). Only then do they solve it, and only an accepted
solve with no tutor help counts. Passing marks the concept "transfer verified"; a miss lowers
the mastery estimate and opens a fresh problem after a cooldown.

Pure functions. ``socrat.learn.transfers`` loads the state and records the results.
"""

import hashlib
from dataclasses import dataclass, field

from socrat.catalog.registry import Catalog
from socrat.mastery.model import DAY, ConceptState
from socrat.planner import gates

COOLDOWN = DAY  # after a miss, a new problem opens this much later
CHOICES = 4  # one right technique and three distractors
MAX_QUEUED = 2  # at most this many checks on the plan at once
ASSISTED_SCORE = 0.3  # a solve that needed the tutor is a miss, but not a total one
# A concept with one of these statuses still has a check to take.
OFFERED = frozenset({"due", "pending", "wait"})


@dataclass(frozen=True)
class Transfer:
    """What the planner and the gates need: status per concept, modules held back by a check."""

    status: dict[str, str] = field(default_factory=dict)
    blocking: frozenset[str] = frozenset()


def activity_id(concept: str) -> str:
    return f"transfer:{concept}"


def rank(*parts: str) -> int:
    """A stable pseudo-random order: the same learner and concept always see the same choice."""
    return int.from_bytes(hashlib.sha256("|".join(parts).encode()).digest()[:8], "big")


def unseen(catalog: Catalog, concept: str, seen: set[str]) -> list[str]:
    """Problems for ``concept`` the learner has not opened, run, been helped on or been asked."""
    course_id, _, local = concept.partition(":")
    return sorted(
        pid
        for pid, (owner, problem) in catalog.problems.items()
        if owner == course_id and problem.concepts[0] == local and pid not in seen
    )


def pick(seed: str, candidates: list[str]) -> str | None:
    return min(candidates, key=lambda pid: rank(seed, pid), default=None)


def choices(
    catalog: Catalog, concept: str, seed: str, curriculum: set[str], known: set[str]
) -> list[str] | None:
    """The right technique among distractors, in a fixed shuffled order; ``None`` if too few.

    A direct prerequisite or follow-on is never a distractor: a problem can fairly need both,
    and then "which technique" would have two right answers.
    """
    near = {concept, *catalog.prerequisites[concept]} | {
        c for c in curriculum if concept in catalog.prerequisites[c]
    }
    pool = sorted(curriculum - near)
    pool.sort(key=lambda c: (c not in known, rank(seed, c)))  # concepts they have met first
    if len(pool) < CHOICES - 1:
        return None
    return sorted([*pool[: CHOICES - 1], concept], key=lambda c: rank(seed, "order", c))


def status(
    outcome: dict | None,
    verified: bool,
    state: ConceptState,
    available: bool,
    now: int,
) -> str | None:
    """verified | pending (unseen problem named, solve outstanding) | wait (cooling down after a
    miss) | due (ready to take) | None (nothing to do: not mastered, or no unseen problem)."""
    if verified:
        return "verified"
    outcome = outcome or {}
    if outcome.get("state") == "pending":
        return "pending"
    if outcome.get("state") == "failed" and now < int(outcome.get("at", 0)) + COOLDOWN:
        return "wait"  # even if the miss pulled mastery down: it cannot be dodged by failing
    return "due" if state.mastered(now) and available else None


def blocking_modules(
    catalog: Catalog,
    course_id: str,
    statuses: dict[str, str],
    states: dict[str, ConceptState],
    completed: set[str],
    now: int,
) -> frozenset[str]:
    """Modules whose checkpoint is passed but which stay shut until one of their concepts is
    transfer verified. A module with no check on offer never blocks, and neither does one the
    learner has already moved past (they have evidence in a later module)."""
    keys = gates.module_keys(catalog, course_id)
    held: set[str] = set()
    for index, key in enumerate(keys[:-1]):
        if not gates.cleared(catalog, key, states, completed, now):
            continue
        members = gates.module_concepts(catalog, key)
        marks = {statuses.get(c) for c in members}
        if "verified" in marks or not marks & OFFERED:
            continue
        later = (c for k in keys[index + 1 :] for c in gates.module_concepts(catalog, k))
        if any((s := states.get(c)) and s.evidence_count and not s.assumed for c in later):
            continue
        held.add(key)
    return frozenset(held)
