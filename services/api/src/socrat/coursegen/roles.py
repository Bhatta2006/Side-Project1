"""One model call per agent role, with that role's provider, model, effort and prices.

Agents reply with JSON only. Any provider works (no provider-specific structured output),
so the reply is parsed and schema-checked here, and a malformed reply becomes feedback for
the next round instead of a crash.
"""

import json
import re
from dataclasses import dataclass

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from socrat.assistant import budget
from socrat.assistant.gateway import Provider, Turn, make_provider
from socrat.config import Settings
from socrat.models import now

ROLES = {"architect", "critic", "author", "quiz", "atoms", "facts", "reviewer"}
# Override key -> Settings field(s) it replaces for that role.
KEYS = {
    "provider": ("ai_provider",),
    "model": ("ai_model", "openai_model"),
    "effort": ("ai_effort",),
    "base_url": ("openai_base_url",),
    "price_input_per_mtok": ("ai_price_input_per_mtok",),
    "price_output_per_mtok": ("ai_price_output_per_mtok",),
}
DEFAULT_EFFORT = "high"  # outlines and reviews are worth the extra thinking


def check_roles(roles: dict) -> None:
    for role, overrides in roles.items():
        if role not in ROLES:
            raise ValueError(f"SOCRAT_GEN_ROLES: unknown role {role!r}")
        unknown = set(overrides) - set(KEYS)
        if unknown:
            raise ValueError(f"SOCRAT_GEN_ROLES[{role}]: unknown keys {sorted(unknown)}")


def role_settings(settings: Settings, role: str) -> Settings:
    update: dict = {"ai_effort": DEFAULT_EFFORT, "ai_timeout_seconds": settings.gen_timeout_seconds}
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


def parse_json(text: str) -> tuple[dict | None, str]:
    # Lessons contain ``` fences inside JSON strings, so only an outer fence is stripped.
    raw = text.strip()
    outer = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
    if outer:
        raw = outer.group(1)
    elif not raw.startswith("{"):
        raw = raw[raw.find("{") : raw.rfind("}") + 1]
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"reply was not valid JSON ({exc.msg} at line {exc.lineno})"
    if not isinstance(value, dict):
        return None, "reply must be one JSON object"
    return value, ""


async def ask(
    engine: Engine,
    settings: Settings,
    role: str,
    system: str,
    prompt: str,
    max_tokens: int,
    make=make_provider,
) -> Reply:
    """One metered call. Raises ProviderError when the provider or global budget refuses."""
    tuned = role_settings(settings, role)
    provider: Provider = make(tuned)
    if provider.name != "offline":
        with Session(engine) as db:
            budget.check(db, tuned, None, now())
    text, cost = "", 0.0
    async for event in provider.converse(system, [Turn("user", prompt)], max_tokens):
        if event.kind == "text":
            text += event.text
        elif event.kind == "usage":
            with Session(engine) as db, db.begin():
                cost += budget.record(
                    db,
                    tuned,
                    user_id=None,
                    feature=f"coursegen.{role}",
                    provider=provider.name,
                    model=budget.model_name(tuned, provider),
                    input_tokens=event.arguments["input_tokens"],
                    output_tokens=event.arguments["output_tokens"],
                    stamp=now(),
                )
    data, problem = parse_json(text)
    return Reply(data, problem, cost, budget.model_name(tuned, provider))
