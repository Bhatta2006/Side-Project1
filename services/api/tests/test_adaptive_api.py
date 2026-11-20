"""Adaptive roadmap API: Socrat proposes, the learner decides, and the plan follows."""

import math
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401  (client is a fixture)

from socrat.adaptive import proposals
from socrat.adaptive.suggest import Draft
from socrat.catalog.registry import default_catalog
from socrat.models import Enrollment, OutboxEvent, PlanProposal, PlanRevision, QuizSession


def enrollment(db: Session) -> Enrollment:
    return db.scalar(select(Enrollment).where(Enrollment.active.is_(True)))


def propose(client, draft: Draft) -> str:  # noqa: F811
    with Session(client.app.state.engine) as db, db.begin():
        row = proposals.add(db, enrollment(db), draft, "tutor", 1)
        assert row is not None
        return row.id


def queue_ids(client) -> list[str]:  # noqa: F811
    plan = client.get("/api/v1/plan").json()
    return [i["id"] for d in plan["days"] for i in d["items"]]


def latest_reasons(client) -> list[str]:  # noqa: F811
    with Session(client.app.state.engine) as db:
        row = db.scalar(select(PlanRevision).order_by(PlanRevision.created_at.desc()))
        return row.reasons


def upcoming(client, offset: int = 0) -> str:  # noqa: F811
    plan = client.get("/api/v1/plan").json()
    concepts = [
        c["concept"]
        for m in plan["modules"]
        for c in m["concepts"]
        if c["status"] in {"upcoming", "in_progress"}
    ]
    return concepts[offset]


def test_roadmap_changes_wait_for_the_learners_yes(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    concept = upcoming(client)
    proposal = propose(
        client,
        Draft("probe", f"probe:{concept}", "Quick check", "To find the gap.", {"concept": concept}),
    )
    pending = client.get("/api/v1/adaptive/proposals").json()["pending"]
    assert [p["id"] for p in pending] == [proposal]
    assert f"probe:{concept}" not in queue_ids(client)  # nothing changes while pending

    response = client.post(f"/api/v1/adaptive/proposals/{proposal}/accept", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["proposal"]["status"] == "accepted"
    assert queue_ids(client)[0] == f"probe:{concept}"
    assert latest_reasons(client)[0] == "You approved: Quick check."
    again = client.post(f"/api/v1/adaptive/proposals/{proposal}/accept", headers=headers)
    assert again.status_code == 409

    other = upcoming(client, 1)
    declined = propose(
        client, Draft("defer", f"defer:{other}", "Set aside", "Later.", {"concept": other})
    )
    client.post(f"/api/v1/adaptive/proposals/{declined}/decline", headers=headers)
    with Session(client.app.state.engine) as db, db.begin():
        draft = Draft("defer", f"defer:{other}", "Set aside", "Later.", {"concept": other})
        assert proposals.add(db, enrollment(db), draft, "planner", 2) is None  # not re-asked
    assert (
        client.post(f"/api/v1/adaptive/proposals/{declined}/accept", headers=headers).status_code
        == 409
    )


def test_accepted_changes_can_be_undone_by_the_learner(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    cat = default_catalog()
    path = cat.closure(cat.course_concepts("basics"))
    needed = {p for c in path for p in cat.prerequisites[c]}
    leaf = next(c for c in reversed(path) if c not in needed)

    def status():
        plan = client.get("/api/v1/plan").json()
        return next(c for m in plan["modules"] for c in m["concepts"] if c["concept"] == leaf)[
            "status"
        ]

    before = status()
    proposal = propose(
        client, Draft("skip", f"skip:{leaf}", "Drop it", "Not needed.", {"concepts": [leaf]})
    )
    client.post(f"/api/v1/adaptive/proposals/{proposal}/accept", headers=headers)
    assert status() == "skipped"
    response = client.post(
        "/api/v1/adaptive/overrides/undo", json={"kind": "skip", "concept": leaf}, headers=headers
    )
    assert response.status_code == 200
    assert status() == before
    assert latest_reasons(client)[0].startswith("You changed your plan")


def take_quiz(client, headers, activity: str, correct: bool) -> dict:  # noqa: F811
    cat = default_catalog()
    view = client.get(f"/api/v1/quiz/{activity}").json()
    with Session(client.app.state.engine) as db:
        session_id = db.scalar(select(QuizSession.id).where(QuizSession.activity_id == activity))
    for question in view["questions"]:
        item = next(q for q in cat.concept(question["concept"]).quiz if q.id == question["id"])
        right = item.shown(session_id)["answer"]
        choice = right if correct else (right + 1) % len(item.options)
        view = client.post(
            f"/api/v1/quiz/{activity}/answer",
            json={"item": question["id"], "choice": choice},
            headers=headers,
        ).json()
    return view


def test_know_this_offers_a_testout_and_passing_skips_ahead(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    concept = upcoming(client)
    response = client.post(
        "/api/v1/adaptive/feel", json={"concept": concept, "signal": "know_this"}, headers=headers
    )
    assert response.status_code == 200, response.text
    assert queue_ids(client)[0] == f"testout:{concept}"
    view = take_quiz(client, headers, f"testout:{concept}", correct=True)
    assert view["completed"] and view["testout"]["passed"] is True
    assert view["feedback"] == "at_end"
    plan = client.get("/api/v1/plan").json()
    status = {c["concept"]: c["status"] for m in plan["modules"] for c in m["concepts"]}
    assert status[concept] == "mastered"
    assert f"testout:{concept}" not in queue_ids(client)

    second = upcoming(client)
    client.post(
        "/api/v1/adaptive/feel", json={"concept": second, "signal": "know_this"}, headers=headers
    )
    view = take_quiz(client, headers, f"testout:{second}", correct=False)
    assert view["testout"]["passed"] is False
    assert upcoming(client) == second  # the normal path carries on


def test_feel_sets_pace_for_one_concept(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    concept = upcoming(client)
    body = client.post(
        "/api/v1/adaptive/feel", json={"concept": concept, "signal": "too_hard"}, headers=headers
    ).json()
    assert body["feel"] == "hard"
    plan = client.get("/api/v1/plan").json()
    row = next(c for m in plan["modules"] for c in m["concepts"] if c["concept"] == concept)
    assert "hard" in row["why"]
    bad = client.post(
        "/api/v1/adaptive/feel",
        json={"concept": "algo:nope", "signal": "too_hard"},
        headers=headers,
    )
    assert bad.status_code == 404


def test_path_styles_preview_and_switch(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    options = client.get("/api/v1/adaptive/path-options").json()
    assert [o["style"] for o in options["options"]] == [
        "thorough",
        "balanced",
        "fast_track",
        "goal_focused",
    ]
    by_style = {o["style"]: o for o in options["options"]}
    assert by_style["thorough"]["remaining_minutes"] > by_style["fast_track"]["remaining_minutes"]
    response = client.post(
        "/api/v1/adaptive/path-style", json={"style": "fast_track"}, headers=headers
    )
    assert response.json()["current"] == "fast_track"
    assert latest_reasons(client)[0] == "You chose the Fast track path."
    assert client.get("/api/v1/plan").json()["style"] == "fast_track"


def test_falling_behind_a_deadline_offers_choices_and_one_choice_retires_the_rest(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    remaining = client.get("/api/v1/plan").json()["remaining_minutes"]
    with Session(client.app.state.engine) as db, db.begin():
        enrollment(db).weekdays = [0, 2, 4]  # three days a week leaves room to add more
    target = date.today() + timedelta(days=math.ceil(remaining / 300 * 7))
    response = client.patch(
        "/api/v1/enrollments/current", json={"target_date": target.isoformat()}, headers=headers
    )
    assert response.status_code == 200
    plan = client.get("/api/v1/plan").json()
    assert plan["forecast"]["on_track"] is False
    pending = [p for p in plan["proposals"]["pending"] if p["group"].startswith("deadline")]
    assert len(pending) >= 2
    choice = next(p for p in pending if p["kind"] == "budget")
    client.post(f"/api/v1/adaptive/proposals/{choice['id']}/accept", headers=headers)
    with Session(client.app.state.engine) as db:
        rows = {r.id: r.status for r in db.scalars(select(PlanProposal))}
        changed = enrollment(db)
        assert changed.minutes_per_day == choice["payload"].get(
            "minutes_per_day", 45
        ) and changed.weekdays == choice["payload"].get("weekdays", [0, 2, 4])
    assert rows[choice["id"]] == "accepted"
    assert all(rows[p["id"]] == "superseded" for p in pending if p["id"] != choice["id"])


def test_today_review_nudges_and_profile(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    today = client.get("/api/v1/today").json()
    assert {"checkin", "nudges", "proposals", "forecast", "milestone"} <= set(today)
    assert today["checkin"]["message"].startswith("Today let's start with")
    review = client.get("/api/v1/adaptive/weekly-review").json()
    assert {"wins", "slipping", "stuck", "forecast", "proposals"} <= set(review)
    assert client.post("/api/v1/adaptive/weekly-review/seen", headers=headers).status_code == 204
    assert client.get("/api/v1/adaptive/weekly-review").json()["seen"] is True
    profile = client.get("/api/v1/adaptive/profile").json()
    assert {"level", "review_scale", "adherence", "concepts"} <= set(profile)

    def nudge_events():
        with Session(client.app.state.engine) as db:
            return db.scalar(
                select(func.count())
                .select_from(OutboxEvent)
                .where(OutboxEvent.kind.like("nudge.%"))
            )

    with Session(client.app.state.engine) as db, db.begin():
        proposals.add(
            db,
            enrollment(db),
            Draft("stretch", "stretch", "Add a stretch", "Strong results."),
            "tutor",
            1,
        )
    client.get("/api/v1/adaptive/nudges")
    first = nudge_events()
    assert first >= 1
    client.get("/api/v1/adaptive/nudges")
    assert nudge_events() == first  # once a day per kind
