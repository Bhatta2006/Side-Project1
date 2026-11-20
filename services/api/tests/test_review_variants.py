"""Backlog 4.2: after a lesson is released, parallel items (same skill, new context) are written
once and reviews prefer them, so a review is not a repeat of the check."""
# ruff: noqa: F811

import json

from sqlalchemy.orm import Session
from test_coursegen_package import (
    ATOMS,
    PASS,
    QUIZ,
    Scripted,
    generate,
    lesson,
    published,  # noqa: F401
    run,
    web,  # noqa: F401
)
from test_learner_api import client  # noqa: F401

from socrat.assistant.gateway import Event, usage_event
from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.coursegen import variants
from socrat.learn import quizzes
from socrat.models import Enrollment, GenerationJob

FIRST = QUIZ["quiz"][0]


def variant(vid, of=FIRST["id"], prompt="A new scenario: which rule did this model learn?"):
    return {
        "id": vid,
        "variant_of": of,
        "prompt": prompt,
        "options": ["The pattern in its examples", "A rule typed by hand"],
        "answer": 0,
        "explanation": "It learned the pattern from the examples it saw.",
        "difficulty": 5,
    }


def replying(body):
    class Provider:
        name = "anthropic"

        async def converse(self, system, turns, *args, **kwargs):
            assert system == variants.VARIANTS
            yield Event("text", text=json.dumps(body))
            yield usage_event(100, 200)

    return lambda settings: Provider()


def test_released_lessons_get_review_variants_and_reviews_prefer_them(client, published, web):
    client.app.state.settings.gen_review_variants = True
    generate(client, published, "what-is-ml")
    script = Scripted(
        author=[lesson()], quiz=[QUIZ], atoms=[ATOMS], facts=[{"claims": []}], reviewer=[PASS]
    )
    assert run(client, script.make, web())
    with Session(client.app.state.engine) as db:
        queued = db.query(GenerationJob).filter_by(kind="variants", state="queued").one()
        assert queued.target == "what-is-ml"
    body = {
        "items": [
            variant("bakery"),
            variant("copy", prompt=FIRST["prompt"]),  # the original reworded: dropped
            variant("orphan", of="no-such-item"),  # names no original: dropped
        ]
    }
    assert run(client, replying(body))
    concept = generated.merged(default_catalog()).concept("ai-basics:what-is-ml")
    assert [v.id for v in concept.review_items] == ["v-bakery"]
    assert concept.review_items[0].difficulty == FIRST["difficulty"]  # kept from the original
    assert concept.quiz_item("v-bakery").prompt.startswith("A new scenario")
    picked = quizzes.choose_items(
        generated.merged(default_catalog()),
        Enrollment(id="e1", language="python"),
        "review:ai-basics:what-is-ml",
        1,
    )
    assert picked[0] == ["ai-basics:what-is-ml", "v-bakery"]
    # Once seen, the variant goes behind items the learner has not just answered.
    again = quizzes.choose_items(
        generated.merged(default_catalog()),
        Enrollment(id="e1", language="python"),
        "review:ai-basics:what-is-ml",
        1,
        {"v-bakery"},
    )
    assert again[0][1] != "v-bakery"
