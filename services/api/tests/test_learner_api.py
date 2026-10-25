"""End-to-end learner journey through the v2 API, on a freshly migrated database."""

import json
from datetime import date

import pytest
from runner_support import SIGNING, WORKER, profiles

from socrat.catalog.registry import default_catalog
from socrat.execution.protocol import CaseResult, ExecutionResult, JobEnvelope, sign

ORIGIN = "http://localhost:3000"


@pytest.fixture
def client(tmp_path):
    from alembic import command
    from alembic.config import Config
    from fastapi.testclient import TestClient

    from socrat.config import Settings
    from socrat.main import create_app

    url = f"sqlite:///{tmp_path / 'learner.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    settings = Settings(
        database_url=url,
        environment="test",
        dev_login_enabled=True,
        execution_profiles=profiles(),
        browser_runtimes=[],
        execution_signing_secret=SIGNING,
        execution_worker_secret=WORKER,
    )
    app = create_app(settings)
    with TestClient(app, base_url=ORIGIN) as test_client:
        yield test_client
    app.state.engine.dispose()


def login(client, subject="ada", name="Ada"):
    response = client.post(
        "/api/v1/auth/dev-login",
        json={"subject": subject, "display_name": name},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200
    return {"Origin": ORIGIN, "X-CSRF-Token": client.get("/api/v1/me").json()["csrf_token"]}


def onboard(client, headers, course="zero", level="brand-new", **extra):
    assert (
        client.patch(
            "/api/v1/me", json={"birth_year": 2001, "timezone": "Asia/Kolkata"}, headers=headers
        ).status_code
        == 200
    )
    body = dict(
        course=course,
        language="python",
        level=level,
        minutes_per_day=45,
        weekdays=[0, 1, 2, 3, 4, 5, 6],
        **extra,
    )
    response = client.post("/api/v1/enrollments", json=body, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def complete_curriculum(client):
    """An already-taught learner for tests that browse the unlocked practice pool."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from socrat.learn import service as learn
    from socrat.models import ActivityRecord, Enrollment

    cat = default_catalog()
    with Session(client.app.state.engine) as db, db.begin():
        enrollment = db.scalar(select(Enrollment).where(Enrollment.active.is_(True)))
        scope = learn.curriculum(cat, enrollment)
        ids = {f"lesson:{c}" for c in scope} | {
            f"checkpoint:{cat.owner[c]}:{cat.module_of(c)}" for c in scope
        }
        for activity in ids - learn.completed_for(db, enrollment):
            db.add(
                ActivityRecord(enrollment_id=enrollment.id, activity_id=activity, completed_at=1)
            )


def test_age_gate_blocks_under_thirteen(client):
    headers = login(client)
    response = client.patch("/api/v1/me", json={"birth_year": 2020}, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "minimum_age"
    body = dict(
        course="zero", language="python", level="brand-new", minutes_per_day=30, weekdays=[0]
    )
    assert (
        client.post("/api/v1/enrollments", json=body, headers=headers).json()["error"]["code"]
        == "profile_incomplete"
    )


def test_beginner_skips_placement_and_learns(client):
    headers = login(client)
    assert onboard(client, headers)["status"] == "active"
    courses = client.get("/api/v1/courses").json()["items"]
    assert [c["id"] for c in courses[:3]] == ["zero", "dsa", "cp"]

    today = client.get("/api/v1/today").json()
    assert today["greeting"].endswith("Ada")
    first = today["next"]
    assert first["id"] == "lesson:zero:programs-and-output"

    concept = client.get("/api/v1/concepts/zero:programs-and-output").json()
    assert concept["resources"] and all(
        not r["languages"] or "python" in r["languages"] for r in concept["resources"]
    )
    assert client.post(f"/api/v1/activities/{first['id']}/complete", headers=headers).json()[
        "completed"
    ]

    quiz = client.get("/api/v1/quiz/quiz:zero:programs-and-output").json()
    catalog = default_catalog()
    # Options are shuffled per session; the server maps display positions back.
    answers = {
        q.id: q.shown(quiz["id"])["answer"]
        for q in catalog.concept("zero:programs-and-output").quiz
    }
    for question in quiz["questions"]:
        view = client.post(
            "/api/v1/quiz/quiz:zero:programs-and-output/answer",
            json={"item": question["id"], "choice": answers[question["id"]]},
            headers=headers,
        ).json()
    assert view["completed"] and view["score"] == 1.0
    assert all(q["correct"] for q in view["questions"])

    today = client.get("/api/v1/today").json()
    assert {d["id"] for d in today["done"]} >= {
        "lesson:zero:programs-and-output",
        "quiz:zero:programs-and-output",
    }
    assert today["streak"]["studied_today"]
    progress = client.get("/api/v1/progress").json()
    first_module = progress["modules"][0]["concepts"][0]
    # One perfect quiz moves an unplaced beginner up, but a single event is capped (≤ 0.15).
    assert first_module["evidence"] == 1 and 1 / 3 < first_module["mastery"] <= 1 / 3 + 0.15 + 1e-9


def test_schedule_update_reflows_the_plan_and_explains_it(client):
    headers = login(client)
    onboard(client, headers)
    before = client.get("/api/v1/plan").json()
    response = client.patch(
        "/api/v1/enrollments/current",
        json={"minutes_per_day": 15, "weekdays": [5, 6], "target_date": "2030-01-01"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    enrollment = response.json()["enrollment"]
    assert enrollment["minutes_per_day"] == 15 and enrollment["weekdays"] == [5, 6]
    assert enrollment["goal"]["target_date"] == "2030-01-01"
    after = client.get("/api/v1/plan").json()
    assert after["projected_finish"] > before["projected_finish"]
    assert after["revisions"][0]["reasons"][0].startswith("You updated your plan: 15 min")
    # Today always counts; every later scheduled day follows the new weekdays.
    assert all(date.fromisoformat(d["date"]).weekday() in {5, 6} for d in after["days"][1:])

    cleared = client.patch(
        "/api/v1/enrollments/current", json={"clear_target_date": True}, headers=headers
    ).json()
    assert "target_date" not in cleared["enrollment"]["goal"]
    unchanged = client.patch("/api/v1/enrollments/current", json={}, headers=headers)
    assert unchanged.status_code == 200
    assert len(client.get("/api/v1/plan").json()["revisions"]) == len(after["revisions"]) + 1
    bad = client.patch("/api/v1/enrollments/current", json={"weekdays": [9]}, headers=headers)
    assert bad.json()["error"]["code"] == "validation_failed"


def test_placement_adapts_and_seeds_the_plan(client):
    headers = login(client)
    enrollment = onboard(
        client, headers, course="dsa", level="knows-basics", target_role="new-grad"
    )
    assert enrollment["status"] == "placement"
    catalog = default_catalog()
    asked = 0
    while True:
        view = client.get("/api/v1/placement").json()
        if view["done"]:
            break
        question = view["question"]
        concept = next(
            c for c in catalog.concepts.values() if any(q.id == question["id"] for q in c.quiz)
        )
        item = next(q for q in concept.quiz if q.id == question["id"])
        correct = item.shown(f"placement:{int(enrollment['id'].replace('-', '')[:8], 16)}")[
            "answer"
        ]
        # Knows the basics course, not yet DSA.
        known = concept in [catalog.concept(k) for k in catalog.course_concepts("zero")]
        choice = correct if known else None
        client.post(
            "/api/v1/placement/answer",
            json={"item": question["id"], "choice": choice},
            headers=headers,
        )
        asked += 1
        assert asked <= 12
    summary = client.get("/api/v1/placement/summary").json()
    assert summary["known_concepts"] and summary["starting_concept"]
    plan = client.get("/api/v1/plan").json()
    bridge = [m for m in plan["modules"] if m["bridge"]]
    assert bridge, "beginner foundations appear as a bridge"
    statuses = {c["status"] for m in bridge for c in m["concepts"]}
    assert "assumed" in statuses
    assert plan["revisions"] and plan["days"][0]["items"]


def test_submit_round_trip_records_evidence_and_isolation(client):
    headers = login(client)
    onboard(client, headers)
    worker = {"Authorization": "Bearer " + WORKER}
    images = [p["image"] for p in profiles()]
    assert (
        client.post(
            "/api/v1/execution/worker/heartbeat",
            json={"worker_id": "w1", "images": images},
            headers=worker,
        ).status_code
        == 200
    )
    source = 'name = input().strip()\nprint(f"Hello, {name}! Welcome to Socrat.")\n'
    job = client.post(
        "/api/v1/problems/greeting/submit", json={"source": source}, headers=headers
    ).json()
    assert job["status"] == "queued"

    envelope = JobEnvelope.model_validate(
        client.post(
            "/api/v1/execution/worker/claim", json={"worker_id": "w1"}, headers=worker
        ).json()["job"]
    )
    cases = [
        CaseResult(
            index=i,
            status="passed",
            wall_ms=5,
            stdout=t.expected or "" if t.visibility == "public" else "",
        )
        for i, t in enumerate(envelope.tests)
    ]
    manifest = envelope.manifest
    result = ExecutionResult(
        job_id=manifest.job_id,
        nonce=manifest.nonce,
        code_hash=manifest.code_hash,
        test_digest=manifest.test_digest,
        image=manifest.image,
        operational_status="healthy",
        cases=cases,
        reason_code="execution_finalized",
    ).model_dump()
    response = client.post(
        "/api/v1/execution/worker/result",
        json={
            "worker_id": "w1",
            "envelope": {"result": result, "signature": sign(result, SIGNING)},
        },
        headers=worker,
    )
    assert response.json()["verdict"] == "accepted"
    hidden = [c for c in response.json()["cases"] if not c["public"]]
    assert hidden and all(c["input"] is None and c["expected"] is None for c in hidden)

    problem = client.get("/api/v1/problems/greeting").json()
    assert problem["solved"] and problem["draft"] == source
    assert "problem:greeting" in {d["id"] for d in client.get("/api/v1/today").json()["done"]}
    progress = client.get("/api/v1/progress").json()
    assert progress["solves"]["independent_solves"] == 1

    other = login(client, subject="bob", name="Bob")
    assert other  # bob is now the active session
    assert client.get(f"/api/v1/submissions/{job['id']}").status_code == 404


def test_assistant_is_socratic_and_gates_the_answer(client):
    headers = login(client)
    onboard(client, headers)

    def ask(message, intent="chat", new_attempt=False):
        response = client.post(
            "/api/v1/assistant/messages",
            json={
                "scope": "problem:time-convert",
                "message": message,
                "intent": intent,
                "new_attempt": new_attempt,
            },
            headers=headers,
        )
        assert response.status_code == 200
        events = [
            (
                block.split("\n")[0].removeprefix("event: "),
                json.loads(block.split("\n")[1].removeprefix("data: ")),
            )
            for block in response.text.strip().split("\n\n")
        ]
        return dict(events)

    first = ask("help")
    assert first["meta"]["allowed_level"] == 0
    assert "What have you tried" in first["done"]["text"]
    second = ask("I divided by 60 but my minutes are wrong for the second example")
    assert second["meta"]["allowed_level"] == 1
    blocked = ask("just give me the answer", intent="reveal")
    assert blocked["meta"]["reveal_blocked"]
    assert "```" not in blocked["done"]["text"]
    thread = client.get("/api/v1/assistant/thread", params={"scope": "problem:time-convert"}).json()
    assert [m["role"] for m in thread["messages"]][:2] == ["user", "assistant"]
    assert (
        client.post(
            "/api/v1/assistant/messages", json={"scope": "../etc", "message": "x"}, headers=headers
        ).status_code
        == 422
    )


def test_export_and_delete_account(client):
    headers = login(client)
    onboard(client, headers)
    data = client.get("/api/v1/me/export").json()
    assert data["profile"]["display_name"] == "Ada" and data["enrollments"]
    assert client.delete("/api/v1/me", headers=headers).status_code == 204
    assert client.get("/api/v1/me").status_code == 401


def test_concepts_link_curated_practice_and_company_lists(client):
    headers = login(client)
    onboard(client, headers, course="dsa", level="new-to-programming")
    complete_curriculum(client)
    concept = client.get("/api/v1/concepts/dsa:two-pointers").json()
    practice = concept["more_practice"]
    assert practice and all("dsa:two-pointers" in p["concepts"] for p in practice)
    # A not-yet-started learner is offered easier problems first.
    assert practice[0]["difficulty"] == "easy"
    assert all(set(p) >= {"title", "url", "platform", "difficulty"} for p in practice)
    assert concept["handbook"][0]["url"].startswith("https://cses.fi/book/book.pdf#page=")
    assert all(
        i["url"].startswith("https://github.com/TheAlgorithms/") for i in concept["implementations"]
    )

    listing = client.get("/api/v1/companies?q=goo").json()
    assert any(c["slug"] == "google" for c in listing["items"])
    google = client.get("/api/v1/companies/google?window=thirty-days&difficulty=easy").json()
    assert google["total"] > 0
    assert all(p["difficulty"] == "easy" and p["window"] == "thirty-days" for p in google["items"])
    assert all(p["concept"] is None or p["concept"]["band"] for p in google["items"])
    assert client.get("/api/v1/companies/not-a-company").status_code == 404


def test_zero_problems_start_from_beginner_code(client):
    headers = login(client)
    onboard(client, headers)
    starter = client.get("/api/v1/problems/ticket-stub").json()["starter"]
    assert "input()" in starter and "sys" not in starter and "def main" not in starter
