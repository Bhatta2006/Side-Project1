"""Placement is strict: hard questions only, two right answers per concept, spot checks below
the frontier, nobody tests out of a whole course, and the plan starts at the frontier."""

from datetime import date

from catalog_support import catalog

from socrat.catalog.registry import default_catalog
from socrat.mastery.model import placed
from socrat.placement import engine as placement
from socrat.planner.engine import build_plan


def track_path(cat, course):
    return [
        c for c in cat.closure(cat.course_concepts(course)) if cat.concept(c).status != "planned"
    ]


def run(cat, state, right):
    while not state.done:
        item = placement.question(cat, state)
        assert item is not None
        good = item.shown(placement.seed_of(state))["answer"]
        index = state.pending["index"]
        placement.answer(cat, state, good if right(index, item) else -1)
    return state


def test_one_miss_on_the_confirming_question_marks_the_concept_unknown():
    cat = default_catalog()
    path = track_path(cat, "algo")
    start = "algo:pairs"
    state = placement.start(cat, path, start, seed=5, language="python")
    anchor = state.pending["index"]
    seen: dict[int, int] = {}

    def right(index, _item):
        seen[index] = seen.get(index, 0) + 1
        return not (index == anchor and seen[index] == 2)  # right once, then wrong

    run(cat, state, right)
    assert not placement.result(state)[start]
    assert start in placement.missed(state)


def test_not_sure_counts_as_not_known():
    cat = default_catalog()
    path = track_path(cat, "basics")
    state = run(
        cat,
        placement.start(cat, path, "basics:lists", seed=3, language="python"),
        lambda *_: False,
    )
    assert not any(placement.result(state).values())


def test_spot_checks_pull_the_frontier_back_to_a_real_gap():
    cat = default_catalog()
    path = track_path(cat, "algo")
    state = placement.start(cat, path, "algo:graphs", seed=9, language="python")
    anchor = state.pending["index"]
    # Answers everything at or above the self-reported level, nothing below it.
    run(cat, state, lambda index, _item: index >= anchor)
    assert state.spots >= 1
    assert state.frontier < anchor
    missed = placement.missed(state)
    assert missed and all(path.index(c) < anchor for c in missed)
    assert not placement.result(state)[missed[0]]


def test_today_starts_at_the_frontier_not_with_confirmations():
    cat = catalog()
    concepts = cat.course_concepts("algo")
    path = cat.closure(concepts)
    known = {c: placed(True, 0) for c in path[:3]}
    plan = build_plan(cat, concepts, known, set(), [], date(2026, 1, 5), 0, {0, 1, 2, 3, 4}, 30)
    kinds = [a.kind for a in plan.queue]
    assert kinds[0] != "testout"
    assert plan.queue[0].concept not in known
    confirms = [i for i, a in enumerate(plan.queue) if a.code == "assumed_confirm"]
    assert {plan.queue[i].concept for i in confirms} == set(known)
    first_lesson = next(i for i, a in enumerate(plan.queue) if a.kind == "lesson")
    assert first_lesson < min(confirms)
