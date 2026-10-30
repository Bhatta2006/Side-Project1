"""Transfer verification: the pure rules, then the whole check through the API."""

# ruff: noqa: F811  (`client` is a fixture imported from test_learner_api)

import pytest
from runner_support import SIGNING, WORKER, profiles
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.catalog.registry import default_catalog
from socrat.execution.protocol import CaseResult, ExecutionResult, JobEnvelope, sign
from socrat.learn import service as learn
from socrat.mastery import transfer
from socrat.mastery.model import DAY, ConceptState
from socrat.models import ActivityRecord, AssistantThread, Enrollment, Evidence, now
from socrat.planner import gates

CAT = default_catalog()
FIRST = CAT.course("zero").modules[0]
CONCEPT = f"zero:{FIRST.concepts[0]}"  # programs-and-output: two problems, no prerequisites
STRONG = dict(alpha=20.0, beta=1.0, evidence_count=8, review_step=3)


def mastered(stamp):
    return ConceptState(**STRONG, last_evidence_at=stamp, next_review_at=stamp + 7 * DAY)


def master(client, concept=CONCEPT):
    with Session(client.app.state.engine) as db, db.begin():
        enrollment = db.scalar(select(Enrollment).where(Enrollment.active.is_(True)))
        learn.set_state(db, enrollment, concept, mastered(now()), now())


def learner(client):
    headers = login(client)
    onboard(client, headers)
    master(client)
    return headers


def accept(client, headers, problem_id):
    """Submit a solution and have the worker judge it accepted."""
    worker = {"Authorization": "Bearer " + WORKER}
    images = [p["image"] for p in profiles()]
    client.post(
        "/api/v1/execution/worker/heartbeat",
        json={"worker_id": "w1", "images": images},
        headers=worker,
    )
    client.post(
        f"/api/v1/problems/{problem_id}/submit", json={"source": "print(1)"}, headers=headers
    )
    envelope = JobEnvelope.model_validate(
        client.post(
            "/api/v1/execution/worker/claim", json={"worker_id": "w1"}, headers=worker
        ).json()["job"]
    )
    cases = [
        CaseResult(index=i, status="passed", wall_ms=5, stdout=t.expected or "")
        for i, t in enumerate(envelope.tests)
    ]
    m = envelope.manifest
    result = ExecutionResult(
        job_id=m.job_id,
        nonce=m.nonce,
        code_hash=m.code_hash,
        test_digest=m.test_digest,
        image=m.image,
        operational_status="healthy",
        cases=cases,
        reason_code="execution_finalized",
    ).model_dump()
    done = client.post(
        "/api/v1/execution/worker/result",
        json={
            "worker_id": "w1",
            "envelope": {"result": result, "signature": sign(result, SIGNING)},
        },
        headers=worker,
    )
    assert done.json()["verdict"] == "accepted"


def check(client):
    return client.get(f"/api/v1/transfer/{CONCEPT}").json()


def classify(client, headers, view, choice):
    return client.post(
        f"/api/v1/transfer/{CONCEPT}/classify",
        json={"problem": view["problem"]["id"], "choice": choice},
        headers=headers,
    )


def wrong_choice(view):
    return next(c["id"] for c in view["choices"] if c["id"] != CONCEPT)


# ---------------------------------------------------------------- pure rules


def test_choices_are_four_unique_stable_and_never_a_neighbour():
    scope = set(CAT.closure(CAT.course_concepts("zero")))
    first = transfer.choices(CAT, CONCEPT, "seed", scope, set())
    assert first == transfer.choices(CAT, CONCEPT, "seed", scope, set())
    assert len(first) == transfer.CHOICES == len(set(first)) and CONCEPT in first
    follow_on = {c for c in scope if CONCEPT in CAT.prerequisites[c]}
    assert follow_on and not follow_on & set(first)
    assert (
        transfer.choices(CAT, CONCEPT, "seed", {CONCEPT, "zero:variables-and-types"}, set()) is None
    )


def test_distractors_come_from_what_the_learner_has_met():
    scope = set(CAT.closure(CAT.course_concepts("zero")))
    near = {CONCEPT, *CAT.prerequisites[CONCEPT]} | {
        c for c in scope if CONCEPT in CAT.prerequisites[c]
    }
    known = set(sorted(scope - near)[:3])
    assert known <= set(transfer.choices(CAT, CONCEPT, "seed", scope, known))


def test_status_follows_the_attempt():
    strong, weak, t = mastered(1_000), ConceptState(), 1_000
    s = transfer.status
    assert s(None, True, strong, True, t) == "verified"
    assert s(None, False, strong, True, t) == "due"
    assert s(None, False, strong, False, t) is None  # no unseen problem left
    assert s(None, False, weak, True, t) is None  # not mastered
    assert s({"state": "pending"}, False, weak, False, t) == "pending"
    miss = {"state": "failed", "at": t}
    assert s(miss, False, weak, True, t + 10) == "wait"  # a miss cannot be dodged by failing
    assert s(miss, False, strong, True, t + transfer.COOLDOWN) == "due"


def test_a_module_is_held_only_by_an_offered_check_nobody_has_moved_past():
    states = {CONCEPT: mastered(now())}
    done = {gates.gate_id(f"zero:{FIRST.id}")}
    args = (CAT, "zero", states, done, now())
    held = transfer.blocking_modules(CAT, "zero", {CONCEPT: "due"}, states, done, now())
    assert held == {f"zero:{FIRST.id}"}
    assert not gates.cleared(CAT, f"zero:{FIRST.id}", *args[2:], held=held)
    assert (
        transfer.blocking_modules(CAT, "zero", {CONCEPT: "verified"}, states, done, now()) == set()
    )
    assert transfer.blocking_modules(CAT, "zero", {}, states, done, now()) == set()
    nxt = f"zero:{CAT.course('zero').modules[1].concepts[0]}"
    moved = {**states, nxt: mastered(now())}
    assert transfer.blocking_modules(CAT, "zero", {CONCEPT: "due"}, moved, done, now()) == set()


# ---------------------------------------------------------------- the check, end to end


def test_a_full_check_verifies_the_concept(client):
    headers = learner(client)
    view = check(client)
    assert view["state"] == "classify" and len(view["choices"]) == 4
    assert not {"title", "hints", "approach", "reference", "starter"} & view["problem"].keys()

    right = classify(client, headers, view, CONCEPT)
    assert right.json() == dict(correct=True, state="solve", problem=view["problem"]["id"])
    assert check(client) == dict(
        concept=CONCEPT, title=view["title"], state="solve", problem=view["problem"]["id"]
    )

    accept(client, headers, view["problem"]["id"])
    assert check(client)["state"] == "verified"
    plan = client.get("/api/v1/plan").json()
    row = next(c for m in plan["modules"] for c in m["concepts"] if c["concept"] == CONCEPT)
    assert row["transfer"] == "verified"
    with Session(client.app.state.engine) as db:
        rows = list(db.scalars(select(Evidence).where(Evidence.kind == "transfer")))
    assert [(r.score, r.details["stage"], r.details["ok"]) for r in rows] == [(1.0, "solve", True)]


def test_naming_the_wrong_technique_ends_the_attempt_and_the_problem_is_not_reused(client):
    headers = learner(client)
    view = check(client)
    missed = classify(client, headers, view, wrong_choice(view)).json()
    assert missed["correct"] is False and missed["answer"] == view["title"]
    assert check(client)["state"] == "wait"
    assert classify(client, headers, view, CONCEPT).status_code == 409  # no second guess

    with Session(client.app.state.engine) as db, db.begin():  # the cooldown passes
        record = db.scalar(
            select(ActivityRecord).where(ActivityRecord.activity_id.like("transfer:%"))
        )
        record.outcome = {**record.outcome, "at": now() - transfer.COOLDOWN - 1}
        evidence = db.scalar(select(Evidence).where(Evidence.kind == "transfer"))
        assert evidence.score == 0.0 and evidence.details["stage"] == "classify"
    again = check(client)
    assert again["state"] == "classify" and again["problem"]["id"] != view["problem"]["id"]


def test_tutor_help_makes_the_solve_a_miss(client):
    headers = learner(client)
    view = check(client)
    assert classify(client, headers, view, CONCEPT).status_code == 200
    pid = view["problem"]["id"]
    with Session(client.app.state.engine) as db, db.begin():
        user_id = db.scalar(select(Enrollment.user_id).where(Enrollment.active.is_(True)))
        db.add(AssistantThread(user_id=user_id, scope=f"problem:{pid}", ladder={"max_level": 3}))
    accept(client, headers, pid)
    assert check(client)["state"] == "wait"
    with Session(client.app.state.engine) as db:
        row = db.scalar(select(Evidence).where(Evidence.kind == "transfer"))
    assert row.score == transfer.ASSISTED_SCORE and row.details["ok"] is False


def test_a_problem_the_learner_has_met_is_never_offered(client):
    headers = learner(client)
    view = check(client)
    with Session(client.app.state.engine) as db, db.begin():
        enrollment = db.scalar(select(Enrollment).where(Enrollment.active.is_(True)))
        for pid, (owner, problem) in CAT.problems.items():
            if owner == "zero" and f"zero:{problem.concepts[0]}" == CONCEPT:
                db.add(ActivityRecord(enrollment_id=enrollment.id, activity_id=f"problem:{pid}"))
    assert check(client)["state"] == "unavailable"
    assert classify(client, headers, view, CONCEPT).status_code == 409


def test_an_unmastered_concept_has_no_check_and_a_stale_problem_is_refused(client):
    headers = login(client)
    onboard(client, headers)
    assert check(client)["state"] == "unavailable"
    master(client)
    view = check(client)
    stale = client.post(
        f"/api/v1/transfer/{CONCEPT}/classify",
        json={"problem": "not-the-problem", "choice": CONCEPT},
        headers=headers,
    )
    assert stale.status_code == 409 and view["state"] == "classify"
    elsewhere = client.post(
        f"/api/v1/transfer/{CONCEPT}/classify",
        json={"problem": view["problem"]["id"], "choice": "zero:not-offered"},
        headers=headers,
    )
    assert elsewhere.status_code == 422


def test_a_passed_checkpoint_holds_the_next_module_until_the_check_is_passed(client):
    headers = learner(client)
    module = f"zero:{FIRST.id}"
    with Session(client.app.state.engine) as db, db.begin():
        enrollment = db.scalar(select(Enrollment).where(Enrollment.active.is_(True)))
        db.add(
            ActivityRecord(
                enrollment_id=enrollment.id, activity_id=gates.gate_id(module), completed_at=1
            )
        )
    plan = client.get("/api/v1/plan").json()
    held = next(m for m in plan["modules"] if m["locked_by"] and m["locked_by"]["needs_transfer"])
    assert held["locked_by"]["transfer"] == f"transfer:{CONCEPT}"
    assert any(a["id"] == f"transfer:{CONCEPT}" for a in plan["days"][0]["items"])

    view = check(client)
    classify(client, headers, view, CONCEPT)
    accept(client, headers, view["problem"]["id"])
    after = client.get("/api/v1/plan").json()
    assert not any(
        m["locked_by"] and m["locked_by"].get("needs_transfer") for m in after["modules"]
    )


def test_transfer_cannot_be_completed_directly(client):
    headers = learner(client)
    done = client.post(f"/api/v1/activities/transfer:{CONCEPT}/complete", headers=headers)
    assert done.status_code == 409
    assert check(client)["state"] == "classify"


@pytest.mark.parametrize("path", ["/transfer/dsa:arrays-hashing", "/transfer/zero:nope"])
def test_concepts_outside_the_course_are_not_found(client, path):
    headers = login(client)
    onboard(client, headers)
    assert client.get("/api/v1" + path).status_code == 404
