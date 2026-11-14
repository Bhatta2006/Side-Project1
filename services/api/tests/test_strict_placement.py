"""Placement is strict: hard questions only, two right answers per concept, spot checks below
the frontier, nobody tests out of a whole course, and the plan starts at the frontier."""

from datetime import date

import pytest
from catalog_support import catalog

from socrat.catalog.registry import default_catalog
from socrat.mastery.model import placed
from socrat.placement import bank
from socrat.placement import engine as placement
from socrat.planner.engine import build_plan

LEVELS = {"zero": "functions", "dsa": "graph-traversal", "cp": "dp-classics"}


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


@pytest.mark.parametrize("course", ["zero", "dsa", "cp"])
def test_a_perfect_learner_meets_only_hard_questions_and_cannot_clear_the_course(course):
    cat = default_catalog()
    path = track_path(cat, course)
    start = f"{course}:{LEVELS[course]}"
    state = run(cat, placement.start(cat, path, start, seed=11, language="python"), lambda *_: True)
    asked = [placement.find_item(cat, x["concept"], x["item"]) for x in state.asked]
    assert asked and all(q.difficulty >= placement.HARD for q in asked)
    # The written bank is used, not the lesson quizzes, wherever it has questions.
    banked = {q.id for k in cat.placement_items for q in cat.placement_items[k]}
    assert sum(q.id in banked for q in asked) >= len(asked) * 0.8
    known = placement.result(state)
    assert not all(known.values()), "nobody tests out of a whole course"
    assert sum(known.values()) <= int(len(path) * placement.SKIP_CAP)
    # Every concept the search answered "known" for was confirmed twice.
    for concept in {x["concept"] for x in state.asked}:
        answers = [x for x in state.asked if x["concept"] == concept]
        if known[concept]:
            assert len(answers) >= placement.CONFIRM
    assert len(state.asked) <= placement.MAX_QUESTIONS


def test_one_miss_on_the_confirming_question_marks_the_concept_unknown():
    cat = default_catalog()
    path = track_path(cat, "dsa")
    start = "dsa:binary-search"
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
    path = track_path(cat, "zero")
    state = run(
        cat,
        placement.start(cat, path, "zero:lists", seed=3, language="python"),
        lambda *_: False,
    )
    assert not any(placement.result(state).values())


def test_spot_checks_pull_the_frontier_back_to_a_real_gap():
    cat = default_catalog()
    path = track_path(cat, "cp")
    state = placement.start(cat, path, "cp:dp-classics", seed=9, language="python")
    anchor = state.pending["index"]
    # Answers everything at or above the self-reported level, nothing below it.
    run(cat, state, lambda index, _item: index >= anchor)
    assert state.spots >= 1
    assert state.frontier < anchor
    missed = placement.missed(state)
    assert missed and all(path.index(c) < anchor for c in missed)
    assert not placement.result(state)[missed[0]]


def test_the_bank_refuses_easy_or_unknown_items(tmp_path):
    cat = default_catalog()
    item = dict(
        id="pl-x",
        kind="mcq",
        prompt="Which one is right?",
        options=["a", "b"],
        answer=0,
        explanation="Because it is.",
        difficulty=3,
    )
    (tmp_path / "zero.yaml").write_text(
        f"course: zero\nconcepts:\n  lists:\n    - {item}\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="difficulty 4 or 5"):
        bank.load(tmp_path, cat)
    item["difficulty"] = 5
    (tmp_path / "zero.yaml").write_text(
        f"course: zero\nconcepts:\n  no-such-concept:\n    - {item}\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="unknown concept"):
        bank.load(tmp_path, cat)


def test_every_track_has_a_bank_for_every_live_concept():
    cat = default_catalog()
    for course in ("zero", "dsa", "cp"):
        for concept in cat.course_concepts(course):
            if cat.concept(concept).status == "live":
                assert len(placement.bank(cat, concept)) >= 2, concept


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


def test_three_misses_in_a_row_end_placement_early():
    cat = default_catalog()
    path = [
        c for c in cat.closure(cat.course_concepts("dsa")) if cat.concept(c).status != "planned"
    ]
    start = cat.course("dsa").levels[1].start_concept
    state = placement.start(cat, path, f"dsa:{start}", seed=7, language="python")
    while not state.done:
        placement.answer(cat, state, -1)  # "not sure yet"
    assert len(state.asked) == placement.STOP_AFTER_MISSES
    assert state.frontier == 0
