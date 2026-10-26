"""Soc's teaching engine and chat history."""

import asyncio
import json

from test_learner_api import client, login, onboard  # noqa: F401

from socrat.assistant import engine
from socrat.assistant.gateway import Event
from socrat.assistant.service import TurnPlan, stream_reply
from socrat.config import Settings


def test_classify_reads_the_learners_intent():
    assert engine.classify("hi") == "greeting"
    assert engine.classify("I give up, this is too hard") == "frustrated"
    assert engine.classify("I still don't get it") == "confused"
    assert engine.classify("just give me the code") == "answer_seeking"
    assert engine.classify("ok got it, thanks") == "understood"
    assert engine.classify("What is a hash map?") == "question"
    assert engine.classify("What should I focus on this week") == "planning"
    assert (
        engine.classify("I think we loop over the array and keep a running total of the sum")
        == "attempt"
    )


def test_confusion_switches_style_and_understanding_is_checked_not_trusted():
    state = engine.State()
    move, state = engine.decide(state, "question", "general")
    assert move.name == "explain"
    move, state = engine.decide(state, "confused", "general")
    assert move.name == "switch_style" and "analogy" in move.instruction
    move, state = engine.decide(state, "confused", "general")
    assert move.name == "switch_style" and "worked example" in move.instruction
    move, state = engine.decide(state, "understood", "general")
    assert move.name == "check" and state.pending_check
    move, state = engine.decide(state, "attempt", "general")
    assert move.name == "evaluate" and not state.pending_check
    assert engine.State.from_dict(state.to_dict()) == state


def test_problem_scope_holds_the_line_and_hints_stay_guided():
    move, _ = engine.decide(engine.State(), "answer_seeking", "problem:two-sum")
    assert move.name == "hold"
    move, _ = engine.decide(engine.State(), "question", "problem:two-sum", "hint")
    assert move.name == "guide"
    move, _ = engine.decide(engine.State(), "answer_seeking", "general")
    assert move.name == "explain"


def test_reply_always_keeps_the_moves_promise_to_check_understanding():
    move, _ = engine.decide(engine.State(), "question", "general")

    class Provider:
        name = "synthetic"

        async def converse(self, *args):
            yield Event("text", "<level>5</level>A hash map stores key-value pairs.")

    async def run():
        plan = TurnPlan("thread", "general", 5, None, [], "Fallback", move=move)
        return [item async for item in stream_reply(Provider(), plan, Settings(environment="test"))]

    events = asyncio.run(run())
    assert ("move", {"name": "explain", "label": move.label}) in events
    done = events[-1][1]
    assert done["text"].startswith("A hash map") and done["text"].rstrip().endswith("?")
    assert "".join(d["text"] for e, d in events if e == "delta") == done["text"]
    assert engine.closing("Does that make sense?", move) == ""


def _send(client, headers, message):  # noqa: F811
    response = client.post(
        "/api/v1/assistant/messages", json={"scope": "general", "message": message}, headers=headers
    )
    response.raise_for_status()
    return [
        json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")
    ]


def test_new_chat_archives_history_and_an_old_chat_can_be_resumed(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    _send(client, headers, "What is recursion?")
    assert client.post(
        "/api/v1/assistant/chats", json={"scope": "general"}, headers=headers
    ).json()["archived"]
    assert (
        client.get("/api/v1/assistant/thread?scope=general", headers=headers).json()["messages"]
        == []
    )
    _send(client, headers, "What is a stack?")

    chats = client.get("/api/v1/assistant/chats?scope=general", headers=headers).json()["items"]
    assert [c["title"] for c in chats] == ["What is a stack?", "What is recursion?"]
    assert [c["current"] for c in chats] == [True, False]
    old = client.get(f"/api/v1/assistant/chats/{chats[1]['id']}", headers=headers).json()
    assert old["archived"] and old["messages"][0]["content"] == "What is recursion?"

    client.post(
        f"/api/v1/assistant/chats/{chats[1]['id']}/resume", headers=headers
    ).raise_for_status()
    current = client.get("/api/v1/assistant/thread?scope=general", headers=headers).json()
    assert current["messages"][0]["content"] == "What is recursion?"
    assert (
        len(client.get("/api/v1/assistant/chats?scope=general", headers=headers).json()["items"])
        == 2
    )

    context = client.get("/api/v1/assistant/context?scope=general", headers=headers).json()
    assert context["sections"] and context["teaching"]
    assert client.get("/api/v1/assistant/chats/not-a-thread", headers=headers).status_code == 404
