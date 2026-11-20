"""Personalised reading lists and learner feedback on the tutor."""

from test_learner_api import client, login, onboard  # noqa: F401  (client is a fixture)


def test_resources_are_ranked_and_feedback_reorders_them(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    concept = "basics:values"
    view = client.get(f"/api/v1/concepts/{concept}").json()
    resources = view["resources"]
    assert resources and sum(r["picked"] for r in resources) == min(3, len(resources))
    assert resources[0]["picked"] and not resources[0]["opened"]

    top = resources[0]["url"]
    opened = client.post(
        f"/api/v1/concepts/{concept}/resources",
        json={"url": top, "action": "open"},
        headers=headers,
    ).json()
    assert opened == {"opened": True, "helpful": None}
    client.post(
        f"/api/v1/concepts/{concept}/resources",
        json={"url": top, "action": "unhelpful"},
        headers=headers,
    )
    after = client.get(f"/api/v1/concepts/{concept}").json()["resources"]
    marked = next(r for r in after if r["url"] == top)
    assert marked["helpful"] is False and marked["opened"]
    if len(after) > 1:
        assert after[0]["url"] != top  # an unhelpful pick sinks below the rest

    bad = client.post(
        f"/api/v1/concepts/{concept}/resources",
        json={"url": "https://example.com/not-curated", "action": "open"},
        headers=headers,
    )
    assert bad.status_code == 404
    exported = client.get("/api/v1/me/export").json()
    assert exported["resource_feedback"][0]["url"] == top


def test_learners_rate_tutor_replies(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    client.post(
        "/api/v1/assistant/messages",
        json={"scope": "general", "message": "What should I study first?"},
        headers=headers,
    )
    thread = client.get("/api/v1/assistant/thread?scope=general").json()
    reply = next(m for m in thread["messages"] if m["role"] == "assistant")
    user_message = next(m for m in thread["messages"] if m["role"] == "user")
    rated = client.post(
        f"/api/v1/assistant/messages/{reply['id']}/rating", json={"rating": 1}, headers=headers
    ).json()
    assert rated["rating"] == 1
    again = client.get("/api/v1/assistant/thread?scope=general").json()
    assert next(m for m in again["messages"] if m["id"] == reply["id"])["rating"] == 1
    cleared = client.post(
        f"/api/v1/assistant/messages/{reply['id']}/rating", json={"rating": 0}, headers=headers
    ).json()
    assert cleared["rating"] is None
    own = client.post(
        f"/api/v1/assistant/messages/{user_message['id']}/rating",
        json={"rating": 1},
        headers=headers,
    )
    assert own.status_code == 404  # only tutor replies can be rated

    other = login(client, subject="other", name="Oz")
    stolen = client.post(
        f"/api/v1/assistant/messages/{reply['id']}/rating", json={"rating": -1}, headers=other
    )
    assert stolen.status_code == 404
