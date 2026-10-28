"""The capability registry: name, typed input, sandboxed run, uniform result."""

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import BaseModel, ValidationError


@dataclass(frozen=True)
class Capability:
    name: str  # "math.check": the studio or subject, then the verb
    summary: str  # what a model is told it does (kept short; it is a tool description)
    input: type[BaseModel]  # validated before anything runs
    run: Callable[[dict], dict]  # pure and deterministic; runs in the sandbox
    parameters: dict = field(default_factory=dict)  # JSON Schema shown to models
    timeout: float = 6.0
    tutor: bool = True  # offered to the tutor as a tool

    @property
    def tool_name(self) -> str:
        return self.name.replace(".", "_")


@dataclass(frozen=True)
class Result:
    capability: str
    ok: bool
    output: dict
    error: str = ""
    ms: int = 0


_REGISTRY: dict[str, Capability] = {}


def register(capability: Capability) -> Capability:
    if capability.name in _REGISTRY:
        raise ValueError(f"capability {capability.name} is already registered")
    _REGISTRY[capability.name] = capability
    return capability


def capabilities() -> dict[str, Capability]:
    from socrat.harness import library  # noqa: F401  (registers the built-in capabilities)

    return dict(_REGISTRY)


def call(name: str, arguments: dict) -> Result:
    """Validate, run in the sandbox, and never raise: a failure is a Result with ``ok=False``."""
    from socrat.harness import sandbox

    found = capabilities().get(name)
    if found is None:
        return Result(name, False, {}, f"No capability named {name}.")
    try:
        clean = found.input.model_validate(arguments).model_dump(exclude_none=True)
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(str(p) for p in first["loc"]) or "input"
        return Result(name, False, {}, f"Invalid {where}: {first['msg']}")
    started = time.monotonic()
    try:
        output = sandbox.run(name, clean, found.timeout)
    except sandbox.Failed as exc:
        return Result(name, False, {}, str(exc), int((time.monotonic() - started) * 1000))
    return Result(name, True, output, "", int((time.monotonic() - started) * 1000))
