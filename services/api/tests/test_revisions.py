"""A rewrite keeps quiz progress resolvable (acceptance criterion 15)."""

# ruff: noqa: F811
import pytest
from sqlalchemy.orm import Session
from test_coursegen_package import published  # noqa: F401
from test_learner_api import client, login, onboard  # noqa: F401
from test_maintainer import KEY, concept, released, site  # noqa: F401

from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.catalog.revisions import carry, same_question
from socrat.catalog.schema import Concept
from socrat.coursegen import maintain


@pytest.fixture
def base():
    return default_catalog().concept("cp:bitmasks")


def test_a_renamed_question_keeps_its_old_id(base):
    first = base.quiz[0]
    new = base.model_copy(
        update={"quiz": [first.model_copy(update={"id": "new-id"}), *base.quiz[1:]]}
    )
    out = carry(base, new)
    assert out.quiz[0].id == "new-id" and first.id in out.quiz[0].former_ids
    assert out.quiz_item(first.id).id == "new-id"
    assert out.retired_quiz == [] and maintain.lost_ids(base, out) == []


def test_a_lightly_reworded_question_with_the_same_answer_matches(base):
    first = base.quiz[0]
    reworded = first.model_copy(update={"id": "reworded", "prompt": first.prompt + " "})
    assert same_question(first, reworded) == 1.0
    tweaked = first.model_copy(update={"id": "tweaked", "prompt": "In short: " + first.prompt})
    assert 0.85 <= same_question(first, tweaked) < 1.0
    # An identical prompt is the same question even if its key was corrected.
    fixed = first.model_copy(
        update={"id": "fixed", "answer": (first.answer + 1) % len(first.options)}
    )
    assert same_question(first, fixed) == 1.0
    # A reworded prompt only matches when the correct answer is the same.
    reworded_other = tweaked.model_copy(update={"answer": (first.answer + 1) % len(first.options)})
    if (
        first.options[reworded_other.answer].strip().lower()
        != first.options[first.answer].strip().lower()
    ):
        assert same_question(first, reworded_other) == 0.0


def test_a_dropped_question_is_retired_but_still_found(base):
    first = base.quiz[0]
    replacement = first.model_copy(
        update={"id": "brand-new", "prompt": "An entirely different question about something else?"}
    )
    out = carry(base, base.model_copy(update={"quiz": [replacement, *base.quiz[1:]]}))
    assert [q.id for q in out.retired_quiz] == [first.id]
    assert first.id not in [q.id for q in out.quiz]  # never offered again
    assert out.quiz_item(first.id).prompt == first.prompt  # but open sessions resolve
    Concept.model_validate(out.model_dump(mode="json"))  # still a valid concept
    # A later rewrite that brings it back takes it out of the retired list.
    back = carry(out, out.model_copy(update={"quiz": [first, *base.quiz[1:]]}))
    assert [q.id for q in back.retired_quiz] == ["brand-new"]
    assert back.quiz_item(first.id).id == first.id


def test_retiring_everything_when_a_concept_goes_back_to_planned(base):
    planned = Concept.model_validate(
        base.model_dump(mode="json")
        | {
            "status": "planned",
            "lesson": "",
            "quiz": [],
            "key_points": [],
            "resources": [],
            "sequence": [],
            "problems": [],
        }
    )
    out = carry(base, planned)
    assert {q.id for q in out.retired_quiz} == {q.id for q in base.quiz}
    assert out.quiz_item(base.quiz[1].id).id == base.quiz[1].id


def test_a_retired_id_cannot_also_be_live(base):
    with pytest.raises(ValueError, match="still live"):
        Concept.model_validate(
            base.model_dump(mode="json") | {"retired_quiz": [base.quiz[0].model_dump(mode="json")]}
        )


def test_store_concept_carries_ids_for_a_released_generated_lesson(client, released):
    live = concept(client)
    old_ids = [q.id for q in live.quiz]
    renamed = live.model_copy(
        update={"quiz": [q.model_copy(update={"id": f"v2-{q.id}"[:60]}) for q in live.quiz]}
    )
    with Session(client.app.state.engine) as db, db.begin():
        generated.store_concept(db, default_catalog(), "ai-basics", renamed, None, reason="rewrite")
    after = concept(client)
    assert [q.id for q in after.quiz] == [f"v2-{i}"[:60] for i in old_ids]
    for old in old_ids:
        assert after.quiz_item(old).id == f"v2-{old}"[:60]
    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner, course="ai-basics")
    assert client.get(f"/api/v1/concepts/{KEY}").status_code == 200
