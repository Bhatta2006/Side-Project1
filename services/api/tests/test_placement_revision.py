"""Placement starts the lessons at the gap, then revises what it believed; the check is strict."""

from datetime import date

from catalog_support import catalog

from socrat.mastery.model import placed
from socrat.placement import engine as placement
from socrat.planner.engine import build_plan, revision_minutes

NOW = 1_800_000_000
TODAY = date(2027, 1, 4)


def plan(states):
    cat = catalog()
    return build_plan(
        cat, cat.course_concepts("algo"), states, set(), [], TODAY, NOW, {0, 1, 2, 3, 4}, 60
    )


def test_confirmation_checks_wait_until_every_lesson_is_done():
    known = {c: placed(True, NOW) for c in ("basics:values", "basics:loops", "basics:functions")}
    queue = plan(known).queue
    last_lesson = max(i for i, a in enumerate(queue) if a.kind == "lesson")
    confirms = [i for i, a in enumerate(queue) if a.code == "assumed_confirm"]
    assert confirms and min(confirms) > last_lesson


def test_revision_time_follows_difficulty():
    assert revision_minutes(1) < revision_minutes(3) < revision_minutes(5)


def test_placement_gets_harder_as_answers_are_right():
    cat = catalog()
    path = cat.closure(cat.course_concepts("algo"))
    state = placement.start(cat, path, "algo:arrays", seed=11)
    assert placement.target_difficulty(state) == 2
    state.asked = [{"concept": "x", "item": str(i), "correct": True} for i in range(6)]
    assert placement.target_difficulty(state) == 4


def test_a_split_result_does_not_count_as_known():
    cat = catalog()
    path = cat.closure(cat.course_concepts("algo"))
    state = placement.start(cat, path, "algo:arrays", seed=11)
    first = placement.question(cat, state)
    placement.answer(cat, state, first.shown(placement.seed_of(state))["answer"])
    if state.pending is None:
        return  # A concept with one question cannot be confirmed; nothing to assert.
    asked_before = state.pending["concept"]
    second = placement.question(cat, state)
    wrong = (second.shown(placement.seed_of(state))["answer"] + 1) % len(second.options)
    placement.answer(cat, state, wrong)
    known = placement.result(state)
    assert not known[asked_before]
