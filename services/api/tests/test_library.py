"""Practice library: personalised browsing, marks, recommendations and Codeforces sync."""

import pytest
from test_learner_api import (  # noqa: F401  (client is a fixture)
    client,
    complete_curriculum,
    login,
    onboard,
)

from socrat.library import codeforces, ladder, recommend
from socrat.mastery.model import ConceptState

NOW = 1_800_000_000


def strong(now: int = NOW) -> ConceptState:
    return ConceptState(alpha=19, beta=1, evidence_count=10, next_review_at=now + 86400)


def test_concepts_outside_the_course_do_not_hold_the_rating_down():
    states = {c: strong() for _, concepts in ladder.TIERS[:2] for c in concepts}
    del states["zero:debugging"]  # not part of this learner's course path
    assert ladder.estimate_rating(states, NOW) == 1200


def test_rating_estimate_climbs_the_ladder_tier_by_tier():
    assert ladder.estimate_rating({}, NOW) == 800
    first = {c: strong() for c in ladder.TIERS[0][1]}
    two = first | {c: strong() for c in ladder.TIERS[1][1]}
    assert ladder.estimate_rating(first, NOW) == 1000
    assert ladder.estimate_rating(two, NOW) == 1200
    # A linked contest rating is blended in, not ignored.
    assert 1200 < ladder.estimate_rating(two, NOW, linked=1700) < 1700


def test_recommendations_fit_the_level_and_skip_solved():
    from socrat.catalog.practice import default_index, rating_of
    from socrat.catalog.registry import default_catalog

    index, catalog = default_index(), default_catalog()
    learner = recommend.Learner(
        course="dsa", states={"dsa:two-pointers": strong()}, now=NOW, rating=1200, seed="s"
    )
    picks = recommend.best_for(index, learner, "dsa:two-pointers", 6)
    low, high = recommend.window(learner, "dsa:two-pointers")
    assert picks and all(low - 300 < rating_of(p) < high + 300 for p in picks)
    learner.solved = {picks[0]["id"]}
    assert picks[0]["id"] not in {
        p["id"] for p in recommend.best_for(index, learner, "dsa:two-pointers", 6)
    }
    # Stretch picks for a strong concept lean on rated platforms.
    stretch = recommend.next_problems(index, catalog, learner, None, limit=4)
    assert any(p["kind"] == "stretch" for p in stretch)
    assert all(p["reason"] and p["concept"]["id"] for p in stretch)


def test_codeforces_summary_counts_verdicts_and_skips_gym():
    subs = [
        {"verdict": "OK", "problem": {"contestId": 1873, "index": "A", "tags": ["greedy"]}},
        {
            "verdict": "WRONG_ANSWER",
            "problem": {"contestId": 1873, "index": "A", "tags": ["greedy"]},
        },
        {"verdict": "WRONG_ANSWER", "problem": {"contestId": 1873, "index": "B", "tags": ["dp"]}},
        {"verdict": "OK", "problem": {"contestId": 100001, "index": "A", "tags": ["math"]}},
    ]
    summary = codeforces.summarize(subs)
    assert summary["solved"] == ["cf:1873A"]
    assert summary["attempted"] == ["cf:1873B"]
    assert summary["tag_stats"]["dp"] == {"solved": 0, "unsolved": 1}


def test_library_browse_mark_and_recommend(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers, course="dsa", level="new-to-programming")
    complete_curriculum(client)
    meta = client.get("/api/v1/library/meta").json()
    assert set(meta["platforms"]) == {"LeetCode", "CSES", "Codeforces"}
    assert any(c["id"] == "dsa:two-pointers" for c in meta["concepts"])

    page = client.get(
        "/api/v1/library?concept=zero:input-and-arithmetic&platform=Codeforces&limit=5"
    ).json()
    assert page["total"] > 0 and len(page["items"]) == 5
    assert all(p["platform"] == "Codeforces" and p["rating"] for p in page["items"])
    rated = client.get(
        "/api/v1/library?platform=Codeforces&rating_min=800&rating_max=1000&sort=easiest"
    ).json()["items"]
    assert rated and all(800 <= p["rating"] <= 1000 for p in rated)
    assert rated == sorted(rated, key=lambda p: p["rating"])

    target = page["items"][0]["id"]
    assert (
        client.put(f"/api/v1/library/problems/{target}", json={"bookmarked": True}).status_code
        == 403
    )
    assert (
        client.post(f"/api/v1/library/problems/{target}/opened", headers=headers).json()["status"]
        == "attempted"
    )
    marked = client.put(
        f"/api/v1/library/problems/{target}", json={"status": "solved"}, headers=headers
    ).json()
    assert marked["status"] == "solved"
    solved = client.get("/api/v1/library?status=solved").json()
    assert [p["id"] for p in solved["items"]] == [target]
    unsolved = client.get(
        "/api/v1/library?concept=zero:input-and-arithmetic&platform=Codeforces&status=unsolved"
    )
    assert target not in {p["id"] for p in unsolved.json()["items"]}
    assert client.put("/api/v1/library/problems/cf:0Z", json={}, headers=headers).status_code == 404

    recs = client.get("/api/v1/library/recommendations").json()
    assert recs["level"]["rating"] >= 800 and recs["level"]["name"]
    assert recs["problems"] and all(p["reason"] for p in recs["problems"])
    assert target not in {p["id"] for p in recs["problems"]}
    assert recs["topics"] and recs["topics"][0]["reason"]

    exported = client.get("/api/v1/me/export").json()
    assert exported["practice_marks"][0]["problem"] == target
    # A self-reported solve is weak evidence on the problem's concept.
    assert any(e["kind"] == "external" for e in exported["evidence"])


def test_codeforces_link_uses_synced_profile(client, monkeypatch):  # noqa: F811
    headers = login(client)
    onboard(client, headers, course="cp", level="new-to-programming")
    complete_curriculum(client)

    async def fake(handle):
        if handle == "ghost":
            raise codeforces.CodeforcesError("handle_not_found")
        return {
            "handle": "Tourist_fan",
            "rating": 1450,
            "max_rating": 1510,
            "rank": "specialist",
            "solved": ["cf:1000A"],
            "attempted": ["cf:1000B"],
            "tag_stats": {"dp": {"solved": 1, "unsolved": 3}},
        }

    monkeypatch.setattr(codeforces, "fetch_profile", fake)
    bad = client.post("/api/v1/library/codeforces", json={"handle": "ghost"}, headers=headers)
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "codeforces_handle_not_found"
    assert (
        client.post(
            "/api/v1/library/codeforces", json={"handle": "x y"}, headers=headers
        ).status_code
        == 422
    )
    linked = client.post(
        "/api/v1/library/codeforces", json={"handle": "tourist_fan"}, headers=headers
    )
    account = linked.json()["account"]
    assert account["rating"] == 1450 and account["weak_tags"] == ["dp"]
    # Synced solves count as solved in the library; the rating lifts the level estimate.
    assert client.get("/api/v1/library?status=solved").json()["items"][0]["id"] == "cf:1000A"
    assert client.get("/api/v1/library/recommendations").json()["level"]["rating"] > 1000
    again = client.post("/api/v1/library/codeforces/sync", headers=headers).json()
    assert again["synced"] is False  # cooldown
    assert client.delete("/api/v1/library/codeforces", headers=headers).status_code == 204
    assert client.get("/api/v1/library/codeforces").json()["account"] is None


@pytest.mark.parametrize("rating", [800, 1350, 2100])
def test_level_view_is_bounded(rating):
    view = recommend.level_view(rating)
    assert 0 <= view["progress"] <= 1 and view["name"]


def test_public_stats_and_light_summary(client):  # noqa: F811
    stats = client.get("/api/v1/library/stats").json()  # no sign-in needed
    assert (
        stats["courses"] == 3 and 400 <= stats["library"] <= 600
    )  # the curated list and stats["problems"] > 50
    headers = login(client)
    assert client.get("/api/v1/me/summary").json() == {"streak": None, "minutes": None}
    onboard(client, headers)
    summary = client.get("/api/v1/me/summary").json()
    assert summary["minutes"] == {"done": 0, "goal": 45}
    assert summary["streak"]["current"] == 0 and summary["streak"]["studied_today"] is False


def test_autosync_refreshes_stale_accounts(client, monkeypatch):  # noqa: F811
    import asyncio

    from sqlalchemy import update
    from sqlalchemy.orm import Session

    from socrat.library import autosync
    from socrat.models import LinkedAccount

    headers = login(client, subject="auto", name="Ana")
    onboard(client, headers)
    solved = ["cf:1000A"]

    async def fake(handle):
        return {
            "handle": "ana",
            "rating": 1300,
            "max_rating": 1300,
            "rank": "pupil",
            "solved": list(solved),
            "attempted": [],
            "tag_stats": {},
        }

    monkeypatch.setattr(codeforces, "fetch_profile", fake)
    client.post("/api/v1/library/codeforces", json={"handle": "ana"}, headers=headers)
    engine = client.app.state.engine
    assert asyncio.run(autosync.sync_stale(engine)) == 0  # fresh: nothing to do
    with Session(engine) as db, db.begin():
        db.execute(update(LinkedAccount).values(synced_at=1))
    solved.append("cf:1873A")
    assert asyncio.run(autosync.sync_stale(engine)) == 1
    account = client.get("/api/v1/library/codeforces").json()["account"]
    assert account["solved"] == 2
    exported = client.get("/api/v1/me/export").json()
    assert any(e["kind"] == "verified" for e in exported["evidence"])


def test_library_ranking_is_cached_per_learner_state_and_matches_direct_scoring():
    from socrat.catalog.practice import default_index
    from socrat.library import service

    index = default_index()
    states: dict = {}  # a new learner: the curated list has picks at their level
    learner = recommend.Learner(course="dsa", states=states, now=NOW, rating=1300, seed="s")
    fits = service.fits_for("u1", learner, index, "dsa:arrays-hashing")
    again = recommend.Learner(course="dsa", states=states, now=NOW, rating=1300, seed="s")
    assert service.fits_for("u1", again, index, "dsa:arrays-hashing") is fits

    for pid in index.by_concept["dsa:arrays-hashing"][:50]:
        direct = recommend.score(learner, index.problems[pid], "dsa:arrays-hashing")
        assert fits.get(pid) == direct

    solved = next(iter(fits))
    moved = recommend.Learner(
        course="dsa", states=states, now=NOW, rating=1300, seed="s", solved={solved}
    )
    refreshed = service.fits_for("u1", moved, index, "dsa:arrays-hashing")
    assert refreshed is not fits and solved not in refreshed


def test_curated_library_is_current_and_keeps_pattern_problems():
    """curated.json is what scripts/dev/curate_practice.py writes from the imported index."""
    import importlib.util
    import json

    from socrat.catalog.practice import default_index
    from socrat.catalog.registry import REPO_ROOT

    spec = importlib.util.spec_from_file_location(
        "curate_practice", REPO_ROOT / "scripts" / "dev" / "curate_practice.py"
    )
    assert spec and spec.loader
    curate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(curate)
    built = curate.build()
    saved = json.loads((REPO_ROOT / "content" / "practice" / "curated.json").read_text("utf-8"))
    assert saved == built, "run scripts/dev/curate_practice.py"
    assert 400 <= built["total"] <= 550
    known = {p for group in built["by_concept"].values() for p in group}
    assert curate.pattern_ids(set(default_index().problems)) <= set(built["problems"])
    assert all(len(group) <= curate.CAP for group in built["by_concept"].values())
    assert known <= set(built["problems"])
