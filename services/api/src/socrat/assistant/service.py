"""Context-aware Socratic replies streamed over SSE, with server-side reveal control.

The provider writes the words; this module decides how much it may reveal, watches the
stream for leaks below the allowed level, and falls back to curated hints when a model is
unavailable, refuses, or oversteps.
"""

import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat import entitlements
from socrat.assessments import service as assessments
from socrat.assistant import engine, socratic
from socrat.assistant.gateway import Provider, ProviderError, ToolRunner, ToolSpec, Turn, complete
from socrat.assistant.prompts import (
    GENERAL_SYSTEM,
    LESSON_STYLES,
    LESSON_SYSTEM,
    SYSTEM,
    render_context,
)
from socrat.assistant.tools import LABELS
from socrat.catalog.registry import Catalog
from socrat.catalog.schema import Problem
from socrat.config import Settings
from socrat.learn import service as learn
from socrat.library import recommend
from socrat.library import service as library
from socrat.mastery.model import band
from socrat.models import (
    AssistantMessage,
    AssistantThread,
    Enrollment,
    LessonVariant,
    Submission,
    User,
)
from socrat.models import (
    now as clock,
)
from socrat.style import access as style_access
from socrat.style import spec as styles

HISTORY_TURNS = 12
PLANNING_MODE = (
    "You are building this learner's roadmap with them. Interview them one question at a "
    "time, in this order, skipping anything the context already answers: what they want "
    "(job interviews and which role, contests and a target rating, or programming "
    "foundations); any date they are working toward; what they already know and what feels "
    "shaky; how much time they can give per day and on which days; and what worries them. "
    "After at most five questions, summarise the plan in three or four bullets, then call "
    "propose_goal (and propose_plan_change for schedule or path style when they named one) "
    "so they can confirm on screen. Never claim the plan changed until they accept."
)
LANGUAGE_NAMES = {"python": "Python", "cpp": "C++", "java": "Java"}
_SCOPE = re.compile(
    r"^(general|plan|problem:[a-z0-9-]{1,64}|concept:[a-z0-9-]{1,64}:[a-z0-9-]{1,64})$"
)


@dataclass
class TurnPlan:
    thread_id: str
    scope: str
    allowed: int
    problem: Problem | None
    turns: list[Turn]
    fallback: str
    reveal_blocked: str = ""
    paused: str = ""  # policy reply that replaces the model (e.g. during an assessment)
    move: engine.Move | None = None  # the teaching engine's decision for this reply
    system: str = ""  # the tutor prompt to use; empty means the default


def validate_scope(scope: str) -> str:
    if not _SCOPE.match(scope):
        raise HTTPException(422, "invalid_scope")
    return scope


def thread_for(db: Session, user_id: str, scope: str) -> AssistantThread:
    thread = db.scalar(
        select(AssistantThread).where(
            AssistantThread.user_id == user_id, AssistantThread.scope == scope
        )
    )
    if thread is None:
        thread = AssistantThread(user_id=user_id, scope=scope, ladder={})
        db.add(thread)
        db.flush()
    return thread


def history(db: Session, thread: AssistantThread) -> list[AssistantMessage]:
    rows = list(
        db.scalars(
            select(AssistantMessage)
            .where(AssistantMessage.thread_id == thread.id)
            .order_by(AssistantMessage.seq.desc())
            .limit(HISTORY_TURNS)
        )
    )
    return list(reversed(rows))


def check_quota(db: Session, settings: Settings, user_id: str, now: int, feature: str = "chat"):
    entitlements.enforce(db, user_id, feature, now)
    sent = db.scalar(
        select(func.count())
        .select_from(AssistantMessage)
        .join(AssistantThread, AssistantThread.id == AssistantMessage.thread_id)
        .where(
            AssistantThread.user_id == user_id,
            AssistantMessage.role == "user",
            AssistantMessage.created_at >= now - 86400,
        )
    )
    if (sent or 0) >= settings.ai_daily_messages:
        raise HTTPException(429, "assistant_daily_limit")


def activity_path(activity_id: str) -> str:
    """Same paths as the web app's activityHref."""
    kind, _, rest = activity_id.partition(":")
    segments = rest.replace(":", "/")
    if kind == "lesson":
        return f"/learn/{segments}"
    if kind == "problem":
        return f"/problems/{segments}"
    if kind in {"example", "explain", "checkin", "stretch"}:
        return f"/learn/{segments}?step={kind}"
    if kind == "quiz":
        return f"/quiz/{segments}"
    return f"/quiz/{kind}/{segments}"


def learner_sections(
    db: Session, catalog: Catalog, user: User, enrollment: Enrollment | None, now: int
) -> dict[str, str]:
    if enrollment is None:
        return {"learner": f"Name: {user.display_name or 'learner'}. Not enrolled in a course yet."}
    course = catalog.course(enrollment.course_id)
    plan = learn.plan_for(db, catalog, user, enrollment, now, record=False)
    states = learn.states_for(db, enrollment)
    groups: dict[str, list[str]] = {
        "strong": [],
        "developing": [],
        "needs_practice": [],
        "likely_known": [],
    }
    for item in plan.roadmap:
        state = states.get(item["concept"])
        if state is None:
            continue
        label = band(state, now)
        if label in groups:
            groups[label].append(item["title"])
    upcoming = [f"{a.kind}: [{a.title}]({activity_path(a.id)})" for a in plan.queue[:5]]
    recent = learn.history_for(db, enrollment, limit=6)
    streak = learn.streak(db, user, enrollment, now)
    learner_state = library.learner_for(db, catalog, user, enrollment, now)
    practice_level = recommend.level_view(learner_state.rating)
    account = library.account_for(db, user.id)
    level = next(
        (x.label for x in course.levels if x.id == enrollment.level_id), enrollment.level_id
    )
    learner = (
        f"Name: {user.display_name or 'learner'}\n"
        f"Course: {course.title}; self-described level: {level}\n"
        f"Goal details: {json.dumps(enrollment.goal) if enrollment.goal else 'none given'}\n"
        f"Language: {LANGUAGE_NAMES.get(enrollment.language, enrollment.language)}\n"
        f"Study budget: {enrollment.minutes_per_day} min on {len(enrollment.weekdays)} days/week\n"
        f"Current pace: {plan.pace} ({plan.pace_reason})\n"
        f"Streak: {streak['current']} study days; projected finish {plan.projected_finish}\n"
        f"Today: {learn.local_day(user, now).isoformat()}\n"
        f"Practice level: {practice_level['name']} (~{practice_level['rating']}); "
        f"{len(learner_state.solved)} library problems solved"
        + (
            f"\nCodeforces: {account.handle}, rating {account.rating or 'unrated'}"
            if account
            else ""
        )
    )
    mastery = "\n".join(
        f"{name}: {', '.join(values[:12])}" for name, values in groups.items() if values
    )
    recent_text = "\n".join(
        f"{x['kind']} on {catalog.concept(x['concept']).title}: score {x['score']:.2f}"
        f"{' (with help level ' + str(x['assistance']) + ')' if x['assistance'] else ''}"
        for x in recent
        if x["concept"] in catalog.concepts
    )
    return {
        "learner": learner,
        "mastery": mastery or "No scored evidence yet.",
        "next_up": "\n".join(upcoming) or "Nothing scheduled.",
        "recent_results": recent_text or "No results yet.",
        "adaptive": adaptive_section(db, catalog, enrollment, plan, states, now),
    }


def adaptive_section(db: Session, catalog: Catalog, enrollment, plan, states, now: int) -> str:
    """What the planner sees: stuck signals, trends, mistakes, deadline, pending changes."""
    from socrat.adaptive import proposals
    from socrat.adaptive import service as adaptive

    if enrollment.status != "active":
        return ""
    skill = adaptive.build_profiles(db, catalog, enrollment, states, now)
    stuck = adaptive.stuck_map(skill, now)
    lines = [f"Path style: {plan.style}; goal focus: {plan.focus}."]
    forecast = plan.forecast
    if forecast.get("target_date"):
        status = "on track" if forecast.get("on_track") else "BEHIND"
        lines.append(
            f"Target date {forecast['target_date']}: {status} (realistic finish "
            f"{forecast['realistic_finish']}, studies {round(forecast['adherence'] * 100)}% "
            "of planned time)."
        )
    elif forecast.get("adherence", 1) < 0.8:
        lines.append(f"Studies about {round(forecast['adherence'] * 100)}% of planned time.")
    for concept, found in list(stuck.items())[:3]:
        lines.append(f"STUCK on {catalog.concept(concept).title}: {found.summary}")
    trending = [
        f"{catalog.concept(p.concept).title} {'up' if p.trend > 0 else 'down'}"
        for p in skill.values()
        if p.trend is not None and abs(p.trend) >= 0.2
    ][:4]
    if trending:
        lines.append(f"Trends this week: {', '.join(trending)}.")
    mistakes = sorted({m for p in skill.values() for m, n in p.misconceptions.items() if n >= 2})[
        :4
    ]
    if mistakes:
        lines.append(f"Recurring mistakes: {', '.join(mistakes)}.")
    leaning = [
        catalog.concept(p.concept).title
        for p in skill.values()
        if p.hint_dependence >= 0.6 and p.attempts >= 3
    ][:3]
    if leaning:
        lines.append(f"Relies on hints for: {', '.join(leaning)}.")
    waiting = proposals.pending(db, enrollment)
    if waiting:
        lines.append(
            "Plan changes waiting for the learner's decision: "
            + "; ".join(p.title for p in waiting[:4])
        )
    if plan.milestones:
        first = plan.milestones[0]
        names = ", ".join(c["title"] for c in first["concepts"][:3])
        lines.append(f"This week's milestone (ends {first['ends']}): {names}.")
    return "\n".join(lines)


def problem_sections(
    db: Session,
    problem: Problem,
    user_id: str,
    code: str,
    language: str,
    allowed: int,
    concept_title: str = "",
) -> dict[str, str]:
    last = db.scalar(
        select(Submission)
        .where(
            Submission.user_id == user_id,
            Submission.problem_id == problem.id,
            Submission.status == "done",
        )
        .order_by(Submission.created_at.desc())
    )
    result = "No runs yet."
    if last is not None:
        result = f"Last {last.mode}: {last.verdict}, {last.passed}/{last.total} tests passed."
        failing = next((c for c in last.cases if c["status"] != "passed" and c.get("public")), None)
        if failing:
            result += (
                f"\nFirst failing visible test input:\n{failing.get('input') or ''}\n"
                f"Expected:\n{failing.get('expected') or ''}\nGot:\n{failing.get('stdout') or ''}\n"
                f"Errors:\n{(failing.get('stderr') or '')[:1500]}"
            )
    examples = "\n".join(f"Input:\n{e.input}\nOutput:\n{e.output}" for e in problem.examples)
    notes = "\n".join(f"- {h}" for h in problem.hints[:allowed])
    if allowed >= 4:
        notes += f"\nApproach: {problem.approach}"
    sections = {
        "practice_problem": f"Concept: {concept_title}\n{problem.title}\n{problem.statement}\n"
        f"Input: {problem.input_format}\n"
        f"Output: {problem.output_format}\nConstraints: {'; '.join(problem.constraints)}\n"
        f"Examples:\n{examples}",
        "tutor_notes": f"Hints you may use at this level:\n{notes}" if notes else "",
        "learner_code": f"Language: {LANGUAGE_NAMES.get(language, language)}\n{code[:12000] or '(empty)'}",
        "latest_result": result,
        "help_policy": f"ALLOWED_LEVEL: {allowed} — {socratic.LEVELS[allowed]}",
    }
    if allowed >= 5:
        sections["reference_solution_python"] = problem.reference
    return sections


def offline_reply(
    scope: str, allowed: int, problem: Problem | None, catalog: Catalog, language: str
) -> str:
    if problem is not None:
        if allowed == 0:
            return (
                "Let's work through it together. What have you tried so far, and where does your "
                "output first differ from the expected output on the examples?"
            )
        if allowed <= 3:
            hint = problem.hints[min(allowed - 1, len(problem.hints) - 1)]
            return f"{hint}\n\nTry that on the first example by hand. What do you notice?"
        if allowed == 4:
            first = problem.approach.split(". ")[0].strip().rstrip(".")
            return f"Here's the shape of the idea: {first}. What would the core step look like in your code?"
        code = (
            f"\n\nA reference solution in Python:\n\n```python\n{problem.reference.strip()}\n```"
            if language == "python"
            else ""
        )
        return f"**Full walkthrough**\n\n{problem.approach.strip()}{code}\n\nOnce it makes sense, close this and rewrite it yourself from memory — then try a similar problem."
    if scope.startswith("concept:"):
        concept = catalog.concept(scope.removeprefix("concept:"))
        points = "\n".join(f"- {p}" for p in concept.key_points)
        return f"**{concept.title}** — {concept.summary}\n\nThe key ideas:\n{points}\n\nWhich of these feels least clear right now?"
    return (
        "I can't give you a full answer just now. Meanwhile, the Today page shows exactly what to "
        "focus on next, and every lesson and problem has curated hints — ask me there, or try "
        "again in a minute."
    )


def prepare(
    db: Session,
    catalog: Catalog,
    settings: Settings,
    user: User,
    scope: str,
    message: str,
    intent: str,
    code: str,
    new_attempt: bool,
    now: int,
) -> TurnPlan:
    scope = validate_scope(scope)
    check_quota(db, settings, user.id, now)
    enrollment = learn.active_enrollment(db, user.id)
    language = enrollment.language if enrollment else "python"
    if scope.startswith("concept:") and scope.removeprefix("concept:") not in learn.curriculum(
        catalog, enrollment
    ):
        raise HTTPException(404, "not_found")
    if scope.startswith("problem:"):
        target = catalog.problems.get(scope.removeprefix("problem:"))
        if target is None or f"{target[0]}:{target[1].concepts[0]}" not in learn.curriculum(
            catalog, enrollment
        ):
            raise HTTPException(404, "not_found")
    thread = thread_for(db, user.id, scope)
    problem: Problem | None = None
    allowed = 5
    reveal_blocked = ""
    sections = learner_sections(db, catalog, user, enrollment, now)
    if scope.startswith("problem:"):
        problem_id = scope.removeprefix("problem:")
        if problem_id not in catalog.problems:
            raise HTTPException(404, "not_found")
        problem = catalog.problem(problem_id)
        ladder = socratic.Ladder.from_dict(thread.ladder.get("state"))
        attempts = (
            db.scalar(
                select(func.count())
                .select_from(Submission)
                .where(
                    Submission.user_id == user.id,
                    Submission.problem_id == problem_id,
                    Submission.status == "done",
                )
            )
            or 0
        )
        # A client flag cannot manufacture effort or reuse the same completed run.
        new_attempt = attempts > int(thread.ladder.get("attempts_seen", 0))
        ladder = socratic.advance(ladder, message, new_attempt)
        failed = failed_submits(db, user.id, problem.id)
        if intent in {"reveal", "reveal_confirmed"}:
            ok, why = socratic.reveal_eligibility(ladder, failed)
            if not ok:
                reveal_blocked = why
            elif intent == "reveal_confirmed":
                ladder = socratic.Ladder(ladder.ceiling, ladder.turns_at_ceiling, revealed=True)
        allowed = 5 if ladder.revealed else ladder.ceiling
        thread.ladder = {**thread.ladder, "state": ladder.to_dict(), "attempts_seen": attempts}
        course_id = catalog.problems[problem_id][0]
        title = catalog.concept(f"{course_id}:{problem.concepts[0]}").title
        sections.update(problem_sections(db, problem, user.id, code, language, allowed, title))
    elif scope.startswith("concept:"):
        qualified = scope.removeprefix("concept:")
        if qualified not in catalog.concepts:
            raise HTTPException(404, "not_found")
        concept = catalog.concept(qualified)
        sections["current_lesson"] = f"{concept.title}: {concept.summary}\n" + "\n".join(
            concept.key_points
        )
        sections["help_policy"] = (
            "ALLOWED_LEVEL: 5 — general concept teaching (not a graded problem)."
        )
    elif scope == "plan":
        sections["help_policy"] = (
            "ALLOWED_LEVEL: 5 — planning conversation about the learner's goal and roadmap."
        )
        sections["planning_mode"] = PLANNING_MODE
    else:
        sections["help_policy"] = (
            "ALLOWED_LEVEL: 5 — general questions about learning and the plan."
        )
    teaching, state = engine.decide(
        engine.State.from_dict(thread.ladder.get("engine")),
        engine.classify(message, new_attempt),
        scope,
        intent,
    )
    thread.ladder = {**thread.ladder, "engine": state.to_dict()}
    sections["teaching_move"] = engine.instruction(teaching)
    style = personal_style(settings, user, enrollment)
    if style is not None:
        sections["learning_style"] = styles.tutor_block(style)
    text = message.strip() or ("I'd like a hint." if intent == "hint" else "Can you help me?")
    if intent == "reveal_confirmed" and not reveal_blocked:
        text = "I've tried my best and I'm still stuck. Please walk me through the full solution."
    db.add(AssistantMessage(thread_id=thread.id, role="user", content=text, created_at=now))
    thread.updated_at = now
    turns = [Turn(m.role, m.content) for m in history(db, thread)[:-1]]
    turns.append(
        Turn("user", f"{render_context(sections)}\n\n<learner_message>\n{text}\n</learner_message>")
    )
    fallback = offline_reply(scope, allowed, problem, catalog, language)
    paused = ""
    if enrollment is not None and assessments.in_progress(db, enrollment, now) is not None:
        paused = (
            "Your weekly assessment is in progress, so I'm stepping back until you submit it — "
            "it measures what *you* know right now. Finish it and I'll go through every "
            "question with you."
        )
    if enrollment is not None:
        from socrat.learn import sessions

        if sessions.instruction_blocked(db, enrollment, now):
            paused = "This is your independent challenge. Try your own approach and submit an attempt; we can review it together afterwards."
        gate = (
            learn.locked_concepts(db, catalog, enrollment, now).get(scope.removeprefix("concept:"))
            if scope.startswith("concept:")
            else None
        )
        if gate == entitlements.PLAN_GATE:
            paused = "This topic is part of the Founding Member plan. Upgrade to unlock it, then we can work through it together."
        elif gate is not None:
            paused = "This concept follows a locked prerequisite. Complete the checkpoint first, then we can work through it together."
    return TurnPlan(
        thread.id,
        scope,
        allowed,
        problem,
        turns,
        fallback,
        reveal_blocked,
        paused,
        teaching,
        GENERAL_SYSTEM if style is not None else "",
    )


STYLE_KEY = styles.STYLE_KEY


def personal_style(settings: Settings, user: User, enrollment) -> styles.StyleSpec | None:
    """The learning style this learner set for themselves. Admin accounts only while the
    style engine is tested: anyone else gets the standard tutor even if a style is stored."""
    if enrollment is None or not style_access.enabled(settings, user):
        return None
    return styles.parse((enrollment.adaptive or {}).get(STYLE_KEY))


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def stream_reply(
    provider: Provider,
    plan: TurnPlan,
    settings: Settings,
    tools: list[ToolSpec] | None = None,
    run_tool: ToolRunner | None = None,
) -> AsyncIterator[tuple[str, dict]]:
    """Yield (event, payload); the final ("done", ...) carries the persisted text and level.

    "tool" events name the lookup in progress so the UI can show it.
    """
    yield (
        "meta",
        {
            "allowed_level": plan.allowed,
            "thread_id": plan.thread_id,
            "reveal_blocked": plan.reveal_blocked,
        },
    )
    if plan.move is not None and not plan.paused and not plan.reveal_blocked:
        yield "move", {"name": plan.move.name, "label": plan.move.label}
    if plan.paused:
        yield "delta", {"text": plan.paused}
        yield "done", {"text": plan.paused, "level": 0, "provider": "policy"}
        return
    if plan.reveal_blocked:
        text = (
            f"I can tell you want to move on — that's fair. To unlock the full walkthrough, "
            f"{plan.reveal_blocked}. Until then: {plan.fallback}"
        )
        yield "delta", {"text": text}
        yield "done", {"text": text, "level": min(plan.allowed, 4), "provider": "policy"}
        return
    reference = plan.problem.reference if plan.problem else ""
    guarded = plan.problem is not None
    raw = ""
    shown = ""
    level: int | None = None
    try:
        paragraph = False
        async for event in provider.converse(
            plan.system or SYSTEM,
            plan.turns,
            settings.ai_reply_tokens,
            tools if settings.ai_tools else None,
            run_tool,
            settings.ai_tool_rounds,
        ):
            if event.kind == "tool_call":
                paragraph = bool(raw.strip())
                yield (
                    "tool",
                    {"name": event.name, "label": LABELS.get(event.name, "Looking that up")},
                )
                continue
            if event.kind != "text":
                continue
            delta = event.text
            if paragraph and level is not None and shown.strip():
                delta = "\n\n" + delta.lstrip()
            paragraph = False
            raw += delta
            if level is None:
                if "</level>" not in raw and len(raw) < 40:
                    continue
                level, body = socratic.parse_level(raw)
                level = plan.allowed if level is None else min(level, plan.allowed)
                shown = body
                if shown and not guarded:
                    yield "delta", {"text": shown}
                continue
            if plan.problem is not None and plan.allowed < 5 and opens_code(raw):
                raise ProviderError("leak_guard")
            shown += delta
            if not guarded:
                yield "delta", {"text": delta}
        if level is None:
            level, shown = socratic.parse_level(raw)
            level = plan.allowed if level is None else min(level, plan.allowed)
            if shown and not guarded:
                yield "delta", {"text": shown}
        if plan.problem is not None and socratic.leaks(
            shown, plan.allowed, reference, plan.problem.approach
        ):
            raise ProviderError("leak_guard")
        if not shown.strip():
            raise ProviderError("empty_reply")
        # The engine's promise (e.g. end by checking understanding) holds whatever the model wrote.
        extra = engine.closing(shown, plan.move)
        shown += extra
        if extra and not guarded:
            yield "delta", {"text": extra}
        if guarded:
            # Validate the complete answer before any protected problem text reaches SSE.
            yield "delta", {"text": shown}
        yield "done", {"text": shown.strip(), "level": level, "provider": provider.name}
    except ProviderError as exc:
        text = plan.fallback
        if str(exc) != "provider_offline":
            yield "replace", {"text": text}
        else:
            yield "delta", {"text": text}
        yield (
            "done",
            {"text": text, "level": plan.allowed, "provider": "curated", "reason": str(exc)},
        )


def opens_code(text: str) -> bool:
    """A code fence in a programming language has started (checked while streaming)."""
    for match in re.finditer(r"```([a-zA-Z+#]*)", text):
        if match.group(1).lower() in {
            "python",
            "py",
            "cpp",
            "c++",
            "java",
            "c",
            "js",
            "javascript",
        }:
            return True
    return False


def persist_reply(db: Session, thread_id: str, text: str, level: int, provider: str, now: int):
    thread = db.get(AssistantThread, thread_id)
    if thread is None:
        return None
    message = AssistantMessage(
        thread_id=thread_id,
        role="assistant",
        content=text,
        level=level,
        provider=provider,
        created_at=now,
    )
    db.add(message)
    thread.ladder = {
        **thread.ladder,
        "max_level": max(int(thread.ladder.get("max_level", 0)), level),
    }
    thread.updated_at = now
    db.flush()
    return message


def assistance_for(db: Session, user_id: str, problem_id: str) -> int:
    thread = db.scalar(
        select(AssistantThread).where(
            AssistantThread.user_id == user_id, AssistantThread.scope == f"problem:{problem_id}"
        )
    )
    return int(thread.ladder.get("max_level", 0)) if thread else 0


def rate(db: Session, user_id: str, message_id: str, rating: int) -> dict:
    """A learner's thumbs up (+1), down (-1) or clear (0) on one of the tutor's replies."""
    message = db.get(AssistantMessage, message_id)
    thread = db.get(AssistantThread, message.thread_id) if message else None
    if (
        message is None
        or thread is None
        or thread.user_id != user_id
        or message.role != "assistant"
    ):
        raise HTTPException(404, "not_found")
    message.rating = rating or None
    return {"id": message.id, "rating": message.rating}


def failed_submits(db: Session, user_id: str, problem_id: str) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Submission)
            .where(
                Submission.user_id == user_id,
                Submission.problem_id == problem_id,
                Submission.mode == "submit",
                Submission.status == "done",
                Submission.verdict != "accepted",
            )
        )
        or 0
    )


def reveal_view(db: Session, user_id: str, scope: str, state: dict | None) -> dict | None:
    """Whether "Show solution" works yet, so the panel never offers what it will refuse (Z-8)."""
    if not scope.startswith("problem:"):
        return None
    ladder = socratic.Ladder.from_dict(state)
    ok, needs = socratic.reveal_eligibility(
        ladder, failed_submits(db, user_id, scope.removeprefix("problem:"))
    )
    return {"ok": ok, "needs": "" if ok else needs}


def thread_view(db: Session, user_id: str, scope: str) -> dict:
    scope = validate_scope(scope)
    thread = db.scalar(
        select(AssistantThread).where(
            AssistantThread.user_id == user_id, AssistantThread.scope == scope
        )
    )
    if thread is None:
        return {
            "scope": scope,
            "messages": [],
            "ladder": {},
            "reveal": reveal_view(db, user_id, scope, None),
        }
    rows = db.scalars(
        select(AssistantMessage)
        .where(AssistantMessage.thread_id == thread.id)
        .order_by(AssistantMessage.seq)
        .limit(200)
    )
    return {
        "scope": scope,
        "ladder": thread.ladder.get("state", {}),
        "reveal": reveal_view(db, user_id, scope, thread.ladder.get("state")),
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "level": m.level,
                "rating": m.rating,
                "at": m.created_at,
            }
            for m in rows
        ],
    }


ARCHIVED = "#"  # archived chats keep their scope with a suffix: "<scope>#<thread id>"
CONTEXT_TITLES = {
    "learner": "About you",
    "mastery": "What you know",
    "next_up": "Next in your plan",
    "recent_results": "Recent results",
    "adaptive": "Where you're stuck and trends",
}


def _owned_thread(db: Session, user_id: str, thread_id: str) -> AssistantThread:
    thread = db.get(AssistantThread, thread_id)
    if (
        thread is None
        or thread.user_id != user_id
        or not _SCOPE.match(thread.scope.split(ARCHIVED)[0])
    ):
        raise HTTPException(404, "not_found")
    return thread


def _has_messages(db: Session, thread: AssistantThread) -> bool:
    return bool(
        db.scalar(
            select(AssistantMessage.id).where(AssistantMessage.thread_id == thread.id).limit(1)
        )
    )


def new_chat(db: Session, user_id: str, scope: str, now: int) -> dict:
    """Archive the current chat for this scope. The hint ladder carries over so a fresh chat
    never resets how much help a problem allows; only the conversation starts over."""
    scope = validate_scope(scope)
    current = db.scalar(
        select(AssistantThread).where(
            AssistantThread.user_id == user_id, AssistantThread.scope == scope
        )
    )
    if current is None or not _has_messages(db, current):
        return {"scope": scope, "archived": None}
    current.scope = f"{scope}{ARCHIVED}{current.id}"
    db.flush()
    carried = {k: v for k, v in current.ladder.items() if k != "engine"}
    db.add(
        AssistantThread(
            user_id=user_id, scope=scope, ladder=carried, created_at=now, updated_at=now
        )
    )
    db.flush()
    return {"scope": scope, "archived": current.id}


def list_chats(db: Session, user_id: str, scope: str) -> dict:
    scope = validate_scope(scope)
    threads = list(
        db.scalars(
            select(AssistantThread)
            .where(
                AssistantThread.user_id == user_id,
                (AssistantThread.scope == scope)
                | AssistantThread.scope.startswith(f"{scope}{ARCHIVED}", autoescape=True),
            )
            # The current chat first, then the newest archived ones.
            .order_by((AssistantThread.scope == scope).desc(), AssistantThread.updated_at.desc())
            .limit(30)
        )
    )
    items = []
    for thread in threads:
        first = db.scalar(
            select(AssistantMessage.content)
            .where(AssistantMessage.thread_id == thread.id, AssistantMessage.role == "user")
            .order_by(AssistantMessage.seq)
            .limit(1)
        )
        count = db.scalar(
            select(func.count())
            .select_from(AssistantMessage)
            .where(AssistantMessage.thread_id == thread.id)
        )
        if not count:
            continue
        items.append(
            {
                "id": thread.id,
                "title": (first or "Chat")[:80],
                "messages": count,
                "updated_at": thread.updated_at,
                "current": thread.scope == scope,
            }
        )
    return {"scope": scope, "items": items}


def chat_view(db: Session, user_id: str, thread_id: str) -> dict:
    """One chat, current or archived, read in full."""
    thread = _owned_thread(db, user_id, thread_id)
    base = thread.scope.split(ARCHIVED)[0]
    view = (
        thread_view(db, user_id, base)
        if thread.scope == base
        else {
            "scope": base,
            "ladder": {},
            "reveal": None,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "level": m.level,
                    "rating": m.rating,
                    "at": m.created_at,
                }
                for m in db.scalars(
                    select(AssistantMessage)
                    .where(AssistantMessage.thread_id == thread.id)
                    .order_by(AssistantMessage.seq)
                    .limit(200)
                )
            ],
        }
    )
    return {**view, "thread_id": thread.id, "archived": thread.scope != base}


def resume_chat(db: Session, user_id: str, thread_id: str, now: int) -> dict:
    """Make an archived chat current again; the chat it replaces is archived in turn."""
    thread = _owned_thread(db, user_id, thread_id)
    base = thread.scope.split(ARCHIVED)[0]
    if thread.scope == base:
        return {"scope": base, "thread_id": thread.id}
    current = db.scalar(
        select(AssistantThread).where(
            AssistantThread.user_id == user_id, AssistantThread.scope == base
        )
    )
    ladder = {k: v for k, v in (current.ladder if current else {}).items() if k != "engine"}
    if current is not None:
        if _has_messages(db, current):
            current.scope = f"{base}{ARCHIVED}{current.id}"
        else:
            db.delete(current)
        db.flush()
    thread.scope = base
    # The newest hint ladder wins, so resuming an old chat cannot change how much help is allowed.
    thread.ladder = (
        {**ladder, "engine": thread.ladder.get("engine", {})} if ladder else thread.ladder
    )
    thread.updated_at = now
    db.flush()
    return {"scope": base, "thread_id": thread.id}


def context_view(db: Session, catalog: Catalog, user: User, scope: str, now: int) -> dict:
    """What Soc reads before every reply in this chat, shown to the learner as-is."""
    scope = validate_scope(scope)
    enrollment = learn.active_enrollment(db, user.id)
    sections = learner_sections(db, catalog, user, enrollment, now)
    thread = db.scalar(
        select(AssistantThread).where(
            AssistantThread.user_id == user.id, AssistantThread.scope == scope
        )
    )
    state = engine.State.from_dict(thread.ladder.get("engine") if thread else None)
    return {
        "scope": scope,
        "sections": [
            {
                "title": CONTEXT_TITLES.get(name, name.replace("_", " ").capitalize()),
                "text": text.strip(),
            }
            for name, text in sections.items()
            if text and text.strip()
        ],
        "teaching": engine.describe(state),
        "history_turns": HISTORY_TURNS,
    }


async def lesson_variant(
    db: Session,
    provider: Provider,
    catalog: Catalog,
    settings: Settings,
    qualified: str,
    language: str,
    style: str,
) -> tuple[str, str]:
    cached = db.get(LessonVariant, (qualified, language, style))
    if cached is not None:
        return cached.content, cached.provider
    concept = catalog.concept(qualified)
    prompt = (
        f"Learner language: {LANGUAGE_NAMES.get(language, language)}\n"
        f"Request: {LESSON_STYLES[style]}\n\nOriginal lesson:\n{concept.lesson}"
    )
    try:
        text = await complete(provider, LESSON_SYSTEM, [Turn("user", prompt)], 1500)
    except ProviderError:
        text = ""
    if not text.strip():
        points = "\n".join(f"- {p}" for p in concept.key_points)
        pitfalls = "\n".join(f"- {p}" for p in concept.pitfalls)
        text = f"## {concept.title} in short\n\n{concept.summary}\n\n### Remember\n{points}"
        if pitfalls:
            text += f"\n\n### Watch out for\n{pitfalls}"
        return text, "curated"
    db.add(
        LessonVariant(
            concept=qualified,
            language=language,
            style=style,
            content=text,
            provider=provider.name,
            created_at=clock(),
        )
    )
    return text, provider.name


sse = _sse
