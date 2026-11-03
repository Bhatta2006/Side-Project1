"""Brief → outline: agents run as a job, the owner reviews, edits, revises and publishes."""

import asyncio
import json

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.assistant.gateway import Event, usage_event
from socrat.catalog.registry import default_catalog
from socrat.coursegen import jobs, roles
from socrat.coursegen.outline import ARCHITECT
from socrat.models import AIUsage

BRIEF = dict(
    id="ai-basics",
    title="AI Basics",
    audience="Curious programmers who have never studied machine learning.",
    outcome="Explain how a model learns from data and train a tiny one in Python.",
    reuse=["zero:programs-and-output"],
    budget_usd=5.0,
    research=False,
)


def concept(cid, prerequisites=(), depth="overview"):
    return dict(
        id=cid,
        title=cid.replace("-", " ").title(),
        summary=f"What {cid} is and when it matters.",
        prerequisites=list(prerequisites),
        difficulty=2,
        estimated_minutes=40,
        depth=depth,
        objectives=[f"Explain {cid} with an example"],
        misconceptions=["More data always fixes a bad model"],
        assessment=["quiz", "explain"],
    )


OUTLINE = dict(
    tagline="How machines learn from examples.",
    description="A first, deep course on how models learn from data, from loss to training.",
    shape=dict(studio="code", loop="solve", evidence=["tests", "quiz"], tools=["editor"]),
    levels=[
        dict(
            id="brand-new", label="New", description="Start at the beginning.", start_concept=None
        ),
        dict(id="some", label="Some", description="Skip the idea.", start_concept="loss"),
    ],
    modules=[
        dict(
            id="ideas",
            title="Core ideas",
            summary="What learning from data means.",
            concepts=[
                concept("what-is-ml", ["zero:programs-and-output"]),
                concept("loss", ["what-is-ml"], "practitioner"),
            ],
        )
    ],
)


class Scripted:
    """Answers each role from its own queue of replies and remembers every prompt."""

    def __init__(self, architect: list[str], critic: list[str]):
        self.replies = {"architect": architect, "critic": critic}
        self.prompts: dict[str, list[str]] = {"architect": [], "critic": []}

    def make(self, settings):
        script = self

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                role = "architect" if system == ARCHITECT else "critic"
                script.prompts[role].append(turns[0].content)
                yield Event("text", text=script.replies[role].pop(0))
                yield usage_event(1000, 2000)

        return Provider()


def run(client, script):  # noqa: F811
    base = default_catalog()
    return asyncio.run(
        jobs.run_once(client.app.state.engine, client.app.state.settings, base, script.make)
    )


@pytest.fixture
def admin(client):  # noqa: F811
    client.app.state.settings.admin_subjects = ["boss"]
    return login(client, subject="boss", name="Boss")


def test_brief_becomes_a_reviewed_outline_then_a_published_course(client, admin):  # noqa: F811
    job = client.post("/api/v1/admin/courses/briefs", json=BRIEF, headers=admin)
    assert job.status_code == 200 and job.json()["state"] == "queued"
    again = client.post("/api/v1/admin/courses/briefs", json=BRIEF, headers=admin)
    assert again.json()["error"]["code"] == "generation_in_progress"

    broken = dict(OUTLINE, modules=[dict(OUTLINE["modules"][0], concepts=[concept("x")])])
    script = Scripted(
        architect=["not json", json.dumps(broken), "```json\n" + json.dumps(OUTLINE) + "\n```"],
        critic=[json.dumps({"verdict": "pass", "summary": "Solid.", "issues": []})],
    )
    assert run(client, script)
    assert not run(client, script)  # queue empty
    # Bad JSON and a schema failure both came back to the architect as feedback.
    assert "not valid JSON" in script.prompts["architect"][1]
    assert "failed validation" in script.prompts["architect"][2]
    assert "zero:programs-and-output — Programs and output" in script.prompts["architect"][0]

    detail = client.get("/api/v1/admin/courses/ai-basics").json()
    assert detail["status"] == "review"
    assert [c["status"] for c in detail["course"]["concepts"]] == ["planned", "planned"]
    assert detail["course"]["concepts"][1]["outline"]["depth"] == "practitioner"
    assert detail["jobs"][0]["state"] == "done" and detail["spent_usd"] > 0
    with Session(client.app.state.engine) as db:
        features = set(db.scalars(select(AIUsage.feature)))
    assert features == {"coursegen.architect", "coursegen.critic"}

    # Under review, learners cannot see it.
    assert "ai-basics" not in {c["id"] for c in client.get("/api/v1/courses").json()["items"]}

    edited = detail["course"] | {"title": "AI Basics, edited"}
    edited["concepts"][0]["prerequisites"] = ["zero:nope"]
    bad = client.put(
        "/api/v1/admin/courses/ai-basics/outline", json={"course": edited}, headers=admin
    )
    assert bad.json()["saved"] is False and "unknown prerequisite" in bad.json()["errors"][0]
    edited["concepts"][0]["prerequisites"] = []
    good = client.put(
        "/api/v1/admin/courses/ai-basics/outline", json={"course": edited}, headers=admin
    )
    assert good.json() == {"saved": True, "errors": []}

    revise = client.post(
        "/api/v1/admin/courses/ai-basics/revise",
        json={"notes": "Add a module on training."},
        headers=admin,
    )
    assert revise.status_code == 200
    script = Scripted(
        architect=[json.dumps(OUTLINE)],
        critic=[json.dumps({"verdict": "pass", "summary": "Fine.", "issues": []})],
    )
    run(client, script)
    assert "Add a module on training." in script.prompts["architect"][0]
    assert "Your previous outline" in script.prompts["architect"][0]

    assert client.post("/api/v1/admin/courses/ai-basics/publish", headers=admin).json() == {
        "published": True
    }
    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner, course="ai-basics")
    plan = client.get("/api/v1/plan").json()
    statuses = {c["concept"]: c["status"] for m in plan["modules"] for c in m["concepts"]}
    assert statuses["ai-basics:loss"] == "preparing"


def test_critic_revisions_are_capped_and_the_best_outline_is_kept(client, admin):  # noqa: F811
    client.post("/api/v1/admin/courses/briefs", json=BRIEF, headers=admin)
    nag = json.dumps(
        {
            "verdict": "revise",
            "summary": "Thin.",
            "issues": [{"where": "loss", "problem": "Too broad", "fix": "Split"}],
        }
    )
    script = Scripted(architect=[json.dumps(OUTLINE)] * 3, critic=[nag] * 3)
    run(client, script)
    assert "loss: Too broad Fix: Split" in script.prompts["architect"][1]
    detail = client.get("/api/v1/admin/courses/ai-basics").json()
    assert detail["status"] == "review"
    verdicts = [e.get("verdict") for e in detail["jobs"][0]["log"] if e["role"] == "critic"]
    assert verdicts == ["revise"] * jobs.ROUNDS


def test_budget_and_provider_failures_end_the_job_without_a_course(client, admin):  # noqa: F811
    client.post("/api/v1/admin/courses/briefs", json=BRIEF | {"budget_usd": 0.01}, headers=admin)
    run(client, Scripted(architect=["no json here"] * 3, critic=[]))
    detail = client.get("/api/v1/admin/courses/ai-basics").json()
    assert detail["status"] == "drafting" and detail["course"] is None
    assert detail["jobs"][0]["state"] == "failed"
    assert any(e.get("event") == "budget_reached" for e in detail["jobs"][0]["log"])

    client.post(
        "/api/v1/admin/courses/briefs", json=BRIEF | {"id": "offline-course"}, headers=admin
    )
    asyncio.run(
        jobs.run_once(client.app.state.engine, client.app.state.settings, default_catalog())
    )
    failed = client.get("/api/v1/admin/courses/offline-course").json()["jobs"][0]
    assert failed["state"] == "failed" and "provider_offline" in failed["error"]


def test_admin_only_and_brief_checks(client, admin):  # noqa: F811
    assert (
        client.post(
            "/api/v1/admin/courses/briefs", json=BRIEF | {"id": "dsa"}, headers=admin
        ).json()["error"]["code"]
        == "course_exists"
    )
    assert (
        client.post(
            "/api/v1/admin/courses/briefs", json=BRIEF | {"reuse": ["zero:nope"]}, headers=admin
        ).json()["error"]["code"]
        == "unknown_reuse_concept"
    )
    learner = login(client, subject="ada", name="Ada")
    assert (
        client.post("/api/v1/admin/courses/briefs", json=BRIEF, headers=learner).status_code == 403
    )
    assert client.get("/api/v1/admin/courses").status_code == 403


def test_role_overrides_are_checked_and_applied(client):  # noqa: F811
    with pytest.raises(ValueError, match="unknown keys"):
        roles.check_roles({"critic": {"temperature": 1}})
    with pytest.raises(ValueError, match="unknown role"):
        roles.check_roles({"poet": {}})
    settings = client.app.state.settings.model_copy(
        update={"gen_roles": {"critic": {"provider": "openai", "model": "m-1", "effort": "low"}}}
    )
    critic = roles.role_settings(settings, "critic")
    assert (critic.ai_provider, critic.openai_model, critic.ai_effort) == ("openai", "m-1", "low")
    assert roles.role_settings(settings, "architect").ai_effort == "high"


def test_an_identical_brief_reuses_the_passed_outline_without_a_model_call(client, admin):  # noqa: F811
    first = Scripted(
        architect=[json.dumps(OUTLINE)],
        critic=[json.dumps({"verdict": "pass", "summary": "Solid.", "issues": []})],
    )
    client.post("/api/v1/admin/courses/briefs", json=BRIEF, headers=admin)
    assert run(client, first)

    # Same request, another course id and budget: the design is the same, so is the outline.
    twin = dict(BRIEF, id="ai-basics-two", budget_usd=9.0)
    client.post("/api/v1/admin/courses/briefs", json=twin, headers=admin)
    silent = Scripted(architect=[], critic=[])  # any model call would pop from an empty list
    assert run(client, silent)
    assert silent.prompts == {"architect": [], "critic": []}
    detail = client.get("/api/v1/admin/courses/ai-basics-two").json()
    assert detail["status"] == "review" and detail["jobs"][0]["state"] == "done"
    assert [c["id"] for c in detail["course"]["concepts"]] == ["what-is-ml", "loss"]
    log = detail["jobs"][0]["log"]
    assert any(e.get("reused_from") == "ai-basics" for e in log)
    assert detail["spent_usd"] == 0

    # A different request is designed afresh.
    other = dict(BRIEF, id="ai-deeper", outcome="Derive gradient descent and implement it.")
    client.post("/api/v1/admin/courses/briefs", json=other, headers=admin)
    fresh = Scripted(
        architect=[json.dumps(OUTLINE)],
        critic=[json.dumps({"verdict": "pass", "summary": "Fine.", "issues": []})],
    )
    assert run(client, fresh)
    assert len(fresh.prompts["architect"]) == 1


def test_an_outline_the_critic_did_not_pass_is_never_reused(client, admin):  # noqa: F811
    revise = json.dumps({"verdict": "revise", "summary": "Weak.", "issues": []})
    weak = Scripted(architect=[json.dumps(OUTLINE)] * 3, critic=[revise] * 3)
    client.post("/api/v1/admin/courses/briefs", json=BRIEF, headers=admin)
    assert run(client, weak)
    client.post("/api/v1/admin/courses/briefs", json=dict(BRIEF, id="ai-again"), headers=admin)
    retry = Scripted(
        architect=[json.dumps(OUTLINE)],
        critic=[json.dumps({"verdict": "pass", "summary": "Ok.", "issues": []})],
    )
    assert run(client, retry)
    assert len(retry.prompts["architect"]) == 1


def test_a_later_start_counts_every_earlier_module_as_known(client, admin):  # noqa: F811
    """Found in a live run: a learner placed at module 3 of a generated course whose start
    concept does not depend on module 2 had module 2 neither known nor written, so module 2's
    checkpoint locked the very lesson generated for them and Today offered nothing."""
    from socrat.catalog import generated
    from socrat.learn import service as learn
    from socrat.models import Enrollment

    modules = [
        dict(id="basics", title="Basics", summary="What a chance is, on a scale.",
             concepts=[concept("scale")]),
        dict(id="combining", title="Combining", summary="Joining two chances together.",
             concepts=[concept("both", ["scale"]), concept("either", ["both"])]),
        dict(id="games", title="Games", summary="What a bet is worth on average.",
             concepts=[concept("worth", ["scale"])]),
    ]
    levels = [
        dict(id="new", label="New", description="Start at the beginning.", start_concept=None),
        dict(id="games", label="I can combine events", description="Start at games.",
             start_concept="worth"),
    ]
    graph = dict(OUTLINE, modules=modules, levels=levels)
    client.post("/api/v1/admin/courses/briefs", json=BRIEF, headers=admin)
    passed = json.dumps({"verdict": "pass", "summary": "Fine.", "issues": []})
    assert run(client, Scripted(architect=[json.dumps(graph)], critic=[passed]))
    client.post("/api/v1/admin/courses/ai-basics/publish", headers=admin)

    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner, course="ai-basics", level="games")
    with Session(client.app.state.engine) as db:
        enrollment = db.scalars(select(Enrollment)).one()
        known = {q for q, s in learn.states_for(db, enrollment).items() if s.assumed}
        cat = generated.merged(default_catalog())
        locked = learn.locked_concepts(db, cat, enrollment, int(__import__("time").time()))
    # Everything before the start in course order is known, not only its prerequisites ...
    # (dependency order puts "worth" before "either", which is deeper; course order does not)
    assert {"ai-basics:scale", "ai-basics:both", "ai-basics:either"} <= known
    assert "ai-basics:worth" not in known
    # ... so the start concept is not locked behind the skipped module's checkpoint.
    assert "ai-basics:worth" not in locked


def test_a_written_start_lesson_is_not_locked_behind_unwritten_earlier_modules(client, admin):  # noqa: F811
    """Second shape of the live-run bug: the start lesson exists, so placement probes there, and
    the earlier lessons (not written, level says known) used to stay unknown, so module
    checkpoints locked the written lesson for good."""
    import time

    from socrat.catalog import generated
    from socrat.learn import service as learn
    from socrat.models import Enrollment

    modules = [
        dict(id="basics", title="Basics", summary="What a chance is, on a scale.",
             concepts=[concept("scale")]),
        dict(id="combining", title="Combining", summary="Joining two chances together.",
             concepts=[concept("both", ["scale"]), concept("either", ["both"])]),
        dict(id="games", title="Games", summary="What a bet is worth on average.",
             concepts=[concept("worth", ["scale"])]),
    ]
    levels = [
        dict(id="new", label="New", description="Start at the beginning.", start_concept=None),
        dict(id="games", label="I can combine events", description="Start at games.",
             start_concept="worth"),
    ]
    client.post("/api/v1/admin/courses/briefs", json=BRIEF, headers=admin)
    passed = json.dumps({"verdict": "pass", "summary": "Fine.", "issues": []})
    graph = dict(OUTLINE, modules=modules, levels=levels)
    assert run(client, Scripted(architect=[json.dumps(graph)], critic=[passed]))
    client.post("/api/v1/admin/courses/ai-basics/publish", headers=admin)

    base = default_catalog()
    model = base.concept("zero:programs-and-output").model_dump(mode="json")
    live = type(base.concept("zero:programs-and-output")).model_validate(
        model | dict(id="worth", module="games", prerequisites=["scale"], outline=None, sequence=[], problems=[], practice_links=[])
    )
    with Session(client.app.state.engine) as db, db.begin():
        generated.store_concept(db, base, "ai-basics", live, None)

    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner, course="ai-basics", level="games")
    with Session(client.app.state.engine) as db:
        enrollment = db.scalars(select(Enrollment)).one()
        assert enrollment.status == "placement"  # the written start lesson is probed
        cat = generated.merged(default_catalog())
        known = {q for q, s in learn.states_for(db, enrollment).items() if s.assumed}
        locked = learn.locked_concepts(db, cat, enrollment, int(time.time()))
    assert {"ai-basics:scale", "ai-basics:both", "ai-basics:either"} <= known
    assert "ai-basics:worth" not in known and "ai-basics:worth" not in locked
