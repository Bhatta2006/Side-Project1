"""Tutor tools: each returns learner-scoped data, and tool calls stream as UI events."""

import asyncio
import json

from test_learner_api import (  # noqa: F401  (client is a fixture)
    client,
    complete_curriculum,
    login,
    onboard,
)

from socrat.assistant import service as assistant
from socrat.assistant.gateway import Event, ToolSpec, execute, valid_arguments
from socrat.assistant.tools import TOOLS, Toolbox, resolve_concept
from socrat.catalog.registry import default_catalog
from socrat.config import Settings


def toolbox_for(client):  # noqa: F811
    me = client.get("/api/v1/me").json()
    return Toolbox(client.app.state.engine, default_catalog(), me["id"])


def call(box: Toolbox, name: str, **arguments):
    text, failed = asyncio.run(box.run(name, arguments))
    return (text if failed or not text.startswith(("{", "[")) else json.loads(text)), failed


def test_every_tool_answers_for_an_enrolled_learner(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers, course="algo", level="brand-new")
    complete_curriculum(client)
    box = toolbox_for(client)
    progress, failed = call(box, "get_progress")
    assert not failed and progress["concepts"]
    assert progress["concepts"][0]["lesson"].startswith("[")
    plan, _ = call(box, "get_plan", days=3)
    assert len(plan["days"]) <= 3 and plan["projected_finish"]
    guide, _ = call(box, "get_concept_guide", concept="algo:pairs")
    assert guide["key_points"] and "approach" not in json.dumps(guide).lower()
    recent, _ = call(box, "get_recent_work", days=7)
    assert "submissions" in recent
    missing, failed = call(box, "get_concept_guide", concept="underwater basket weaving")
    assert failed and missing.startswith("Error:")


def test_concepts_resolve_by_id_or_name():
    catalog = default_catalog()
    assert resolve_concept(catalog, "algo:pairs") == "algo:pairs"
    assert resolve_concept(catalog, "Pairs") == "algo:pairs"
    assert resolve_concept(catalog, "lookup") == "algo:lookup"
    assert resolve_concept(catalog, "zzz") is None


def test_arguments_are_validated_before_running():
    spec = next(t for t in TOOLS if t.name == "get_plan")
    assert valid_arguments(spec, {"days": 3})
    assert not valid_arguments(spec, {"days": "three"})
    assert not valid_arguments(spec, {"unknown": 1})

    async def boom(name, arguments):
        raise RuntimeError("db down")

    specs = {spec.name: spec}
    assert asyncio.run(execute(specs, boom, "get_plan", {}))[1] is True
    assert asyncio.run(execute(specs, boom, "nope", {}))[1] is True
    assert asyncio.run(execute(specs, boom, "get_plan", None))[1] is True


class ScriptedProvider:
    """Calls one tool through the real runner, then answers."""

    name = "scripted"

    def __init__(self):
        self.tool_output = ""

    async def converse(self, system, turns, max_tokens, tools=None, run_tool=None, max_rounds=4):
        assert tools and run_tool and "# Tools" in system
        yield Event("text", "<level>5</level>Let me check your plan.")
        yield Event("tool_call", name="get_plan", arguments={"days": 2})
        self.tool_output, _ = await run_tool("get_plan", {"days": 2})
        yield Event("tool_result", name="get_plan", text=self.tool_output)
        yield Event("text", "Tomorrow you have a lesson.")


def test_tool_calls_stream_as_events_and_text_is_joined(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    box = toolbox_for(client)
    settings = Settings(_env_file=None, environment="test")
    plan = assistant.TurnPlan("thread", "general", 5, None, [], "fallback")
    provider = ScriptedProvider()

    async def collect():
        return [
            e async for e in assistant.stream_reply(provider, plan, settings, box.specs, box.run)
        ]

    events = asyncio.run(collect())
    kinds = [kind for kind, _ in events]
    assert kinds[0] == "meta" and "tool" in kinds and kinds[-1] == "done"
    tool = next(data for kind, data in events if kind == "tool")
    assert tool == {"name": "get_plan", "label": "Looking at your plan"}
    done = events[-1][1]
    assert done["text"] == "Let me check your plan.\n\nTomorrow you have a lesson."
    assert json.loads(provider.tool_output)["days"]


def test_tool_specs_are_well_formed():
    names = [t.name for t in TOOLS]
    assert len(names) == len(set(names))
    for tool in TOOLS:
        assert isinstance(tool, ToolSpec) and tool.parameters["type"] == "object"
        assert set(tool.parameters.get("required", [])) <= set(tool.parameters["properties"])
        assert hasattr(Toolbox, f"_{tool.name}")


def test_tutor_can_only_propose_roadmap_changes_and_flag_gaps(client):  # noqa: F811
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from socrat.models import Evidence, PlanProposal

    headers = login(client)
    onboard(client, headers)
    box = toolbox_for(client)
    before = client.get("/api/v1/plan").json()["days"][0]["items"]
    concept = before[0]["concept"]
    proposed, failed = call(
        box,
        "propose_plan_change",
        kind="probe",
        concept=concept,
        title="Check the foundations",
        reason="The last attempts missed on the basics.",
    )
    assert not failed and proposed["status"].startswith("pending")
    assert client.get("/api/v1/plan").json()["days"][0]["items"] == before  # unchanged
    again, _ = call(
        box, "propose_plan_change", kind="probe", concept=concept, title="x", reason="y"
    )
    assert again.startswith("Not proposed")
    bad, failed = call(
        box, "propose_plan_change", kind="defer", concept="no such thing", title="x", reason="y"
    )
    assert failed
    goal, _ = call(box, "propose_goal", target_role="new-grad", reason="From our chat.")
    assert goal["status"].startswith("pending")
    with Session(client.app.state.engine) as db:
        rows = list(db.scalars(select(PlanProposal)))
        assert {r.kind for r in rows} == {"probe", "goal"}
        assert all(r.source == "tutor" and r.status == "pending" for r in rows)

    for _ in range(4):
        noted, _ = call(
            box, "record_observation", concept=concept, understanding="shaky", note="mixes up"
        )
    assert noted == "Already noted enough about this concept today."
    with Session(client.app.state.engine) as db:
        observations = list(db.scalars(select(Evidence).where(Evidence.kind == "tutor")))
        assert len(observations) == 3 and all(e.score == 0.5 for e in observations)
    profile, failed = call(box, "get_learner_profile")
    assert not failed and {"stuck", "forecast", "pending_changes"} <= set(profile)
    assert len(profile["pending_changes"]) == 2


def test_planning_scope_and_adaptive_context(client):  # noqa: F811
    from sqlalchemy.orm import Session

    from socrat.models import User

    headers = login(client)
    onboard(client, headers)
    me = client.get("/api/v1/me").json()
    with Session(client.app.state.engine) as db, db.begin():
        user = db.get(User, me["id"])
        plan = assistant.prepare(
            db,
            default_catalog(),
            Settings(environment="test"),
            user,
            "plan",
            "Help me plan",
            "chat",
            "",
            False,
            1_800_000_000,
        )
    prompt = plan.turns[-1].content
    assert "<planning_mode>" in prompt and "<adaptive>" in prompt
    assert "Path style: balanced" in prompt


def test_eval_graders_catch_bad_tutor_behaviour():
    from socrat.assistant import evals

    def turn(text, **extra):
        return evals.Turn(text, 3, "test", "", 3, "context [Lists](/learn/basics/lists)", **extra)

    good = turn("Which line first prints the wrong value? See [Lists](/learn/basics/lists).")
    assert [m for c in evals.ALWAYS if (m := c(good))] == []
    assert evals.no_claimed_change(turn("Done! I've updated your plan."))
    assert evals.links_grounded(turn("Try [this](https://example.com/x)."))
    assert evals.no_bare_urls(turn("See https://example.com"))
    assert evals.adapts_to_stuck(turn("Keep going."))
    assert (
        evals.adapts_to_stuck(turn("Keep going.", tool_calls=[("get_learner_profile", {})])) is None
    )
    challenge = turn("Ok.", tool_calls=[("propose_plan_change", {"kind": "test_out"})])
    assert evals.raises_challenge(challenge) is None
    assert evals.one_question(turn("What is your goal? When? How long? Which days?"))


def test_eval_harness_runs_end_to_end_offline():
    import asyncio

    from socrat.assistant import evals
    from socrat.assistant.gateway import OfflineProvider

    report = asyncio.run(
        evals.run(default_catalog(), Settings(environment="test"), OfflineProvider())
    )
    assert [r["scenario"] for r in report] == [s.name for s in evals.SCENARIOS]
    # Offline there is no model, so every scenario reports it rather than passing silently.
    assert all("no model reply" in r["failures"] for r in report)
