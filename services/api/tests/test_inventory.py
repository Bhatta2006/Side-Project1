"""Content inventory export: every record states its rights and review, never silently empty."""

import csv
import importlib.util
from collections import Counter
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "content" / "inventory.py"
spec = importlib.util.spec_from_file_location("inventory", SCRIPT)
assert spec and spec.loader
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


@pytest.fixture(scope="module")
def rows():
    return inventory.build_rows()


def test_no_record_has_an_empty_rights_or_review_field(rows):
    assert rows
    assert [r["record_id"] for r in rows if not r["rights_or_license"].strip()] == []
    assert [r["record_id"] for r in rows if not r["review_record"].strip()] == []


def test_unknown_rights_are_labelled_unknown_not_guessed(rows):
    lessons = [r for r in rows if r["asset_type"] == "lesson"]
    legacy = [r for r in lessons if r["provenance_origin"] == "not recorded"]
    assert legacy and all(r["rights_or_license"].startswith("unknown") for r in legacy)
    # Newer lessons state their provenance; their rights come from it, never a guess.
    recorded = [r for r in lessons if r not in legacy]
    assert all(r["provenance_origin"] == "original" for r in recorded)
    assert all(r["rights_or_license"] == "Socrat original, all rights reserved" for r in recorded)


def test_external_links_take_their_license_from_the_source_registry(rows):
    leetcode = next(r for r in rows if r["record_id"].startswith("external_problem:leetcode:"))
    assert leetcode["rights_or_license"] == "All rights reserved / site terms (unverified)"
    assert leetcode["license_status"] == "unverified"
    algorithms = next(r for r in rows if r["asset_type"] == "implementation_link")
    assert algorithms["rights_or_license"].startswith("MIT")
    assert algorithms["license_status"] == "unverified"


def test_record_counts_match_the_catalog(rows):
    from socrat.catalog.registry import default_catalog

    catalog = default_catalog()
    counts = Counter(r["asset_type"] for r in rows)
    assert counts["course"] == 3
    assert counts["lesson"] == len(catalog.concepts)
    assert counts["quiz"] == sum(len(c.quiz) for c in catalog.concepts.values())
    assert counts["native_problem"] == len(catalog.problems)
    assert counts["external_problem"] == 13889
    assert len({r["record_id"] for r in rows}) == len(rows)


def test_written_csv_has_the_new_columns_and_passes_the_check(tmp_path, rows):
    out = tmp_path / "inventory.csv"
    inventory.write_csv(rows, out)
    with out.open(encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle))
    for column in (
        "rights_or_license",
        "review_record",
        "pattern_ids",
        "band",
        "misconception_ids",
        "provenance_origin",
        "license_status",
        "last_verified_at",
    ):
        assert column in header
    assert inventory.problems(rows) == []
