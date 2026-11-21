"""Declarative sketches (master prompt 5 and 14): the model writes data, the host owns all the
code that runs in the learner's browser."""

import asyncio
import copy
import json
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_explainer import QA, Provider, configured, generate  # noqa: F401
from test_learner_api import client  # noqa: F401

from socrat.config import Settings
from socrat.explainer import generator, sketch
from socrat.explainer.artifact import ArtifactError, validate
from socrat.models import PlaygroundJob

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


def test_declarative_sketches_are_on_by_default():
    settings = Settings(environment="test")
    assert settings.explainer_sketch_declarative is True
    assert settings.explainer_sketch_effort == "low"  # sketches and routing think little


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


def one_variant(steps):
    return {
        "title": "Counting up",
        "desc": "One row of numbers.",
        "summary": "Counting adds one each time. The row shows each new number in turn, and the "
        "pen marks the one just added so you can see the total grow.",
        "variants": [{"steps": steps}],
    }


def row(*texts, kind=None, values=None, active=None):
    items = [
        {"text": t, "state": "active" if n == active else ""}
        | ({"value": values[n]} if values else {})
        for n, t in enumerate(texts)
    ]
    return {"rows": [{"id": "a", "items": items} | ({"kind": kind} if kind else {})]}


@pytest.mark.parametrize(
    ("steps", "message"),
    [
        # The same drawing twice: the step teaches nothing.
        ([{"note": "Start.", "scene": row("1")}, {"note": "Again.", "scene": row("1")}], "same"),
        # A note states a total that is drawn nowhere (the model's arithmetic slipped).
        (
            [
                {"note": "Start with 40.", "scene": row("40")},
                {"note": "40 plus 15 is 65.", "scene": row("40", "15", "55", active=2)},
            ],
            "says 65",
        ),
        # A bar printed as one number but drawn at another height.
        (
            [
                {"note": "Year one.", "scene": row("100", kind="bars", values=[100])},
                {"note": "Year two.", "scene": row("100", "110", kind="bars", values=[100, 150])},
            ],
            "bar value is 150",
        ),
        # One variant with one step has nothing to step through or choose.
        ([{"note": "Only this.", "scene": row("1")}], "at least 2 steps"),
    ],
)
def test_the_deterministic_accuracy_checks_name_the_slip(steps, message):
    with pytest.raises(ArtifactError, match=message):
        sketch.check(one_variant(steps), "Count up")


def test_numbers_from_the_request_rounded_bars_and_small_positions_pass():
    steps = [
        {"note": "Put 1000 in at 10%.", "scene": row("$1,000", kind="bars", values=[1000])},
        {
            "note": "After 4 years it is $1,464.10, step 2 of the growth.",
            "scene": row("$1,000", "$1,464.10", kind="bars", values=[1000, 1464], active=1),
        },
    ]
    spec = sketch.check(one_variant(steps), "How does 1000 grow at 10% over 4 years?")
    assert spec["variants"][0]["steps"][1]["note"].startswith("After 4 years")
    options = copy.deepcopy(EXAMPLE)
    options["input"]["options"] = ["23", "23 "]
    with pytest.raises(ArtifactError, match="must all differ"):
        sketch.check(options)


def test_every_sketch_page_has_a_host_step_slider_even_with_one_variant():
    spec = sketch.check(
        one_variant(
            [{"note": "Start at 1.", "scene": row("1")}, {"note": "Add 2.", "scene": row("1", "2")}]
        )
    )
    page = sketch.page(spec)
    assert 'id="scrub" type="range" min="0" max="1"' in page and 'id="variant"' not in page
    validate(page)  # the validator wants an input control: the slider is one
    qa = asyncio.run(generator.render_check(validate(page), Settings(environment="test")))
    assert qa["ok"] and qa["step_count"] == 2


def test_a_declarative_sketch_is_shown_before_its_ai_review(client, configured, monkeypatch):  # noqa: F811
    headers, provider = configured
    client.app.state.settings.explainer_sketch_declarative = True
    provider.responses = iter([json.dumps(EXAMPLE)])
    seen = []

    async def review(*args):
        with Session(client.app.state.engine) as db:
            seen.append(db.scalars(select(PlaygroundJob.status)).all())

    monkeypatch.setattr(generator, "review", review)
    job = generate(
        client,
        headers,
        dict(prompt="Explain binary search", request_id=str(uuid.uuid4()), mode="sketch"),
    )
    # Only one model call wrote it, and the job was already ready when the review ran.
    assert job["status"] == "ready" and seen == [["ready"]]
    assert job["artifact"]["prompt_version"] == "visual-sketch-spec-v1"
    assert job["artifact"]["qa"]["ai_review"] == "passed"  # the verdict replaced "pending"


def test_the_api_runs_queued_visuals_itself_only_in_development():
    assert Settings(environment="development").explainer_runner is True
    assert Settings(environment="test").explainer_runner is False
    assert Settings(environment="test", explainer_runner=True).explainer_runner is True


def test_cosmetic_slips_are_normalised_instead_of_costing_a_repair():
    spec = copy.deepcopy(EXAMPLE)
    scene = spec["variants"][0]["steps"][1]["scene"]
    scene["rows"][0]["items"][0]["state"] = "glowing"
    scene["pointers"][0]["tone"] = "neon"
    scene["links"] = [{"from": "a.0", "to": "a.1", "label": "next one"}]
    fixed = sketch.check(sketch.normalize(spec))["variants"][0]["steps"][1]["scene"]
    assert fixed["rows"][0]["items"][0]["state"] == ""
    assert "tone" not in fixed["pointers"][0] and fixed["links"] == [{"from": "a.0", "to": "a.1"}]


def test_the_sketch_review_reads_the_spec_not_the_host_page():
    provider = Provider(['{"issues": []}'])
    verdict = asyncio.run(
        generator.audit(provider, "<html>host</html>", "Explain binary search", [], EXAMPLE)
    )
    system, turns = provider.calls[0]
    assert verdict == {"ai_review": "passed"} and system == generator.REVIEW_SKETCH
    assert '"sketch"' in turns[0].content and "<html>host" not in turns[0].content


def test_words_after_a_finished_sketch_are_ignored_not_a_repair():
    raw = generator.SKETCH_EXAMPLE + " databases}"
    assert sketch.parse(raw)["title"] == EXAMPLE["title"]
    with pytest.raises(ArtifactError, match="did not parse"):
        sketch.parse(generator.SKETCH_EXAMPLE[:-40])  # a sketch cut off mid-way still fails
