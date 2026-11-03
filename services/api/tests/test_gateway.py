"""Provider tool loops, exercised with fake SDK clients (no network, no keys)."""

import asyncio
import json
from types import SimpleNamespace as NS

import httpx
import pytest

from socrat.assistant import gateway
from socrat.assistant.gateway import (
    AnthropicProvider,
    Event,
    OfflineProvider,
    OpenAIProvider,
    ProviderError,
    ToolSpec,
    Turn,
    _ThinkFilter,
    complete,
    make_provider,
)
from socrat.config import Settings
from socrat.library import codeforces

TOOL = ToolSpec(
    "lookup",
    "Look something up.",
    {"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]},
)


def settings(**extra) -> Settings:
    return Settings(_env_file=None, environment="test", **extra)


def collect(stream, usage: bool = False) -> list[Event]:
    """Events of a stream; token-usage events only when asked for."""

    async def run():
        return [event async for event in stream if usage or event.kind != "usage"]

    return asyncio.run(run())


async def runner(name: str, arguments: dict) -> tuple[str, bool]:
    return json.dumps({"answer": arguments["q"].upper()}), False


# ------------------------------------------------------------------ OpenAI-compatible


def chunk(content=None, tool_calls=None, finish=None):
    delta = NS(content=content, tool_calls=tool_calls)
    return NS(choices=[NS(delta=delta, finish_reason=finish)])


def call(index, name=None, arguments=None, id=None):
    return NS(index=index, id=id, function=NS(name=name, arguments=arguments))


class FakeCompletions:
    def __init__(self, rounds: list[list]):
        self.rounds = rounds
        self.requests: list[dict] = []

    async def create(self, **params):
        self.requests.append(params)
        chunks = self.rounds[len(self.requests) - 1]

        async def stream():
            for c in chunks:
                yield c

        return stream()


def openai_provider(rounds: list[list]) -> tuple[OpenAIProvider, FakeCompletions]:
    provider = OpenAIProvider(settings(ai_provider="openai", openai_model="m", openai_api_key="k"))
    fake = FakeCompletions(rounds)
    provider.client = NS(chat=NS(completions=fake))  # type: ignore[assignment]
    return provider, fake


def test_openai_streams_text_without_tools():
    provider, fake = openai_provider([[chunk("Hel"), chunk("lo", finish="stop")]])
    text = asyncio.run(complete(provider, "sys", [Turn("user", "hi")], 100))
    assert text == "Hello"
    assert "tools" not in fake.requests[0]
    assert "extra_body" not in fake.requests[0]
    assert fake.requests[0]["messages"][0] == {"role": "system", "content": "sys"}


def test_chat_template_options_are_sent_only_to_compatible_endpoints():
    official = settings(ai_provider="openai", openai_model="gpt-5.4-mini", openai_api_key="k")
    assert (
        make_provider(
            official, chat_template_kwargs={"enable_thinking": False}
        ).chat_template_kwargs
        == {}
    )


def test_chat_template_options_are_explicit_and_do_not_change_other_provider_instances():
    config = settings(
        ai_provider="openai",
        openai_model="m",
        openai_api_key="k",
        openai_base_url="https://compatible.example/v1/",
    )
    provider = make_provider(config, chat_template_kwargs={"enable_thinking": False})
    fake = FakeCompletions([[chunk('{"issues":[]}', finish="stop")]])
    provider.client = NS(chat=NS(completions=fake))
    assert (
        collect(
            provider.converse(
                "sys", [Turn("user", "review")], 100, response_format={"type": "json_object"}
            )
        )[-1].text
        == '{"issues":[]}'
    )
    assert fake.requests[0]["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert fake.requests[0]["response_format"] == {"type": "json_object"}
    assert make_provider(config).chat_template_kwargs == {}


def test_configured_chat_template_options_apply_to_every_call_and_explicit_ones_win():
    config = settings(
        ai_provider="openai",
        openai_model="m",
        openai_api_key="k",
        openai_base_url="https://compatible.example/v1/",
        openai_chat_template_kwargs={"thinking": False, "x": 1},
    )
    assert make_provider(config).chat_template_kwargs == {"thinking": False, "x": 1}
    assert make_provider(config, chat_template_kwargs={"x": 2}).chat_template_kwargs == {
        "thinking": False,
        "x": 2,
    }


def test_openai_runs_a_tool_then_answers():
    provider, fake = openai_provider(
        [
            [
                chunk(tool_calls=[call(0, "look", '{"q":', id="c1")]),
                chunk(tool_calls=[call(0, "up", ' "x"}')], finish="tool_calls"),
            ],
            [chunk("Done"), chunk(".", finish="stop")],
        ]
    )
    events = collect(provider.converse("sys", [Turn("user", "go")], 100, [TOOL], runner))
    kinds = [e.kind for e in events]
    assert kinds == ["tool_call", "tool_result", "text", "text"]
    assert events[0].name == "lookup" and events[0].arguments == {"q": "x"}
    second = fake.requests[1]["messages"]
    assert second[-2]["tool_calls"][0]["function"]["name"] == "lookup"
    assert second[-1] == {"role": "tool", "tool_call_id": "c1", "content": '{"answer": "X"}'}


def test_openai_reports_bad_arguments_to_the_model():
    provider, fake = openai_provider(
        [
            [chunk(tool_calls=[call(0, "lookup", "{not json", id="c1")], finish="tool_calls")],
            [chunk("Sorry", finish="stop")],
        ]
    )
    events = collect(provider.converse("sys", [Turn("user", "go")], 100, [TOOL], runner))
    result = next(e for e in events if e.kind == "tool_result")
    assert "Invalid arguments" in result.text
    assert fake.requests[1]["messages"][-1]["content"].startswith("Invalid arguments")


def test_openai_stops_offering_tools_after_the_round_limit():
    looping = [chunk(tool_calls=[call(0, "lookup", '{"q":"a"}', id="c")], finish="tool_calls")]
    provider, fake = openai_provider([looping, [chunk("Final", finish="stop")]])
    events = collect(provider.converse("s", [Turn("user", "go")], 100, [TOOL], runner, 1))
    assert fake.requests[0]["tool_choice"] == "auto"
    assert fake.requests[1]["tool_choice"] == "none"
    assert events[-1].text == "Final"


def test_openai_retries_once_when_the_answer_after_tools_is_empty():
    provider, fake = openai_provider(
        [
            [chunk(tool_calls=[call(0, "lookup", '{"q":"a"}', id="c")], finish="tool_calls")],
            [chunk(None, finish="stop")],
            [chunk("Recovered", finish="stop")],
        ]
    )
    events = collect(provider.converse("s", [Turn("user", "go")], 100, [TOOL], runner))
    assert events[-1].text == "Recovered"
    assert fake.requests[2]["tool_choice"] == "none"


def test_think_spans_are_hidden_even_when_split_across_chunks():
    f = _ThinkFilter()
    out = f.feed("Hi <thi") + f.feed("nk>secret</th") + f.feed("ink> there") + f.flush()
    assert out == "Hi  there"
    unfinished = _ThinkFilter()
    assert unfinished.feed("<think>never closed") + unfinished.flush() == ""


# ------------------------------------------------------------------ Anthropic


class FakeStream:
    def __init__(self, texts, final):
        self.texts, self.final = texts, final

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    @property
    def text_stream(self):
        async def gen():
            for t in self.texts:
                yield t

        return gen()

    async def get_final_message(self):
        return self.final


class FakeMessages:
    def __init__(self, rounds):
        self.rounds = rounds
        self.requests: list[dict] = []

    def stream(self, **params):
        self.requests.append(params)
        texts, final = self.rounds[len(self.requests) - 1]
        return FakeStream(texts, final)


def anthropic_provider(rounds) -> tuple[AnthropicProvider, FakeMessages]:
    provider = AnthropicProvider(settings(ai_provider="anthropic", anthropic_api_key="k"))
    fake = FakeMessages(rounds)
    provider.client = NS(beta=NS(messages=fake))  # type: ignore[assignment]
    return provider, fake


def tool_use(id, name, input):
    return NS(type="tool_use", id=id, name=name, input=input)


def test_anthropic_tool_loop_appends_history_and_caches_tools():
    first = NS(stop_reason="tool_use", content=[tool_use("t1", "lookup", {"q": "y"})])
    second = NS(stop_reason="end_turn", content=[NS(type="text", text="Done")])
    provider, fake = anthropic_provider([(["Checking. "], first), (["Done"], second)])
    events = collect(provider.converse("sys", [Turn("user", "go")], 100, [TOOL], runner))
    assert [e.kind for e in events] == ["text", "tool_call", "tool_result", "text"]
    request = fake.requests[0]
    assert request["tools"][-1]["cache_control"] == {"type": "ephemeral"}
    assert request["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert request["fallbacks"] == "default"
    history = fake.requests[1]["messages"]
    assert history[-2] == {"role": "assistant", "content": first.content}
    assert history[-1]["content"][0]["tool_use_id"] == "t1"
    assert history[-1]["content"][0]["is_error"] is False


def test_anthropic_refusal_and_round_limit():
    refused = NS(stop_reason="refusal", content=[])
    provider, _ = anthropic_provider([([], refused)])
    with pytest.raises(ProviderError, match="provider_refusal"):
        collect(provider.converse("s", [Turn("user", "x")], 100))

    looping = NS(stop_reason="tool_use", content=[tool_use("t", "lookup", {"q": "z"})])
    done = NS(stop_reason="end_turn", content=[])
    provider, fake = anthropic_provider([([], looping), (["ok"], done)])
    collect(provider.converse("s", [Turn("user", "x")], 100, [TOOL], runner, max_rounds=1))
    assert "tool_choice" not in fake.requests[0]
    assert fake.requests[1]["tool_choice"] == {"type": "none"}


def test_unknown_tools_and_failing_tools_become_error_results():
    async def boom(name, arguments):
        raise RuntimeError("down")

    specs = {TOOL.name: TOOL}
    assert asyncio.run(gateway.execute(specs, boom, "lookup", {"q": "a"}))[1]
    assert asyncio.run(gateway.execute(specs, runner, "missing", {}))[1]
    assert gateway.parse_arguments("[1, 2]") is None
    assert gateway.parse_arguments("") == {}


def test_offline_and_factory():
    assert isinstance(make_provider(settings()), OfflineProvider)
    assert isinstance(
        make_provider(settings(ai_provider="openai", openai_model="m", openai_api_key="k")),
        OpenAIProvider,
    )
    with pytest.raises(ProviderError):
        collect(OfflineProvider().converse("s", [], 10))


# ------------------------------------------------------------------ Codeforces API client


def mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.parametrize(
    "body, code",
    [
        (
            {"status": "FAILED", "comment": "handles: User with handle x not found"},
            "handle_not_found",
        ),
        ({"status": "FAILED", "comment": "Call limit exceeded"}, "rate_limited"),
        ({"status": "FAILED", "comment": "Internal error"}, "unavailable"),
    ],
)
def test_codeforces_errors_map_to_safe_codes(monkeypatch, body, code):
    monkeypatch.setattr(codeforces, "MIN_GAP_SECONDS", 0)

    async def run():
        async with mock_client(lambda r: httpx.Response(200, json=body)) as client:
            await codeforces._call(client, "user.info", {"handles": "x"})

    with pytest.raises(codeforces.CodeforcesError, match=code):
        asyncio.run(run())


def test_codeforces_fetch_profile_reads_user_and_submissions(monkeypatch):
    monkeypatch.setattr(codeforces, "MIN_GAP_SECONDS", 0)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("user.info"):
            user = {"handle": "Ada", "rating": 1500, "maxRating": 1600, "rank": "specialist"}
            return httpx.Response(200, json={"status": "OK", "result": [user]})
        sub = {"verdict": "OK", "problem": {"contestId": 1, "index": "A", "tags": ["math"]}}
        return httpx.Response(200, json={"status": "OK", "result": [sub]})

    real = httpx.AsyncClient
    monkeypatch.setattr(
        codeforces.httpx,
        "AsyncClient",
        lambda **kw: real(transport=httpx.MockTransport(handler), **kw),
    )
    profile = asyncio.run(codeforces.fetch_profile("ada"))
    assert profile["handle"] == "Ada" and profile["solved"] == ["cf:1A"]
    with pytest.raises(codeforces.CodeforcesError, match="invalid_handle"):
        asyncio.run(codeforces.fetch_profile("x y"))

    def broken(request):
        return httpx.Response(200, text="<html>")

    monkeypatch.setattr(
        codeforces.httpx,
        "AsyncClient",
        lambda **kw: real(transport=httpx.MockTransport(broken), **kw),
    )
    with pytest.raises(codeforces.CodeforcesError, match="unavailable"):
        asyncio.run(codeforces.fetch_profile("ada"))


def test_providers_report_token_usage_per_round():
    provider, fake = openai_provider(
        [
            [
                chunk("Hi", finish="stop"),
                NS(choices=[], usage=NS(prompt_tokens=120, completion_tokens=7)),
            ]
        ]
    )
    events = collect(provider.converse("sys", [Turn("user", "hi")], 100), usage=True)
    assert events[-1].kind == "usage"
    assert events[-1].arguments == {"input_tokens": 120, "output_tokens": 7}
    assert fake.requests[0]["stream_options"] == {"include_usage": True}

    # Endpoints that report nothing are estimated, so budgets still apply.
    provider, _ = openai_provider([[chunk("Hello there", finish="stop")]])
    usage = collect(provider.converse("s" * 400, [Turn("user", "hi")], 100), usage=True)[-1]
    assert usage.kind == "usage" and usage.arguments["input_tokens"] > 100

    final = NS(
        stop_reason="end_turn",
        content=[],
        usage=NS(
            input_tokens=100,
            output_tokens=20,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=1000,
        ),
    )
    provider, _ = anthropic_provider([(["Hi"], final)])
    usage = collect(provider.converse("s", [Turn("user", "x")], 100), usage=True)[-1]
    assert usage.arguments == {"input_tokens": 200, "output_tokens": 20}
