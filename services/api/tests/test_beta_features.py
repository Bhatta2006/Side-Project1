"""Beta features: the signed-out tutor demo, Skill Passports and company sprints."""

import json

from test_learner_api import ORIGIN, client, complete_curriculum, login, onboard  # noqa: F401

from socrat import trial
from socrat.assistant import socratic


def events(response) -> list[tuple[str, dict]]:
    out = []
    for chunk in response.text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in chunk.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def test_try_problem_needs_no_account_and_hides_big_tests(client):  # noqa: F811
    view = client.get("/api/v1/try").json()
    assert view["id"] == trial.PROBLEM_ID and view["starter"]
    assert view["tests"] and all(len(t["input"]) <= trial.MAX_TEST_BYTES for t in view["tests"])
    assert any(t["public"] for t in view["tests"])


def test_try_tutor_streams_curated_hints_without_a_model(client):  # noqa: F811
    trial._recent.clear()
    response = client.post(
        "/api/v1/try/messages",
        json={"message": "help", "code": "print(1)"},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200
    stream = events(response)
    assert stream[0] == ("meta", {"allowed_level": 0, "thread_id": "", "reveal_blocked": ""})
    done = stream[-1][1]
    assert done["provider"] == "curated" and "tried" in done["text"]


def test_try_ladder_is_replayed_and_capped_below_the_answer():
    effort = trial.TryTurn(role="user", content="I add every window of k values up from scratch")
    history = [effort] * 6
    ladder = trial.ladder_for(history, "still stuck, here is my idea again in words", False)
    assert ladder.ceiling == 2  # talk alone never climbs past a nudge...
    assert trial.ladder_for(history, "here is my run", True).ceiling == 3  # ...a run does
    plan = trial.plan_turn(
        trial.catalog(), trial.TryMessage(history=history, message="more", new_attempt=True)
    )
    assert plan.allowed == trial.MAX_LEVEL < 5  # ...but the demo never reaches code
    assert "reference_solution" not in plan.turns[-1].content
    assert socratic.LEVELS[trial.MAX_LEVEL] in plan.turns[-1].content


def test_try_limits_turns_and_visitors(client):  # noqa: F811
    trial._recent.clear()
    history = [{"role": "user", "content": "x"}, {"role": "assistant", "content": "y"}]
    full = client.post(
        "/api/v1/try/messages",
        json={"history": history * trial.MAX_TURNS, "message": "again"},
        headers={"Origin": ORIGIN},
    )
    assert full.status_code == 429 and full.json()["error"]["code"] == "try_turns_used"
    assert all(trial.allow("visitor", 2, stamp=100.0 + i) for i in range(2))
    assert not trial.allow("visitor", 2, stamp=103.0)
    assert trial.allow("visitor", 2, stamp=100.0 + 3601)


def test_visitor_key_ignores_client_supplied_forwarding(client):  # noqa: F811
    from starlette.requests import Request

    def key(header: str) -> str:
        scope = {"type": "http", "app": client.app, "client": ("10.0.0.9", 1), "method": "GET"}
        scope["headers"] = [(b"x-forwarded-for", header.encode())]
        return trial.visitor(Request(scope))

    assert key("1.1.1.1, 203.0.113.7") == key("9.9.9.9, 203.0.113.7")
    assert key("1.1.1.1, 203.0.113.7") != key("1.1.1.1, 203.0.113.8")


def test_features_expose_the_community_link(client):  # noqa: F811
    assert client.get("/api/v1/features").json()["community_url"] is None


def test_passport_is_private_until_published_and_stops_when_hidden(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    mine = client.get("/api/v1/me/passport").json()
    assert mine["public"] is False and mine["slug"] is None
    assert mine["preview"]["name"] == "Ada" and mine["preview"]["counts"]["unaided_solves"] == 0

    published = client.put("/api/v1/me/passport", json={"public": True}, headers=headers).json()
    slug = published["slug"]
    assert published["public"] and published["path"] == f"/passport/{slug}"
    client.cookies.clear()
    shared = client.get(f"/api/v1/passport/{slug}")
    assert shared.status_code == 200
    body = shared.json()
    assert body["name"] == "Ada" and body["course"] == "Programming from Zero"
    assert "id" not in body and "birth_year" not in json.dumps(body)

    headers = login(client)
    again = client.put("/api/v1/me/passport", json={"public": False}, headers=headers).json()
    assert again["slug"] == slug and not again["public"]
    assert client.get(f"/api/v1/passport/{slug}").status_code == 404
    assert client.get("/api/v1/passport/not-a-real-slug").status_code == 404
    assert client.get("/api/v1/passport/..%2F..").status_code == 404
    assert client.get("/api/v1/me/export").json()["skill_passport"]["slug"] == slug


def test_company_sprint_plans_weeks_and_asks_before_changing_the_goal(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers, course="dsa", level="new-to-programming")
    overview = client.get("/api/v1/library/company-sprints").json()
    assert overview["current"] is None
    slugs = [c["slug"] for c in overview["companies"]]
    assert "amazon" in slugs and overview["weeks"] == [4, 6, 8]

    sprint = client.post(
        "/api/v1/library/company-sprints",
        json={"company": "amazon", "role": "sde1", "weeks": 6},
        headers=headers,
    ).json()
    assert sprint["title"] == "Amazon SDE-1 in 6 weeks"
    assert len(sprint["weeks"]) == 6 and sprint["current_week"] == 1
    assert sprint["weeks"][-1]["review"] and not sprint["weeks"][-1]["concepts"]
    assert sum(len(w["concepts"]) for w in sprint["weeks"]) == sprint["counts"]["concepts"] > 0
    # Nothing unlocked yet: question titles stay hidden until their skills are finished.
    assert all(not w["questions"] for w in sprint["weeks"])
    assert sum(w["locked_questions"] for w in sprint["weeks"]) == sprint["counts"]["questions"]

    proposal = sprint["proposal"]
    assert proposal["status"] == "pending" and proposal["source"] == "company_sprint"
    assert proposal["payload"]["target_role"] == "new-grad"
    assert proposal["payload"]["target_date"] == sprint["ends_on"]
    accepted = client.post(f"/api/v1/adaptive/proposals/{proposal['id']}/accept", headers=headers)
    assert accepted.status_code == 200
    me = client.get("/api/v1/me").json()
    assert me["enrollment"]["goal"]["target_date"] == sprint["ends_on"]

    complete_curriculum(client)
    unlocked = client.get("/api/v1/library/company-sprints").json()["current"]
    assert any(w["questions"] for w in unlocked["weeks"])
    assert unlocked["counts"]["concepts_done"] > 0

    stopped = client.post(f"/api/v1/library/company-sprints/{sprint['id']}/stop", headers=headers)
    assert stopped.status_code == 200
    assert client.get("/api/v1/library/company-sprints").json()["current"] is None


def test_company_sprint_rejects_unknown_companies(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers, course="dsa", level="new-to-programming")
    missing = client.post(
        "/api/v1/library/company-sprints", json={"company": "no-such-co"}, headers=headers
    )
    assert missing.status_code == 404
