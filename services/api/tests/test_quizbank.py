"""Quiz families, bank items, generator specs and the read-only wrap of the 284 legacy items."""

import copy
from collections import Counter

import pytest
import yaml
from pydantic import ValidationError

from socrat.catalog import patterns, quizbank
from socrat.catalog.atoms import load_taxonomy
from socrat.catalog.registry import CONTENT_ROOT, CatalogError, load

ORIGINAL = {"origin": "original", "author": "Socrat Learning"}
GENERATED = {
    "id": "quiz:dsa:sliding-window:fixed-window-sum",
    "family": "fixed-window-sum",
    "concept": "dsa:sliding-window",
    "format": "output_prediction",
    "tracks": ["foundations", "interview", "competitive"],
    "languages": ["python", "cpp", "java"],
    "generator": {
        "template": "fixed_window_sum",
        "params": {"n": [6, 8], "k": [2, 4]},
        "reference": "max(sum(a[i:i+k]) for i in range(len(a)-k+1))",
        "seeds": {
            "practice": {"start": 0, "stop": 7000},
            "assessment": {"start": 7000, "stop": 10000},
        },
    },
    "distractors": [{"rule": "window of size k-1", "misconception": "sliding-window-repair"}],
    "hint_ladder": ["Restate what one window covers.", "Compute the first window."],
    "provenance": ORIGINAL,
}
STATIC = {
    "id": "quiz:dsa:sliding-window:shrink-condition",
    "family": "shrink-condition",
    "concept": "dsa:sliding-window",
    "format": "mcq",
    "tracks": ["interview"],
    "languages": ["python"],
    "items": [
        {
            "id": "when-to-shrink",
            "band": 3,
            "prompt": "When does a variable-size window move its left edge?",
            "options": [
                "While the window is invalid",
                "On every step",
                "Never",
                "When right reaches the end",
            ],
            "answer": 0,
            "misconceptions": [None, "sliding-window-repair", None, None],
            "explanation": "Shrinking restores validity; it runs only while the window breaks the rule.",
        }
    ],
    "provenance": ORIGINAL,
}


@pytest.fixture(scope="module")
def catalog():
    return load()


@pytest.fixture(scope="module")
def taxonomy():
    return load_taxonomy(CONTENT_ROOT.parent / "atoms")


def write_family(root, payload, name=None, generator=True):
    course, concept = payload["concept"].split(":")
    folder = root / course / concept
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name or payload['family']}.yaml").write_text(yaml.safe_dump(payload), "utf-8")
    if generator and payload.get("generator"):
        generators = root / "generators"
        generators.mkdir(exist_ok=True)
        (generators / f"{payload['generator']['template']}.py").write_text("# fixture\n", "utf-8")


def test_generator_and_static_families_load(tmp_path, catalog, taxonomy):
    write_family(tmp_path, GENERATED)
    write_family(tmp_path, STATIC)
    families = quizbank.load(tmp_path, catalog, taxonomy)
    assert set(families) == {GENERATED["id"], STATIC["id"]}
    assert families[STATIC["id"]].items[0].status == "provisional"
    assert families[GENERATED["id"]].provenance.review is None


def test_repository_families_are_provisional_original_and_unreviewed(catalog):
    assert {
        "quiz:dsa:sliding-window:fixed-window-sum",
        "quiz:dsa:binary-search:boundaries",
        "quiz:zero:for-loops:accumulator",
    } <= set(catalog.quiz_families)
    for family in catalog.quiz_families.values():
        assert family.status == "provisional" and family.provenance.review is None
        assert family.provenance.origin == "original"
        if family.pattern:
            # A pattern's family gets its answers from executed reference code.
            assert family.generator is not None, family.id
        elif family.generator is None:
            # A secondary family may be static; unreviewed, its items never count as mastery
            # evidence, and every distractor still names the misconception it tests.
            assert len(family.items) >= 3, family.id
            assert all(
                t is not None
                for i in family.items
                for k, t in enumerate(i.misconceptions)
                if k != i.answer
            ), family.id


def test_generator_template_file_must_exist(tmp_path, catalog, taxonomy):
    write_family(tmp_path, GENERATED, generator=False)
    with pytest.raises(CatalogError, match="generator template fixed_window_sum"):
        quizbank.load(tmp_path, catalog, taxonomy)


@pytest.mark.parametrize(
    "change, message",
    [
        ({"id": "quiz:dsa:nothing:fixed-window-sum", "concept": "dsa:nothing"}, "unknown concept"),
        (
            {"distractors": [{"rule": "window of size k-1", "misconception": "made-up"}]},
            "unknown misconception",
        ),
    ],
)
def test_broken_family_references_fail(tmp_path, catalog, taxonomy, change, message):
    write_family(tmp_path, {**copy.deepcopy(GENERATED), **change})
    with pytest.raises(CatalogError, match=message):
        quizbank.load(tmp_path, catalog, taxonomy)


def test_item_misconceptions_are_checked_against_the_taxonomy(tmp_path, catalog, taxonomy):
    payload = copy.deepcopy(STATIC)
    payload["items"][0]["misconceptions"] = [None, "made-up", None, None]
    write_family(tmp_path, payload)
    with pytest.raises(CatalogError, match="unknown misconception made-up"):
        quizbank.load(tmp_path, catalog, taxonomy)


def test_file_path_must_match_the_family(tmp_path, catalog, taxonomy):
    write_family(tmp_path, GENERATED, name="other")
    with pytest.raises(CatalogError, match="file path must match"):
        quizbank.load(tmp_path, catalog, taxonomy)


def test_family_rules():
    with pytest.raises(ValidationError, match="generator or static items"):
        quizbank.QuizFamily.model_validate(
            {**{k: v for k, v in GENERATED.items() if k != "generator"}}
        )
    overlap = copy.deepcopy(GENERATED)
    overlap["generator"]["seeds"]["assessment"] = {"start": 6000, "stop": 9000}
    with pytest.raises(ValidationError, match="must not overlap"):
        quizbank.QuizFamily.model_validate(overlap)
    with pytest.raises(ValidationError, match="must be quiz:dsa:sliding-window:fixed-window-sum"):
        quizbank.QuizFamily.model_validate({**GENERATED, "id": "quiz:dsa:sliding-window:other"})
    with pytest.raises(ValidationError, match="human review"):
        quizbank.QuizFamily.model_validate({**GENERATED, "status": "calibrated"})


def test_correct_option_cannot_carry_a_misconception():
    payload = copy.deepcopy(STATIC["items"][0])
    payload["misconceptions"] = ["sliding-window-repair", None, None, None]
    with pytest.raises(ValidationError, match="correct option"):
        quizbank.BankItem.model_validate(payload)


def test_pattern_quiz_family_must_resolve_to_a_family_for_that_pattern(tmp_path, catalog, taxonomy):
    from test_patterns import VALID

    family = {**copy.deepcopy(GENERATED), "pattern": "dsa:sliding-window/variable-size"}
    write_family(tmp_path / "quiz", family)
    families = quizbank.load(tmp_path / "quiz", catalog, taxonomy)
    pattern = {**copy.deepcopy(VALID), "quiz_family": family["id"]}
    folder = tmp_path / "patterns" / "dsa" / "sliding-window"
    folder.mkdir(parents=True)
    (folder / "variable-size.yaml").write_text(yaml.safe_dump(pattern), "utf-8")
    ids = patterns.external_problem_ids(CONTENT_ROOT.parent / "practice" / "problems.jsonl")
    loaded = patterns.load(tmp_path / "patterns", catalog, taxonomy, lambda: ids, families)
    assert loaded[VALID["id"]].quiz_family == family["id"]
    pattern["quiz_family"] = "quiz:dsa:sliding-window:missing"
    (folder / "variable-size.yaml").write_text(yaml.safe_dump(pattern), "utf-8")
    with pytest.raises(CatalogError, match="unknown quiz family"):
        patterns.load(tmp_path / "patterns", catalog, taxonomy, lambda: ids, families)


def test_legacy_items_are_wrapped_read_only_with_global_keys_and_bands(catalog):
    items = quizbank.legacy_items(catalog)
    embedded = [q for c in catalog.concepts.values() for q in c.quiz]
    assert len(items) == len(embedded) >= 284
    assert len({i.key for i in items}) == len(items)
    assert all(i.status == "provisional" for i in items)
    assert Counter(i.format for i in items) == Counter(
        quizbank.LEGACY_FORMAT[q.kind] for q in embedded
    )
    for item in items:
        expected = quizbank.BAND_FOR_DIFFICULTY[item.difficulty]
        if item.languages:
            expected = max(expected, 2)
        assert item.band == expected
    first = items[0]
    assert first.key == f"{first.concept}:{first.item_id}"
