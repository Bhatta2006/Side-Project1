"""Stronger agents at low cost: a strong model where judgement decides the result, a fast one
for reading and sorting, the default for the rest, and the strong one again when the usual
model has failed. Nothing changes until SOCRAT_GEN_TIERS is set."""

# ruff: noqa: F811
import json

import pytest
from pydantic import ValidationError
from test_coursegen_package import (  # noqa: F401
    ATOMS,
    FACTS_OK,
    PASS,
    QUIZ,
    ROLES,
    Scripted,
    generate,
    lesson,
    published,
    run,
    web,
)
from test_learner_api import client  # noqa: F401

from socrat.assistant.gateway import Event, usage_event
from socrat.config import Settings
from socrat.coursegen import costs, roles

TIERS = {
    "strong": {"model": "big-model", "price_input_per_mtok": 3.0, "price_output_per_mtok": 15.0},
    "fast": {"model": "small-model", "effort": "low"},
}


def base(**extra) -> Settings:
    return Settings(environment="test", ai_model="claude-default", **extra)


def model(settings: Settings, role: str, escalate: bool = False) -> str:
    return roles.role_settings(settings, role, escalate).ai_model


def test_without_tiers_every_role_runs_on_the_default_model_as_before():
    settings = base()
    assert {model(settings, r) for r in roles.ROLES} == {"claude-default"}
    assert model(settings, "quiz", escalate=True) == "claude-default"  # nothing to escalate to


def test_each_role_runs_on_its_tier():
    settings = base(gen_tiers=TIERS)
    for role in ("architect", "reviser", "facts", "reviewer"):
        assert model(settings, role) == "big-model", role
    for role in ("researcher", "stylist", "intent", "experience"):
        assert model(settings, role) == "small-model", role
    for role in ("author", "quiz", "atoms", "critic", "grader"):
        assert model(settings, role) == "claude-default", role
    tuned = roles.role_settings(settings, "facts")
    assert (tuned.ai_price_input_per_mtok, tuned.ai_price_output_per_mtok) == (3.0, 15.0)
    assert roles.role_settings(settings, "intent").ai_effort == "low"


def test_a_roles_own_setting_wins_over_its_tier_but_not_over_an_escalation():
    settings = base(
        gen_tiers=TIERS, gen_roles={"facts": {"model": "pinned"}, "quiz": {"model": "q"}}
    )
    assert model(settings, "facts") == "pinned"
    assert model(settings, "quiz") == "q"
    assert model(settings, "quiz", escalate=True) == "big-model"  # the second try is the strong one


def test_the_reviser_falls_back_to_the_author_only_when_nothing_stronger_is_set():
    assert model(base(gen_roles={"author": {"model": "writer"}}), "reviser") == "writer"
    assert model(base(gen_tiers=TIERS, gen_roles={"author": {"model": "writer"}}), "reviser") == (
        "big-model"
    )
    only_fast = base(gen_tiers={"fast": {"model": "small-model"}})
    assert model(only_fast, "reviser") == "claude-default"
    assert model(only_fast, "architect") == "claude-default"  # its tier is not configured


def test_an_unknown_tier_or_key_is_refused_at_startup():
    with pytest.raises(ValidationError):
        base(gen_tiers={"huge": {"model": "x"}})
    with pytest.raises(ValidationError):
        base(gen_tiers={"strong": {"temperature": 1}})


class Recording(Scripted):
    """The scripted model, remembering which model each role's calls ran on."""

    def __init__(self, **replies):
        super().__init__(**replies)
        self.models: dict[str, list[str]] = {}

    def make(self, settings):
        script = self

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                role = ROLES[system]
                script.models.setdefault(role, []).append(settings.ai_model)
                script.prompts[role].append(turns[0].content)
                yield Event("text", text=script.replies[role].pop(0))
                yield usage_event(1000, 3000)

        return Provider()


def test_a_part_the_usual_model_garbled_is_asked_again_of_the_strong_model(client, published, web):
    client.app.state.settings.gen_tiers = TIERS
    generate(client, published, "what-is-ml")
    script = Recording(
        author=[lesson()], quiz=[QUIZ], atoms=[ATOMS], facts=[FACTS_OK], reviewer=[PASS]
    )
    script.replies["quiz"] = ["{not json", json.dumps(QUIZ)]
    assert run(client, script.make, web())
    assert script.models["quiz"] == ["claude-opus-5-5", "big-model"]
    assert script.models["author"] == ["claude-opus-5-5"]  # the first draft stays cheap
    assert script.models["facts"] == ["big-model"] and script.models["reviewer"] == ["big-model"]
    detail = client.get("/api/v1/admin/courses/ai-basics/concepts/what-is-ml", headers=published)
    calls = detail.json()["jobs"][0]["log"][-1]["calls"]
    assert [(c["role"], c["tier"]) for c in calls if c["role"] == "quiz"] == [
        ("quiz", "default"),
        ("quiz", "strong"),
    ]
    assert {c["tier"] for c in calls if c["role"] in ("facts", "reviewer")} == {"strong"}


def test_the_cost_report_shows_tiers_models_and_courses_over_the_lesson_target(
    client, published, web
):
    settings = client.app.state.settings
    settings.gen_tiers = TIERS
    settings.gen_lesson_cost_target_usd = 0.01
    generate(client, published, "what-is-ml")
    script = Recording(
        author=[lesson()], quiz=[QUIZ], atoms=[ATOMS], facts=[FACTS_OK], reviewer=[PASS]
    )
    assert run(client, script.make, web())
    report = client.get("/api/v1/admin/engine-costs", headers=published).json()
    # This server has no provider (offline), so the report says so instead of naming a model.
    assert report["tiers"]["facts"] == {"tier": "strong", "model": "offline", "effort": "high"}
    live = costs.tiers(base(ai_provider="anthropic", gen_tiers=TIERS))
    assert live["facts"] == {"tier": "strong", "model": "big-model", "effort": "high"}
    assert live["author"]["model"] == "claude-default" and live["intent"]["model"] == "small-model"
    assert report["tiers"]["author"]["tier"] == "default"
    assert report["tiers"]["intent"]["tier"] == "fast"
    assert report["models"]["big-model"]["calls"] == 2  # facts and reviewer
    assert report["models"]["big-model"]["cost_per_call_usd"] > 0
    course = next(c for c in report["courses"] if c["course_id"] == "ai-basics")
    assert course["released_concepts"] == 1 and course["over_target"] is True
    assert report["lesson_cost_target_usd"] == 0.01
    settings.gen_lesson_cost_target_usd = 100
    again = client.get("/api/v1/admin/engine-costs", headers=published).json()
    assert (
        next(c for c in again["courses"] if c["course_id"] == "ai-basics")["over_target"] is False
    )
    # No key, URL or secret in the tier report.
    assert not any(k in json.dumps(report["tiers"]) for k in ("key", "secret", "http"))
    assert costs.tiers(Settings(environment="test"))["architect"]["tier"] == "default"
