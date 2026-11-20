"""Beta features: the signed-out tutor demo, Skill Passports and company sprints."""

import json

from test_learner_api import client, login, onboard  # noqa: F401

from socrat import trial


def test_visitor_limits_are_hourly_and_per_key():
    trial._recent.clear()
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
    assert body["name"] == "Ada" and body["course"] == "Basics"
    assert "id" not in body and "birth_year" not in json.dumps(body)

    headers = login(client)
    again = client.put("/api/v1/me/passport", json={"public": False}, headers=headers).json()
    assert again["slug"] == slug and not again["public"]
    assert client.get(f"/api/v1/passport/{slug}").status_code == 404
    assert client.get("/api/v1/passport/not-a-real-slug").status_code == 404
    assert client.get("/api/v1/passport/..%2F..").status_code == 404
    assert client.get("/api/v1/me/export").json()["skill_passport"]["slug"] == slug
