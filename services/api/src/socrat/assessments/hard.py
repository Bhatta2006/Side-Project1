"""Hard weekly questions, written fresh for each exam and proven by running them.

The item bank tops out at medium difficulty for many topics, so the weekly exam asks the
model for edge-case programs on each studied topic: overflow, negative division, empty and
single-element inputs, aliasing, off-by-one bounds, recursion limits, evaluation order.

Nothing the model says is trusted on its own. Every question is a short program in the
learner's language; the execution plane runs it, and the question is kept only when

- it compiles and runs, and prints one short line,
- the model's own claimed answer is exactly that output (so its explanation is right),
- the four options are distinct and the output is one of them.

A question that fails any check is dropped; the bank fills the gap.
"""

import asyncio
import hashlib
import logging
import random
import secrets

from sqlalchemy import Engine

from socrat.assistant.gateway import ProviderError
from socrat.catalog.schema import Concept
from socrat.config import Settings
from socrat.coursegen import execute
from socrat.coursegen.roles import ask

log = logging.getLogger(__name__)

LABEL = {"python": "Python 3", "cpp": "C++17", "java": "Java 17"}
BUDGET_SECONDS = 110  # the whole generation, model and runs; the exam starts after it
MAX_LINES = 40
MAX_OUTPUT = 120
EXTRA = 2  # ask for a couple more than needed: some will not survive the checks

SYSTEM = """You write the hardest questions in a weekly programming exam. The learner studied
the topic this week and must now prove it under pressure. Questions that a learner who only
skimmed the lesson would get right are useless. Every question hinges on an edge case or a
special condition: integer overflow, negative division and modulo, empty or single-element
input, duplicates, aliasing and shared references, off-by-one bounds, short-circuit and
evaluation order, recursion base cases, floating point, stable versus unstable order,
mutation while iterating, the worst case of an algorithm. Each must need real tracing, not
recall. Reply with one JSON object only."""

PROMPT = """Topic: {title}
What it covers: {summary}
Key points: {points}
Known pitfalls: {pitfalls}

Write {count} questions of the form "What does this program print?" in {language}.

Rules for every question:
- "code": one complete {language} program, at most 30 lines, that reads no input and prints
  exactly one line. {extra}
- It must compile and run as written. No undefined behaviour, no randomness, no time, no
  reliance on hash or dictionary iteration order unless the language guarantees it.
- The output must be short (under 60 characters).
- "prompt": one sentence naming what to work out (never the answer).
- "options": exactly 4 distinct strings, each formatted exactly as the program would print
  it. The wrong ones are what a learner who misses the edge case would predict.
- "answer": the index (0-3) of the option the program really prints. Trace it carefully.
- "edge": the edge case being tested, in a few words.
- "explanation": 1-3 sentences on why that output, naming the edge case.
- Each question tests a different edge case. All of them on this topic.
- Make them genuinely hard. Every program stacks at least two traps that interact (for
  example negative modulo inside a loop bound, overflow hidden in an intermediate product,
  a short-circuit that skips a side effect, integer division before a cast, a loop whose
  last iteration is the edge case). Use 6-25 lines of real logic, not a one-line textbook
  example. A learner who knows the rules but does not trace every step must get it wrong.
- The wrong options must each be the result of one specific, plausible mistake.

Reply: {{"items": [{{"prompt": "...", "code": "...", "options": ["..", "..", "..", ".."],
"answer": 0, "edge": "...", "explanation": "..."}}]}}"""

EXTRA_RULE = {
    "python": "",
    "cpp": "Use #include <bits/stdc++.h> and int main().",
    "java": 'The class is "public class Main" with a main method.',
}


def _shape(raw) -> dict | None:
    """The item if it is well formed, else None."""
    if not isinstance(raw, dict):
        return None
    code, prompt, options = raw.get("code"), raw.get("prompt"), raw.get("options")
    answer, explanation = raw.get("answer"), raw.get("explanation")
    if not (isinstance(code, str) and isinstance(prompt, str) and isinstance(explanation, str)):
        return None
    if not (isinstance(options, list) and len(options) == 4 and isinstance(answer, int)):
        return None
    options = [str(o).strip() for o in options]
    if len(set(options)) != 4 or not 0 <= answer < 4 or any(not o for o in options):
        return None
    if len(code.splitlines()) > MAX_LINES or not prompt.strip() or len(prompt) > 400:
        return None
    return dict(
        prompt=prompt.strip(),
        code=code.strip("\n"),
        options=options,
        answer=answer,
        explanation=explanation.strip()[:600],
        edge=str(raw.get("edge", "")).strip()[:80],
    )


def _key(concept: str, code: str) -> str:
    digest = hashlib.sha256(f"{concept}\n{code}".encode()).hexdigest()[:10]
    return f"gen-{digest}-{secrets.token_hex(3)}"


async def _verify(broker, language: str, item: dict) -> dict | None:
    try:
        (case,) = await broker.run(language, item["code"], [""])
    except execute.Unavailable:
        return None
    except Exception:  # a broken item must not break the exam
        log.exception("weekly item run failed")
        return None
    if case.get("status") != "executed":
        return None
    printed = (case.get("stdout") or "").strip()
    if not printed or "\n" in printed or len(printed) > MAX_OUTPUT:
        return None
    if item["options"][item["answer"]] != printed:
        return None  # the model mis-traced its own program: its explanation is wrong too
    # Models put the right answer first far too often: shuffle so position tells nothing.
    order = random.sample(range(4), 4)
    options = [item["options"][k] for k in order]
    return {**item, "options": options, "answer": options.index(printed)}


async def _for_concept(
    engine: Engine,
    settings: Settings,
    broker,
    concept_key: str,
    concept: Concept,
    language: str,
    count: int,
    user_id: str | None,
) -> list[dict]:
    prompt = PROMPT.format(
        title=concept.title,
        summary=concept.summary,
        points="; ".join(concept.key_points) or "(see topic)",
        pitfalls="; ".join(concept.pitfalls) or "(see topic)",
        count=count + EXTRA,
        language=LABEL[language],
        extra=EXTRA_RULE[language],
    )
    try:
        reply = await ask(engine, settings, "weekly", SYSTEM, prompt, 8000, user_id=user_id)
    except ProviderError:
        log.warning("weekly generation refused for %s", concept_key)
        return []
    raw = (reply.data or {}).get("items")
    shaped = [x for x in map(_shape, raw if isinstance(raw, list) else []) if x]
    checked = await asyncio.gather(*(_verify(broker, language, x) for x in shaped))
    kept = [x for x in checked if x][:count]
    return [{**x, "concept": concept_key, "key": _key(concept_key, x["code"])} for x in kept]


async def generate(
    engine: Engine,
    settings: Settings,
    catalog,
    wanted: dict[str, int],
    language: str,
    user_id: str | None = None,
    broker=None,
    budget: float = BUDGET_SECONDS,
) -> list[dict]:
    """Verified hard items, ``wanted[concept]`` at most per topic. Empty when the model or the
    runner is unavailable, so the caller always has the bank to fall back on."""
    if settings.ai_provider == "offline" or not wanted:
        return []
    broker = broker or execute.Broker(engine, settings, timeout=40, poll=0.5)
    if language not in broker.available([language]):
        return []
    tasks = [
        asyncio.create_task(
            _for_concept(engine, settings, broker, c, catalog.concept(c), language, n, user_id)
        )
        for c, n in wanted.items()
        if n > 0
    ]
    done, pending = await asyncio.wait(tasks, timeout=budget)
    for task in pending:
        task.cancel()
    items: list[dict] = []
    for task in done:
        if not task.cancelled() and task.exception() is None:
            items += task.result()
    return items
