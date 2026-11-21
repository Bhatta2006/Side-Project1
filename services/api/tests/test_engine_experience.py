"""Experience Designer: registered visuals only, validated, never blocking a lesson."""

# ruff: noqa: F811
import json

import pytest
from test_coursegen_package import (  # noqa: F401
    ATOMS,
    FACTS_OK,
    PASS,
    QUIZ,
    ROLES,
    generate,
    lesson,
    published,
    run,
    web,
)
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.assistant.gateway import Event, ProviderError, usage_event
from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.catalog.schema import Concept
from socrat.engine import design

GOOD_MAP = dict(
    renderer="concept-map",
    params=dict(
        nodes=["Examples", "Rule", "Prediction"],
        edges=[["Examples", "Rule"], ["Rule", "Prediction"]],
    ),
    purpose="See how examples lead to a rule and then to predictions",
    fallback_text="Examples lead to a rule. The rule makes predictions.",
    alt_text="Three boxes in a row: examples, rule, prediction.",
)


class Designer:
    """The package script plus the Experience Designer's reply (or its failure)."""

    def __init__(self, visuals=None, fail=False, **replies):
        self.replies = {role: [json.dumps(r) for r in rs] for role, rs in replies.items()}
        self.visuals, self.fail, self.prompts = visuals, fail, []

    def make(self, settings):
        script = self

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                if system == design.SYSTEM:
                    script.prompts.append(turns[0].content)
                    if script.fail:
                        raise ProviderError("provider_offline")
                    yield Event("text", text=json.dumps({"visuals": script.visuals}))
                else:
                    yield Event("text", text=script.replies[ROLES[system]].pop(0))
                yield usage_event(1000, 3000)

        return Provider()


def release(client, admin, web, designer):
    client.app.state.settings.gen_visuals = True
    generate(client, admin, "what-is-ml")
    assert run(client, designer.make, web())
    return generated.merged(default_catalog()).concept("ai-basics:what-is-ml")


def script(**kw):
    return Designer(
        author=[lesson()], quiz=[QUIZ], atoms=[ATOMS], facts=[FACTS_OK], reviewer=[PASS], **kw
    )


def test_the_designer_sees_only_allowed_renderers_and_valid_visuals_are_kept(
    client, published, web
):
    bad = [
        dict(GOOD_MAP, renderer="playground-visual"),  # sandboxed: not offered
        dict(GOOD_MAP, renderer="evil-script"),  # not registered
        dict(GOOD_MAP, params=dict(nodes=["only one"], edges=[])),  # fails the param schema
        dict(GOOD_MAP, fallback_text="short"),  # no usable fallback
    ]
    designer = script(visuals=[*bad, GOOD_MAP])
    live = release(client, published, web, designer)
    assert live.status == "live" and [v.renderer for v in live.visuals] == ["concept-map"]
    offered = designer.prompts[0]
    assert "concept-map" in offered and "playground-visual" not in offered
    assert "code-studio" not in offered

    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner, course="ai-basics")
    view = client.get("/api/v1/concepts/ai-basics:what-is-ml").json()
    assert view["visuals"][0]["renderer"] == "concept-map"
    assert view["visuals"][0]["fallback_text"] and view["visuals"][0]["alt_text"]


def test_no_visual_is_better_than_a_decorative_one(client, published, web):
    live = release(client, published, web, script(visuals=[]))
    assert live.status == "live" and live.visuals == []


def test_a_designer_failure_never_blocks_the_lesson(client, published, web):
    live = release(client, published, web, script(fail=True))
    assert live.status == "live" and live.visuals == []
    detail = client.get("/api/v1/admin/courses/ai-basics/concepts/what-is-ml", headers=published)
    log = detail.json()["jobs"][0]["log"]
    assert any(e.get("role") == "experience" and e.get("event") == "unavailable" for e in log)


def test_off_by_default(client, published, web):
    client.app.state.settings.gen_visuals = False
    generate(client, published, "what-is-ml")
    designer = script(visuals=[GOOD_MAP])
    assert run(client, designer.make, web())
    assert designer.prompts == []  # the designer was never asked


def test_a_concept_cannot_carry_an_unregistered_or_malformed_visual():
    base = dict(
        id="x",
        title="X thing",
        summary="What x is and when it matters here.",
        module="m",
        difficulty=1,
        estimated_minutes=10,
        status="planned",
    )
    assert (
        Concept.model_validate(base | dict(visuals=[GOOD_MAP])).visuals[0].renderer == "concept-map"
    )
    for broken in (dict(GOOD_MAP, renderer="nope"), dict(GOOD_MAP, params={})):
        with pytest.raises(ValueError):
            Concept.model_validate(base | dict(visuals=[broken]))


FILL = dict(
    renderer="fill-blank",
    section="Part 1",
    params=dict(text="A model learns its [[rule|rules]] from [[examples]]."),
    purpose="Recall where a model's rule comes from",
    fallback_text="A model learns its rule from examples.",
    alt_text="A sentence with two gaps to fill.",
)
ORDER = dict(
    renderer="order-steps",
    section="part 2",  # matched to the heading whatever its case and punctuation
    params=dict(prompt="Put the steps in order.", items=["Collect data", "Train", "Test"]),
    purpose="Order the steps of building a model",
    fallback_text="Collect data, then train, then test.",
    alt_text="Three steps to put in order.",
)


def test_interactions_are_placed_in_the_lesson_sections(client, published, web):
    same_section = dict(FILL, section="Part 1", params=dict(text="Data is [[examples]]."))
    nowhere = dict(GOOD_MAP, section="A heading the lesson does not have")
    broken = dict(ORDER, section="Part 3", params=dict(prompt="Order.", items=["a", "a", "b"]))
    designer = script(visuals=[FILL, same_section, ORDER, nowhere, broken])
    live = release(client, published, web, designer)
    assert [(v.renderer, v.section) for v in live.visuals] == [
        ("fill-blank", "Part 1"),
        ("order-steps", "Part 2"),
        ("concept-map", ""),  # unknown section: shown after the lesson, as before
    ]
    offered = designer.prompts[0]
    assert "fill-blank" in offered and "- Part 0" in offered and "<learner>" in offered


@pytest.mark.parametrize(
    "renderer, params",
    [
        (
            "predict-reveal",
            dict(prompt="What happens next?", options=["a", "b"], answer=2, explanation="Because."),
        ),
        (
            "predict-reveal",
            dict(prompt="What happens next?", options=["a", "A"], answer=0, explanation="Because."),
        ),
        (
            "sort-buckets",
            dict(
                prompt="Sort these.",
                buckets=["x", "y"],
                items=[
                    dict(text="1", bucket="x"),
                    dict(text="2", bucket="x"),
                    dict(text="3", bucket="z"),
                ],
            ),
        ),
        (
            "sort-buckets",
            dict(
                prompt="Sort these.",
                buckets=["x", "y"],
                items=[dict(text=str(i), bucket="x") for i in range(3)],
            ),
        ),
        ("fill-blank", dict(text="No blanks in this sentence.")),
        ("fill-blank", dict(text="An empty [[ ]] blank.")),
        (
            "match-pairs",
            dict(
                prompt="Match them.",
                pairs=[
                    dict(left="a", right="1"),
                    dict(left="a", right="2"),
                    dict(left="b", right="3"),
                ],
            ),
        ),
        ("step-through", dict(steps=[dict(body="only one")])),
    ],
)
def test_an_inconsistent_answer_key_is_rejected(renderer, params):
    spec = dict(FILL, renderer=renderer, params=params)
    from socrat.engine import renderers

    assert renderers.validate_spec(spec)


def test_interactions_are_offered_in_every_subject_and_never_count_as_mastery():
    from socrat.engine import domains, renderers

    manifests = renderers.all_manifests()
    assert all(manifests[r].evidence == "exposure" for r in renderers.INTERACTIONS)
    for adapter in domains.ADAPTERS:
        course = default_catalog().course("basics")
        offered = {m.id for m in design.allowed(course, adapter)}
        assert set(renderers.INTERACTIONS) <= offered
