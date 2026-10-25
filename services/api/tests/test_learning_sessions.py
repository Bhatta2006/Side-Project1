"""Trust boundaries and evidence integrity for the content-placement playbook."""

import json
import sys

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from runner_support import SIGNING, WORKER, profiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.catalog.atoms import Adapter, AtomPack
from socrat.catalog.registry import default_catalog
from socrat.catalog.validate_atoms import check_adapter
from socrat.execution.protocol import CaseResult, ExecutionResult, JobEnvelope, sign
from socrat.learn import service as learn
from socrat.learn import sessions
from socrat.learn.feedback import submission_copy
from socrat.mastery.model import ConceptState
from socrat.models import (
    ContentIssue,
    Enrollment,
    Evidence,
    LearningSession,
    OutboxEvent,
    Submission,
    now,
)
from socrat.planner.sessions import compose


def complete_current(client, headers, view):  # noqa: F811
    if view["current"]["kind"] == "atom" and view["current"]["atom"].get("check"):
        with Session(client.app.state.engine) as db:
            row = db.get(LearningSession, view["id"])
            atom = row.payload["blocks"][view["index"]]["atom"]
            step = atom["steps"][row.payload["step"]]
            order = sessions.option_order(
                row.id, view["index"], row.payload["step"], len(step["options"])
            )
            choice = order.index(step["answer"])
        body = dict(
            block=view["index"], step=view["current"]["atom"]["check"]["step"], choice=choice
        )
        response = client.post(
            f"/api/v1/learning-sessions/{view['id']}/answer", json=body, headers=headers
        )
        assert response.status_code == 200, response.text
    body = {"block": view["index"]}
    if view["current"]["kind"] == "reflection":
        body["reflection"] = "clear"
    response = client.post(
        f"/api/v1/learning-sessions/{view['id']}/advance", json=body, headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def verified_solve(client, headers, pid):  # noqa: F811
    worker = {"Authorization": "Bearer " + WORKER}
    response = client.post(
        "/api/v1/execution/worker/heartbeat",
        json={"worker_id": "playbook-worker", "images": [p["image"] for p in profiles()]},
        headers=worker,
    )
    assert response.status_code == 200
    response = client.post(
        f"/api/v1/problems/{pid}/submit",
        json={"source": default_catalog().problem(pid).reference},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    envelope = JobEnvelope.model_validate(
        client.post(
            "/api/v1/execution/worker/claim", json={"worker_id": "playbook-worker"}, headers=worker
        ).json()["job"]
    )
    manifest = envelope.manifest
    result = ExecutionResult(
        job_id=manifest.job_id,
        nonce=manifest.nonce,
        code_hash=manifest.code_hash,
        test_digest=manifest.test_digest,
        image=manifest.image,
        operational_status="healthy",
        cases=[
            CaseResult(
                index=i,
                status="passed",
                wall_ms=5,
                stdout=(t.expected or "") if t.visibility == "public" else "",
            )
            for i, t in enumerate(envelope.tests)
        ],
        reason_code="execution_finalized",
    ).model_dump()
    response = client.post(
        "/api/v1/execution/worker/result",
        json={
            "worker_id": "playbook-worker",
            "envelope": {"result": result, "signature": sign(result, SIGNING)},
        },
        headers=worker,
    )
    assert response.status_code == 200 and response.json()["verdict"] == "accepted", response.text


def test_starter_content_has_explicit_versions_rights_and_language_adapters():
    catalog = default_catalog()
    assert len(catalog.atom_packs) == 30
    for course in ("zero", "dsa", "cp"):
        # New concepts inserted into the starter range carry pattern packs, not reviewed concept packs,
        # so the starter range is the first ten pre-expansion concepts.
        starters = [
            c for c in catalog.course_concepts(course) if catalog.concepts[c].provenance is None
        ][:10]
        assert len(starters) == 10 and set(starters) <= catalog.atom_packs.keys()
    for pack in catalog.atom_packs.values():
        assert pack.status == "released" and pack.review
        worked = next(a for a in pack.atoms if a.kind == "worked")
        assert set(worked.adapters) == {"python", "cpp", "java"}
        assert len({a.expected for a in worked.adapters.values()}) == 1
    repairs = {
        a.misconception for p in catalog.atom_packs.values() for a in p.atoms if a.kind == "micro"
    }
    assert len(repairs) == 31


def test_atom_publication_rejects_unreviewed_or_invalid_content():
    raw = next(iter(default_catalog().atom_packs.values())).model_dump()
    raw["review"] = None
    with pytest.raises(ValidationError, match="human review"):
        AtomPack.model_validate(raw)
    raw["status"] = "draft"
    raw["atoms"][0]["body"] = "word " * 121
    with pytest.raises(ValidationError, match="words"):
        AtomPack.model_validate(raw)


def test_adapter_checker_rejects_plausible_but_wrong_output():
    with pytest.raises(ValueError, match="disagrees"):
        check_adapter(
            "python", Adapter(code="print(3)", expected="4\n"), {"python": [sys.executable]}
        )


@pytest.mark.parametrize("minutes", [10, 20, 30, 45, 60, 90])
def test_session_composer_preserves_independence_and_one_new_idea(minutes):
    catalog = default_catalog()
    blocks = compose(
        catalog,
        "zero:programs-and-output",
        {},
        ["echo-reading"],
        minutes,
        True,
        False,
        None,
        {},
        False,
        False,
        100,
        "python",
    )
    assert len({b["concept"] for b in blocks}) == 1
    assert sum(b.get("mode") == "independent" for b in blocks) == 1
    assert sum(b["seconds"] for b in blocks) <= minutes * 60 + 10
    assert not any(b.get("mode") == "guided" for b in blocks)
    repairs = compose(
        catalog,
        "dsa:binary-search",
        {},
        ["lower-bound-queries", "koko-speed"],
        minutes,
        False,
        False,
        None,
        {"binary-search-repair": 2},
        True,
        False,
        100,
        "cpp",
    )
    assert sum(b.get("atom", {}).get("kind") == "micro" for b in repairs) == 1


def test_strong_or_slow_correct_receives_strategy_not_remediation():
    catalog = default_catalog()
    strong = ConceptState(alpha=20, beta=1, evidence_count=12)
    blocks = compose(
        catalog,
        "dsa:binary-search",
        {"dsa:binary-search": strong},
        ["koko-speed"],
        30,
        False,
        False,
        None,
        {},
        False,
        False,
        100,
        "java",
    )
    assert not any(b.get("atom", {}).get("kind") in {"concept", "worked", "micro"} for b in blocks)
    assert any(b.get("atom", {}).get("kind") == "pattern" for b in blocks)


def test_session_hides_answers_requires_real_work_and_exports_truthful_summary(client, monkeypatch):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    response = client.post("/api/v1/learning-sessions", json={"minutes": 30}, headers=headers)
    assert response.status_code == 200, response.text
    view = response.json()
    assert view["concept"] == "zero:programs-and-output"
    assert (
        client.post("/api/v1/learning-sessions", json={"minutes": 60}, headers=headers).json()["id"]
        == view["id"]
    )
    assert '"answer"' not in json.dumps(view) and '"expected"' not in json.dumps(view)
    reserved = next(b["problem"] for b in view["blocks"] if b.get("mode") == "independent")
    assert (
        client.post(
            f"/api/v1/problems/{reserved}/submit", json={"source": "print(0)"}, headers=headers
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/learning-sessions/{view['id']}/advance", json={"block": 9}, headers=headers
        ).status_code
        == 409
    )
    initial = client.get("/api/v1/me/export").json()
    assert initial["learning_sessions"] and "atoms" not in json.dumps(initial["learning_sessions"])
    while view["current"]["kind"] != "problem":
        before = len(client.get("/api/v1/me/export").json()["evidence"])
        kind = view["current"].get("atom", {}).get("kind")
        if kind == "visualizer":
            assert (
                client.post(
                    f"/api/v1/learning-sessions/{view['id']}/advance",
                    json={"block": view["index"]},
                    headers=headers,
                ).status_code
                == 409
            )
        view = complete_current(client, headers, view)
        if kind in {"hook", "worked", "visualizer"}:
            assert len(client.get("/api/v1/me/export").json()["evidence"]) == before
    assert view["current"]["mode"] == "independent"
    response = client.post(
        f"/api/v1/learning-sessions/{view['id']}/advance",
        json={"block": view["index"]},
        headers=headers,
    )
    assert (
        response.status_code == 409
        and response.json()["error"]["code"] == "independent_attempt_required"
    )
    assert client.get("/api/v1/concepts/zero:programs-and-output").status_code == 423
    assert client.get("/api/v1/quiz/quiz:zero:programs-and-output").status_code == 423
    tutor = client.post(
        "/api/v1/assistant/messages",
        json={"scope": "general", "message": "Give me the solution"},
        headers=headers,
    )
    assert tutor.status_code == 200 and "independent challenge" in tutor.text
    verified_solve(client, headers, view["current"]["problem"])
    while not view["finished"]:
        view = complete_current(client, headers, view)
    summary = view["summary"]
    assert summary["independent_solves"] == 1 and summary["assisted_solves"] == 0
    assert (
        summary["evidence"] == 3
    )  # guided reasoning, independently judged solve, structured explanation
    assert summary["next"]["title"] and summary["changes"]
    assert summary["evidence_ids"]
    for _ in range(2):
        assert (
            client.post(
                f"/api/v1/learning-sessions/{view['id']}/summary-viewed", headers=headers
            ).status_code
            == 200
        )
    with Session(client.app.state.engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(OutboxEvent)
                .where(OutboxEvent.kind == "learning.summary_viewed")
            )
            == 1
        )
    # The report is pinned; later practice cannot rewrite what this session achieved.
    assert client.get(f"/api/v1/learning-sessions/{view['id']}").json()["summary"] == summary
    from socrat.learn import session_routes

    tomorrow = now() + 86400
    monkeypatch.setattr(session_routes, "now", lambda: tomorrow)
    next_session = client.post(
        "/api/v1/learning-sessions", json={"minutes": 20}, headers=headers
    ).json()
    assert next_session["id"] != view["id"]
    # programs-and-output now has a second judged problem, so practice continues there.
    assert next_session["concept"] == "zero:programs-and-output"


def test_session_and_issue_ownership_csrf_replay_and_deletion(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    assert client.post("/api/v1/learning-sessions", json={}).status_code == 403
    view = client.post("/api/v1/learning-sessions", json={}, headers=headers).json()
    issue = client.post(
        f"/api/v1/learning-sessions/{view['id']}/issues",
        json={"block": 0, "reason": "unclear", "note": "Please make the first sentence shorter."},
        headers=headers,
    )
    assert issue.status_code == 200
    assert client.get("/api/v1/me/export").json()["content_issues"][0]["reason"] == "unclear"
    view = complete_current(client, headers, view)
    view = complete_current(client, headers, view)
    assert view["current"]["atom"]["kind"] == "faded"
    body = dict(block=view["index"], step=0, choice=0)
    for _ in range(2):
        assert (
            client.post(
                f"/api/v1/learning-sessions/{view['id']}/answer", json=body, headers=headers
            ).status_code
            == 200
        )
    with Session(client.app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(Evidence)) == 1
    other = login(client, "bob", "Bob")
    onboard(client, other)
    assert client.get(f"/api/v1/learning-sessions/{view['id']}").status_code == 404
    assert (
        client.post(
            f"/api/v1/learning-sessions/{view['id']}/advance", json={"block": 0}, headers=other
        ).status_code
        == 404
    )
    headers = login(client)
    assert client.delete("/api/v1/me", headers=headers).status_code == 204
    with Session(client.app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(ContentIssue)) == 0
        assert db.get(LearningSession, view["id"]) is None
    assert client.get(f"/api/v1/learning-sessions/{view['id']}").status_code == 401


def test_visible_tests_and_assistance_are_never_labelled_independent():
    public = Submission(status="done", verdict="accepted", mode="run", assistance=0)
    helped = Submission(status="done", verdict="accepted", mode="submit", assistance=3)
    independent = Submission(status="done", verdict="accepted", mode="submit", assistance=0)
    assert "independent evidence" not in submission_copy(public)
    assert "independent evidence" not in submission_copy(helped)
    assert "independent evidence" in submission_copy(independent)


def test_quarantine_stops_pinned_teaching_content():
    catalog = default_catalog()
    key = "dsa:binary-search"
    original = catalog.atom_packs[key]
    try:
        catalog.atom_packs[key] = original.model_copy(update={"status": "quarantined"})
        with pytest.raises(HTTPException) as error:
            sessions.ensure_content(catalog, {"kind": "atom", "concept": key})
        assert error.value.status_code == 423
    finally:
        catalog.atom_packs[key] = original


def test_session_revision_prevents_lost_progress(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    view = client.post("/api/v1/learning-sessions", json={}, headers=headers).json()
    with Session(client.app.state.engine) as first, Session(client.app.state.engine) as second:
        a = first.get(LearningSession, view["id"])
        b = second.get(LearningSession, view["id"])
        a.payload = {**a.payload, "summary_viewed": 1}
        first.commit()
        b.payload = {**b.payload, "summary_viewed": 2}
        with pytest.raises(StaleDataError):
            second.commit()
        second.rollback()
    with Session(client.app.state.engine) as db:
        assert db.get(LearningSession, view["id"]).payload["summary_viewed"] == 1


@pytest.mark.parametrize("repaired", [False, True])
def test_repair_detour_uses_unresolved_misconceptions_only(client, repaired):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    stamp = now()
    with Session(client.app.state.engine) as db, db.begin():
        enrollment = db.scalar(select(Enrollment).where(Enrollment.active.is_(True)))
        for i, score in enumerate([0, 0] + ([1] if repaired else [])):
            learn.record_evidence(
                db,
                enrollment,
                "zero:programs-and-output",
                "guided",
                score,
                f"check:{i}",
                stamp,
                assistance=2,
                details={"misconception": "programs-and-output-repair"},
            )
    view = client.post("/api/v1/learning-sessions", json={}, headers=headers).json()
    repairs = [b for b in view["blocks"] if b["title"].startswith("Repair:")]
    assert len(repairs) == (0 if repaired else 1)
