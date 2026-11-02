"""Course Maintainer: dead links are removed only when certain, every change is a version,
rollback works, and learners keep their place throughout."""

# ruff: noqa: F811
import asyncio
import time

import httpx
import pytest
from sqlalchemy.orm import Session
from test_coursegen_package import (  # noqa: F401
    ATOMS,
    FACTS_OK,
    GOOD,
    PASS,
    QUIZ,
    Scripted,
    generate,
    lesson,
    published,
    run,
)
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.coursegen import links, maintain
from socrat.coursegen import maintain_routes as routes
from socrat.models import ConceptVersion, Enrollment, ResourceEvent, ResourceHealth

THIRD = "https://blog.example.com/ml/notes"
FOURTH = "https://paper.example.net/ml/survey"
KEY = "ai-basics:what-is-ml"
DAY = 86400


class Site:
    """The web as the maintainer sees it: a link answers 200 until it is taken down."""

    def __init__(self, *urls):
        self.alive = set(urls)
        self.transport = httpx.MockTransport(
            lambda request: httpx.Response(200 if str(request.url) in self.alive else 404)
        )

    def client(self):
        return httpx.AsyncClient(transport=self.transport)


@pytest.fixture
def site(monkeypatch):
    monkeypatch.setattr(links, "public_https", lambda url: url.startswith("https://"))
    monkeypatch.setattr(routes, "http", None)
    return Site(*GOOD, THIRD, FOURTH)


@pytest.fixture
def released(client, published, site):
    """A live generated concept with four resources, learner enrolled in its course."""
    generate(client, published, "what-is-ml")
    script = Scripted(
        author=[lesson(urls=[*GOOD, THIRD, FOURTH])],
        quiz=[QUIZ],
        atoms=[ATOMS],
        facts=[FACTS_OK],
        reviewer=[PASS],
    )
    assert run(client, script.make, site.client())
    return published


def sweep(client, site, at):
    state = client.app.state
    return asyncio.run(
        maintain.sweep(state.engine, state.settings, default_catalog(), at, site.client())
    )


def concept(client):
    with Session(client.app.state.engine) as db:
        return generated.merged(default_catalog()).concept(KEY) if db else None


def urls(client):
    return [str(r.url) for r in concept(client).resources]


T0 = int(time.time())


def test_a_link_must_fail_repeatedly_over_days_before_it_counts_as_dead(client, released, site):
    site.alive.discard(THIRD)
    sweep(client, site, T0)
    sweep(client, site, T0 + 3600)
    third = sweep(client, site, T0 + 7200)  # three failures, but only two hours apart
    assert third["failed"] == 1 and third["repaired"] == []
    assert THIRD in urls(client)
    # A blip that recovers resets the count.
    site.alive.add(THIRD)
    sweep(client, site, T0 + 9000)
    site.alive.discard(THIRD)
    sweep(client, site, T0 + 3 * DAY)
    assert sweep(client, site, T0 + 3 * DAY + 60)["repaired"] == []
    assert THIRD in urls(client)


def test_a_dead_link_is_dropped_as_a_new_version_and_learners_keep_their_place(
    client, released, site
):
    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner, course="ai-basics")
    with Session(client.app.state.engine) as db:
        before = db.query(Enrollment).count()
    site.alive.discard(THIRD)
    repaired = []
    for step in range(5):  # third failure at day 2 is the first to be both repeated and old
        repaired += sweep(client, site, T0 + step * DAY)["repaired"]
    assert [(r["concept"], r["removed"]) for r in repaired] == [(KEY, [THIRD])]
    assert THIRD not in urls(client) and len(urls(client)) == 3
    assert concept(client).provenance.version == 2

    # The released version was kept, so nothing is lost.
    with Session(client.app.state.engine) as db:
        kept = db.query(ConceptVersion).all()
        assert [(v.version, v.reason) for v in kept] == [(1, "dead-link")]
        assert THIRD in [r["url"] for r in kept[0].payload["resources"]]
        assert db.query(Enrollment).count() == before  # the learner's enrolment is untouched
        assert db.get(ResourceHealth, (KEY, THIRD)) is None  # handled: no longer a problem
    # And the lesson still opens for the learner.
    assert client.get(f"/api/v1/concepts/{KEY}").status_code == 200
    # Running again changes nothing.
    assert sweep(client, site, T0 + 6 * DAY)["repaired"] == []


def test_without_two_good_links_left_the_maintainer_asks_a_person(client, released, site):
    boss = released
    for url in (FOURTH, THIRD, GOOD[1]):
        site.alive.discard(url)
    for step in range(4):
        got = sweep(client, site, T0 + step * DAY)
    # Only one good link would remain, so nothing was removed.
    assert got["repaired"] == [] and len(urls(client)) == 4
    queue = client.get("/api/v1/admin/maintenance", headers=boss).json()
    stuck = queue["dead_without_replacement"]
    assert [(s["concept"], s["good"]) for s in stuck] == [(KEY, 1)]
    # Learners are not sent to dead links meanwhile.
    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner, course="ai-basics")
    shown = [r["url"] for r in client.get(f"/api/v1/concepts/{KEY}").json()["resources"]]
    assert shown == [GOOD[0]]


def test_rollback_restores_a_kept_version_and_can_itself_be_undone(client, released, site):
    boss = released
    site.alive.discard(THIRD)
    for step in range(4):
        sweep(client, site, T0 + step * DAY)
    assert len(urls(client)) == 3
    history = client.get("/api/v1/admin/maintenance/ai-basics/what-is-ml/versions", headers=boss)
    (version,) = history.json()["items"]
    back = client.post(
        "/api/v1/admin/maintenance/ai-basics/what-is-ml/rollback",
        json={"version": version["id"]},
        headers=boss,
    ).json()
    assert back["restored_version"] == 1 and THIRD in urls(client)
    # The version we rolled away from is kept too.
    versions = client.get("/api/v1/admin/maintenance/ai-basics/what-is-ml/versions", headers=boss)
    assert [v["version"] for v in versions.json()["items"]] == [2, 1] or len(
        versions.json()["items"]
    ) == 2
    unknown = client.post(
        "/api/v1/admin/maintenance/ai-basics/what-is-ml/rollback",
        json={"version": "nope"},
        headers=boss,
    )
    assert unknown.status_code == 404


def test_rollback_is_refused_while_the_concept_is_being_rewritten(client, released, site):
    from socrat.coursegen import quality

    boss = released
    site.alive.discard(THIRD)
    for step in range(4):
        sweep(client, site, T0 + step * DAY)
    (version,) = client.get(
        "/api/v1/admin/maintenance/ai-basics/what-is-ml/versions", headers=boss
    ).json()["items"]
    with Session(client.app.state.engine) as db, db.begin():
        quality.quarantine(db, default_catalog(), "ai-basics", "what-is-ml", "owner", ["bad"])
    refused = client.post(
        "/api/v1/admin/maintenance/ai-basics/what-is-ml/rollback",
        json={"version": version["id"]},
        headers=boss,
    )
    assert refused.status_code == 409


def test_old_and_unhelpful_content_is_listed_not_changed(client, released, site):
    for name in ("ann", "bob", "cy"):
        login(client, subject=name, name=name)
        with Session(client.app.state.engine) as db, db.begin():
            from socrat.models import User

            user = db.query(User).filter(User.display_name == name).one()
            db.add(ResourceEvent(user_id=user.id, concept=KEY, url=THIRD, helpful=False))
    login(client, subject="boss", name="Boss")
    with Session(client.app.state.engine) as db:
        got = maintain.attention(db, T0 + 400 * DAY, 365)
    assert [s["concept"] for s in got["stale"]] == [KEY]
    assert got["stale"][0]["review_after_days"] == 180  # a code course ages faster
    assert [(u["url"], u["unhelpful"]) for u in got["unhelpful"]] == [(THIRD, 3)]
    with Session(client.app.state.engine) as db:
        assert maintain.attention(db, T0 + DAY, 365)["stale"] == []
    assert THIRD in urls(client)  # listed only


def test_a_rewrite_that_orphans_ids_says_so():
    base = default_catalog().concept("cp:bitmasks")
    renamed = base.model_copy(
        update={"quiz": [base.quiz[0].model_copy(update={"id": "new-id"}), *base.quiz[1:]]}
    )
    assert maintain.lost_ids(base, renamed) == [f"quiz:{base.quiz[0].id}"]
    carried = base.model_copy(
        update={
            "quiz": [
                base.quiz[0].model_copy(update={"id": "new-id", "former_ids": [base.quiz[0].id]}),
                *base.quiz[1:],
            ]
        }
    )
    assert maintain.lost_ids(base, carried) == []


def test_maintenance_is_admin_only_and_the_run_endpoint_reports(client, released, site):
    boss = released
    learner = login(client, subject="ada", name="Ada")
    assert client.get("/api/v1/admin/maintenance", headers=learner).status_code == 403
    assert client.post("/api/v1/admin/maintenance/run", headers=learner).status_code == 403
    boss = login(client, subject="boss", name="Boss")
    routes.http = site.client()
    got = client.post("/api/v1/admin/maintenance/run", headers=boss).json()
    assert got == {"checked": 4, "failed": 0, "repaired": []}
    assert client.get("/api/v1/admin/maintenance", headers=boss).json()["enabled"] is False
