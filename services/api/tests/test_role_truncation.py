"""A reply cut off at its token limit is retried once with more room, and never loops."""

# ruff: noqa: F811
import asyncio

from test_learner_api import client  # noqa: F401

from socrat.assistant.gateway import Event, usage_event
from socrat.coursegen import roles


def make_provider(replies):
    """Each call gets the next (text, output_tokens). Records the limit it was given."""
    calls: list[int] = []

    def make(settings):
        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                calls.append(max_tokens)
                text, produced = replies[min(len(calls), len(replies)) - 1]
                if text:
                    yield Event("text", text=text)
                yield usage_event(100, produced)

        return Provider()

    return make, calls


def ask(client, make, limit=1000):
    state = client.app.state
    return asyncio.run(
        roles.ask(state.engine, state.settings, "reviewer", "sys", "prompt", limit, make)
    )


def test_a_reply_that_ran_out_of_budget_is_asked_again_with_more_room(client):
    make, calls = make_provider([("", 1000), ('{"verdict": "pass"}', 400)])
    reply = ask(client, make)
    assert reply.data == {"verdict": "pass"} and reply.problem == ""
    assert calls == [1000, 2000]


def test_the_retry_happens_once_and_the_problem_says_what_happened(client):
    make, calls = make_provider([("", 1000), ("", 2000), ("", 4000)])
    reply = ask(client, make)
    assert reply.data is None
    assert calls == [1000, 2000]
    assert "cut off at the 2000 token limit" in reply.problem


def test_bad_json_that_was_not_cut_off_is_not_retried(client):
    make, calls = make_provider([("not json at all", 50)])
    reply = ask(client, make)
    assert reply.data is None and calls == [1000]
    assert "not valid JSON" in reply.problem


def test_the_doubled_budget_has_a_ceiling(client):
    make, calls = make_provider([("", 12000), ('{"ok": true}', 10)])
    ask(client, make, limit=12000)
    assert calls == [12000, roles.TRUNCATION_CEILING]
