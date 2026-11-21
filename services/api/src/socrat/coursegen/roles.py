"""One model call per agent role, with that role's provider, model, effort and prices.

Agents reply with JSON only. Any provider works (no provider-specific structured output),
so the reply is parsed and schema-checked here, and a malformed reply becomes feedback for
the next round instead of a crash.
"""

import contextvars
import hashlib
import json
import re
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from socrat.assistant import budget
from socrat.assistant.gateway import Provider, Turn, make_provider
from socrat.config import Settings
from socrat.models import now

ROLES = {
    "architect",
    "critic",
    "author",
    # Rewrites a lesson that failed its gates or review. Unset, it is the author's model; set
    # a stronger one (SOCRAT_GEN_ROLES) so a cheap model drafts and a strong one fixes.
    "reviser",
    "quiz",
    "atoms",
    "facts",
    "reviewer",
    "engineer",
    "designer",  # projects
    "grader",  # learners' free-text answers and project milestones
    "stylist",  # a free-text learning wish -> a style spec
    "researcher",  # finds open, public sources for a concept
    "extractor",  # sources -> a root unit's reusable material (coursegen/brain/researcher.py)
    "diagnostic",  # a short placement quiz for a learner's own course
    "experience",  # picks registered visuals/labs for a lesson (never writes code)
    "director",  # plans one lesson's sections before it is written (coursegen/director.py)
    "intent",  # a learner's free-text request -> a structured intent
    "onboarding",  # Lesson 0: starter scenarios and a two-step calibration
    "translator",  # lesson text -> another language, under placeholder and glossary checks
    "weekly",  # hard, execution-verified weekly exam questions
    "scoper",  # a topic -> the units a course on it needs (coursegen/brain/scoper.py)
}
# Override key -> Settings field(s) it replaces for that role.
KEYS = {
    "provider": ("ai_provider",),
    "model": ("ai_model", "openai_model", "vertex_model"),
    "effort": ("ai_effort",),
    "base_url": ("openai_base_url",),
    # e.g. {"thinking": true} so the reviser reasons while cheap drafts do not
    "chat_template_kwargs": ("openai_chat_template_kwargs",),
    "price_input_per_mtok": ("ai_price_input_per_mtok",),
    "price_output_per_mtok": ("ai_price_output_per_mtok",),
}
# One retry of a truncated reply may double its budget, up to this many output tokens.
TRUNCATION_CEILING = 16000
DEFAULT_EFFORT = "high"  # outlines and reviews are worth the extra thinking
# Finding and screening sources is retrieval, not reasoning: low effort keeps the cost down.
ROLE_EFFORT = {
    "researcher": "low",
    "stylist": "low",
    "intent": "low",
    "onboarding": "low",
    "diagnostic": "low",
    "experience": "low",
    # A short structured plan, on the first lesson's critical path (live: 15 s at high).
    "director": "low",
}

# A person is waiting on these: a stalled call falls back (generic doors, no calibration, the
# rules reading) instead of holding a visitor for the generation timeout. A live Vertex run
# saw one doors call take 62 s.
ROLE_TIMEOUT = {"onboarding": 25.0, "intent": 30.0}
# Set by the worker while it runs a job a learner is waiting on (``gen_waiting_learner``): every
# call in it is cut at ``gen_waiting_timeout_seconds`` and the job retries, instead of one call
# holding the learner up to the generation timeout (a live run saw a 567 s call).
WAITING: contextvars.ContextVar[bool] = contextvars.ContextVar("waiting", default=False)


# Model tiers: a strong model where judgement decides the result, a fast cheap one where
# the work is retrieval or reading, the default model for everything else. Before this every
# role ran on one model unless each was overridden by hand, so a course was either dear
# everywhere or weak everywhere. A tier does nothing until SOCRAT_GEN_TIERS configures it.
TIERS = ("strong", "fast")
ROLE_TIER = {
    # One call shapes the whole course; a weak plan is paid for in every lesson after it.
    "architect": "strong",
    # Only lessons that failed reach the reviser, so the strong model is paid for rarely.
    "reviser": "strong",
    # The two checks that decide what a learner is shown.
    "facts": "strong",
    "reviewer": "strong",
    # Reading and sorting, not reasoning.
    "researcher": "fast",
    "scoper": "fast",
    "stylist": "fast",
    "intent": "fast",
    "onboarding": "fast",  # a visitor is waiting on it
    "experience": "fast",
    "director": "fast",
}


def tier_of(role: str, escalate: bool = False) -> str:
    """The tier a role runs on: "strong", "fast" or "" (the default model)."""
    return "strong" if escalate else ROLE_TIER.get(role, "")


def check_tiers(tiers: dict) -> None:
    for tier, overrides in tiers.items():
        if tier not in TIERS:
            raise ValueError(f"SOCRAT_GEN_TIERS: unknown tier {tier!r}; use {list(TIERS)}")
        unknown = set(overrides) - set(KEYS)
        if unknown:
            raise ValueError(f"SOCRAT_GEN_TIERS[{tier}]: unknown keys {sorted(unknown)}")


def check_roles(roles: dict) -> None:
    for role, overrides in roles.items():
        if role not in ROLES:
            raise ValueError(f"SOCRAT_GEN_ROLES: unknown role {role!r}")
        unknown = set(overrides) - set(KEYS)
        if unknown:
            raise ValueError(f"SOCRAT_GEN_ROLES[{role}]: unknown keys {sorted(unknown)}")


def role_settings(settings: Settings, role: str, escalate: bool = False) -> Settings:
    """The settings one call runs with. Most specific wins: the role's own override
    (SOCRAT_GEN_ROLES), then its tier (SOCRAT_GEN_TIERS), then SOCRAT_AI_*. ``escalate``
    moves this call to the strong tier: a second try at something the usual model got wrong."""
    update: dict = {
        "ai_effort": ROLE_EFFORT.get(role, DEFAULT_EFFORT),
        "ai_timeout_seconds": ROLE_TIMEOUT.get(role, settings.gen_timeout_seconds),
    }
    if WAITING.get():
        update["ai_timeout_seconds"] = min(
            update["ai_timeout_seconds"], settings.gen_waiting_timeout_seconds
        )
    tier = tier_of(role, escalate)
    strong = "strong" in settings.gen_tiers
    if role == "reviser" and role not in settings.gen_roles and not strong:
        role, tier = "author", tier_of("author", escalate)  # nothing stronger: the author revises
    for key, value in settings.gen_tiers.get(tier, {}).items():
        for field in KEYS[key]:
            update[field] = value
    # An escalated call exists to use the strong model: a per-role override that pins the
    # usual model for this role must not undo that.
    if not (escalate and strong):
        for key, value in settings.gen_roles.get(role, {}).items():
            for field in KEYS[key]:
                update[field] = value
    return settings.model_copy(update=update)


@dataclass
class Reply:
    data: dict | None  # parsed JSON object, or None when the reply was not one
    problem: str  # why parsing failed, for the next round
    cost_usd: float
    model: str = ""
    prompt_version: str = ""  # see ``prompt_version``
    ms: int = 0  # wall time of the call


@dataclass(frozen=True)
class Envelope:
    """The typed result every bounded worker hands the orchestrator (master prompt 7): whether
    its reply parsed, plus the confidence, assumptions, unresolved issues and evidence it
    stated. Read from optional top-level keys of the reply; anything malformed is dropped,
    never trusted. The orchestrator still validates the payload itself before using it."""

    role: str
    ok: bool
    problem: str = ""
    confidence: float | None = None
    assumptions: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    def as_log(self) -> dict:
        out: dict = {"ok": self.ok}
        if self.problem:
            out["problem"] = self.problem[:300]
        if self.confidence is not None:
            out["confidence"] = self.confidence
        for name in ("assumptions", "unresolved", "evidence"):
            if value := getattr(self, name):
                out[name] = list(value)
        return out


def _texts(value, limit: int = 10) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(v)[:300] for v in value if isinstance(v, str | int | float) and str(v))[:limit]


def envelope(role: str, reply: "Reply") -> Envelope:
    data = reply.data
    if data is None:
        return Envelope(role, False, reply.problem)
    raw = data.get("confidence")
    confidence = (
        round(float(raw), 3)
        if isinstance(raw, int | float) and not isinstance(raw, bool) and 0 <= raw <= 1
        else None
    )
    return Envelope(
        role,
        True,
        confidence=confidence,
        assumptions=_texts(data.get("assumptions")),
        unresolved=_texts(data.get("unresolved")),
        evidence=_texts(data.get("evidence")),
    )


# LaTeX commands that start with a JSON escape letter (\b \f \n \r \t). Written with one
# backslash, json.loads reads "\frac" as a form feed plus "rac" without any error, so inside
# $...$ the backslash is doubled before parsing. \ne, \nu, \not and \ni are left alone: after a
# real newline they are ordinary words.
_LATEX = re.compile(
    r"(?<!\\)\\(?=(?:b(?:eta|ar|inom|mod|oldsymbol|igg?|ot|ullet|egin)|f(?:rac|orall|lat)"
    r"|n(?:abla|eq|otin|mid|eg)|r(?:ho|ight|ightarrow|angle|ceil|floor)"
    r"|t(?:heta|au|ext|extbf|extit|imes|ilde|frac|riangle|o|op))(?![A-Za-z]))"
)
_MATH_SPAN = re.compile(r"\$\$.+?\$\$|\$[^$]+?\$", re.DOTALL)


# An odd run of backslashes followed by a character JSON cannot escape (\s of \sigma, \{, \l of
# \land, \u not followed by four hex digits): invalid JSON that would fail the whole reply. A
# live run lost a lesson round to it (2026-11-21). Doubling the last backslash is always safe.
_INVALID_ESCAPE = re.compile(r'(?<!\\)((?:\\\\)*)\\(?=[^"\\/bfnrtu]|u(?![0-9a-fA-F]{4}))')


def keep_latex(raw: str) -> str:
    """Raw JSON with LaTeX backslashes kept: commands inside maths that JSON would silently
    read as escapes (\\frac, \\beta), and anywhere a backslash JSON cannot read (\\sigma)."""
    raw = _MATH_SPAN.sub(lambda m: _LATEX.sub(r"\\\\", m.group(0)), raw)
    return _INVALID_ESCAPE.sub(r"\1\\\\", raw)


def parse_json(text: str) -> tuple[dict | None, str]:
    # Lessons contain ``` fences inside JSON strings, so only an outer fence is stripped.
    raw = text.strip()
    outer = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
    if outer:
        raw = outer.group(1)
    elif not raw.startswith("{"):
        raw = raw[raw.find("{") : raw.rfind("}") + 1]
    try:
        value = json.loads(keep_latex(raw))
    except json.JSONDecodeError as exc:
        return None, f"reply was not valid JSON ({exc.msg} at line {exc.lineno})"
    if not isinstance(value, dict):
        return None, "reply must be one JSON object"
    return value, ""


def prompt_version(system: str) -> str:
    """A short, stable id of a role's instructions: any edit to the prompt changes it, so every
    artifact records exactly which wording produced it."""
    return hashlib.sha256(system.encode()).hexdigest()[:12]


async def ask(
    engine: Engine,
    settings: Settings,
    role: str,
    system: str,
    prompt: str,
    max_tokens: int,
    make=make_provider,
    user_id: str | None = None,
    escalate: bool = False,
) -> Reply:
    """One metered call, charged to ``user_id`` when a learner caused it. Raises ProviderError
    when the provider, the global budget or that learner's budget refuses. ``escalate``: run
    this call on the strong tier (see ``role_settings``)."""
    started = time.monotonic()
    tuned = role_settings(settings, role, escalate)
    provider: Provider = make(tuned)
    if provider.name != "offline":
        with Session(engine) as db:
            budget.check(db, tuned, user_id, now())
    cost = 0.0
    extra: dict[str, Any] = (
        {"response_format": {"type": "json_object"}}
        if provider.name == "openai" and tuned.openai_json_mode
        else {"response_format": {"type": "json_object"}}
        if provider.name == "vertex" and tuned.vertex_json_mode
        else {}
    )
    limit = max_tokens
    for attempt in range(2):
        text, produced = "", 0
        async for event in provider.converse(system, [Turn("user", prompt)], limit, **extra):
            if event.kind == "text":
                text += event.text
            elif event.kind == "usage":
                produced = event.arguments["output_tokens"]
                with Session(engine) as db, db.begin():
                    cost += budget.record(
                        db,
                        tuned,
                        user_id=user_id,
                        feature=f"coursegen.{role}",
                        provider=provider.name,
                        model=budget.model_name(tuned, provider),
                        input_tokens=event.arguments["input_tokens"],
                        output_tokens=produced,
                        stamp=now(),
                    )
        data, problem = parse_json(text)
        # A reasoning model can spend its whole budget thinking and never reach the JSON. That is
        # a budget problem, not a content verdict: ask the same question once with more room
        # instead of letting the caller score an empty reply and burn a whole revision round.
        cut_off = data is None and produced >= int(limit * 0.97)
        if not cut_off:
            break
        if attempt == 0:
            limit = min(limit * 2, TRUNCATION_CEILING)
            # The retry answers without thinking: a model that spent 16000 tokens reasoning would
            # spend them again, and a cut-off fact check fails a lesson the reviewer rated well.
            # The question and the checks on the answer are the same; only the reasoning goes.
            kwargs = dict(tuned.openai_chat_template_kwargs or {})
            if kwargs.get("thinking"):
                tuned = tuned.model_copy(
                    update={"openai_chat_template_kwargs": {**kwargs, "thinking": False}}
                )
                provider = make(tuned)
            continue
        problem = f"reply was cut off at the {limit} token limit before the JSON was complete"
    ms = int((time.monotonic() - started) * 1000)
    return Reply(
        data, problem, cost, budget.model_name(tuned, provider), prompt_version(system), ms
    )
