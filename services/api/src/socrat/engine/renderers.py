"""Renderer registry: every interactive thing a lesson can show is a registered, typed renderer.

A model never writes UI code. It picks a renderer by id and fills its typed ``params``; the web
app renders only registered renderers. Each manifest states what the renderer takes, what events
it reports, what it needs at runtime, how it feeds evidence, its accessible alternative, how
failure is handled, and the static fallback shown when it cannot run. A lesson that names an
unknown renderer, bad params, or omits the fallback is rejected before publication.

Adding a renderer: define a params model, add a ``Manifest`` with ``register``, and add the
component to the web registry. Nothing in the course compiler changes.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

Evidence = Literal["none", "exposure", "application", "performance"]  # what it may contribute


class Params(BaseModel):
    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True)
class Manifest:
    id: str
    version: str
    description: str
    domains: tuple[str, ...]  # domain adapter ids it suits ("*" = any)
    params: type[Params]
    events: tuple[str, ...]  # interaction events it reports back
    runtime: tuple[str, ...]  # browser capabilities it needs, e.g. "wasm", "canvas"
    evidence: Evidence  # the strongest evidence kind an interaction here may produce
    accessible_alternative: str  # what a learner who cannot use it gets
    on_error: str  # what happens when it crashes or fails to load
    supports: tuple[str, ...] = ()  # objective kinds it helps teach
    sandboxed: bool = False  # runs model-influenced content in an isolated frame


_REGISTRY: dict[str, Manifest] = {}


def register(manifest: Manifest) -> Manifest:
    if manifest.id in _REGISTRY:
        raise ValueError(f"renderer {manifest.id} is already registered")
    _REGISTRY[manifest.id] = manifest
    return manifest


def all_manifests() -> dict[str, Manifest]:
    return dict(_REGISTRY)


def describe(manifest: Manifest) -> dict:
    return dict(
        id=manifest.id,
        version=manifest.version,
        description=manifest.description,
        domains=list(manifest.domains),
        input_schema=manifest.params.model_json_schema(),
        events=list(manifest.events),
        runtime=list(manifest.runtime),
        evidence=manifest.evidence,
        accessible_alternative=manifest.accessible_alternative,
        on_error=manifest.on_error,
        supports=list(manifest.supports),
        sandboxed=manifest.sandboxed,
    )


# --- parameter models ------------------------------------------------------------------------


class Markdown(Params):
    body: str = Field(min_length=1, max_length=20_000)


class FunctionPlot(Params):
    expressions: list[str] = Field(min_length=1, max_length=6)  # e.g. "sin(x)"
    x_range: tuple[float, float] = (-10, 10)
    y_range: tuple[float, float] | None = None
    sliders: list[str] = Field(default_factory=list, max_length=4)  # parameter names


class CodeTask(Params):
    language: Literal["python", "cpp", "java"]
    starter: str = Field(default="", max_length=20_000)
    problem_id: str | None = None  # a judged problem; None = free practice (evidence: none)


class ConceptMap(Params):
    nodes: list[str] = Field(min_length=2, max_length=40)
    edges: list[tuple[str, str]] = Field(max_length=120)


class GeneratedVisual(Params):
    request: str = Field(min_length=5, max_length=600)  # what the concept visual must show


class Simulation(Params):
    model: Literal[
        "projectile",
        "free_fall",
        "pendulum",
        "spring_mass",
        "circuit",
        "wave",
        "refraction",
        "heating",
    ]
    inputs: dict[str, float] = Field(default_factory=dict)


class Timeline(Params):
    """A time-ordered track editor: frames, beats or events (animation, music, history)."""

    unit: Literal["frame", "beat", "second"]
    length: int = Field(ge=1, le=100_000)
    tracks: list[str] = Field(min_length=1, max_length=12)


class SelfCheck(Params):
    """Learner compares their own real-world attempt against criteria (not verified)."""

    criteria: list[str] = Field(min_length=1, max_length=12)
    how_to_record: str = Field(default="", max_length=500)


MARKDOWN = register(
    Manifest(
        id="markdown",
        version="1.0",
        description="Plain lesson text with headings, lists and equations.",
        domains=("*",),
        params=Markdown,
        events=("viewed",),
        runtime=(),
        evidence="exposure",
        accessible_alternative="It is already text.",
        on_error="Show the raw text.",
        supports=("explain", "read"),
    )
)
FUNCTION_PLOT = register(
    Manifest(
        id="function-plot",
        version="1.0",
        description="Interactive graphs of functions with sliders (JSXGraph).",
        domains=("math-science",),
        params=FunctionPlot,
        events=("slider_changed", "point_moved"),
        runtime=("canvas",),
        evidence="exposure",
        accessible_alternative="A table of values and a sentence describing the curve.",
        on_error="Show the table of values.",
        supports=("explore", "visualise"),
    )
)
CODE_STUDIO = register(
    Manifest(
        id="code-studio",
        version="1.0",
        description="Editor that runs code in the browser or the judge, with tests.",
        domains=("software",),
        params=CodeTask,
        events=("run", "submit"),
        runtime=("wasm",),
        evidence="performance",
        accessible_alternative="The problem statement and tests as text, solvable in any editor.",
        on_error="Offer the judged submit page, or a copyable starter.",
        supports=("practise", "debug", "build"),
    )
)
CONCEPT_MAP = register(
    Manifest(
        id="concept-map",
        version="1.0",
        description="Nodes and prerequisite edges as a navigable graph.",
        domains=("*",),
        params=ConceptMap,
        events=("node_opened",),
        runtime=("canvas",),
        evidence="exposure",
        accessible_alternative="An indented list: each concept with what it depends on.",
        on_error="Show the indented list.",
        supports=("relate", "plan"),
    )
)
CONCEPT_PLAYGROUND = register(
    Manifest(
        id="concept-playground",
        version="1.0",
        description="A model-designed interactive visual, run in a network-blocked sandbox frame.",
        domains=("*",),
        params=GeneratedVisual,
        events=("viewed", "reported"),
        runtime=("sandbox-iframe",),
        evidence="exposure",
        accessible_alternative="The written explanation that accompanies the visual.",
        on_error="Show the explanation and a report button; never substitute another lesson.",
        supports=("explore", "visualise"),
        sandboxed=True,
    )
)
SIMULATION = register(
    Manifest(
        id="simulation",
        version="1.0",
        description="Vetted physical experiments computed by the harness, with units.",
        domains=("math-science", "electronics"),
        params=Simulation,
        events=("parameter_changed", "predicted", "observed"),
        runtime=("canvas",),
        evidence="application",
        accessible_alternative="A results table with units and the formula used.",
        on_error="Show the results table computed on the server.",
        supports=("explore", "predict"),
    )
)
TIMELINE = register(
    Manifest(
        id="timeline",
        version="1.0",
        description="Track editor for timing, rhythm and sequence (animation, music).",
        domains=("music", "animation-movement"),
        params=Timeline,
        events=("marker_placed", "track_changed"),
        runtime=("canvas",),
        evidence="application",
        accessible_alternative="A table of numbered steps with what happens at each.",
        on_error="Show the numbered table.",
        supports=("time", "compose", "analyse"),
    )
)
SELF_CHECK = register(
    Manifest(
        id="self-check",
        version="1.0",
        description="Criteria checklist for real-world practice the engine cannot observe.",
        domains=("music", "animation-movement", "electronics", "general"),
        params=SelfCheck,
        events=("criterion_rated",),
        runtime=(),
        evidence="performance",
        accessible_alternative="It is already a text checklist.",
        on_error="Show the criteria as text.",
        supports=("perform", "reflect"),
    )
)


# --- specs a lesson carries ------------------------------------------------------------------


class VisualizationSpec(BaseModel):
    """What an author (human or model) puts in a lesson to show something interactive."""

    model_config = ConfigDict(extra="forbid")
    renderer: str
    version: str = "1.0"
    params: dict = Field(default_factory=dict)
    purpose: str = Field(min_length=5, max_length=300)  # the learning objective it serves
    fallback_text: str = Field(min_length=10, max_length=4000)  # shown if it cannot run
    alt_text: str = Field(min_length=5, max_length=600)  # accessible description


def validate_spec(spec: dict | VisualizationSpec) -> list[str]:
    """Problems that block publication; empty means the spec is safe to render."""
    try:
        parsed = (
            spec if isinstance(spec, VisualizationSpec) else VisualizationSpec.model_validate(spec)
        )
    except ValidationError as exc:
        return [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()[:10]]
    manifest = _REGISTRY.get(parsed.renderer)
    if manifest is None:
        return [f"unknown renderer {parsed.renderer!r}"]
    problems = []
    major = parsed.version.split(".")[0]
    if major != manifest.version.split(".")[0]:
        problems.append(
            f"renderer {manifest.id} is version {manifest.version}, spec asks {parsed.version}"
        )
    try:
        manifest.params.model_validate(parsed.params)
    except ValidationError as exc:
        problems += [
            f"params.{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()[:10]
        ]
    return problems


def select(domain: str, kind: str, has: Callable[[Manifest], bool] | None = None) -> Manifest:
    """The registered renderer that best supports an objective kind (``explore``, ``practise``,
    ``time``, ...) in a domain. Deterministic: exact domain match first, then any-domain, then
    plain markdown. Domains with no suitable renderer get text, never an invented widget."""
    candidates = [m for m in _REGISTRY.values() if kind in m.supports and (has is None or has(m))]
    for wanted in (domain, "*"):
        for m in sorted(candidates, key=lambda m: m.id):
            if wanted in m.domains and not m.sandboxed:
                return m
    return MARKDOWN


@dataclass
class Plan:
    renderer: str
    reason: str
    fallback: str = field(default="")
