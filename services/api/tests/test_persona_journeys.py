"""Whole-course persona walks through the real API: the adaptive loop end to end.

Each walk follows Today's next step the way a learner would, answers with a persona's policy,
and moves the clock to the next day when today's plan is done. Problems are recorded as an
accepted (or failed) judge verdict, the same calls the worker callback makes.
"""

import sys

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401

from socrat import models
from socrat.catalog.registry import default_catalog
from socrat.learn import quizzes, transfers
from socrat.learn import service as learn
from socrat.models import Enrollment, User
from socrat.placement import engine as placement_engine

DAY = 86_400
QUIZ_KINDS = {"quiz", "review", "remedial", "probe", "testout", "moduletest", "checkpoint"}
SELF_KINDS = {"lesson", "example", "explain", "checkin", "stretch"}


@pytest.fixture
def clock(monkeypatch):
    """One clock for every module that imported ``socrat.models.now``."""
    state = {"t": models.now()}
    original = models.now
    for name, module in list(sys.modules.items()):
        if name.startswith("socrat") and getattr(module, "now", None) is original:
            monkeypatch.setattr(module, "now", lambda: state["t"])
    return state


def correct_choice(cat, session_id: str, question: dict) -> int:
    item = quizzes.item(cat, question["concept"], question["id"])  # lesson quiz or hard bank
    return item.shown(session_id)["answer"]


def take(client, headers, cat, activity_id: str, right) -> dict:  # noqa: F811
    """Answer a quiz-style activity until it finishes; ``right(question)`` picks right/wrong."""
    view = client.get(f"/api/v1/quiz/{activity_id}").json()
    if view["completed"]:  # a one-off check already taken shows its result
        return view
    for _ in range(40):
        q = next(x for x in view["questions"] if not x["answered"])
        good = correct_choice(cat, view["id"], q)
        choice = good if right(q) else (good + 1) % len(q["options"])
        response = client.post(
            f"/api/v1/quiz/{activity_id}/answer",
            json={"item": q["id"], "choice": choice},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        # A new GET after the last answer would open a retake, so read the answer's view.
        view = response.json()
        if view["completed"]:
            return view
    raise AssertionError(f"{activity_id} never finished")


def solve(client, cat, activity_id: str, clock, accepted=True):  # noqa: F811
    """Record a judge verdict for a problem exactly as the worker callback does."""
    problem_id = activity_id.removeprefix("problem:")
    course_id, problem = cat.problems[problem_id]
    concept = f"{course_id}:{problem.concepts[0]}"
    with Session(client.app.state.engine) as db, db.begin():
        enrollment = db.scalar(select(Enrollment).where(Enrollment.active.is_(True)))
        user = db.get(User, enrollment.user_id)
        learn.start_activity(db, enrollment, activity_id, clock["t"])
        learn.record_evidence(
            db, enrollment, concept, "code", 1.0 if accepted else 0.0, activity_id, clock["t"]
        )
        if accepted:
            learn.complete_activity(db, user, enrollment, activity_id, clock["t"], solved=True)


def take_transfer(client, headers, cat, concept: str, clock):  # noqa: F811
    """A strong learner names the technique, then solves the unseen problem unaided."""
    view = client.get(f"/api/v1/transfer/{concept}").json()
    if view["state"] == "classify":
        named = client.post(
            f"/api/v1/transfer/{concept}/classify",
            json={"problem": view["problem"]["id"], "choice": concept},
            headers=headers,
        )
        assert named.status_code == 200 and named.json()["correct"], named.text
        problem_id = named.json()["problem"]
    else:
        assert view["state"] == "solve", view
        problem_id = view["problem"]
    solve(client, cat, f"problem:{problem_id}", clock)
    with Session(client.app.state.engine) as db, db.begin():
        enrollment = db.scalar(select(Enrollment).where(Enrollment.active.is_(True)))
        user = db.get(User, enrollment.user_id)
        transfers.on_solve(db, cat, user, enrollment, problem_id, 0, clock["t"])


def walk(client, headers, clock, policy, max_steps=900, max_days=120):  # noqa: F811
    """Follow Today until the course is complete. Returns the log of steps taken."""
    cat = default_catalog()
    log, days = [], 0
    for _ in range(max_steps):
        today = client.get("/api/v1/today").json()
        nxt = today["next"]
        if nxt is None:
            if today["progress"]["complete"]:
                return log, today
            days += 1
            assert days <= max_days, f"stalled: {today['progress']}"
            clock["t"] += DAY
            continue
        assert nxt.get("code"), f"every planned step says why: {nxt}"
        kind = nxt["kind"]
        log.append(dict(id=nxt["id"], kind=kind, code=nxt["code"], t=clock["t"]))
        if kind == "review":
            # Never early: the concept's review is actually due.
            progress = client.get("/api/v1/progress").json()
            row = next(
                c for m in progress["modules"] for c in m["concepts"] if c["id"] == nxt["concept"]
            )
            assert row["next_review"] is None or row["next_review"] <= clock["t"], repr(nxt)
        if kind in SELF_KINDS:
            r = client.post(f"/api/v1/activities/{nxt['id']}/complete", headers=headers)
            assert r.status_code == 200, (nxt, r.text)
        elif kind in QUIZ_KINDS:
            take(client, headers, cat, nxt["id"], lambda q, n=nxt: policy(n, q, log))
        elif kind == "problem":
            solve(client, cat, nxt["id"], clock, accepted=policy(nxt, None, log))
        elif kind == "transfer":
            take_transfer(client, headers, cat, nxt["concept"], clock)
        else:
            raise AssertionError(f"unknown kind {kind}")
        clock["t"] += 120
    raise AssertionError("walk did not finish")


def always_right(_activity, _question, _log):
    return True


def place(client, headers, enrollment, right):  # noqa: F811
    cat = default_catalog()
    seed = f"placement:{int(enrollment['id'].replace('-', '')[:8], 16)}"
    items = [q for c in cat.concepts.values() for q in c.quiz]
    items += [q for bank in cat.placement_items.values() for q in bank]
    for _ in range(placement_engine.MAX_QUESTIONS + 1):
        view = client.get("/api/v1/placement").json()
        if view["done"]:
            return client.get("/api/v1/placement/summary").json()
        question = view["question"]
        item = next(q for q in items if q.id == question["id"])
        good = item.shown(seed)["answer"]
        client.post(
            "/api/v1/placement/answer",
            json={"item": question["id"], "choice": good if right(item) else None},
            headers=headers,
        )
    raise AssertionError("placement never finished")


@pytest.mark.parametrize("course", ["zero", "dsa", "cp"])
def test_a_strong_learner_finishes_every_course_with_every_skill_proven(client, clock, course):  # noqa: F811
    headers = login(client, subject=f"strong-{course}")
    level = {"zero": "brand-new", "dsa": "new-to-programming", "cp": "knows-dsa-basics"}[course]
    enrollment = onboard(client, headers, course=course, level=level)
    if enrollment["status"] == "placement":
        place(client, headers, enrollment, lambda _: True)
    log, today = walk(client, headers, clock, always_right)
    progress = today["progress"]
    assert progress["complete"] and progress["percent"] == 100 and not progress["assumed"]
    # Search lists only this course; switching courses is off.
    concepts = client.get("/api/v1/library/meta").json()["concepts"]
    assert concepts and all(c["id"].startswith(f"{course}:") for c in concepts)
    again = client.post(
        "/api/v1/enrollments",
        json=dict(
            course="zero",
            language="python",
            level="brand-new",
            minutes_per_day=30,
            weekdays=[0, 1, 2, 3, 4],
        ),
        headers=headers,
    )
    assert again.status_code == 409 and again.json()["error"]["code"] == "already_enrolled"
    assert {s["code"] for s in log} >= {"path", "checkpoint"}
    # The finished course points onward: the next course, and hard problems still open.
    following = {"zero": "dsa", "dsa": "cp", "cp": None}[course]
    finale = today["finale"]
    assert finale and len(finale["challenges"]) <= 3
    assert (finale["next_course"] or {}).get("id") == following
    # Every course ends in a graded capstone that ties its skills together.
    capstone = finale["capstone"]
    assert capstone["id"].startswith(f"{course}:capstone-")
    assert capstone["done"] == 0 and capstone["total"] >= 3
    listed = client.get("/api/v1/projects").json()["projects"]
    assert capstone["id"] in {p["id"] for p in listed}
    if following:
        onward = client.post(
            "/api/v1/enrollments",
            json=dict(
                course=following,
                language="python",
                level={"dsa": "new-to-programming", "cp": "knows-dsa-basics"}[following],
                minutes_per_day=30,
                weekdays=[0, 1, 2, 3, 4],
            ),
            headers=headers,
        )
        assert onward.status_code == 200, onward.text


def test_placement_knowledge_counts_only_after_its_confirmation_check(client, clock):  # noqa: F811
    headers = login(client, subject="placed")
    enrollment = onboard(client, headers, course="dsa", level="knows-basics")
    zero = set(default_catalog().course_concepts("zero"))
    summary = place(client, headers, enrollment, lambda item: True)
    assert summary["known_concepts"], "a strong placement skips lessons"
    today = client.get("/api/v1/today").json()
    assert today["progress"]["assumed"] > 0 and today["progress"]["finished"] == 0
    # Today starts where placement left off, never back at the start of the path.
    first = today["next"]
    assert first["kind"] != "testout", first
    assert default_catalog().concept(first["concept"]).title == summary["starting_concept"]
    # The confirmation checks for what placement believes come after it.
    plan = client.get("/api/v1/plan").json()
    queued = [i for d in plan["days"] for i in d["items"]]
    confirms = [i for i in queued if i.get("code") == "assumed_confirm"]
    assert confirms and queued.index(confirms[0]) > 0
    nxt = confirms[0]
    assert nxt["kind"] == "testout" and nxt["title"].startswith("Confirm:")
    cat = default_catalog()
    passed = take(client, headers, cat, nxt["id"], lambda q: True)
    assert passed["testout"]["passed"]
    after = client.get("/api/v1/today").json()["progress"]
    assert after["finished"] == 1 and after["assumed"] == today["progress"]["assumed"] - 1
    # Missing a confirmation puts the real lesson back on the path.
    plan = client.get("/api/v1/plan").json()
    second = next(i for d in plan["days"] for i in d["items"] if i.get("code") == "assumed_confirm")
    take(client, headers, cat, second["id"], lambda q: False)
    plan = client.get("/api/v1/plan").json()
    queued = {i["id"] for d in plan["days"] for i in d["items"]}
    assert f"lesson:{second['concept']}" in queued or second["concept"] in zero


def test_a_missed_check_is_not_done_and_socrat_reteaches_before_a_fresh_check(client, clock):  # noqa: F811
    headers = login(client, subject="misses")
    onboard(client, headers)
    cat = default_catalog()
    concept = "zero:programs-and-output"
    client.post(f"/api/v1/activities/lesson:{concept}/complete", headers=headers)
    first = take(client, headers, cat, f"quiz:{concept}", lambda q: False)
    assert first["completed"] and first["score"] == 0
    today = client.get("/api/v1/today").json()
    plan_ids = [a["id"] for a in [today["next"], *today["queue"]] if a]
    assert f"quiz:{concept}" in plan_ids, "the check comes back"
    support = next(a for a in [today["next"], *today["queue"]] if a["id"] == f"explain:{concept}")
    assert support["code"] == "failed_check_refresh"
    assert plan_ids.index(f"explain:{concept}") < plan_ids.index(f"quiz:{concept}")
    rows = client.get("/api/v1/plan").json()["modules"][0]["concepts"]
    row = next(r for r in rows if r["concept"] == concept)
    assert row["status"] != "practiced"
    assert "failed_check_refresh" in row["reason_codes"]
    # The retake leads with different questions where the bank allows it.
    client.post(f"/api/v1/activities/explain:{concept}/complete", headers=headers)
    clock["t"] += DAY
    retake = client.get(f"/api/v1/quiz/quiz:{concept}").json()
    fitting = [q for q in cat.concept(concept).quiz if q.fits("python")]
    if len(fitting) > 5:
        assert {q["id"] for q in retake["questions"]} != {q["id"] for q in first["questions"]}


def test_a_mixed_learner_misses_first_tries_and_still_finishes(client, clock):  # noqa: F811
    headers = login(client, subject="mixed")
    onboard(client, headers)
    misses: dict[str, int] = {}

    def mixed(activity, question, _log):
        # Every concept check is missed on its first try (two wrong answers fail a 4-of-5 pass
        # mark however long the check is), then passed; everything else goes right.
        if activity["kind"] != "quiz":
            return True
        if question is not None and misses.get(activity["id"], 0) < 2:
            misses[activity["id"]] = misses.get(activity["id"], 0) + 1
            return False
        return True

    log, today = walk(client, headers, clock, mixed)
    assert today["progress"]["complete"]
    codes = [s["code"] for s in log]
    assert "failed_check_refresh" in codes, "a miss changes the plan the learner sees"


def test_adaptive_concept_check_closes_the_same_plan_step(client, clock):  # noqa: F811
    from socrat.quiz import service as engine_service

    headers = login(client, subject="adaptive")
    onboard(client, headers)
    cat = default_catalog()
    concept = "zero:programs-and-output"
    started = client.post(
        "/api/v1/adaptive-quiz/sessions",
        json={"mode": "concept_check", "concepts": [concept]},
        headers=headers,
    ).json()
    assert started["engine"] == "adaptive"
    session, bands = started, []
    while not session["finished"]:
        current = session["current"]
        bands.append(current["band"])
        item = engine_service.item_by_key(cat, current["item"])
        shown = engine_service.render(cat, item, session["id"], "python")
        session = client.post(
            f"/api/v1/adaptive-quiz/sessions/{session['id']}/answer",
            json={"item": current["item"], "choice": shown["answer"]},
            headers=headers,
        ).json()["session"]
    assert session["passed"] and session["score"] == 1.0
    assert max(bands) > min(bands), f"difficulty climbs with right answers: {bands}"
    done = {d["id"] for d in client.get("/api/v1/today").json()["done"]}
    assert {f"quiz:{concept}", f"lesson:{concept}"} <= done
    # Another course's skill is out of scope for the engine too.
    outside = client.post(
        "/api/v1/adaptive-quiz/sessions",
        json={"mode": "concept_check", "concepts": ["dsa:complexity"]},
        headers=headers,
    )
    assert outside.status_code == 404
