"""Provenance on authored content (Content Master Plan M1)."""

import pytest
from catalog_support import concept, quiz
from pydantic import ValidationError

from socrat.catalog.atoms import Atom
from socrat.catalog.registry import load
from socrat.catalog.schema import Concept, Provenance, QuizItem

ADAPTED_FROM = dict(
    source_id="tech-interview-handbook",
    title="Algorithms study cheatsheet",
    author="Yangshun Tay",
    url="https://www.techinterviewhandbook.org/algorithms/study-cheatsheet/",
    license_spdx="MIT",
    license_url="https://github.com/yangshun/tech-interview-handbook/blob/main/LICENSE",
    retrieved_at="2026-10-16",
    content_sha256="0" * 64,
    changes="Reworded and reordered; examples replaced.",
)


def test_every_existing_content_file_still_loads_without_provenance():
    catalog = load()
    # The 61 concepts that predate provenance still load without it; newer ones record it.
    assert sum(c.provenance is None for c in catalog.concepts.values()) == 61
    assert all(c.provenance.origin == "original" for c in catalog.concepts.values() if c.provenance)
    assert all(q.provenance is None for c in catalog.concepts.values() for q in c.quiz)
    assert all(p.provenance is None for _, p in catalog.problems.values())
    assert all(pack.provenance is None for pack in catalog.atom_packs.values())


def test_provenance_defaults_describe_unreviewed_socrat_original():
    value = Provenance()
    assert value.origin == "original"
    assert value.author == "Socrat Learning"
    assert value.review is None
    assert value.version == 1
    assert value.rights == "Socrat original, all rights reserved"


def test_adapted_content_must_name_what_it_was_adapted_from():
    with pytest.raises(ValidationError, match="adapted content must cite"):
        Provenance(origin="adapted")
    assert Provenance(origin="adapted", authors_adapted_from=[ADAPTED_FROM]).origin == "adapted"


def test_original_content_cannot_claim_adapted_sources():
    with pytest.raises(ValidationError, match="only adapted content"):
        Provenance(origin="original", authors_adapted_from=[ADAPTED_FROM])


def test_review_records_need_a_named_reviewer_and_a_date():
    with pytest.raises(ValidationError):
        Provenance(review={"by": "", "at": "2026-10-16"})
    with pytest.raises(ValidationError):
        Provenance(review={"by": "A Reviewer", "at": "yesterday"})


def test_provenance_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        Provenance(origin="original", reviewed=True)


def test_concepts_and_quiz_items_accept_optional_provenance():
    payload = concept("loops", "m1")
    payload["provenance"] = {"origin": "original", "author": "Socrat Learning"}
    payload["quiz"] = quiz("loops")
    payload["quiz"][0]["provenance"] = {"origin": "original"}
    parsed = Concept.model_validate(payload)
    assert parsed.provenance is not None and parsed.provenance.origin == "original"
    assert parsed.quiz[0].provenance is not None
    assert QuizItem.model_validate(quiz("x")[0]).provenance is None


def test_atom_payload_sent_to_learners_is_unchanged():
    """Provenance is pack-level, so the atom JSON in session blocks keeps its shape."""
    assert "provenance" not in Atom.model_fields
