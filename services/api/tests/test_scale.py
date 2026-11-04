"""Scale guards: shared limits on open endpoints, cache headers on public catalogues, and the
per-course generation cost report."""

# ruff: noqa: F811
from sqlalchemy.orm import Session
from test_learner_api import client, login  # noqa: F401

from socrat import limits
from socrat.models import AIUsage, GeneratedConcept, GeneratedCourse, GenerationJob, now


def test_limiter_slides_and_isolates_keys():
    lim = limits.Limiter()
    assert [lim.allow("a", 2, 60, at=t) for t in (0, 1, 2)] == [True, True, False]
    assert lim.allow("b", 2, 60, at=2)  # another key has its own window
    assert lim.allow("a", 2, 60, at=61)  # the first hit has aged out
    assert lim.allow("a", 2, 60, at=61.5)
    assert not lim.allow("a", 2, 60, at=62)  # two hits inside the window again


def test_limiter_forgets_idle_keys():
    lim = limits.Limiter(max_keys=3)
    for i in range(6):
        lim.allow(f"k{i}", 1, 10, at=i * 100)
    assert len(lim._hits) <= 4


def test_simulate_is_limited_per_learner(client):
    limits.LIMITER.clear()
    client.app.state.settings.simulate_per_minute = 3
    url = "/api/v1/engine/simulate"
    one = login(client, subject="one")
    codes = [client.post(url, json={"model": "circuit"}, headers=one).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
    assert client.post(url, json={"model": "circuit"}, headers=one).json()["error"]["code"] == (
        "rate_limited"
    )
    two = login(client, subject="two")  # a different learner is not affected
    assert client.post(url, json={"model": "circuit"}, headers=two).status_code == 200
    client.app.state.settings.simulate_per_minute = 0  # 0 turns the limit off
    assert client.post(url, json={"model": "circuit"}, headers=two).status_code == 200
    limits.LIMITER.clear()


def test_public_catalogues_are_cacheable_and_revalidate(client):
    first = client.get("/api/v1/engine/renderers")
    assert first.status_code == 200
    assert "public" in first.headers["cache-control"]
    tag = first.headers["etag"]
    again = client.get("/api/v1/engine/renderers", headers={"If-None-Match": tag})
    assert again.status_code == 304 and again.headers["etag"] == tag
    assert (
        client.get("/api/v1/engine/renderers", headers={"If-None-Match": '"x"'}).status_code == 200
    )
    for path in ("/api/v1/engine/domains", "/api/v1/engine/simulations"):
        assert "public" in client.get(path).headers["cache-control"]


def test_everything_else_stays_uncacheable(client):
    login(client)
    assert client.get("/api/v1/me").headers["cache-control"] == "no-store"
    assert client.get("/api/v1/locales").headers["cache-control"] == "no-store"


def test_engine_cost_report_by_course_and_role(client):
    client.app.state.settings.admin_subjects = ["boss"]
    admin = login(client, subject="boss", name="Boss")
    stamp = now()
    with Session(client.app.state.engine) as db, db.begin():
        for cid, owner in (("cheap", None), ("dear", None)):
            db.add(GeneratedCourse(id=cid, payload={"title": cid.title()}, owner_id=owner))
        db.flush()
        for cid, cost, live in (("cheap", 0.5, 2), ("dear", 3.0, 1)):
            for kind in ("outline", "package"):
                db.add(GenerationJob(kind=kind, course_id=cid, input={}, cost_usd=cost / 2))
            for i in range(live):
                db.add(
                    GeneratedConcept(course_id=cid, concept_id=f"c{i}", payload={"status": "live"})
                )
        db.add(GeneratedConcept(course_id="dear", concept_id="d", payload={"status": "planned"}))
        day = limits_day(stamp)
        for feature, cost in (("coursegen.author", 1.0), ("coursegen.author", 0.5), ("tutor", 9)):
            db.add(
                AIUsage(
                    feature=feature,
                    provider="p",
                    model="m",
                    input_tokens=10,
                    output_tokens=5,
                    cost_usd=cost,
                    day=day,
                    created_at=stamp,
                )
            )
    report = client.get("/api/v1/admin/engine-costs", headers=admin).json()
    courses = {c["course_id"]: c for c in report["courses"]}
    assert [c["course_id"] for c in report["courses"]] == ["dear", "cheap"]  # costliest first
    assert courses["dear"]["cost_usd"] == 3.0 and courses["dear"]["released_concepts"] == 1
    assert courses["dear"]["cost_per_released_concept_usd"] == 3.0
    assert courses["cheap"]["cost_per_released_concept_usd"] == 0.25
    assert report["roles"] == {"author": dict(calls=2, cost_usd=1.5, tokens=30)}  # tutor excluded
    login(client, subject="learner")
    assert client.get("/api/v1/admin/engine-costs").status_code in (401, 403)


def limits_day(stamp: int) -> str:
    from socrat.assistant.budget import day_of

    return day_of(stamp)


def test_cold_catalog_is_loaded_once_when_many_requests_arrive_together():
    """A cold server used to parse the whole catalog once per concurrent request (about 6 s of
    CPU each) and stall for minutes under 25 learners. Now the first caller loads, others wait."""
    import threading
    import time

    from socrat.catalog.registry import single_flight

    calls = []

    @single_flight
    def slow() -> str:
        calls.append(1)
        time.sleep(0.2)
        return "catalog"

    results: list[str] = []
    threads = [threading.Thread(target=lambda: results.append(slow())) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results == ["catalog"] * 12 and len(calls) == 1
    slow.cache_clear()  # type: ignore[attr-defined]
    assert slow() == "catalog" and len(calls) == 2


def test_engine_report_shows_reliability_latency_and_time_to_first_lesson(client):
    client.app.state.settings.admin_subjects = ["boss"]
    admin = login(client, subject="boss", name="Boss")
    with Session(client.app.state.engine) as db, db.begin():
        db.add(GeneratedCourse(id="c", payload={"title": "C"}, created_at=1_000))
        calls = [{"role": "author", "ms": 900}, {"role": "reviewer", "ms": 300}]
        released = {"event": "released", "at": 1_600, "calls": calls}
        db.add(GenerationJob(kind="package", course_id="c", input={}, state="done", log=[released]))
        db.add(GenerationJob(kind="package", course_id="c", input={}, state="dead", attempts=3))
        db.add(GenerationJob(kind="package", course_id="c", input={}, state="queued", attempts=1))
        db.add(GenerationJob(kind="outline", course_id="c", input={}, state="done"))
    got = client.get("/api/v1/admin/engine-costs", headers=admin).json()["reliability"]
    assert got["jobs"]["package"] == {"done": 1, "dead": 1, "queued": 1}
    assert got["success_rate"] == {"package": 0.5, "outline": 1.0}
    assert got["retried_jobs"] == 2 and got["dead_jobs"] == 1
    assert got["latency_ms"]["author"] == {"calls": 1, "p50": 900, "p95": 900}
    assert got["first_lesson_seconds"] == {"courses": 1, "p50": 600, "p95": 600}
