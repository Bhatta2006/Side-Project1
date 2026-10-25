"""Curriculum boundaries, progressive questions, selected sources and ungraded lessons."""

from urllib.parse import urlparse

import pytest
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.catalog import practice
from socrat.catalog.registry import default_catalog
from socrat.learn import resources
from socrat.learn import service as learn
from socrat.mastery.model import ConceptState, placed
from socrat.models import now


@pytest.fixture
def tiny_index(monkeypatch):
    def problem(pid, topics):
        return dict(
            id=pid,
            title=pid,
            url=f"https://leetcode.com/problems/{pid}/",
            platform="LeetCode",
            difficulty="easy",
            rating=None,
            concepts=topics,
            companies=1,
            sheets=[],
        )

    index = practice.PracticeIndex(
        problems={
            p["id"]: p
            for p in [
                problem("lc:output", ["zero:programs-and-output"]),
                problem("lc:combined", ["zero:programs-and-output", "zero:variables-and-types"]),
                problem("lc:advanced", ["dsa:arrays-hashing"]),
                problem("lc:unmapped", []),
            ]
        },
        companies={
            "google": dict(
                name="Google",
                problems=[
                    (pid, 50, "thirty-days")
                    for pid in ["lc:output", "lc:combined", "lc:advanced", "lc:unmapped"]
                ],
            )
        },
    )
    for pid, p in index.problems.items():
        for topic in p["concepts"]:
            index.by_concept.setdefault(topic, []).append(pid)
    monkeypatch.setattr(practice, "default_index", lambda: index)
    return index


def test_progressively_unlocks_all_sorts_company_counts_and_question_writes(client, tiny_index):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    for sort in ["recommended", "popular", "title", "easiest", "hardest"]:
        assert client.get(f"/api/v1/library?sort={sort}").json()["total"] == 0
    assert client.get("/api/v1/companies").json()["items"] == []
    assert client.get("/api/v1/companies/google").json()["total"] == 0
    assert (
        client.put(
            "/api/v1/library/problems/lc:combined", json={"status": "solved"}, headers=headers
        ).status_code
        == 403
    )
    assert (
        client.post("/api/v1/library/problems/lc:output/opened", headers=headers).status_code == 403
    )
    assert (
        client.post(
            "/api/v1/activities/lesson:zero:programs-and-output/complete", headers=headers
        ).status_code
        == 200
    )
    for sort in ["recommended", "popular", "title", "easiest", "hardest"]:
        result = client.get(f"/api/v1/library?sort={sort}").json()
        assert result["total"] == 1 and result["items"][0]["id"] == "lc:output"
    assert client.get("/api/v1/companies").json()["items"][0]["problems"] == 1
    assert client.get("/api/v1/companies/google").json()["total"] == 1
    assert client.get("/api/v1/library?concept=dsa:arrays-hashing&q=advanced").json()["items"] == []
    assert (
        client.put(
            "/api/v1/library/problems/lc:output", json={"bookmarked": True}, headers=headers
        ).status_code
        == 200
    )
    client.post("/api/v1/activities/lesson:zero:variables-and-types/complete", headers=headers)
    assert client.get("/api/v1/library?status=all").json()["total"] == 2
    assert client.get("/api/v1/companies/google").json()["total"] == 2
    meta = client.get("/api/v1/library/meta").json()
    assert meta["platforms"] == {"LeetCode": 2}


def test_course_scope_holds_for_search_direct_urls_and_tutor(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    concepts = client.get("/api/v1/library/meta").json()["concepts"]
    zero = default_catalog().course_concepts("zero")
    assert len(concepts) == len(zero) and all(c["id"].startswith("zero:") for c in concepts)
    for url in [
        "/concepts/dsa:complexity",
        "/quiz/quiz:dsa:complexity",
        "/playground/lessons/dsa:complexity",
        "/problems/two-sum",
    ]:
        assert client.get("/api/v1" + url).status_code == 404
    assert (
        client.post(
            "/api/v1/concepts/dsa:complexity/explain", json={"style": "simpler"}, headers=headers
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/activities/lesson:dsa:complexity/complete", headers=headers
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/playground/generate",
            json={"concept": "dsa:complexity", "confusion": "Explain the cost"},
            headers=headers,
        ).status_code
        == 404
    )
    outside_problem = next(
        pid for pid, (course, _) in default_catalog().problems.items() if course == "dsa"
    )
    assert (
        client.put(
            f"/api/v1/problems/{outside_problem}/draft",
            json={"source": "print(1)"},
            headers=headers,
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/problems/{outside_problem}/run", json={"source": "print(1)"}, headers=headers
        ).status_code
        == 404
    )
    from test_tutor_tools import call, toolbox_for

    result, failed = call(toolbox_for(client), "get_concept_guide", concept="dsa:complexity")
    assert failed and "outside" in result
    result, failed = call(toolbox_for(client), "search_library", query="", limit=10)
    assert not failed and result["total"] == 0


def test_bridge_topics_remain_in_enrolled_course_scope(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers, course="dsa", level="new-to-programming")
    concepts = client.get("/api/v1/library/meta").json()["concepts"]
    assert any(c["id"].startswith("zero:") for c in concepts)
    assert any(c["id"].startswith("dsa:") for c in concepts)
    assert not any(c["id"].startswith("cp:") for c in concepts)
    assert client.get("/api/v1/concepts/zero:programs-and-output").status_code == 200
    assert client.get("/api/v1/concepts/cp:fast-io").status_code == 404


def test_placement_knowledge_unlocks_topics_without_self_reported_solves(client, tiny_index):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    with Session(client.app.state.engine) as db, db.begin():
        user_id = client.get("/api/v1/me").json()["id"]
        enrollment = learn.active_enrollment(db, user_id)
        learn.set_state(db, enrollment, "zero:programs-and-output", placed(True, now()), now())
    assert client.get("/api/v1/library").json()["total"] == 1


def test_every_concept_has_deeper_teaching():
    cat = default_catalog()
    for qualified, concept in cat.concepts.items():
        # Programming from Zero names the cost section for beginners (no Big-O yet).
        edge = "Things to watch for" if qualified.startswith("zero:") else "Boundary cases and cost"
        for heading in ["Worked walkthrough", "Why this works", edge, "Check your understanding"]:
            assert heading in concept.lesson, qualified
    assert sum(len(c.lesson.split()) for c in cat.concepts.values()) > 37000


def test_only_selected_course_sources_are_used_and_language_is_respected():
    data = resources.course_links()
    assert set(data) == set(default_catalog().concepts)
    numbers = {q["number"] for r in data.values() for q in r["exercises"]}
    assert len(numbers) == 28 and 71 not in numbers and 73 not in numbers
    assert resources.selected("zero:recursion", "java", "exercises") == []
    assert resources.selected("zero:recursion", "python", "exercises")
    for content in data.values():
        for link in content["roadmap"]:
            parsed = urlparse(link["url"])
            assert parsed.netloc == "github.com"
            assert "/roadmaps/" in parsed.path and "/content/" in parsed.path
            assert parsed.path.split("/roadmaps/")[1].split("/")[0] in {
                "python",
                "cpp",
                "java",
                "datastructures-and-algorithms",
            }


def test_playground_suggests_weak_topics_from_progress(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    with Session(client.app.state.engine) as db, db.begin():
        enrollment = learn.active_enrollment(db, client.get("/api/v1/me").json()["id"])
        learn.set_state(
            db,
            enrollment,
            "zero:programs-and-output",
            ConceptState(alpha=1, beta=4, evidence_count=2, failures=2),
            now(),
        )
    overview = client.get("/api/v1/playground").json()
    assert overview["suggestions"][0]["id"] == "zero:programs-and-output"
    assert client.get("/api/v1/playground/lessons/zero:programs-and-output").status_code == 404


def test_independent_work_blocks_playground(client, monkeypatch):  # noqa: F811
    from socrat.learn import sessions

    headers = login(client)
    onboard(client, headers)
    monkeypatch.setattr(sessions, "instruction_blocked", lambda *args: True)
    assert client.get("/api/v1/playground").status_code == 423
    assert (
        client.post(
            "/api/v1/playground/generate",
            json={"confusion": "Explain binary search"},
            headers=headers,
        ).status_code
        == 423
    )


def test_roadmap_tracks_completion_from_saved_activity(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)

    def first():
        return next(
            c
            for m in client.get("/api/v1/plan").json()["modules"]
            for c in m["concepts"]
            if c["concept"] == "zero:programs-and-output"
        )

    assert first()["lesson_done"] is False
    client.post("/api/v1/activities/lesson:zero:programs-and-output/complete", headers=headers)
    node = first()
    assert node["lesson_done"] and not node["quiz_done"] and node["roadmap_resources"]
