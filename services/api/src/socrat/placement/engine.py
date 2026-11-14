"""Binary-search the learner's knowledge frontier along the prerequisite order, strictly.

The course path is topologically ordered, so "knows concept i" is treated as
evidence for the concepts before it. Placement is deliberately hard to pass:

- Questions come from the placement bank (``content/placement``: edge cases, special
  cases, traces and bugs written to be the hardest of their topic), then from the
  concept's own hardest quiz items. Easy items are used only when nothing harder exists.
- A concept counts as known only after ``CONFIRM`` correct answers on it. One miss, or
  "not sure yet", marks it unknown: a lucky guess cannot carry a learner forward.
- Once the search settles, ``SPOT_CHECKS`` earlier concepts the search only inferred are
  tested too. A miss there pulls the frontier back to that concept, so the plan starts
  at the learner's real gap rather than past it.
- Three misses (or "not sure yet") in a row end the check early: the learner has shown where
  their gap is, and more hard questions would only drag on. The frontier stays where it was.
- However well a learner does, at most ``SKIP_CAP`` of the path can be placed as known:
  nobody tests out of the whole course.
"""

import random
from dataclasses import dataclass, field

from socrat.catalog.registry import Catalog
from socrat.catalog.schema import QuizItem

MAX_QUESTIONS = 10  # placement should feel short: at most 10 questions
STOP_AFTER_MISSES = 3  # misses in a row that end the check early
SKIP_CAP = 0.6  # most of the path placement may mark as assumed known
CONFIRM = 2  # correct answers a concept needs before placement believes it
SPOT_CHECKS = 2  # inferred concepts below the frontier that are tested anyway
HARD = 4  # quiz items below this difficulty are used only when nothing harder is left


@dataclass
class PlacementState:
    path: list[str]
    lo: int  # every concept before lo is believed known
    hi: int  # every concept at or after hi is believed unknown
    asked: list[dict] = field(default_factory=list)  # {concept, item, correct}
    pending: dict | None = None
    seed: int = 0
    language: str | None = None  # questions about other languages are skipped (D-1)
    spots: int = 0  # spot checks started

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, value: dict) -> "PlacementState":
        return cls(**value)

    @property
    def done(self) -> bool:
        return self.pending is None and (self.lo >= self.hi or len(self.asked) >= MAX_QUESTIONS)

    @property
    def frontier(self) -> int:
        # A short check can't vouch for the whole path: the last stretch always stays to learn.
        return min(self.lo, int(len(self.path) * SKIP_CAP))


def start(
    catalog: Catalog,
    path: list[str],
    start_concept: str | None,
    seed: int,
    language: str | None = None,
) -> PlacementState:
    if start_concept is None:
        return PlacementState(path=path, lo=0, hi=0, seed=seed)  # Absolute beginner.
    anchor = path.index(start_concept) if start_concept in path else len(path) // 2
    # Self-report sets where to start probing, not where the learner is placed.
    state = PlacementState(path=path, lo=0, hi=len(path), seed=seed, language=language)
    state.pending = _probe(catalog, state, anchor)
    return state


def bank(catalog: Catalog, concept: str) -> list[QuizItem]:
    """The hard placement-only items written for ``concept`` (may be empty)."""
    return list(getattr(catalog, "placement_items", {}).get(concept, []))


def find_item(catalog: Catalog, concept: str, item_id: str) -> QuizItem:
    for q in bank(catalog, concept):
        if q.matches(item_id):
            return q
    return next(q for q in catalog.concept(concept).quiz if q.matches(item_id))


def _candidates(catalog: Catalog, state: PlacementState, concept: str) -> list[QuizItem]:
    used = {x["item"] for x in state.asked}

    def fit(items: list[QuizItem]) -> list[QuizItem]:
        return [
            q
            for q in items
            if q.id not in used and (state.language is None or q.fits(state.language))
        ]

    hardest_first = sorted(fit(catalog.concept(concept).quiz), key=lambda q: (-q.difficulty, q.id))
    # The written bank first; then the lesson quiz's hardest items; easy ones only as a last resort.
    return (
        fit(bank(catalog, concept))
        or [q for q in hardest_first if q.difficulty >= HARD]
        or hardest_first
    )


def _item(catalog: Catalog, state: PlacementState, concept: str) -> QuizItem:
    items = _candidates(catalog, state, concept)
    if not items:
        return catalog.concept(concept).quiz[0]
    rng = random.Random(f"{state.seed}:{concept}:{len(state.asked)}")
    return rng.choice(items[:3])


def _probe(catalog: Catalog, state: PlacementState, index: int) -> dict:
    concept = state.path[index]
    item = _item(catalog, state, concept)
    return {"concept": concept, "index": index, "item": item.id}


def question(catalog: Catalog, state: PlacementState) -> QuizItem | None:
    if state.pending is None:
        return None
    return find_item(catalog, state.pending["concept"], state.pending["item"])


def seed_of(state: PlacementState) -> str:
    return f"placement:{state.seed}"


def _spot(catalog: Catalog, state: PlacementState) -> dict | None:
    """The next inferred concept below the frontier to test directly, if any."""
    asked = {x["concept"] for x in state.asked}
    frontier = state.frontier
    while state.spots < SPOT_CHECKS and frontier > 0:
        state.spots += 1
        index = (frontier * (SPOT_CHECKS + 1 - state.spots)) // (SPOT_CHECKS + 1)
        # Walk down to the nearest concept nobody asked about yet.
        while index >= 0 and state.path[index] in asked:
            index -= 1
        if index >= 0:
            return _probe(catalog, state, index)
    return None


def answer(catalog: Catalog, state: PlacementState, choice: int) -> bool:
    """``choice`` is the display position the learner picked, or -1 for "I don't know"."""
    if state.pending is None:
        raise ValueError("placement_complete")
    item = question(catalog, state)
    assert item is not None
    correct = item.is_correct(seed_of(state), choice)
    probe = state.pending
    index = probe["index"]
    state.asked.append({"concept": probe["concept"], "item": probe["item"], "correct": correct})
    recent = state.asked[-STOP_AFTER_MISSES:]
    if len(recent) == STOP_AFTER_MISSES and not any(x["correct"] for x in recent):
        # The gap is found: stop here, below the miss, rather than keep asking hard questions.
        state.hi = min(state.hi, index)
        state.lo = min(state.lo, state.hi)
        state.hi = state.lo
        state.pending = None
        return correct
    same = [x for x in state.asked if x["concept"] == probe["concept"]]
    budget = len(state.asked) < MAX_QUESTIONS
    if correct and len(same) < CONFIRM and budget and _candidates(catalog, state, probe["concept"]):
        # Right once is not enough: confirm with another hard question on the same concept.
        state.pending = _probe(catalog, state, index)
        return correct
    confirmed = len(same) >= CONFIRM or not _candidates(catalog, state, probe["concept"])
    if confirmed and all(x["correct"] for x in same):
        state.lo = max(state.lo, index + 1)
    else:
        # Any miss is decisive, including a spot check below the frontier.
        state.hi = min(state.hi, index)
        state.lo = min(state.lo, state.hi)
    state.pending = None
    if not budget:
        return correct
    if state.lo < state.hi:
        state.pending = _probe(catalog, state, (state.lo + state.hi) // 2)
    else:
        state.pending = _spot(catalog, state)
    return correct


def result(state: PlacementState) -> dict[str, bool]:
    """Concept -> believed known (assumed, never mastered). Unresolved gaps count as unknown.

    Assumed concepts still owe a confirmation check before they count as learned.
    """
    return {concept: index < state.frontier for index, concept in enumerate(state.path)}


def missed(state: PlacementState) -> list[str]:
    """Concepts the learner got wrong during placement, in path order (their weak spots)."""
    wrong = {x["concept"] for x in state.asked if not x["correct"]}
    return [c for c in state.path if c in wrong]
