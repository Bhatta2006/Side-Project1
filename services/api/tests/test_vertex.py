"""Vertex layer: the text provider, image and speech capabilities, errors and metering.

No test reaches the network: a fake client stands in for the google-genai one.
"""

import asyncio
import io
import wave
from types import SimpleNamespace as NS

import pytest
from google.genai import errors, types
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.assistant import vertex
from socrat.assistant.budget import model_name
from socrat.assistant.gateway import ProviderError, ToolSpec, Turn, make_provider
from socrat.config import Settings
from socrat.models import AIUsage

LOOKUP = ToolSpec(
    "lookup",
    "Look something up.",
    {"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]},
)


def settings(**extra) -> Settings:
    base = dict(
        _env_file=None,
        environment="test",
        ai_provider="vertex",
        vertex_model="gemini-test",
        socrat_vertex_api_key="k",
    )
    return Settings(**(base | extra))


def chunk(*parts, usage=(0, 0, 0)):
    prompt, out, thoughts = usage
    return NS(
        candidates=[NS(content=types.Content(role="model", parts=list(parts)))],
        usage_metadata=NS(
            prompt_token_count=prompt, candidates_token_count=out, thoughts_token_count=thoughts
        ),
    )


class FakeModels:
    def __init__(self, rounds=(), reply=None, error=None):
        self.rounds, self.reply, self.error, self.calls = list(rounds), reply, error, []

    async def generate_content_stream(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        chunks = self.rounds.pop(0)

        async def stream():
            for c in chunks:
                yield c

        return stream()

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.reply


def fake(**kwargs):
    models = FakeModels(**kwargs)
    return NS(aio=NS(models=models)), models


def collect(stream, usage=False):
    async def run():
        return [e async for e in stream if usage or e.kind != "usage"]

    return asyncio.run(run())


def test_text_streams_and_reports_thinking_tokens_as_output():
    client, models = fake(
        rounds=[
            [
                chunk(types.Part(text="Hel")),
                chunk(types.Part(text="hidden", thought=True)),
                chunk(types.Part(text="lo"), usage=(10, 3, 40)),
            ]
        ]
    )
    provider = vertex.VertexProvider(settings(vertex_thinking_level="low"), client)
    events = collect(provider.converse("be kind", [Turn("user", "hi")], 500), usage=True)
    assert "".join(e.text for e in events if e.kind == "text") == "Hello"
    assert events[-1].kind == "usage" and events[-1].arguments == dict(
        input_tokens=10, output_tokens=43
    )
    sent = models.calls[0]
    assert sent["model"] == "gemini-test"
    assert sent["config"].system_instruction == "be kind"
    assert sent["config"].max_output_tokens == 500
    assert sent["config"].thinking_config.thinking_level == "LOW"


def test_tool_call_runs_and_its_result_goes_back_to_the_model():
    call = types.Part(function_call=types.FunctionCall(id="c1", name="lookup", args={"q": "x"}))
    client, models = fake(rounds=[[chunk(call)], [chunk(types.Part(text="done"))]])
    seen = []

    async def run_tool(name, arguments):
        seen.append((name, arguments))
        return "RESULT", False

    provider = vertex.VertexProvider(settings(), client)
    events = collect(provider.converse("s", [Turn("user", "q")], 100, [LOOKUP], run_tool))
    assert [e.kind for e in events] == ["tool_call", "tool_result", "text"]
    assert seen == [("lookup", {"q": "x"})]
    second = models.calls[1]["contents"]
    assert second[1].role == "model" and second[1].parts[0].function_call.name == "lookup"
    reply = second[2].parts[0].function_response
    assert reply.id == "c1" and reply.response == {"output": "RESULT"}


def test_tools_are_withdrawn_after_the_round_limit_and_bad_arguments_reach_the_model():
    call = types.Part(function_call=types.FunctionCall(name="lookup", args={"nope": 1}))
    client, models = fake(rounds=[[chunk(call)], [chunk(types.Part(text="ok"))]])

    async def run_tool(name, arguments):  # never reached: the arguments do not match the schema
        raise AssertionError

    provider = vertex.VertexProvider(settings(), client)
    collect(provider.converse("s", [Turn("user", "q")], 100, [LOOKUP], run_tool, max_rounds=1))
    assert models.calls[0]["config"].tool_config is None
    assert models.calls[1]["config"].tool_config.function_calling_config.mode == "NONE"
    assert "error" in models.calls[1]["contents"][2].parts[0].function_response.response


def test_json_mode_is_requested_only_when_asked():
    client, models = fake(rounds=[[chunk(types.Part(text="{}"))]] * 2)
    provider = vertex.VertexProvider(settings(), client)
    collect(provider.converse("s", [Turn("user", "q")], 10, response_format={"type": "json"}))
    collect(provider.converse("s", [Turn("user", "q")], 10))
    assert models.calls[0]["config"].response_mime_type == "application/json"
    assert models.calls[1]["config"].response_mime_type is None


@pytest.mark.parametrize(
    "error, code",
    [
        (errors.ClientError(429, {"error": {"message": "secret body"}}), "provider_rate_limited"),
        (errors.ServerError(503, {"error": {"message": "secret body"}}), "provider_http_503"),
        (OSError("down"), "provider_unreachable"),
    ],
)
def test_failures_become_short_codes_without_provider_text(error, code):
    client, _ = fake(error=error)
    provider = vertex.VertexProvider(settings(), client)
    with pytest.raises(ProviderError) as raised:
        collect(provider.converse("s", [Turn("user", "q")], 10))
    assert str(raised.value) == code


def test_factory_budget_name_and_configuration_checks():
    provider = make_provider(settings())
    assert isinstance(provider, vertex.VertexProvider) and provider.name == "vertex"
    assert model_name(settings(), provider) == "gemini-test"
    with pytest.raises(ValueError, match="SOCRAT_VERTEX_MODEL"):
        settings(vertex_model="")
    # the owner's own .env name is accepted as the key
    assert (
        Settings(
            _env_file=None, environment="test", vertex_ai_main_gemini_api="from-env"
        ).vertex_api_key.get_secret_value()
        == "from-env"
    )
    assert Settings(_env_file=None, environment="test").ai_provider == "offline"


def reply(data, mime, usage=None):
    return NS(parts=[NS(inline_data=NS(data=data, mime_type=mime))], usage_metadata=usage)


def test_image_returns_bytes_and_sends_prompt_ratio_and_references():
    client, models = fake(reply=reply(b"PNG", "image/png"))
    media = asyncio.run(
        vertex.generate_image(
            settings(),
            "a banana",
            aspect_ratio="16:9",
            reference_images=((b"ref", "image/png"),),
            client=client,
        )
    )
    assert (media.data, media.mime, media.model) == (
        b"PNG",
        "image/png",
        "gemini-3.1-flash-lite-image",
    )
    sent = models.calls[0]
    assert sent["config"].response_modalities == ["IMAGE"]
    assert sent["config"].image_config.aspect_ratio == "16:9"
    assert [p.text for p in sent["contents"][0].parts] == [None, "a banana"]


def test_speech_wraps_raw_pcm_in_a_wav_and_passes_wav_through():
    pcm = b"\x00\x01" * 100
    client, models = fake(reply=reply(pcm, "audio/l16; rate=16000; channels=1"))
    media = asyncio.run(vertex.speak(settings(), "hello", voice="Puck", client=client))
    with wave.open(io.BytesIO(media.data)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getnframes()) == (16000, 1, 100)
    assert media.mime == "audio/wav"
    voice = models.calls[0]["config"].speech_config.voice_config.prebuilt_voice_config
    assert voice.voice_name == "Puck"
    client, _ = fake(reply=reply(b"RIFFxx", "audio/wav"))
    assert asyncio.run(vertex.speak(settings(), "hi", client=client)).data == b"RIFFxx"


def test_media_is_offline_without_a_key_or_with_the_kill_switch_and_empty_replies_fail():
    client, models = fake(reply=reply(b"x", "image/png"))
    for off in (settings(socrat_vertex_api_key=""), settings(ai_enabled=False)):
        with pytest.raises(ProviderError, match="provider_offline"):
            asyncio.run(vertex.generate_image(off, "p", client=client))
    assert models.calls == []
    client, _ = fake(reply=NS(parts=[NS(inline_data=None)], usage_metadata=None))
    with pytest.raises(ProviderError, match="provider_empty_reply"):
        asyncio.run(vertex.generate_image(settings(), "p", client=client))


def test_media_calls_are_budget_checked_and_recorded_at_a_flat_price(tmp_path):
    from alembic import command
    from alembic.config import Config

    from socrat.database import make_engine

    url = f"sqlite:///{tmp_path / 'v.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = make_engine(url)
    try:
        client, _ = fake(reply=reply(b"PNG", "image/png"))
        paid = settings(vertex_image_price_usd=0.04)
        asyncio.run(vertex.generate_image(paid, "p", engine=engine, feature="cover", client=client))
        with Session(engine) as db:
            row = db.scalars(select(AIUsage)).one()
        assert (row.feature, row.provider, row.model) == (
            "cover",
            "vertex",
            "gemini-3.1-flash-lite-image",
        )
        assert row.cost_usd == pytest.approx(0.04)
        capped = settings(ai_daily_budget_usd=0.03, vertex_image_price_usd=0.04)
        with pytest.raises(ProviderError, match="ai_budget_reached"):
            asyncio.run(vertex.generate_image(capped, "p", engine=engine, client=client))
    finally:
        engine.dispose()
