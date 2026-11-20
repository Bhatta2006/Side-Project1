"""The scoper (backlog 3.5, flag ``brain_scoper``): one fast-model call splits a topic into the
units a course on it needs, so a later request can be built from several researched units
instead of one. Runs inside the research job of a top-level unit; a sub-unit is never scoped
again (its key carries ``SUB``). Models propose, code checks: keys, depths, and prerequisites
only on units listed earlier."""

import re

from socrat.coursegen import roles
from socrat.coursegen.brain.spec import LEVELS

SUB = "--"  # "<topic key>--<sub key>.<depth>": a sub-unit of a scoped topic
MAX_UNITS = 5
SCOPER = f"""You split one learning topic into the units a complete course on it needs.

Rules:
- 2 to {MAX_UNITS} units, in learning order; each is one coherent part a learner could study
  over a few sessions.
- "key" is short kebab-case, unique; "depth" is one of {", ".join(LEVELS[1:])}.
- "prerequisites" lists only keys of units earlier in your list.
- Cover the topic; do not add neighbouring topics.

Reply with one JSON object only:
{{"units": [{{"key": "kebab-case", "title": "2-80 chars", "depth": "beginner", "prerequisites": []}}]}}"""
KEY = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+){0,5}$")


def check(reply: dict | None) -> tuple[list[dict], list[str]]:
    """(units, problems). Any problem rejects the whole scope: a partial split is not kept."""
    units = (reply or {}).get("units")
    if not isinstance(units, list) or not 2 <= len(units) <= MAX_UNITS:
        return [], [f"need 2-{MAX_UNITS} units"]
    out, seen, problems = [], [], []
    for u in units:
        if not isinstance(u, dict):
            return [], ["a unit is not an object"]
        key, title = str(u.get("key", "")), str(u.get("title", "")).strip()
        depth, needs = str(u.get("depth", "")), u.get("prerequisites") or []
        if not KEY.match(key) or key in seen:
            problems.append(f"bad or repeated key {key!r}")
        if not 2 <= len(title) <= 80:
            problems.append(f"{key}: title must be 2-80 chars")
        if depth not in LEVELS[1:]:
            problems.append(f"{key}: unknown depth {depth!r}")
        if not isinstance(needs, list) or any(n not in seen for n in needs):
            problems.append(f"{key}: prerequisites must be earlier keys")
        seen.append(key)
        out.append(dict(key=key, title=title, depth=depth, prerequisites=list(needs)))
    return ([], problems) if problems else (out, [])


def sub_key(unit_key: str, sub: dict) -> str:
    """The sub-unit's own unit key under its parent's topic."""
    return f"{unit_key.rsplit('.', 1)[0][:60]}{SUB}{sub['key']}.{sub['depth']}"[:120]


async def scope(engine, settings, topic: str, depth: str, make) -> tuple[list[dict], float]:
    """(checked units or [], cost). One call, no retry: without a scope the topic stays one
    unit, as before."""
    reply = await roles.ask(
        engine, settings, "scoper", SCOPER, f"Topic: {topic}\nDepth: {depth}", 1500, make
    )
    units, _ = check(reply.data)
    return units, reply.cost_usd
