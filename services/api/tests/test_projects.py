"""Project schema/loader and the JSON contracts that must match the content models."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from socrat.catalog import projects
from socrat.catalog.registry import CatalogError, load

ROOT = Path(__file__).resolve().parents[3]
VALID = {
    "id": "expense-tracker",
    "course": "zero",
    "title": "Expense tracker (CLI)",
    "summary": "Record, list and total expenses from the command line, saved to a file.",
    "skills": ["input validation", "lists and dictionaries", "functions", "file persistence"],
    "concepts": ["zero:functions", "zero:lists"],
    "constraints": ["At least 8 functions", "At least 10 tests", "README with usage"],
    "milestones": [
        {
            "id": "add-and-list",
            "title": "Add and list expenses",
            "checklist": ["Add command works"],
        },
        {"id": "persist", "title": "Save and load", "checklist": ["Data survives a restart"]},
        {"id": "report", "title": "Totals and tests", "checklist": ["10 tests pass"]},
    ],
    "rubric": [
        {"criterion": "Correctness", "weight": 40, "full_marks": "Visible and hidden tests pass"},
        {"criterion": "Structure", "weight": 20, "full_marks": "Small functions, clear names"},
        {"criterion": "Tests", "weight": 20, "full_marks": "Normal, edge and failure cases"},
        {"criterion": "Readability", "weight": 10, "full_marks": "Comments explain why"},
        {"criterion": "README", "weight": 10, "full_marks": "Purpose, how to run, examples"},
    ],
    "self_review": ["Did every function do one thing?"],
    "provenance": {"origin": "original"},
}


@pytest.fixture(scope="module")
def catalog():
    return load()


def write(root, payload, name=None):
    folder = root / payload["course"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name or payload['id']}.yaml").write_text(yaml.safe_dump(payload), "utf-8")


def test_valid_project_loads_and_starts_provisional(tmp_path, catalog):
    write(tmp_path, VALID)
    project = projects.load(tmp_path, catalog)["zero:expense-tracker"]
    assert project.status == "provisional"
    assert "zero:expense-tracker" not in catalog.projects  # a temp root is not the catalog


def test_rubric_weights_must_total_100():
    payload = copy.deepcopy(VALID)
    payload["rubric"][0]["weight"] = 30
    with pytest.raises(ValidationError, match="total 100"):
        projects.Project.model_validate(payload)


@pytest.mark.parametrize(
    "change, message",
    [
        ({"course": "nowhere"}, "unknown course"),
        ({"concepts": ["zero:no-such-concept"]}, "unknown concept"),
    ],
)
def test_broken_references_fail(tmp_path, catalog, change, message):
    write(tmp_path, {**copy.deepcopy(VALID), **change})
    with pytest.raises(CatalogError, match=message):
        projects.load(tmp_path, catalog)


def test_file_name_must_match_the_project_id(tmp_path, catalog):
    write(tmp_path, VALID, name="other")
    with pytest.raises(CatalogError, match="file path must match"):
        projects.load(tmp_path, catalog)


def test_committed_json_contracts_match_the_content_models():
    spec = importlib.util.spec_from_file_location(
        "export_contracts", ROOT / "scripts" / "content" / "export_contracts.py"
    )
    assert spec and spec.loader
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    for name, model in exporter.CONTRACTS.items():
        path = ROOT / "contracts" / "schemas" / name
        assert path.exists(), f"{name} missing: run python scripts/content/export_contracts.py"
        assert json.loads(path.read_text(encoding="utf-8")) == model.model_json_schema(), (
            f"{name} is stale: run python scripts/content/export_contracts.py"
        )
