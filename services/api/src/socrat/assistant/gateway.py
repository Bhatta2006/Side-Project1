"""Provider-neutral streaming gateway with tool use: Anthropic, OpenAI-compatible, or offline.

Providers turn (system, messages, tools) into a stream of text deltas and tool calls. The
caller supplies the tool executor; policy, context and validation live outside, so swapping
providers never changes what the tutor may do or see.
"""

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from socrat.config import Settings


class ProviderError(RuntimeError):
    """Provider unavailable, refused or timed out. Message never echoes provider bodies."""


@dataclass(frozen=True)
class Turn:
    role: str  # "user" | "assistant"
    content: str


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict  # JSON Schema for the arguments object


@dataclass(frozen=True)
class Event:
    kind: str  # "text" | "tool_call" | "tool_result" | "usage" (arguments: token counts)
    text: str = ""
    name: str = ""
    arguments: dict = field(default_factory=dict)


# Runs one tool call; returns the result text and whether it is an error.
ToolRunner = Callable[[str, dict], Awaitable[tuple[str, bool]]]


class Provider(Protocol):
    name: str

    def converse(
        self,
        system: str,
        turns: list[Turn],
        max_tokens: int,
        tools: list[ToolSpec] | None = None,
        run_tool: ToolRunner | None = None,
        max_rounds: int = 4,
    ) -> AsyncIterator[Event]: ...


def usage_event(input_tokens: int, output_tokens: int) -> Event:
    """Token counts of one model round, for metering. Consumers that only want text skip it."""
    return Event(
        "usage",
        arguments=dict(
            input_tokens=max(0, int(input_tokens)), output_tokens=max(0, int(output_tokens))
        ),
    )


def estimated_tokens(text: str) -> int:
    """About four characters per token, for endpoints that report no usage."""
    return len(text) // 4 + 1


def parse_arguments(raw: str) -> dict | None:
    try:
        value = json.loads(raw or "{}")
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def valid_arguments(spec: ToolSpec, arguments: dict) -> bool:
    """Shallow schema check: required keys present, no unknown keys, basic types."""
    props = spec.parameters.get("properties", {})
    if any(key not in props for key in arguments):
        return False
    if any(key not in arguments for key in spec.parameters.get("required", [])):
        return False
    kinds: dict[str, type | tuple[type, ...]] = {
        "string": str,
        "integer": int,
        "boolean": bool,
        "array": list,
        "number": (int, float),
    }
    for key, value in arguments.items():
        expected = kinds.get(props[key].get("type", ""))
        if expected and not isinstance(value, expected):
            return False
        if "enum" in props[key] and value not in props[key]["enum"]:
            return False
    return True


async def execute(
    specs: dict[str, ToolSpec], run_tool: ToolRunner, name: str, arguments: dict | None
) -> tuple[str, bool]:
    spec = specs.get(name)
    if spec is None:
        return f"Unknown tool {name!r}.", True
    if arguments is None or not valid_arguments(spec, arguments):
        return "Invalid arguments for this tool; check the schema and try again.", True
    try:
        return await run_tool(name, arguments)
    except Exception:  # A failing tool must not end the reply; the model can recover.
        return "The tool failed. Answer without it or try different arguments.", True


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, settings: Settings):
        import anthropic

        self.settings = settings
        self.client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value() or None,
            timeout=settings.ai_timeout_seconds,
            max_retries=1,
        )

    async def converse(
        self,
        system: str,
        turns: list[Turn],
        max_tokens: int,
        tools: list[ToolSpec] | None = None,
        run_tool: ToolRunner | None = None,
        max_rounds: int = 4,
    ) -> AsyncIterator[Event]:
        import anthropic

        specs = {t.name: t for t in tools or []}
        tool_params: list[dict] = [
            {"name": t.name, "description": t.description, "input_schema": t.parameters}
            for t in tools or []
        ]
        if tool_params:
            # Tools render before the system prompt; one breakpoint caches both.
            tool_params[-1] = {**tool_params[-1], "cache_control": {"type": "ephemeral"}}
        messages: list[dict[str, Any]] = [{"role": t.role, "content": t.content} for t in turns]
        rounds = 0
        try:
            while True:
                params: dict[str, Any] = dict(
                    model=self.settings.ai_model,
                    max_tokens=max_tokens,
                    system=[
                        {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
                    ],
                    messages=messages,
                    output_config={"effort": self.settings.ai_effort},
                )
                if tool_params:
                    params["tools"] = tool_params
                    if rounds >= max_rounds:
                        params["tool_choice"] = {"type": "none"}
                if self.settings.ai_server_fallbacks:
                    params["betas"] = ["server-side-fallback-2026-07-01"]
                    params["fallbacks"] = "default"
                async with self.client.beta.messages.stream(**params) as stream:
                    async for text in stream.text_stream:
                        yield Event("text", text)
                    final = await stream.get_final_message()
                used = getattr(final, "usage", None)
                if used is not None:
                    yield usage_event(
                        # Cache writes cost 1.25x and cache reads 0.1x of fresh input.
                        int(
                            (used.input_tokens or 0)
                            + 1.25 * (getattr(used, "cache_creation_input_tokens", 0) or 0)
                            + 0.1 * (getattr(used, "cache_read_input_tokens", 0) or 0)
                        ),
                        used.output_tokens or 0,
                    )
                if final.stop_reason == "refusal":
                    raise ProviderError("provider_refusal")
                calls = [b for b in final.content if b.type == "tool_use"]
                if final.stop_reason != "tool_use" or not calls or run_tool is None:
                    return
                rounds += 1
                # Append-only history: the assistant turn goes back exactly as received.
                messages.append({"role": "assistant", "content": final.content})
                results = []
                for call in calls:
                    arguments = call.input if isinstance(call.input, dict) else None
                    yield Event("tool_call", name=call.name, arguments=arguments or {})
                    output, failed = await execute(specs, run_tool, call.name, arguments)
                    yield Event("tool_result", name=call.name, text=output)
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": call.id,
                            "content": output,
                            "is_error": failed,
                        }
                    )
                messages.append({"role": "user", "content": results})
        except anthropic.APIConnectionError as exc:
            raise ProviderError("provider_unreachable") from exc
        except anthropic.RateLimitError as exc:
            raise ProviderError("provider_rate_limited") from exc
        except anthropic.APIStatusError as exc:
            raise ProviderError(f"provider_http_{exc.status_code}") from exc


class _ThinkFilter:
    """Hide <think>…</think> spans some open models write into the visible content."""

    def __init__(self):
        self.buffer = ""
        self.inside = False

    def feed(self, text: str) -> str:
        self.buffer += text
        out = ""
        while self.buffer:
            if self.inside:
                end = self.buffer.find("</think>")
                if end < 0:
                    self.buffer = self.buffer[-8:]
                    return out
                self.buffer = self.buffer[end + 8 :]
                self.inside = False
            else:
                start = self.buffer.find("<think>")
                if start < 0:
                    keep = 0
                    for size in range(1, 7):  # a tag may be split across chunks
                        if "<think>".startswith(self.buffer[-size:]):
                            keep = size
                    out += self.buffer[: len(self.buffer) - keep]
                    self.buffer = self.buffer[len(self.buffer) - keep :]
                    return out
                out += self.buffer[:start]
                self.buffer = self.buffer[start + 7 :]
                self.inside = True
        return out

    def flush(self) -> str:
        rest, self.buffer = ("" if self.inside else self.buffer), ""
        return rest


class OpenAIProvider:
    """OpenAI Chat Completions, or any compatible endpoint (Nebius, vLLM, …)."""

    name = "openai"

    def __init__(self, settings: Settings, chat_template_kwargs: dict | None = None):
        import openai

        self.settings = settings
        # A vLLM/Nebius extension: api.openai.com (no base URL) rejects it, so a value left over
        # from a compatible endpoint must not break every request after switching to OpenAI.
        self.chat_template_kwargs = (
            dict(chat_template_kwargs or {}) if settings.openai_base_url else {}
        )
        self.client = openai.AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value() or None,
            base_url=settings.openai_base_url or None,
            timeout=settings.ai_timeout_seconds,
            # The SDK backs off between tries, riding out brief DNS or network blips.
            max_retries=2,
        )

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
        import openai

        specs = {t.name: t for t in tools or []}
        tool_params = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools or []
        ]
        messages: list[Any] = [{"role": "system", "content": system}]
        messages += [
            {"role": "assistant" if t.role == "assistant" else "user", "content": t.content}
            for t in turns
        ]
        rounds = 0
        retried = False
        try:
            while True:
                params: dict[str, Any] = dict(
                    model=self.settings.openai_model,
                    stream=True,
                    stream_options={"include_usage": True},
                    max_completion_tokens=max_tokens,
                    messages=messages,
                )
                if self.chat_template_kwargs:
                    params["extra_body"] = {"chat_template_kwargs": self.chat_template_kwargs}
                if response_format:
                    params["response_format"] = response_format
                if tool_params:
                    params["tools"] = tool_params
                    params["tool_choice"] = "none" if rounds >= max_rounds else "auto"
                response = await self.client.chat.completions.create(**params)
                think = _ThinkFilter()
                text = ""
                calls: dict[int, dict[str, str]] = {}
                finish = None
                usage = None
                async for chunk in response:
                    if getattr(chunk, "usage", None):
                        usage = chunk.usage
                    if not chunk.choices:
                        continue
                    choice = chunk.choices[0]
                    delta = choice.delta
                    if delta.content:
                        visible = think.feed(delta.content)
                        if visible:
                            text += visible
                            yield Event("text", visible)
                    for tc in delta.tool_calls or []:
                        slot = calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                        slot["id"] = tc.id or slot["id"]
                        if tc.function and tc.function.name:
                            slot["name"] += tc.function.name
                        if tc.function and tc.function.arguments:
                            slot["arguments"] += tc.function.arguments
                    finish = choice.finish_reason or finish
                rest = think.flush()
                if rest:
                    text += rest
                    yield Event("text", rest)
                if usage is not None:
                    yield usage_event(usage.prompt_tokens or 0, usage.completion_tokens or 0)
                else:
                    sent = sum(len(str(m.get("content") or "")) for m in messages)
                    yield usage_event(sent // 4 + 1, estimated_tokens(text))
                if not calls and not text.strip() and rounds and not retried:
                    # Some open models end a turn after tool results with nothing visible;
                    # ask once more for the answer itself.
                    retried = True
                    rounds = max_rounds
                    continue
                if not calls or run_tool is None or finish == "length":
                    return
                rounds += 1
                ordered = [calls[i] for i in sorted(calls)]
                for index, call in enumerate(ordered):
                    call["id"] = call["id"] or f"call_{rounds}_{index}"
                messages.append(
                    {
                        "role": "assistant",
                        "content": text or None,
                        "tool_calls": [
                            {
                                "id": c["id"],
                                "type": "function",
                                "function": {
                                    "name": c["name"],
                                    "arguments": c["arguments"] or "{}",
                                },
                            }
                            for c in ordered
                        ],
                    }
                )
                for call in ordered:
                    arguments = parse_arguments(call["arguments"])
                    yield Event("tool_call", name=call["name"], arguments=arguments or {})
                    output, _ = await execute(specs, run_tool, call["name"], arguments)
                    yield Event("tool_result", name=call["name"], text=output)
                    messages.append({"role": "tool", "tool_call_id": call["id"], "content": output})
        except openai.APIConnectionError as exc:
            raise ProviderError("provider_unreachable") from exc
        except openai.RateLimitError as exc:
            raise ProviderError("provider_rate_limited") from exc
        except openai.APIStatusError as exc:
            raise ProviderError(f"provider_http_{exc.status_code}") from exc


class OfflineProvider:
    """No model configured: the service substitutes curated Socratic replies."""

    name = "offline"

    async def converse(
        self,
        system: str,
        turns: list[Turn],
        max_tokens: int,
        tools: list[ToolSpec] | None = None,
        run_tool: ToolRunner | None = None,
        max_rounds: int = 4,
    ) -> AsyncIterator[Event]:
        raise ProviderError("provider_offline")
        yield Event("text")  # pragma: no cover - makes this an async generator


async def complete(provider: Provider, system: str, turns: list[Turn], max_tokens: int) -> str:
    """Whole text of a tool-free reply."""
    text = ""
    async for event in provider.converse(system, turns, max_tokens):
        if event.kind == "text":
            text += event.text
    return text


def make_provider(settings: Settings, *, chat_template_kwargs: dict | None = None) -> Provider:
    if settings.ai_provider == "anthropic":
        return AnthropicProvider(settings)
    if settings.ai_provider == "openai":
        return OpenAIProvider(settings, chat_template_kwargs)
    return OfflineProvider()
