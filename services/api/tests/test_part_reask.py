"""An unreadable quiz or atoms reply is re-asked once inside the round, not a lost round.

The first live run lost lessons because a quiz reply that was not valid JSON cost a whole
round (3 by default) and the next round could also rewrite the lesson.
"""

# ruff: noqa: F811
import json

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
from test_learner_api import client  # noqa: F401

from socrat.assistant.gateway import Event, usage_event
from socrat.catalog import generated
from socrat.catalog.registry import default_catalog


class Raw:
    """Like the package test's script, but replies are sent as given (so one can be broken)."""

    def __init__(self, **replies):
        self.replies = {
            role: [r if isinstance(r, str) else json.dumps(r) for r in rs]
            for role, rs in replies.items()
        }
        self.prompts: dict[str, list[str]] = {role: [] for role in ROLES.values()}

    def make(self, settings):
        script = self

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                role = ROLES[system]
                script.prompts[role].append(turns[0].content)
                yield Event("text", text=script.replies[role].pop(0))
                yield usage_event(1000, 1000)

        return Provider()


def test_a_broken_quiz_reply_is_reasked_in_the_same_round(client, published, web):
    generate(client, published, "what-is-ml")
    script = Raw(
        author=[lesson()],
        quiz=['{"quiz": [ oops', QUIZ],
        atoms=["not json at all", ATOMS],
        facts=[FACTS_OK],
        reviewer=[PASS],
    )
    assert run(client, script.make, web())
    # One lesson draft, no second round: each broken part was asked again at once.
    assert len(script.prompts["author"]) == 1
    assert len(script.prompts["quiz"]) == 2 and len(script.prompts["atoms"]) == 2
    assert "could not be read" in script.prompts["quiz"][1]
    assert "could not be read" in script.prompts["atoms"][1]
    detail = client.get("/api/v1/admin/courses/ai-basics/concepts/what-is-ml", headers=published)
    log = detail.json()["jobs"][0]["log"]
    assert any(e.get("event") == "reasked" and e.get("round") == 1 for e in log)
    assert detail.json()["jobs"][0]["state"] == "done" and log[-1]["event"] == "released"
    assert generated.merged(default_catalog()).concept("ai-basics:what-is-ml").status == "live"


def test_a_part_that_stays_unreadable_still_costs_the_round(client, published, web):
    generate(client, published, "what-is-ml")
    script = Raw(
        author=[lesson()],
        quiz=["nope", "still nope", QUIZ],
        atoms=[ATOMS],
        facts=[FACTS_OK],
        reviewer=[PASS],
    )
    assert run(client, script.make, web())
    # Round 1: asked, re-asked once, both unreadable. Round 2 asks the quiz only.
    assert len(script.prompts["quiz"]) == 3 and len(script.prompts["author"]) == 1
    assert len(script.prompts["atoms"]) == 1  # the readable atoms were kept
    log = client.get(
        "/api/v1/admin/courses/ai-basics/concepts/what-is-ml", headers=published
    ).json()["jobs"][0]["log"]
    assert any(e.get("event") == "unparsable" and e.get("round") == 1 for e in log)
    assert log[-1]["event"] == "released"
