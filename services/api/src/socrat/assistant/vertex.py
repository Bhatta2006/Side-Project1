"""Google Gemini on Vertex AI: one place for everything Socrat asks of it.

Text goes through ``VertexProvider``, which speaks the same ``Provider`` protocol as the
Anthropic and OpenAI providers, so every existing call site, role override and budget check
gets Gemini by configuration alone (``SOCRAT_AI_PROVIDER=vertex``). Images and speech are not
text, so they are plain functions, ``generate_image`` and ``speak``, that any feature can
call. All three share one client, one error vocabulary (``ProviderError`` codes) and the same
budget table. Nothing here runs unless a Vertex key is configured.
"""

import io
import re
import wave
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from socrat.assistant import budget
from socrat.assistant.gateway import (
    Event,
    ProviderError,
    ToolRunner,
    ToolSpec,
    Turn,
    estimated_tokens,
    execute,
    usage_event,
)
from socrat.config import Settings
from socrat.models import now

# Images and speech take far longer than a tutor reply, so the tutor's short timeout is not used.
MEDIA_TIMEOUT_SECONDS = 90


@dataclass(frozen=True)
class Media:
    data: bytes
    mime: str
    model: str


def make_client(settings: Settings, timeout_seconds: float | None = None) -> Any:
    from google import genai
    from google.genai import types

    seconds = timeout_seconds or settings.ai_timeout_seconds
    return genai.Client(
        vertexai=True,
        api_key=settings.vertex_api_key.get_secret_value() or None,
        project=settings.vertex_project or None,
        location=settings.vertex_location or None,
        http_options=types.HttpOptions(timeout=int(seconds * 1000)),
    )


def _error(exc: BaseException) -> ProviderError:
    """Provider failures as short codes; the provider's own message is never echoed."""
    from google.genai import errors

    if isinstance(exc, errors.APIError):
        return ProviderError(
            "provider_rate_limited" if exc.code == 429 else f"provider_http_{exc.code}"
        )
    return ProviderError("provider_unreachable")


_FAILURES = (httpx.TransportError, OSError)


def _failures() -> tuple[type[BaseException], ...]:
    from google.genai import errors

    return (errors.APIError, *_FAILURES)


class VertexProvider:
    name = "vertex"

    def __init__(self, settings: Settings, client: Any = None):
        self.settings = settings
        self.client = client or make_client(settings)

    async def converse(
        self,
        system: str,
        turns: list[Turn],
        max_tokens: int,
        tools: list[ToolSpec] | None = None,
        run_tool: ToolRunner | None = None,
        max_rounds: int = 4,
        *,
        response_format: dict | None = None,
    ) -> AsyncIterator[Event]:
        from google.genai import types

        specs = {t.name: t for t in tools or []}
        declared = (
            [
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=t.name,
                            description=t.description,
                            parameters_json_schema=t.parameters,
                        )
                        for t in specs.values()
                    ]
                )
            ]
            if specs
            else None
        )
        contents: list[Any] = [
            types.Content(
                role="model" if t.role == "assistant" else "user",
                parts=[types.Part(text=t.content)],
            )
            for t in turns
        ]
        rounds = 0
        try:
            while True:
                config = types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=max_tokens,
                    tools=declared,  # type: ignore[arg-type]  # SDK union is invariant
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    # Past the round limit the model may no longer call tools, only answer.
                    tool_config=types.ToolConfig(
                        function_calling_config=types.FunctionCallingConfig(
                            mode=types.FunctionCallingConfigMode.NONE
                        )
                    )
                    if declared and rounds >= max_rounds
                    else None,
                    thinking_config=types.ThinkingConfig(
                        thinking_level=types.ThinkingLevel(
                            self.settings.vertex_thinking_level.upper()
                        )
                    )
                    if self.settings.vertex_thinking_level
                    else None,
                    response_mime_type="application/json" if response_format else None,
                )
                stream = await self.client.aio.models.generate_content_stream(
                    model=self.settings.vertex_model, contents=contents, config=config
                )
                kept: list[
                    Any
                ] = []  # the model's own parts, replayed so thought signatures survive
                calls: list[Any] = []
                text = ""
                usage = None
                async for chunk in stream:
                    usage = chunk.usage_metadata or usage
                    for part in (
                        (chunk.candidates[0].content.parts or [])
                        if chunk.candidates and chunk.candidates[0].content
                        else []
                    ):
                        kept.append(part)
                        if part.function_call:
                            calls.append(part.function_call)
                        elif part.text and not part.thought:
                            text += part.text
                            yield Event("text", part.text)
                if usage is not None:
                    yield usage_event(
                        usage.prompt_token_count or 0,
                        (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0),
                    )
                else:
                    sent = sum(len(t.content) for t in turns) + len(system)
                    yield usage_event(sent // 4 + 1, estimated_tokens(text))
                if not calls or run_tool is None:
                    return
                rounds += 1
                contents.append(types.Content(role="model", parts=kept))
                answers = []
                for call in calls:
                    arguments = dict(call.args) if call.args is not None else None
                    yield Event("tool_call", name=call.name or "", arguments=arguments or {})
                    output, failed = await execute(specs, run_tool, call.name or "", arguments)
                    yield Event("tool_result", name=call.name or "", text=output)
                    answers.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                id=call.id,
                                name=call.name,
                                response={"error" if failed else "output": output},
                            )
                        )
                    )
                contents.append(types.Content(role="user", parts=answers))
        except _failures() as exc:
            raise _error(exc) from exc


def _wav(pcm: bytes, rate: int) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return out.getvalue()


async def _media(
    settings: Settings,
    *,
    model: str,
    contents: Any,
    config: Any,
    flat_price: float,
    feature: str,
    engine: Engine | None,
    user_id: str | None,
    client: Any,
) -> tuple[Any, bytes, str]:
    """One metered non-text call; returns the first inline-data part of the reply."""
    if not settings.ai_enabled or not settings.vertex_api_key.get_secret_value():
        raise ProviderError("provider_offline")
    if engine is not None:
        with Session(engine) as db:
            budget.check(db, settings, user_id, now(), feature)
    try:
        reply = await (
            client or make_client(settings, MEDIA_TIMEOUT_SECONDS)
        ).aio.models.generate_content(model=model, contents=contents, config=config)
    except _failures() as exc:
        raise _error(exc) from exc
    usage = reply.usage_metadata
    if engine is not None:
        with Session(engine) as db, db.begin():
            budget.record(
                db,
                settings,
                user_id=user_id,
                feature=feature,
                provider="vertex",
                model=model,
                input_tokens=(usage.prompt_token_count or 0) if usage else 0,
                output_tokens=(usage.candidates_token_count or 0) if usage else 0,
                stamp=now(),
                cost_usd=flat_price,
            )
    for part in reply.parts or []:
        if part.inline_data and part.inline_data.data:
            return reply, part.inline_data.data, part.inline_data.mime_type or ""
    raise ProviderError("provider_empty_reply")  # blocked by a safety filter, or text only


async def generate_image(
    settings: Settings,
    prompt: str,
    *,
    aspect_ratio: str | None = None,
    reference_images: tuple[tuple[bytes, str], ...] = (),
    engine: Engine | None = None,
    user_id: str | None = None,
    feature: str = "image",
    client: Any = None,
) -> Media:
    """One image from a prompt, optionally edited from reference ``(bytes, mime)`` images.
    Pass ``engine`` (and ``user_id`` when a learner caused it) to have the call budget-checked
    and recorded. Raises ProviderError."""
    from google.genai import types

    model = settings.vertex_image_model
    parts = [types.Part.from_bytes(data=d, mime_type=m) for d, m in reference_images]
    parts.append(types.Part(text=prompt))
    _, data, mime = await _media(
        settings,
        model=model,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=aspect_ratio) if aspect_ratio else None,
        ),
        flat_price=settings.vertex_image_price_usd,
        feature=feature,
        engine=engine,
        user_id=user_id,
        client=client,
    )
    return Media(data, mime or "image/png", model)


async def speak(
    settings: Settings,
    text: str,
    *,
    voice: str | None = None,
    engine: Engine | None = None,
    user_id: str | None = None,
    feature: str = "speech",
    client: Any = None,
) -> Media:
    """Spoken audio of ``text`` as a WAV file (raw PCM replies are wrapped). Raises ProviderError."""
    from google.genai import types

    model = settings.vertex_tts_model
    _, data, mime = await _media(
        settings,
        model=model,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice or settings.vertex_tts_voice
                    )
                )
            ),
        ),
        flat_price=settings.vertex_tts_price_usd,
        feature=feature,
        engine=engine,
        user_id=user_id,
        client=client,
    )
    if "l16" in mime.lower() or "pcm" in mime.lower():  # headerless 16-bit samples
        rate = re.search(r"rate=(\d+)", mime)
        return Media(_wav(data, int(rate.group(1)) if rate else 24000), "audio/wav", model)
    return Media(data, mime or "audio/wav", model)
