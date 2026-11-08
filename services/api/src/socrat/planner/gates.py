"""Module gates: later modules stay locked until the learner passes a compounding checkpoint.

A checkpoint is an adaptive staircase over the module's questions. A correct answer raises
the next question's difficulty, a miss lowers it and counts a strike. Passing needs a high
difficulty-weighted score *and* correct answers at the module's hardest level, so a run of
easy answers can never unlock the next module. Pure functions; the caller supplies state.
"""

from dataclasses import dataclass

from socrat.catalog.registry import Catalog
from socrat.mastery.model import DAY, ConceptState

MAX_ITEMS = 10
MAX_STRIKES = 3
PASS_SCORE = 0.8
HARD_CORRECT = 2
HARD_FLOOR = 4  # a checkpoint asks only questions at this difficulty or above
COOLDOWN_SECONDS = DAY
RECENT_SECONDS = 14 * DAY  # avoid re-asking items seen this recently, when possible


def gate_id(module_key: str) -> str:
    return f"checkpoint:{module_key}"


def module_keys(catalog: Catalog, course_id: str) -> list[str]:
    return [f"{course_id}:{m.id}" for m in catalog.course(course_id).modules]


def module_concepts(catalog: Catalog, module_key: str) -> list[str]:
    course_id, module_id = module_key.split(":", 1)
    module = next(m for m in catalog.course(course_id).modules if m.id == module_id)
    return [f"{course_id}:{c}" for c in module.concepts]


def cleared(
    catalog: Catalog,
    module_key: str,
    states: dict[str, ConceptState],
    completed: set[str],
    now: int,
    held: frozenset[str] = frozenset(),
) -> bool:
    """A module is cleared by passing its gate, or when every concept is already known.
    ``held`` names modules held shut by a transfer check that is still to be passed."""
    if module_key in held:
        return False
    if gate_id(module_key) in completed:
        return True
    concepts = module_concepts(catalog, module_key)
    return all(
        (s := states.get(c)) is not None and (s.mastered(now) or s.assumed) for c in concepts
    )


def locked_modules(
    catalog: Catalog,
    course_id: str,
    states: dict[str, ConceptState],
    completed: set[str],
    now: int,
    held: frozenset[str] = frozenset(),
) -> dict[str, str]:
    """Locked module key -> the gate that opens the way to it (the first uncleared one)."""
    locked: dict[str, str] = {}
    blocking: str | None = None
    for key in module_keys(catalog, course_id):
        if blocking:
            locked[key] = blocking
        elif not cleared(catalog, key, states, completed, now, held):
            blocking = gate_id(key)
    return locked


def locked_concepts(
    catalog: Catalog,
    course_id: str,
    states: dict[str, ConceptState],
    completed: set[str],
    now: int,
    held: frozenset[str] = frozenset(),
) -> dict[str, str]:
    return {
        concept: gate
        for key, gate in locked_modules(catalog, course_id, states, completed, now, held).items()
        for concept in module_concepts(catalog, key)
    }


@dataclass(frozen=True)
class GateResult:
    done: bool
    passed: bool
    score: float  # difficulty-weighted accuracy
    strikes: int
    hard_level: int
    hard_correct: int
    hard_needed: int
    next_level: int


def evaluate(
    answers: list[tuple[int, bool]],
    levels: list[int],
    hard_available: int,
    exhausted: bool = False,
) -> GateResult:
    """Staircase state after `answers` = [(difficulty, correct), ...] in order asked.

    `levels` are the difficulties that exist in the module (sorted, unique);
    `hard_available` is how many questions exist at the hardest level;
    `exhausted` ends the gate early when the module has no unused questions left.
    """
    levels = sorted(set(levels)) or [1]
    index = min(1, len(levels) - 1)  # start one step above the easiest level
    strikes = 0
    for _, correct in answers:
        if correct:
            index = min(index + 1, len(levels) - 1)
        else:
            index = max(index - 1, 0)
            strikes += 1
    weight = sum(d for d, _ in answers)
    score = sum(d for d, ok in answers if ok) / weight if weight else 0.0
    hard_level = levels[-1]
    hard_correct = sum(1 for d, ok in answers if ok and d == hard_level)
    hard_needed = min(HARD_CORRECT, hard_available)
    done = exhausted or len(answers) >= MAX_ITEMS or strikes >= MAX_STRIKES
    passed = done and strikes < MAX_STRIKES and score >= PASS_SCORE and hard_correct >= hard_needed
    return GateResult(
        done=done,
        passed=passed,
        score=round(score, 3),
        strikes=strikes,
        hard_level=hard_level,
        hard_correct=hard_correct,
        hard_needed=hard_needed,
        next_level=levels[index],
    )
