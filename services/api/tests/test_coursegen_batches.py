"""Generated courses in use: prefetch from learner progress, hold state, budgets and pause,
and quarantine from learner reports."""

from sqlalchemy import select
from sqlalchemy.orm import Session
from test_coursegen_package import (  # noqa: F401  (fixtures)
    ATOMS,
    FACTS_OK,
    PASS,
    QUIZ,
    Scripted,
    lesson,
    published,
    run,
    web,
)
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.coursegen import jobs
from socrat.models import GeneratedConcept, GeneratedCourse, GenerationJob


def package_jobs(client, concept=None):  # noqa: F811
    with Session(client.app.state.engine) as db:
        query = select(GenerationJob).where(GenerationJob.kind == "package")
        if concept:
            query = query.where(GenerationJob.target == concept)
        return list(db.scalars(query.order_by(GenerationJob.created_at)))


def release(client, concept, web):  # noqa: F811
    script = Scripted(
        author=[lesson()], quiz=[QUIZ], atoms=[ATOMS], facts=[FACTS_OK], reviewer=[PASS]
    )
    with Session(client.app.state.engine) as db, db.begin():
        jobs.enqueue(db, "package", "ai-basics", {}, None, target=concept)
    run(client, script.make, web())
    assert generated.merged(default_catalog()).concept(f"ai-basics:{concept}").status == "live"


def test_learner_progress_queues_the_next_concepts_once(client, published):  # noqa: F811
    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner, course="ai-basics")  # placed at the start: prefetch runs
    assert {(j.target, j.input["trigger"]) for j in package_jobs(client)} == {
        ("what-is-ml", "prefetch"),
        ("loss", "prefetch"),
    }
    client.post("/api/v1/activities/lesson:zero:programs-and-output/complete", headers=learner)
    assert len(package_jobs(client)) == 2  # already queued: nothing new

    with Session(client.app.state.engine) as db, db.begin():
        for job in db.scalars(select(GenerationJob).where(GenerationJob.target == "loss")):
            job.state = "failed"
    other = login(client, subject="bo", name="Bo")
    onboard(client, other, course="ai-basics")
    assert len(package_jobs(client, "loss")) == 1  # a failed concept waits for the owner

    nudges = client.get("/api/v1/adaptive/nudges").json()["nudges"]
    preparing = [n for n in nudges if n["kind"] == "preparing"]
    assert preparing and "being written" in preparing[0]["title"]


def test_hand_authored_courses_never_queue_generation(client):  # noqa: F811
    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner)
    client.post("/api/v1/activities/lesson:zero:programs-and-output/complete", headers=learner)
    assert package_jobs(client) == []


def test_budget_pauses_the_course_until_the_owner_raises_it(client, published, web):  # noqa: F811
    admin = published
    with Session(client.app.state.engine) as db, db.begin():
        row = db.get(GeneratedCourse, "ai-basics")
        row.brief = {**row.brief, "budget_usd": 0.02}  # already spent on the outline
        jobs.enqueue(db, "package", "ai-basics", {}, None, target="what-is-ml")
    run(client, Scripted().make, web())
    detail = client.get("/api/v1/admin/courses/ai-basics").json()
    assert detail["paused"] == "budget"
    job = package_jobs(client, "what-is-ml")[0]
    assert job.state == "queued" and job.log[-1]["event"] == "budget_reached_paused"
    assert jobs.claim(client.app.state.engine) is None  # paused: the job waits

    resume = client.post("/api/v1/admin/courses/ai-basics/resume", headers=admin)
    assert resume.json()["error"]["code"] == "budget_reached"
    client.put(
        "/api/v1/admin/courses/ai-basics/budget",
        json={"budget_usd": 50, "concept_budget_usd": 2},
        headers=admin,
    )
    assert client.post("/api/v1/admin/courses/ai-basics/resume", headers=admin).status_code == 200
    script = Scripted(
        author=[lesson()], quiz=[QUIZ], atoms=[ATOMS], facts=[FACTS_OK], reviewer=[PASS]
    )
    run(client, script.make, web())
    assert package_jobs(client, "what-is-ml")[0].state == "done"

    client.post("/api/v1/admin/courses/ai-basics/pause", headers=admin)
    with Session(client.app.state.engine) as db, db.begin():
        jobs.enqueue(db, "package", "ai-basics", {}, None, target="loss")
    assert jobs.claim(client.app.state.engine) is None


def test_one_concept_cannot_spend_past_its_cap(client, published, web):  # noqa: F811
    client.put(
        "/api/v1/admin/courses/ai-basics/budget",
        json={"budget_usd": 50, "concept_budget_usd": 0.01},
        headers=published,
    )
    with Session(client.app.state.engine) as db, db.begin():
        jobs.enqueue(db, "package", "ai-basics", {}, None, target="loss")
    run(client, Scripted(author=[lesson(size=1)]).make, web())  # round 1 fails its gates
    job = package_jobs(client, "loss")[0]
    assert job.state == "failed" and job.log[-2]["event"] == "concept_budget_reached"


def test_learner_reports_quarantine_and_rewrite_a_concept(client, published, web):  # noqa: F811
    release(client, "what-is-ml", web)
    report = dict(route="/learn/ai-basics/what-is-ml", category="content")
    for i, name in enumerate(["ada", "bo", "cy"]):
        headers = login(client, subject=name, name=name.title())
        body = report | {"message": f"The worked example adds wrong ({i})"}
        assert client.post("/api/v1/problem-reports", json=body, headers=headers).status_code == 200
        live = generated.merged(default_catalog()).concept("ai-basics:what-is-ml").status
        assert live == ("live" if i < 2 else "planned")  # the third learner tips it

    with Session(client.app.state.engine) as db:
        row = db.get(GeneratedConcept, ("ai-basics", "what-is-ml"))
        assert row.atoms["status"] == "quarantined"
    rewrite = package_jobs(client, "what-is-ml")[-1]
    assert rewrite.state == "queued" and rewrite.input["trigger"] == "quarantine"
    assert len(rewrite.input["reports"]) == 3

    script = Scripted(
        author=[lesson()], quiz=[QUIZ], atoms=[ATOMS], facts=[FACTS_OK], reviewer=[PASS]
    )
    run(client, script.make, web())
    assert (
        "Learners reported: [content] The worked example adds wrong (0)"
        in script.prompts["author"][0]
    )
    assert "Your previous draft" in script.prompts["author"][0]
    again = generated.merged(default_catalog()).concept("ai-basics:what-is-ml")
    assert again.status == "live" and again.provenance.version == 2


def test_owner_can_withdraw_a_released_concept(client, published, web):  # noqa: F811
    release(client, "what-is-ml", web)
    learner = login(client, subject="ada", name="Ada")
    assert (
        client.post(
            "/api/v1/admin/courses/ai-basics/concepts/what-is-ml/quarantine",
            json={"notes": "Wrong"},
            headers=learner,
        ).status_code
        == 403
    )
    admin = login(client, subject="boss", name="Boss")
    url = "/api/v1/admin/courses/ai-basics/concepts/what-is-ml/quarantine"
    assert client.post(
        url, json={"notes": "Example uses the wrong loss."}, headers=admin
    ).json() == {"quarantined": True}
    assert (
        client.post(url, json={"notes": "Again"}, headers=admin).json()["error"]["code"]
        == "concept_not_live"
    )
    assert package_jobs(client, "what-is-ml")[-1].input["reports"] == [
        "Example uses the wrong loss."
    ]
