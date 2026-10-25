"""Binary-search the learner's knowledge frontier along the prerequisite order.

The course path is topologically ordered, so "knows concept i" is treated as
evidence for the concepts before it. Each probe asks one question; a probe that
lands exactly on a boundary is confirmed with a second question so a single slip
or lucky guess cannot misplace the learner by a whole module.
"""

import random
from dataclasses import dataclass, field

from socrat.catalog.registry import Catalog
from socrat.catalog.schema import QuizItem

MAX_QUESTIONS = 12
SKIP_CAP = 0.85  # most of the path placement may mark as assumed known


@dataclass
class PlacementState:
    path: list[str]
    lo: int  # every concept before lo is believed known
    hi: int  # every concept at or after hi is believed unknown
    asked: list[dict] = field(default_factory=list)  # {concept, item, correct}
    pending: dict | None = None
    seed: int = 0
    language: str | None = None  # questions about other languages are skipped (D-1)

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


def _item(catalog: Catalog, state: PlacementState, concept: str) -> QuizItem:
    used = {x["item"] for x in state.asked}
    items = [
        q
        for q in catalog.concept(concept).quiz
        if q.id not in used and (state.language is None or q.fits(state.language))
    ]
    rng = random.Random(f"{state.seed}:{concept}:{len(state.asked)}")
    items.sort(key=lambda q: (abs(q.difficulty - 2), q.id))
    return rng.choice(items[:2]) if items else catalog.concept(concept).quiz[0]


def _probe(catalog: Catalog, state: PlacementState, index: int) -> dict:
    concept = state.path[index]
    item = _item(catalog, state, concept)
    return {"concept": concept, "index": index, "item": item.id}


def question(catalog: Catalog, state: PlacementState) -> QuizItem | None:
    if state.pending is None:
        return None
    concept = catalog.concept(state.pending["concept"])
    return next(q for q in concept.quiz if q.matches(state.pending["item"]))


def seed_of(state: PlacementState) -> str:
    return f"placement:{state.seed}"


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
    same = [x for x in state.asked if x["concept"] == probe["concept"]]
    if len(same) == 1 and (index == state.lo or index == state.hi - 1) and state.hi - state.lo > 1:
        # Boundary probe: confirm with one more question before committing.
        if len(state.asked) < MAX_QUESTIONS and len(catalog.concept(probe["concept"]).quiz) > 1:
            state.pending = _probe(catalog, state, index)
            return correct
    votes = sum(1 if x["correct"] else -1 for x in same)
    if votes > 0 or (votes == 0 and correct):
        state.lo = max(state.lo, index + 1)
    else:
        state.hi = min(state.hi, index)
    state.pending = None
    if state.lo < state.hi and len(state.asked) < MAX_QUESTIONS:
        state.pending = _probe(catalog, state, (state.lo + state.hi) // 2)
    return correct


def result(state: PlacementState, own: set[str] | None = None) -> dict[str, bool]:
    """Concept → believed known. Concepts in an unresolved gap are treated as unknown.

    Concepts in ``own`` (the enrolled course's own topics) are only skipped when a question
    on them was answered correctly; a few answers must not finish the course (C-1).
    """
    confirmed = {x["concept"] for x in state.asked if x["correct"]}
    return {
        concept: index < state.frontier
        and (own is None or concept not in own or concept in confirmed)
        for index, concept in enumerate(state.path)
    }
