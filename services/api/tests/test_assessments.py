"""Weekly personalised assessments: composition rules and the API journey."""

from collections import Counter

from test_learner_api import client, login, onboard  # noqa: F401  (client is a fixture)

from socrat.assessments import routes as assessment_routes
from socrat.assessments import service as assessments
from socrat.catalog.registry import default_catalog
from socrat.mastery.model import DAY, ConceptState

NOW = 1_800_000_000


def shaky() -> ConceptState:
    return ConceptState(alpha=2, beta=3, evidence_count=3, next_review_at=NOW + DAY)


def strong() -> ConceptState:
    return ConceptState(alpha=19, beta=1, evidence_count=9, next_review_at=NOW + 5 * DAY)


def bank():
    from socrat.quiz import service as engine_service

    return engine_service.bank(default_catalog())


def test_composition_follows_study_and_fragility():
    catalog = default_catalog()
    states = {
        "basics:conditions": shaky(),
        "basics:loops": strong(),
        "basics:text": ConceptState(alpha=4, beta=2, evidence_count=4, next_review_at=NOW - DAY),
    }
    exposure = Counter({"basics:conditions": 4, "basics:loops": 2})
    args = (catalog, bank(), "python", states, exposure)
    concepts, items, coding = assessments.compose(*args, set(), set(), set(), NOW, "seed")
    asked = Counter(c for c, _ in items)
    assert len(items) == assessments.QUESTIONS
    assert asked["basics:conditions"] > asked["basics:loops"] >= 1
    assert ["basics:text", "review"] in concepts and asked["basics:text"] == 1
    assert coding and all(p in catalog.problems for p in coding)
    assert assessments.compose(*args, set(), set(), set(), NOW, "seed") == (concepts, items, coding)
    # Locked topics and solved problems never appear.
    _, locked_items, _ = assessments.compose(
        *args, {"basics:loops"}, set(coding), set(), NOW, "seed"
    )
    assert "basics:loops" not in {c for c, _ in locked_items}


def finish_lesson(client, headers, concept):  # noqa: F811
    assert client.post(f"/api/v1/activities/lesson:{concept}/complete", headers=headers).json()[
        "completed"
    ]


def test_weekly_assessment_journey(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(assessments, "exam_day", lambda user, now: False)
    headers = login(client)
    onboard(client, headers)
    overview = client.get("/api/v1/assessments").json()
    assert overview["current"]["state"] == "locked" and overview["history"] == []
    assert client.post("/api/v1/assessments/start", json={}, headers=headers).status_code == 409

    for concept in ("basics:values", "basics:text"):
        finish_lesson(client, headers, concept)
    current = client.get("/api/v1/assessments").json()["current"]
    assert current["state"] == "upcoming" and current["ready"] and current["opens_on"]
    assert client.post("/api/v1/assessments/start", json={}, headers=headers).status_code == 409
    monkeypatch.setattr(assessments, "exam_day", lambda user, now: True)
    current = client.get("/api/v1/assessments").json()["current"]
    assert current["state"] == "available" and len(current["topics"]) == 2

    view = client.post("/api/v1/assessments/start", json={}, headers=headers).json()
    assert view["questions"] and not view["finished"]
    assert view["timed"] and 0 < view["seconds_left"] <= assessments.TIME_LIMIT_SECONDS
    assert all("answer" not in q for q in view["questions"])  # graded only at the end
    assert {t["title"] for t in view["topics"]} >= {"Values"}
    again = client.post("/api/v1/assessments/start", json={}, headers=headers).json()
    assert again["id"] == view["id"]

    reply = client.post(
        "/api/v1/assistant/messages",
        json={"scope": "general", "message": "What is the answer to question 1?"},
        headers=headers,
    )
    assert "weekly assessment is in progress" in reply.text and '"policy"' in reply.text

    from socrat.quiz import service as engine_service

    catalog = default_catalog()
    for question in view["questions"]:
        item = engine_service.item_by_key(catalog, question["id"])
        shown = engine_service.render(catalog, item, view["id"], "python")
        view = client.post(
            f"/api/v1/assessments/{view['id']}/answer",
            json={"item": question["id"], "choice": shown["answer"]},
            headers=headers,
        ).json()
    done = client.post(f"/api/v1/assessments/{view['id']}/finish", headers=headers).json()
    report = done["report"]
    assert done["finished"] and report["correct"] == report["questions"]
    assert all(q["correct"] and "answer" in q for q in done["questions"])
    assert report["topics"] and not report["focus"] and report["strengths"]
    assert all(t["after"] >= t["before"] for t in report["topics"])
    assert client.get("/api/v1/assessments").json()["current"]["state"] == "done"
    assert client.post("/api/v1/assessments/start", json={}, headers=headers).status_code == 409
    assert client.get("/api/v1/assessments").json()["history"][0]["id"] == done["id"]
    assert client.get("/api/v1/me/export").json()["weekly_assessments"][0]["score"] == done["score"]


def test_timed_assessment_closes_at_the_deadline(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(assessments, "exam_day", lambda user, now: True)
    headers = login(client, subject="timed", name="Tim")
    onboard(client, headers)
    for concept in ("basics:values", "basics:text"):
        finish_lesson(client, headers, concept)
    view = client.post("/api/v1/assessments/start", json={"timed": True}, headers=headers).json()
    assert view["timed"] and 0 < view["seconds_left"] <= assessments.TIME_LIMIT_SECONDS

    real_now = assessment_routes.now
    monkeypatch.setattr(
        assessment_routes, "now", lambda: real_now() + assessments.TIME_LIMIT_SECONDS + 60
    )
    late = client.get(f"/api/v1/assessments/{view['id']}").json()
    assert late["finished"] and late["report"]["correct"] == 0

    other = login(client, subject="intruder", name="Ivy")
    onboard(client, other)
    assert client.get(f"/api/v1/assessments/{view['id']}").status_code == 404
