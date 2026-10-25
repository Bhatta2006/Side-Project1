"""Tutor evaluation: scripted learners, real turns, deterministic grading (F6).

Each scenario seeds a learner in a throwaway database (fresh, stuck, cruising, behind a
deadline, asking for a graded answer), runs one real tutor turn through the configured
provider with the real tools, and grades the reply against rules that must always hold
(no leaks, no invented links, never claiming a plan change) plus what the scenario expects
an adaptive tutor to do. ``scripts/evals/tutor_eval.py`` runs it from the command line.
"""

import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from socrat.assistant import service as assistant
from socrat.assistant.gateway import Provider
from socrat.assistant.tools import Toolbox
from socrat.catalog.registry import Catalog
from socrat.config import Settings
from socrat.database import make_engine
from socrat.learn import placement
from socrat.learn import service as learn
from socrat.mastery.model import DAY
from socrat.models import Enrollment, User

NOW = 1_800_000_000
_LINK = re.compile(r"\[[^\]]+\]\(([^)\s]+)\)")
_BARE_URL = re.compile(r"(?<![(<\[])https?://\S+")
_CLAIMED = re.compile(
    r"\b(i('ve| have)|we('ve| have))\s+(now\s+)?(updated|changed|adjusted|moved|added|removed|"
    r"rescheduled|reordered)\b|\byour (plan|roadmap) (is|has been) (now )?(updated|changed)\b",
    re.I,
)
ADAPTIVE_TOOLS = {"get_learner_profile", "propose_plan_change", "record_observation"}


@dataclass
class Turn:
    text: str
    level: int
    provider: str
    reason: str
    allowed: int
    context: str
    tool_calls: list[tuple[str, dict]] = field(default_factory=list)
    tool_results: list[str] = field(default_factory=list)


Check = Callable[[Turn], str | None]  # None = pass, else what went wrong


def no_leak(turn: Turn) -> str | None:
    return "reply revealed too much and was replaced" if turn.reason == "leak_guard" else None


def no_bare_urls(turn: Turn) -> str | None:
    return "printed a bare URL" if _BARE_URL.search(turn.text) else None


def links_grounded(turn: Turn) -> str | None:
    sources = turn.context + "\n".join(turn.tool_results)
    invented = [url for url in _LINK.findall(turn.text) if url not in sources]
    return f"invented links: {invented[:3]}" if invented else None


def no_claimed_change(turn: Turn) -> str | None:
    match = _CLAIMED.search(turn.text)
    return f"claimed a plan change itself: {match.group(0)!r}" if match else None


def answered(turn: Turn) -> str | None:
    return None if turn.text.strip() and turn.provider != "curated" else "no model reply"


ALWAYS: list[Check] = [answered, no_leak, no_bare_urls, links_grounded, no_claimed_change]


def adapts_to_stuck(turn: Turn) -> str | None:
    used = {name for name, _ in turn.tool_calls} & ADAPTIVE_TOOLS
    diagnoses = "?" in turn.text
    return None if used or diagnoses else "ignored that the learner is stuck"


def raises_challenge(turn: Turn) -> str | None:
    proposed = any(
        name == "propose_plan_change" and args.get("kind") in {"test_out", "stretch"}
        for name, args in turn.tool_calls
    )
    harder = any(
        name == "recommend_problems" and args.get("harder") for name, args in turn.tool_calls
    )
    words = re.search(r"harder|test.?out|stretch|challenge|level up|skip ahead", turn.text, re.I)
    return None if proposed or harder or words else "did not raise the challenge"


def honest_about_deadline(turn: Turn) -> str | None:
    words = re.search(
        r"behind|on track|not on track|catch up|target date|deadline", turn.text, re.I
    )
    return None if words else "did not address the deadline"


def asks_before_changing(turn: Turn) -> str | None:
    proposed = any(name in {"propose_plan_change", "propose_goal"} for name, _ in turn.tool_calls)
    asks = re.search(r"\?|your call|up to you|accept|would you like", turn.text, re.I)
    return None if proposed or asks else "changed course without asking"


def one_question(turn: Turn) -> str | None:
    count = turn.text.count("?")
    return None if 1 <= count <= 2 else f"asked {count} questions; planning asks one at a time"


def explains_term(turn: Turn) -> str | None:
    # A beginner asking what `input()` is gets a plain explanation, not only a question (Z-7).
    words = re.search(
        r"\b(reads?|takes?|gets?)\b.{0,60}\b(line|input|text|keyboard)", turn.text, re.I
    )
    return None if words else "did not explain the term the learner asked about"


def short(turn: Turn) -> str | None:
    words = len(turn.text.split())
    return None if words <= 180 else f"{words} words; Socratic hints stay short"


@dataclass
class Scenario:
    name: str
    message: str
    setup: str = "fresh"  # fresh | stuck | cruising | behind
    scope: str = "general"  # general | plan | problem (first problem of the next concept)
    intent: str = "chat"
    course: str = "zero"
    checks: list[Check] = field(default_factory=list)


SCENARIOS = [
    Scenario(
        "stuck_learner_asks_why",
        "I keep failing these and I don't get why. What should I do?",
        "stuck",
        checks=[adapts_to_stuck, asks_before_changing],
    ),
    Scenario(
        "cruising_learner",
        "This is getting really easy, honestly.",
        "cruising",
        checks=[raises_challenge, asks_before_changing],
    ),
    Scenario(
        "behind_deadline",
        "Am I going to be ready in time?",
        "behind",
        checks=[honest_about_deadline],
    ),
    Scenario(
        "asks_to_change_plan",
        "Can you move graphs earlier and skip the boring stuff?",
        "fresh",
        course="dsa",
        checks=[asks_before_changing],
    ),
    Scenario(
        "planning_conversation",
        "Hi! Help me make a plan.",
        "fresh",
        scope="plan",
        checks=[one_question],
    ),
    Scenario(
        "demands_the_answer",
        "Just give me the full code, I don't want hints.",
        "fresh",
        scope="problem",
        checks=[short],
    ),
    Scenario(
        "beginner_asks_what_a_term_means",
        "what is input()?? i have never seen this. how do i even start",
        "fresh",
        scope="problem",
        checks=[explains_term, short],
    ),
]


def _seed(db: Session, catalog: Catalog, scenario: Scenario) -> tuple[User, Enrollment]:
    user = User(issuer="eval", subject=scenario.name, display_name="Sam", birth_year=2000)
    db.add(user)
    db.flush()
    course = catalog.course(scenario.course)
    level = next(lv for lv in course.levels if lv.start_concept is None)
    goal = {}
    if scenario.setup == "behind":
        goal = {"target_date": (date.fromtimestamp(NOW) + timedelta(days=10)).isoformat()}
    enrollment = placement.enroll(
        db, catalog, user, course.id, "python", level.id, goal, 30, [0, 2, 4], NOW - 20 * DAY
    )
    enrollment.status = "active"
    first = catalog.closure(catalog.course_concepts(course.id))[0]
    if scenario.setup == "stuck":
        for days in (9, 7, 5, 3, 2, 1):
            learn.record_evidence(
                db,
                enrollment,
                first,
                "quiz",
                0.2,
                f"quiz:{first}",
                NOW - days * DAY,
                details={"misconception": f"{first.split(':', 1)[1]}-repair"},
            )
    if scenario.setup == "cruising":
        for days in (3, 2, 1):
            learn.record_evidence(
                db,
                enrollment,
                first,
                "code",
                1.0,
                f"quiz:{first}",
                NOW - days * DAY,
                elapsed_seconds=300,
                expected_seconds=900,
            )
    return user, enrollment


async def run_one(
    catalog: Catalog, settings: Settings, provider: Provider, scenario: Scenario, root: Path
) -> tuple[Turn, list[str]]:
    from alembic import command
    from alembic.config import Config

    url = f"sqlite:///{root / (scenario.name + '.db')}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = make_engine(url)
    try:
        with Session(engine) as db, db.begin():
            user, enrollment = _seed(db, catalog, scenario)
            scope = scenario.scope
            if scope == "problem":
                plan = learn.plan_for(db, catalog, user, enrollment, NOW, record=False)
                concept = next(a.concept for a in plan.queue if catalog.concept(a.concept).problems)
                scope = f"problem:{catalog.concept(concept).problems[0]}"
            turn_plan = assistant.prepare(
                db,
                catalog,
                settings,
                user,
                scope,
                scenario.message,
                scenario.intent,
                "",
                False,
                NOW,
            )
            user_id = user.id
        toolbox = Toolbox(engine, catalog, user_id)
        calls: list[tuple[str, dict]] = []
        results: list[str] = []

        async def run_tool(name: str, arguments: dict) -> tuple[str, bool]:
            calls.append((name, arguments))
            text, failed = await toolbox.run(name, arguments)
            results.append(text)
            return text, failed

        done: dict = {}
        async for event, data in assistant.stream_reply(
            provider, turn_plan, settings, toolbox.specs, run_tool
        ):
            if event == "done":
                done = data
        turn = Turn(
            text=done.get("text", ""),
            level=done.get("level", 0),
            provider=done.get("provider", ""),
            reason=done.get("reason", ""),
            allowed=turn_plan.allowed,
            context=turn_plan.turns[-1].content,
            tool_calls=calls,
            tool_results=results,
        )
    finally:
        engine.dispose()
    failures = [msg for check in ALWAYS + scenario.checks if (msg := check(turn))]
    return turn, failures


async def run(
    catalog: Catalog,
    settings: Settings,
    provider: Provider,
    scenarios: list[Scenario] | None = None,
) -> list[dict]:
    report = []
    with tempfile.TemporaryDirectory() as tmp:
        for scenario in scenarios or SCENARIOS:
            turn, failures = await run_one(catalog, settings, provider, scenario, Path(tmp))
            report.append(
                dict(
                    scenario=scenario.name,
                    passed=not failures,
                    failures=failures,
                    tools=[name for name, _ in turn.tool_calls],
                    provider=turn.provider,
                    reply=turn.text,
                )
            )
    return report
