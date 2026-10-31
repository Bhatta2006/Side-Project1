"""Turn learner evidence into a roadmap, an activity queue and a day-by-day schedule.

Pure function of its inputs: identical inputs always produce the identical plan,
so every adaptation can be replayed and explained.

The roadmap adapts on its own only in how a concept is taught: pace, which problems,
spaced reviews, and support steps (a worked example, a simpler explanation, a tutor
check-in) when the learner is stuck. Changes to the roadmap itself — repairing a
prerequisite, test-outs, setting concepts aside, trimming for a deadline — arrive here
only as ``Adaptive.overrides`` the learner has already approved (``socrat.adaptive``).
"""

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

from socrat.adaptive.stuck import Stuck, next_rung
from socrat.catalog.registry import Catalog
from socrat.mastery import transfer as transfers
from socrat.mastery.model import DAY, ConceptState
from socrat.planner import gates, goals

Pace = Literal["support", "steady", "fast"]
PACE_FACTOR: dict[str, float] = {"support": 1.3, "steady": 1.0, "fast": 0.7}
STYLE_FACTOR: dict[str, float] = {
    "thorough": 1.15,
    "balanced": 1.0,
    "fast_track": 0.9,
    "goal_focused": 1.0,
}
REVIEW_MINUTES = 5
CHECKPOINT_MINUTES = 15
TESTOUT_MINUTES = 10
TRANSFER_MINUTES = 15
SUPPORT_MINUTES = {"example": 10, "explain": 10, "checkin": 5}
MAX_REVIEWS_PER_DAY = 2
HORIZON_DAYS = 14
MILESTONE_WEEKS = 8
SCORED = {"quiz", "code", "checkpoint", "review"}
ActivityKind = Literal[
    "lesson",
    "quiz",
    "problem",
    "checkpoint",
    "review",
    "remedial",
    "probe",
    "testout",
    "moduletest",
    "example",
    "explain",
    "checkin",
    "stretch",
    "transfer",
]


@dataclass(frozen=True)
class Activity:
    id: str
    kind: ActivityKind
    concept: str  # qualified concept (module id for checkpoints and module test-outs)
    title: str
    minutes: int
    reason: str = ""
    # Machine-readable why, so the learner sees which adaptation put this here.
    code: str = "path"

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass(frozen=True)
class Adaptive:
    """Everything beyond raw evidence that shapes the plan. All of it is learner-owned:
    the goal and style they chose, and overrides from proposals they accepted."""

    course_id: str = ""
    goal: dict = field(default_factory=dict)
    style: str = "balanced"
    overrides: dict = field(default_factory=dict)
    stuck: dict[str, Stuck] = field(default_factory=dict)
    tried: dict[str, frozenset[str]] = field(default_factory=dict)  # rungs used per concept
    adherence: float = 1.0


@dataclass
class Plan:
    pace: Pace
    pace_reason: str
    roadmap: list[dict]
    queue: list[Activity]
    days: list[dict]
    remaining_minutes: int
    projected_finish: str
    reasons: list[str] = field(default_factory=list)
    style: str = "balanced"
    focus: str = "foundations"
    milestones: list[dict] = field(default_factory=list)
    forecast: dict = field(default_factory=dict)
    # Signals for suggestions; never applied by the planner itself.
    needs_repair: dict[str, str] = field(default_factory=dict)  # concept -> weak prerequisite
    # Modules whose checkpoint is passed but which stay shut until a transfer check is passed.
    held: frozenset[str] = frozenset()

    def to_dict(self) -> dict:
        return {
            "pace": self.pace,
            "pace_reason": self.pace_reason,
            "roadmap": self.roadmap,
            "queue": [a.to_dict() for a in self.queue],
            "days": self.days,
            "remaining_minutes": self.remaining_minutes,
            "projected_finish": self.projected_finish,
            "reasons": self.reasons,
            "style": self.style,
            "focus": self.focus,
            "milestones": self.milestones,
            "forecast": self.forecast,
        }


def pace_of(history: list[dict]) -> tuple[Pace, str]:
    scored = [x for x in history if x.get("kind") in SCORED][-6:]
    if len(scored) < 3:
        return "steady", "Gathering evidence about your pace."
    last3, last4, last5 = scored[-3:], scored[-4:], scored[-5:]
    ratios = [
        x["elapsed_seconds"] / x["expected_seconds"]
        for x in last3
        if x.get("elapsed_seconds") and x.get("expected_seconds")
    ]
    if all(x["score"] >= 0.85 and x.get("assistance", 0) == 0 for x in last3) and (
        not ratios or sum(ratios) / len(ratios) <= 1.0
    ):
        return "fast", "Three strong independent results in a row — moving you ahead faster."
    if sum(x["score"] < 0.5 for x in last4) >= 2:
        return "support", "A couple of tough results — adding practice and smaller steps."
    if sum(x.get("assistance", 0) >= 3 for x in last5) >= 3:
        return "support", "You've leaned on big hints lately — building independence first."
    return "steady", "You're progressing at a steady pace."


def concept_pace(
    qualified: str, history: list[dict], overall: Pace, adaptive: Adaptive
) -> tuple[Pace, str]:
    """Pace for one concept (C2): the learner's own say first, then results on it."""
    feel = adaptive.overrides.get("feel", {}).get(qualified)
    if feel == "easy":
        return "fast", "You said this feels easy, so it moves faster."
    if feel == "hard":
        return "support", "You said this feels hard, so it gets smaller steps."
    own = [x for x in history if x.get("concept") == qualified and x.get("kind") in SCORED]
    if len(own) >= 3:
        return pace_of(own)
    return overall, ""


def _minutes(value: float, pace: Pace, style: str = "balanced") -> int:
    return max(3, int(math.ceil(value * PACE_FACTOR[pace] * STYLE_FACTOR[style] / 5) * 5))


def concept_activities(
    catalog: Catalog,
    qualified: str,
    state: ConceptState,
    pace: Pace,
    style: str = "balanced",
    support: str | None = None,
    support_reason: str = "",
    support_code: str = "stuck_support",
) -> list[Activity]:
    concept = catalog.concept(qualified)
    est = concept.estimated_minutes
    order = {"easy": 0, "medium": 1, "hard": 2}
    problems = sorted(
        (catalog.problem(p) for p in concept.problems), key=lambda p: (order[p.difficulty], p.id)
    )
    accelerate = (pace == "fast" or style == "fast_track") and style != "thorough"
    if accelerate and len(problems) > 1 and state.failures == 0:
        # Strong learners skip the warm-up problem but keep the real challenge.
        problems = [p for p in problems if p.difficulty != "easy"] or problems[-1:]
    elif pace == "support" and len(problems) > 1 and state.failures >= 1:
        problems = [p for p in problems if p.difficulty != "hard"] or problems[:1]
    items = [
        Activity(
            f"lesson:{qualified}",
            "lesson",
            qualified,
            concept.title,
            _minutes(est * 0.3, pace, style),
            reason="Learn the idea first.",
        ),
        Activity(
            f"quiz:{qualified}",
            "quiz",
            qualified,
            f"{concept.title} check",
            _minutes(est * 0.15, pace, style),
            reason="A quick check that the idea landed.",
        ),
    ]
    if support:
        titles = {
            "example": f"Worked example: {concept.title}",
            "explain": f"{concept.title}, explained another way",
            "checkin": f"Talk it through: {concept.title}",
        }
        step = Activity(
            f"{support}:{qualified}",
            support,  # type: ignore[arg-type]
            qualified,
            titles[support],
            SUPPORT_MINUTES[support],
            reason=support_reason,
            code=support_code,
        )
        # After a missed check, re-teach before the retake; other support follows the check.
        items.insert(1 if support_code == "failed_check_refresh" else len(items), step)
    share = est * 0.55 / max(1, len(problems))
    items += [
        Activity(
            f"problem:{p.id}",
            "problem",
            qualified,
            p.title,
            _minutes(max(10, share), pace, style),
            reason=f"Practice {concept.title} on your own ({p.difficulty}).",
        )
        for p in problems
    ]
    return items


def weakest_prerequisite(
    catalog: Catalog, qualified: str, states: dict[str, ConceptState], now: int
) -> str | None:
    candidates = [
        (states.get(p, ConceptState()).effective(now), p)
        for p in catalog.prerequisites[qualified]
        if states.get(p, ConceptState()).effective(now) < 0.65
    ]
    return min(candidates)[1] if candidates else None


def study_days(start: date, weekdays: set[int], count: int) -> list[date]:
    days = [start]  # The learner is here today, so today is always a study day.
    cursor = start
    while len(days) < count:
        cursor += timedelta(days=1)
        if cursor.weekday() in weekdays:
            days.append(cursor)
    return days


def ordered(catalog: Catalog, path: list[str], score: dict[str, float]) -> list[str]:
    """Prerequisites first; among concepts free to go next, the higher score wins and the
    course order breaks ties, so equal scores keep the authored sequence. A concept passes
    its score down to its prerequisites, so pinning a topic pulls its foundations forward."""
    index = {c: i for i, c in enumerate(path)}
    members = set(path)
    score = dict(score)
    for concept in reversed(path):
        for prereq in catalog.prerequisites[concept]:
            if prereq in members:
                score[prereq] = max(score.get(prereq, 0.0), score.get(concept, 0.0))
    placed: list[str] = []
    done: set[str] = set()
    remaining = list(path)
    while remaining:
        ready = [
            c
            for c in remaining
            if all(p in done or p not in members for p in catalog.prerequisites[c])
        ] or remaining[:1]
        best = max(ready, key=lambda c: (score.get(c, 0.0), -index[c]))
        placed.append(best)
        done.add(best)
        remaining.remove(best)
    return placed


def set_aside(catalog: Catalog, path: list[str], candidates: set[str]) -> set[str]:
    """Candidates no remaining concept depends on; anything needed stays on the path."""
    aside = set(candidates)
    changed = True
    while changed:
        changed = False
        for concept in path:
            if concept in aside:
                continue
            for prereq in catalog.prerequisites[concept]:
                if prereq in aside:
                    aside.discard(prereq)
                    changed = True
    return aside


def module_title(catalog: Catalog, module_key: str) -> str:
    course_id, module_id = module_key.split(":", 1)
    return next(m.title for m in catalog.course(course_id).modules if m.id == module_id)


def build_plan(
    catalog: Catalog,
    targets: list[str],
    states: dict[str, ConceptState],
    completed: set[str],
    history: list[dict],
    today: date,
    now: int,
    weekdays: set[int],
    minutes_per_day: int,
    course_id: str | None = None,
    cooldowns: dict[str, int] | None = None,
    adaptive: Adaptive | None = None,
    transfer: transfers.Transfer | None = None,
) -> Plan:
    if not weekdays:
        raise ValueError("at least one study weekday is required")
    adaptive = adaptive or Adaptive(course_id=course_id or "")
    overrides = adaptive.overrides
    style = adaptive.style if adaptive.style in goals.STYLES else "balanced"
    pace, pace_reason = pace_of(history)
    comeback = overrides.get("comeback") or {}
    if int(comeback.get("until", 0)) > now:
        pace, pace_reason = "support", "Welcome back — easing in with shorter steps this week."
    focus = goals.focus_of(adaptive.course_id or course_id or "", adaptive.goal)
    path = catalog.closure(targets)
    relevance = {
        c: goals.relevance(c, adaptive.course_id or course_id or "", adaptive.goal) for c in path
    }
    priority = set(overrides.get("priority", []))
    deferred = set(overrides.get("defer", []))
    unknown = {c for c in path if not states.get(c, ConceptState()).evidence_count}
    optional_candidates = (
        {c for c in path if relevance[c] < goals.OPTIONAL_BELOW and c in unknown}
        if style == "goal_focused"
        else set()
    )
    skipped_candidates = {c for c in overrides.get("skip", []) if c in path}
    aside = set_aside(catalog, path, optional_candidates | skipped_candidates)
    # A deferred concept takes everything built on it along to the back.
    for member in path:
        if any(p in deferred for p in catalog.prerequisites[member]):
            deferred.add(member)
    if style != "thorough":
        score: dict[str, float] = {
            c: goals.tier(relevance[c])
            + (3 if c in priority else 0)
            - (10 if c in deferred or c in aside else 0)
            for c in path
        }
        path = ordered(catalog, path, score)
    cooldowns = cooldowns or {}
    transfer = transfer or transfers.Transfer()
    gate_targets = (
        gates.locked_modules(catalog, course_id, states, completed, now, transfer.blocking)
        if course_id
        else {}
    )
    locked = (
        gates.locked_concepts(catalog, course_id, states, completed, now, transfer.blocking)
        if course_id
        else {}
    )
    locked_minutes = 0
    roadmap: list[dict] = []
    queue: list[Activity] = []
    front: list[Activity] = []
    reasons: list[str] = []
    needs_repair: dict[str, str] = {}
    seen_modules: dict[str, list[str]] = {}
    for qualified in path:
        module = f"{catalog.owner[qualified]}:{catalog.module_of(qualified)}"
        seen_modules.setdefault(module, []).append(qualified)
    last_of_module = {members[-1]: module for module, members in seen_modules.items()}
    repairs = {tuple(x) for x in overrides.get("repair", [])}
    probes = set(overrides.get("probe", [])) | set(comeback.get("concepts", []))
    for target in overrides.get("testout", []):
        kind: ActivityKind = "moduletest" if target.startswith("module:") else "testout"
        key = target.removeprefix("module:")
        if f"{kind}:{key}" in completed:
            continue
        if kind == "testout" and (
            key in locked or key not in catalog.concepts or catalog.concept(key).status == "planned"
        ):
            continue
        if kind == "moduletest" and any(c in locked for c in gates.module_concepts(catalog, key)):
            continue
        title = module_title(catalog, key) if kind == "moduletest" else catalog.concept(key).title
        front.append(
            Activity(
                f"{kind}:{key}",
                kind,
                key,
                f"Test out: {title}",
                TESTOUT_MINUTES if kind == "testout" else CHECKPOINT_MINUTES,
                reason="You chose to prove what you know; passing skips ahead.",
                code="chosen_testout",
            )
        )
    for probe in sorted(probes):
        if (
            probe in catalog.concepts
            and catalog.concept(probe).status != "planned"
            and f"probe:{probe}" not in completed
        ):
            front.append(
                Activity(
                    f"probe:{probe}",
                    "probe",
                    probe,
                    f"Quick check: {catalog.concept(probe).title} and its foundations",
                    TESTOUT_MINUTES,
                    reason="Finds which building block is the real gap.",
                    code="probe",
                )
            )
    skipped = 0
    for qualified in path:
        state = states.get(qualified, ConceptState())
        concept = catalog.concept(qualified)
        entry_base = {
            "concept": qualified,
            "title": concept.title,
            "module": module_of(catalog, qualified),
            "mastery": round(state.effective(now), 3),
            "confidence": round(state.confidence, 3),
            "minutes": concept.estimated_minutes,
            "relevance": relevance[qualified],
            "priority": qualified in priority,
            "deferred": qualified in set(overrides.get("defer", [])),
            "transfer": transfer.status.get(qualified),
        }
        if qualified in aside and not state.mastered(now):
            why = (
                "You chose to drop this to make your date."
                if qualified in skipped_candidates
                else "Optional for your goal; open it any time."
            )
            status = "skipped" if qualified in skipped_candidates else "optional"
            roadmap.append({**entry_base, "status": status, "why": why})
            continue
        if concept.status == "planned":
            # Outlined but not generated yet: on the roadmap and in the forecast, never queued.
            locked_minutes += sum(
                a.minutes for a in concept_activities(catalog, qualified, state, pace, style)
            )
            roadmap.append({**entry_base, "status": "preparing"})
            continue
        if qualified in locked:
            # Behind a gate: shown on the roadmap and counted in the forecast, not scheduled.
            locked_minutes += sum(
                a.minutes for a in concept_activities(catalog, qualified, state, pace, style)
            )
            roadmap.append({**entry_base, "status": "locked", "locked_by": locked[qualified]})
            continue
        why = ""
        if state.mastered(now):
            status = "mastered"
        elif state.assumed and state.evidence_count == 0:
            # Placement only believes this: a short hard check must prove it before it counts.
            status, why = "assumed", "Placement suggests you know this; a short check confirms it."
            skipped += 1
            if f"testout:{qualified}" not in completed:
                queue.append(
                    Activity(
                        f"testout:{qualified}",
                        "testout",
                        qualified,
                        f"Confirm: {concept.title}",
                        TESTOUT_MINUTES,
                        reason="Placement suggests you know this. Pass a short check to skip "
                        "the lesson; miss and you'll learn it properly.",
                        code="assumed_confirm",
                    )
                )
        else:
            c_pace, c_reason = concept_pace(qualified, history, pace, adaptive)
            stuck = adaptive.stuck.get(qualified)
            support, support_reason = None, ""
            weak = weakest_prerequisite(catalog, qualified, states, now)
            if stuck is not None:
                tried = set(adaptive.tried.get(qualified, ())) | {
                    k for k in SUPPORT_MINUTES if f"{k}:{qualified}" in completed
                }
                rung = next_rung(stuck, tried, weak is not None)
                if rung and not rung[1]:
                    support, support_reason = rung[0], stuck.summary
            support_code = "stuck_support"
            failed_check = (
                f"lesson:{qualified}" in completed
                and f"quiz:{qualified}" not in completed
                and state.failures > 0
            )
            if support is None and failed_check and f"explain:{qualified}" not in completed:
                support, support_code = "explain", "failed_check_refresh"
                support_reason = (
                    "Your check missed; a different explanation first, then a fresh check."
                )
            activities = concept_activities(
                catalog, qualified, state, c_pace, style, support, support_reason, support_code
            )
            pending = [a for a in activities if a.id not in completed]
            status = "upcoming"
            if any(a.id in completed for a in activities) or state.evidence_count:
                status = "in_progress"
            if not pending:
                status = "practiced"
            if (state.failures >= 1 and state.mean < 0.5) or stuck is not None:
                if weak:
                    needs_repair[qualified] = weak
            for weak_concept, for_concept in sorted(repairs):
                if for_concept == qualified and f"remedial:{weak_concept}" not in completed:
                    queue.append(
                        Activity(
                            f"remedial:{weak_concept}",
                            "remedial",
                            weak_concept,
                            f"Refresh: {catalog.concept(weak_concept).title}",
                            _minutes(15, c_pace, style),
                            reason=f"{concept.title} depends on "
                            f"{catalog.concept(weak_concept).title}; you approved a refresher.",
                            code="approved_refresh",
                        )
                    )
            queue.extend(pending)
            if overrides.get("stretch") and pending and f"stretch:{qualified}" not in completed:
                queue.append(
                    Activity(
                        f"stretch:{qualified}",
                        "stretch",
                        qualified,
                        f"Stretch: a harder {concept.title} problem",
                        _minutes(20, c_pace, style),
                        reason="One problem a step above your level, as you asked.",
                        code="stretch",
                    )
                )
            if stuck is not None:
                why = stuck.summary
            elif c_reason:
                why = c_reason
            elif qualified in priority:
                why = "Moved up because you asked to focus on it."
            elif goals.tier(relevance[qualified]) == 2 and style != "thorough":
                why = "High value for your goal."
        if qualified in last_of_module:
            module = last_of_module[qualified]
            module_course, module_id = module.split(":", 1)
            members = seen_modules[module]
            needs = [
                m
                for m in members
                if not states.get(m, ConceptState()).mastered(now) and m not in aside
            ]
            check_id = f"checkpoint:{module}"
            gated_next = next((k for k, g in gate_targets.items() if g == check_id), None)
            if (
                needs
                and not all(states.get(m, ConceptState()).assumed for m in needs)
                and check_id not in completed
            ):
                title = next(
                    x.title for x in catalog.course(module_course).modules if x.id == module_id
                )
                if cooldowns.get(check_id, 0) > now:
                    # Failed recently: strengthen the weakest concepts before the retry opens.
                    weakest = sorted(
                        needs, key=lambda m: states.get(m, ConceptState()).effective(now)
                    )
                    for weak in weakest[:2]:
                        if f"review:{weak}" not in {a.id for a in queue}:
                            queue.append(
                                Activity(
                                    f"review:{weak}",
                                    "review",
                                    weak,
                                    f"Review: {catalog.concept(weak).title}",
                                    REVIEW_MINUTES,
                                    reason=f"Strengthen this before retrying the {title} checkpoint.",
                                    code="checkpoint_retry",
                                )
                            )
                else:
                    unlocks = (
                        f" Passing unlocks {gates_title(catalog, gated_next)}."
                        if gated_next
                        else ""
                    )
                    queue.append(
                        Activity(
                            check_id,
                            "checkpoint",
                            module,
                            f"Checkpoint: {title}",
                            CHECKPOINT_MINUTES,
                            reason="Questions get harder as you get them right." + unlocks,
                            code="checkpoint",
                        )
                    )
        roadmap.append({**entry_base, "status": status, **({"why": why} if why else {})})
    # A check that holds a module shut goes first; the rest wait their turn, a couple at a time.
    checks = sorted(
        (q for q in path if transfer.status.get(q) in {"due", "pending"} and q not in locked),
        key=lambda q: module_of(catalog, q) not in transfer.blocking,
    )[: transfers.MAX_QUEUED]
    for q in checks:
        blocked = module_of(catalog, q) in transfer.blocking
        unfinished = transfer.status[q] == "pending"
        if unfinished:
            reason = "You named the technique; now solve the problem on your own."
        elif blocked:
            reason = "The next module opens once you show a skill here works on new problems."
        else:
            reason = "Show you can use it on a problem you have never seen."
        (front if blocked else queue).append(
            Activity(
                transfers.activity_id(q),
                "transfer",
                q,
                f"{'Finish' if unfinished else 'Prove it'}: {catalog.concept(q).title}",
                TRANSFER_MINUTES,
                reason=reason,
                code="transfer",
            )
        )
    queue = front + queue
    if skipped:
        reasons.append(
            f"Placement suggests you know {skipped} concept(s); each gets a short confirmation "
            "check before it counts."
        )
    if aside:
        reasons.append(f"{len(aside)} concept(s) set aside as optional for your goal.")
    if locked:
        first_gate = next(iter(locked.values()))
        first = first_gate.removeprefix("checkpoint:")
        if first in transfer.blocking:
            reasons.append(
                f"Later modules unlock once you prove a {gates_title(catalog, first)} skill "
                "on problems you have not seen."
            )
        else:
            reasons.append(
                f"Later modules unlock as you pass checkpoints — next up: "
                f"{gates_title(catalog, first)} checkpoint."
            )
    queued_reviews = {a.concept for a in queue if a.kind in {"review", "testout"}}
    reviews = sorted(
        (states[q].next_review_at, q)
        for q in path
        if q in states
        and states[q].next_review_at
        and q not in queued_reviews
        and q not in {a.concept for a in queue[:3]}
        # Only what was actually taught or proven gets reviewed.
        and (f"lesson:{q}" in completed or states[q].mastered(now))
    )
    days: list[dict] = []
    pending_queue = list(queue)
    for day in study_days(today, weekdays, HORIZON_DAYS):
        end = now + (day - today).days * DAY  # due by this time that day, never a day early
        budget = minutes_per_day
        items: list[dict] = []
        due = [q for at, q in reviews if at <= end][:MAX_REVIEWS_PER_DAY]
        for q in due:
            reviews = [(at, c) for at, c in reviews if c != q]
            items.append(
                Activity(
                    f"review:{q}",
                    "review",
                    q,
                    f"Review: {catalog.concept(q).title}",
                    REVIEW_MINUTES,
                    reason=(
                        "You missed this last time; a short refresher keeps it from slipping."
                        if states[q].failures
                        else "Spaced review keeps it from fading."
                    ),
                    code="review_due",
                ).to_dict()
            )
            budget -= REVIEW_MINUTES
        while pending_queue and (budget >= pending_queue[0].minutes * 0.6 or not items):
            activity = pending_queue.pop(0)
            items.append(activity.to_dict())
            budget -= activity.minutes
        days.append({"date": day.isoformat(), "items": items, "minutes": minutes_per_day - budget})
        if not pending_queue and not reviews:
            break
    remaining = sum(a.minutes for a in queue) + locked_minutes
    weekly = minutes_per_day * len(weekdays)
    finish = finish_date(today, remaining, weekly)
    realistic_weekly = weekly * adaptive.adherence
    realistic = finish_date(today, remaining, realistic_weekly)
    target = adaptive.goal.get("target_date")
    forecast = dict(
        planned_finish=finish.isoformat(),
        realistic_finish=realistic.isoformat(),
        adherence=adaptive.adherence,
        weekly_minutes=round(realistic_weekly),
        target_date=target,
        on_track=None if not target else realistic.isoformat() <= target,
    )
    milestones = milestone_weeks(catalog, queue, roadmap, today, realistic_weekly)
    return Plan(
        pace,
        pace_reason,
        roadmap,
        queue,
        days,
        remaining,
        finish.isoformat(),
        reasons,
        style=style,
        focus=focus,
        milestones=milestones,
        forecast=forecast,
        needs_repair=needs_repair,
        held=transfer.blocking,
    )


def finish_date(today: date, remaining: int, weekly: float) -> date:
    weeks = remaining / weekly if weekly else 0
    return today + timedelta(days=math.ceil(weeks * 7))


def milestone_weeks(
    catalog: Catalog, queue: list[Activity], roadmap: list[dict], today: date, weekly: float
) -> list[dict]:
    """Week-by-week goals (B3): which concepts each week should finish, and what that unlocks."""
    if weekly <= 0:
        return []
    finish_at: dict[str, float] = {}
    spent = 0.0
    for activity in queue:
        spent += activity.minutes
        if activity.concept in catalog.concepts:
            finish_at[activity.concept] = spent
    for item in roadmap:
        if item["status"] in {"locked", "preparing"}:
            spent += item["minutes"]
            finish_at[item["concept"]] = spent
    weeks: dict[int, list[str]] = {}
    for concept, minutes in finish_at.items():
        weeks.setdefault(int(minutes // weekly), []).append(concept)
    out = []
    for week in sorted(weeks)[:MILESTONE_WEEKS]:
        concepts = weeks[week]
        lead = catalog.concept(concepts[-1])
        out.append(
            dict(
                week=week + 1,
                ends=(today + timedelta(days=7 * (week + 1) - 1)).isoformat(),
                concepts=[dict(concept=c, title=catalog.concept(c).title) for c in concepts],
                # Planned concepts have no key points yet; their summary stands in.
                outcome=f"You'll be able to: {(lead.key_points or [lead.summary])[0].rstrip('.')}.",
            )
        )
    return out


def gates_title(catalog: Catalog, module_key: str) -> str:
    return module_title(catalog, module_key)


def module_of(catalog: Catalog, qualified: str) -> str:
    return f"{catalog.owner[qualified]}:{catalog.module_of(qualified)}"
