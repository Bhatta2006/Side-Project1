"""Tasks a quiz cannot judge (master prompt 4, 9.4, 12.2): typed with rubrics, ordered with the
concept's other activities, self-checked or judged by a named person, and only a person's grade
counts as evidence."""

# ruff: noqa: F811
import copy

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.catalog.registry import default_catalog
from socrat.catalog.schema import Concept, Task
from socrat.coursegen import package
from socrat.engine import domains
from socrat.learn import tasks
from socrat.models import Evidence

CONCEPT = "zero:programs-and-output"
RUBRIC = [
    {"criterion": "Clear steps", "points": 2, "look_for": "Each step in order"},
    {"criterion": "Correct output", "points": 2, "look_for": "Says what prints"},
]
REFLECT = {
    "id": "think-back",
    "kind": "reflection",
    "prompt": "What surprised you about print?",
    "rubric": RUBRIC,
}
PERFORM = {
    "id": "explain-aloud",
    "kind": "oral",
    "prompt": "Record yourself explaining what this program prints and why.",
    "rubric": RUBRIC,
}


def test_who_judges_follows_the_kind():
    assert Task.model_validate(REFLECT).evaluator == "self"
    assert Task.model_validate(PERFORM).evaluator == "person"
    assert Task.model_validate(PERFORM | {"kind": "performance"}).evaluator == "person"


def test_sequence_must_name_activities_the_concept_has():
    base = default_catalog().concept(CONCEPT).model_dump(mode="json")
    ok = Concept.model_validate(
        base | {"tasks": [REFLECT], "sequence": ["lesson", "task:think-back", "quiz"]}
    )
    assert ok.sequence[1] == "task:think-back"
    with pytest.raises(ValueError, match="unknown activities"):
        Concept.model_validate(base | {"sequence": ["lesson", "task:nope"]})
    with pytest.raises(ValueError, match="repeats"):
        Concept.model_validate(base | {"sequence": ["lesson", "lesson"]})


def test_tasks_are_asked_for_when_the_competency_is_practised_by_doing():
    plain = default_catalog().concept(CONCEPT)
    assert not package.wants_tasks(plain)
    assert package.wants_tasks(plain, domains.ADAPTERS["music"])  # learned by doing
    outline = {"objectives": ["Explain print"], "assessment": ["quiz"], "practice": ["reflection"]}
    reflective = Concept.model_validate(plain.model_dump(mode="json") | {"outline": outline})
    assert package.wants_tasks(reflective)


@pytest.fixture
def with_tasks(monkeypatch):
    real = default_catalog()
    cat = copy.copy(real)
    cat.concepts = dict(real.concepts)
    cat.concepts[CONCEPT] = real.concepts[CONCEPT].model_copy(
        update={"tasks": [Task.model_validate(REFLECT), Task.model_validate(PERFORM)]}
    )
    monkeypatch.setattr(tasks, "catalog", lambda: cat)
    return cat


def _evidence(client) -> list[Evidence]:
    with Session(client.app.state.engine) as db:
        return list(db.scalars(select(Evidence).where(Evidence.kind == "performance")))


def test_self_checked_work_is_kept_but_never_counts(client, with_tasks):
    headers = login(client)
    onboard(client, headers)
    body = {"text": "Print shows text in order, one line each.", "met": ["Clear steps", "Made up"]}
    done = client.post(f"/api/v1/tasks/{CONCEPT}/think-back", json=body, headers=headers).json()
    assert done["status"] == "self_checked" and done["met"] == ["Clear steps"]
    assert _evidence(client) == []


def test_person_judged_work_waits_and_a_named_grade_becomes_evidence(client, with_tasks):
    client.app.state.settings.admin_subjects = ["boss"]
    headers = login(client)
    onboard(client, headers)
    body = {"text": "My recording explains both lines.", "link": "https://example.org/rec.mp3"}
    sent = client.post(f"/api/v1/tasks/{CONCEPT}/explain-aloud", json=body, headers=headers).json()
    assert sent["status"] == "awaiting_person" and _evidence(client) == []
    bad_link = client.post(
        f"/api/v1/tasks/{CONCEPT}/explain-aloud",
        json=body | {"link": "javascript:x"},
        headers=headers,
    )
    assert bad_link.status_code == 422

    admin = login(client, subject="boss", name="Boss")
    queue = client.get("/api/v1/admin/tasks", headers=admin).json()["items"]
    assert [q["id"] for q in queue] == [sent["id"]] and queue[0]["rubric"]
    url = f"/api/v1/admin/tasks/{sent['id']}/grade"
    full = {"Clear steps": 2, "Correct output": 1}
    assert (
        client.post(url, json={"reviewer": "Boss", "points": full}, headers=admin).status_code
        == 422
    )
    too_many = {"Clear steps": 3, "Correct output": 1}
    assert (
        client.post(
            url, json={"reviewer": "Asha Rao", "points": too_many}, headers=admin
        ).status_code
        == 422
    )
    graded = client.post(url, json={"reviewer": "Asha Rao", "points": full}, headers=admin).json()
    assert (
        graded["status"] == "graded"
        and graded["score"] == 0.75
        and graded["reviewer"] == "Asha Rao"
    )
    [row] = _evidence(client)
    assert row.score == 0.75 and row.details["reviewer"] == "Asha Rao"
    assert (
        client.post(url, json={"reviewer": "Asha Rao", "points": full}, headers=admin).status_code
        == 404
    )


def test_unknown_tasks_are_not_found(client, with_tasks):
    headers = login(client)
    onboard(client, headers)
    body = {"text": "Something long enough."}
    assert (
        client.post(f"/api/v1/tasks/{CONCEPT}/nope", json=body, headers=headers).status_code == 404
    )
    assert (
        client.post("/api/v1/tasks/zero:nope/think-back", json=body, headers=headers).status_code
        == 404
    )
