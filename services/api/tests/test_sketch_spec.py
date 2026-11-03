"""Declarative sketches (master prompt 5 and 14): the model writes data, the host owns all the
code that runs in the learner's browser."""

import asyncio
import copy
import json

import pytest
from test_explainer import QA, Provider

from socrat.config import Settings
from socrat.explainer import generator, sketch
from socrat.explainer.artifact import ArtifactError, validate

EXAMPLE = json.loads(generator.SKETCH_EXAMPLE)


def test_the_example_is_valid_and_builds_a_page_the_validator_accepts():
    spec = sketch.check(copy.deepcopy(EXAMPLE))
    document = validate(sketch.page(spec))
    assert document.title == "Binary search, drawn"
    assert "Binary search finds a value" in document.transcript
    # The only script is the host's player with the spec as a literal.
    assert len(document.scripts) == 1 and document.scripts[0].startswith("const SPEC={")
    assert sketch.PLAYER.strip() in document.scripts[0]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda s: s["variants"][0]["steps"][0]["scene"].update(focus=["a.99"]), "focus"),
        (
            lambda s: s["variants"][0]["steps"][0]["scene"].update(
                links=[{"from": "a.0", "to": "b.1"}]
            ),
            "links[0]",
        ),
        (lambda s: s["variants"][0]["steps"][1].update(note="x" * 200), "note"),
        (
            lambda s: s["variants"][0]["steps"][1].update(
                note=s["variants"][0]["steps"][0]["note"]
            ),
            "own note",
        ),
        (lambda s: s["input"].update(options=["23"]), "one option per variant"),
        (lambda s: s.update(summary="Too short."), "summary"),
        (lambda s: s["variants"][0]["steps"][0]["scene"]["rows"][0].update(id="a.b"), "rows[0].id"),
    ],
)
def test_bad_specs_are_rejected_with_the_field_named(change, message):
    spec = copy.deepcopy(EXAMPLE)
    change(spec)
    with pytest.raises(ArtifactError, match=message.replace("[", r"\[").replace("]", r"\]")):
        sketch.check(spec)


def test_text_cannot_break_out_of_the_host_script():
    spec = copy.deepcopy(EXAMPLE)
    spec["variants"][0]["steps"][0]["note"] = "</script><script>alert(1)</script>"
    page = sketch.page(sketch.check(spec))
    assert "</script><script>alert" not in page
    assert page.count("<script>") == 1
    validate(page)


def test_declarative_mode_asks_for_json_and_stores_the_spec(monkeypatch):
    async def check(*args):
        return QA

    async def review(*args):
        pass

    monkeypatch.setattr(generator, "render_check", check)
    monkeypatch.setattr(generator, "review", review)
    bad = copy.deepcopy(EXAMPLE)
    bad["variants"][0]["steps"][0]["scene"]["focus"] = ["nope.1"]
    provider = Provider([json.dumps(bad), json.dumps(EXAMPLE)])
    settings = Settings(environment="test", explainer_sketch_declarative=True)

    async def run():
        return [
            e
            async for e in generator.generate(
                provider, settings, "Explain binary search", "python", "standard"
            )
        ]

    events = asyncio.run(run())
    document = events[-1]["document"]
    assert document["prompt_version"] == "visual-sketch-spec-v1" and document["sketch"]["title"]
    assert "Return ONLY one JSON object" in provider.calls[0][0]
    assert "never write code" in provider.calls[0][0]
    assert "Repair the complete sketch JSON" in provider.calls[1][1][-1].content
    assert "focus" in provider.calls[1][1][-1].content


def test_off_by_default_keeps_the_current_sketch_mode():
    assert Settings(environment="test").explainer_sketch_declarative is False


def test_the_host_player_draws_and_steps_every_variant_in_a_real_browser():
    """The same browser check every generated visual must pass: it loads the page, steps
    through it, and rejects overlapping or cut-off text and script errors."""
    settings = Settings(environment="test")
    qa = asyncio.run(generator.render_check(validate(sketch.page(sketch.check(EXAMPLE))), settings))
    assert qa["ok"] and qa["step_count"] == 4


def test_the_playground_visual_is_a_registered_lesson_renderer():
    from socrat.engine import renderers

    manifest = renderers.all_manifests()["playground-visual"]
    assert manifest.sandboxed and "sandbox-frame" in manifest.runtime
    assert "concept-playground" not in renderers.all_manifests()  # model-designed code: gone
    base = dict(
        renderer="playground-visual",
        version="2.0",
        purpose="See the idea drawn step by step",
        fallback_text="Each step halves the part of the list that can still hold the value.",
        alt_text="A sketch of binary search.",
    )
    assert renderers.validate_spec(base | {"params": {"level": "deep"}}) == []
    assert renderers.validate_spec(base | {"params": {"level": "huge"}})
