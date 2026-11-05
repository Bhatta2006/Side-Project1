"""The writer marks the right option in the item; code derives the stored answer index.

Taken from Wondering's practice items (research/wondering/2026-11-05/responses/055-practices.json),
where every option carries ``isCorrect`` so the key cannot point at the wrong option.
"""
# ruff: noqa: F811

import pytest
from test_coursegen_package import (  # noqa: F401
    ATOMS,
    QUIZ,
    ROLES,
    STEP,
    Scripted,
    lesson,
    published,
    run,
    web,
)
from test_coursegen_package import FACTS_OK as FACTS
from test_coursegen_package import PASS as REVIEW
from test_coursegen_package import generate as queue
from test_learner_api import client  # noqa: F401

from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.coursegen import keyed
from socrat.coursegen import package as pkg

OPTIONS = ["Rules come from examples", "Rules are typed by hand", "Data is optional"]


def flagged(right: int) -> list[dict]:
    return [{"text": t, "correct": i == right} for i, t in enumerate(OPTIONS)]


def test_every_form_gives_the_same_index():
    assert keyed.settle({"options": OPTIONS, "answer": 1})["answer"] == 1
    assert keyed.settle({"options": OPTIONS, "answer": "rules are typed by hand."})["answer"] == 1
    settled = keyed.settle({"options": flagged(2)})
    assert settled == {"options": OPTIONS, "answer": 2}
    wondering = [{"id": "a", "text": OPTIONS[0], "isCorrect": True}, {"text": OPTIONS[1]}]
    assert keyed.settle({"options": wondering})["answer"] == 0
    # Flag and answer agreeing is fine; they are the same claim.
    assert keyed.settle({"options": flagged(0), "answer": OPTIONS[0]})["answer"] == 0


@pytest.mark.parametrize(
    "item, says",
    [
        ({"options": flagged(0), "answer": 2}, "disagree"),
        (
            {"options": [{"text": "a", "correct": True}, {"text": "b", "correct": True}]},
            "exactly one",
        ),
        ({"options": [{"text": "a"}, {"text": "b"}]}, "mark which"),
        ({"options": OPTIONS, "answer": "Something else"}, "copy it exactly"),
        ({"options": OPTIONS, "answer": 3}, "not one of the 3"),
        ({"options": OPTIONS, "answer": True}, "not true or false"),
        ({"options": ["Yes", "yes."], "answer": 0}, "same thing"),
        ({"options": [{"text": "a", "correct": "yes"}, {"text": "b"}]}, "true or false"),
    ],
)
def test_an_unclear_key_is_refused_never_guessed(item, says):
    with pytest.raises(TypeError, match=says):
        keyed.settle(item)


def test_the_marked_prompts_ask_for_the_mark_and_examples_show_it():
    assert pkg.QUIZ_MARKED != pkg.QUIZ and pkg.ATOMS_MARKED != pkg.ATOMS
    for text in (pkg.QUIZ_MARKED, pkg.ATOMS_MARKED):
        assert '"correct": true' in text and '"answer": 0' not in text
    assert "vary the correct position" not in pkg.QUIZ_MARKED
    item = {"id": "q", "options": ["x", "y"], "answer": 1}
    assert keyed.marked(item)["options"] == [
        {"text": "x", "correct": False},
        {"text": "y", "correct": True},
    ]


def test_atom_checks_settle_and_an_unclear_one_is_dropped():
    marked = {k: v for k, v in STEP.items() if k != "answer"}
    marked["options"] = [{"text": "y = 2x", "correct": True}, {"text": "y = x + 1"}]
    unclear = marked | {"answer": 1}  # the flag says 0, the index says 1
    atom = pkg.tidy_atom(ATOMS["atoms"][3] | {"steps": [marked, unclear]})
    assert atom["steps"] == [STEP]
    alone = pkg.tidy_atom(ATOMS["atoms"][3] | {"steps": [unclear]})
    assert alone["kind"] == "concept"  # no check left to grade, so it is a plain card


def test_a_marked_package_is_released_with_the_derived_index(client, published, web):
    client.app.state.settings.gen_marked_answers = True
    roles = ROLES | {pkg.QUIZ_MARKED: "quiz", pkg.ATOMS_MARKED: "atoms"}
    quiz = {**QUIZ, "quiz": [{**q, "options": flagged(i % 3)} for i, q in enumerate(QUIZ["quiz"])]}
    for q in quiz["quiz"]:
        q.pop("answer")
    step = {k: v for k, v in STEP.items() if k != "answer"} | {"answer": "y = 2x"}
    atoms = {"atoms": [*ATOMS["atoms"][:3], ATOMS["atoms"][3] | {"steps": [step]}]}
    script = Scripted(
        author=[lesson()], quiz=[quiz], atoms=[atoms], facts=[FACTS], reviewer=[REVIEW]
    )
    original = dict(ROLES)
    ROLES.update(roles)
    try:
        queue(client, published, "what-is-ml")
        assert run(client, script.make, web())
    finally:
        ROLES.clear()
        ROLES.update(original)
    concept = generated.merged(default_catalog()).concept("ai-basics:what-is-ml")
    assert concept.status == "live"
    assert [q.answer for q in concept.quiz] == [i % 3 for i in range(5)]
    assert all(q.options == OPTIONS for q in concept.quiz)
    pack = generated.merged(default_catalog()).atom_packs["ai-basics:what-is-ml"]
    assert pack.atoms[3].steps[0].answer == 0
