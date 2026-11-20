"""Tools the tutor can call to personalise a reply. Every tool is scoped to one learner.

Tools read the learner's own data. The few that write never change
the roadmap directly: `propose_plan_change` and `propose_goal` only create *pending*
proposals the learner accepts or declines on screen, `record_observation` can only flag a
gap (it never raises mastery). None of them return
hidden tutor notes or reference solutions for graded problems.
"""

import asyncio
import json
import re

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from socrat import harness
from socrat.adaptive import proposals as plan_proposals
from socrat.adaptive import service as adaptive
from socrat.adaptive.suggest import Draft
from socrat.assessments import service as assessments
from socrat.assistant.gateway import ToolSpec
from socrat.catalog.registry import Catalog
from socrat.learn import service as learn
from socrat.mastery.model import DAY, ConceptState, band
from socrat.models import Evidence, Submission, User, WeeklyAssessment
from socrat.models import now as clock

# Learner-facing wording for mastery bands, so replies never echo internal codes.
BAND_WORDS = {
    "not_started": "not started yet",
    "needs_practice": "needs practice",
    "developing": "developing",
    "likely_known": "likely known (not yet confirmed)",
    "strong": "strong",
}
CONCEPT = {
    "type": "string",
    "description": "Concept id like 'course-id:concept-id', or its name as the learner says it.",
}

TOOLS: list[ToolSpec] = [
    ToolSpec(
        "get_progress",
        "The learner's mastery per concept in their course: band (not started yet, needs "
        "practice, developing, likely known, strong), evidence count, recent misses and review "
        "timing, "
        "plus their overall practice level. Use for 'how am I doing', 'what am I weak at', or "
        "before advising what to study.",
        {
            "type": "object",
            "properties": {
                "concept": {**CONCEPT, "description": "Optional: only this concept."},
                "only_weak": {"type": "boolean", "description": "Only concepts that need work."},
            },
            "required": [],
        },
    ),
    ToolSpec(
        "get_plan",
        "The learner's personalised study schedule for the coming days, pace, projected finish "
        "date and the latest reasons the plan changed.",
        {
            "type": "object",
            "properties": {"days": {"type": "integer", "description": "Days ahead, 1-14."}},
            "required": [],
        },
    ),
    ToolSpec(
        "get_recent_work",
        "The learner's recent graded work: quiz and checkpoint scores, code submissions with "
        "verdicts, and problems they marked solved elsewhere. Use 'days' to cover a week.",
        {
            "type": "object",
            "properties": {"days": {"type": "integer", "description": "Look back, 1-30 days."}},
            "required": [],
        },
    ),
    ToolSpec(
        "get_concept_guide",
        "A concept's summary, key points, common pitfalls, curated reading (with links), "
        "and Socrat's own practice problems, plus the learner's band on it.",
        {"type": "object", "properties": {"concept": CONCEPT}, "required": ["concept"]},
    ),
    ToolSpec(
        "get_weekly_report",
        "The learner's latest weekly assessment: score, per-topic results, strengths, topics "
        "to focus on, and whether this week's assessment is available. Use when they ask how "
        "their week went or what to focus on next.",
        {"type": "object", "properties": {}, "required": []},
    ),
]
PROPOSAL_KINDS = [
    "prioritize",
    "defer",
    "repair",
    "probe",
    "test_out",
    "skip",
    "budget",
    "stretch",
    "path_style",
]
TOOLS += [
    ToolSpec(
        "get_learner_profile",
        "The full adaptive picture: practice level, concepts where the learner is stuck (with "
        "why and the likely cause), trends, recurring mistakes, hint dependence, speed versus "
        "plan, deadline forecast and roadmap changes waiting for their decision. Use before "
        "advising on their plan, and whenever they seem stuck or say it's going well.",
        {"type": "object", "properties": {}, "required": []},
    ),
    ToolSpec(
        "propose_plan_change",
        "Propose a change to the learner's roadmap. This changes NOTHING by itself: the learner "
        "sees Accept and Decline buttons under your reply and decides. Use it when the evidence "
        "supports a change (stuck, cruising, behind their date) or they ask for one. Kinds: "
        "prioritize (move a concept up), defer (set a concept aside for later), repair "
        "(refresh prerequisite `concept` before `for_concept`), probe (a quick check of a "
        "concept's foundations), test_out (prove a concept and skip it), skip (drop an optional "
        "concept), budget (minutes_per_day and/or weekdays), stretch (a weekly harder problem), "
        "path_style (thorough, balanced, fast_track or goal_focused).",
        {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": PROPOSAL_KINDS},
                "concept": CONCEPT,
                "for_concept": {**CONCEPT, "description": "repair only: the concept it unblocks."},
                "minutes_per_day": {"type": "integer", "enum": [15, 20, 30, 45, 60, 90, 120]},
                "weekdays": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "0 = Monday ... 6 = Sunday.",
                },
                "style": {
                    "type": "string",
                    "enum": ["thorough", "balanced", "fast_track", "goal_focused"],
                },
                "title": {"type": "string", "description": "Short, e.g. 'Refresh loops first'."},
                "reason": {
                    "type": "string",
                    "description": "One or two sentences to the learner: why this helps.",
                },
            },
            "required": ["kind", "title", "reason"],
        },
    ),
    ToolSpec(
        "propose_goal",
        "In a planning conversation, propose the learner's structured goal: role, target date, "
        "contest rating, up to three focus concepts and motivation. Like every plan change it "
        "is only a proposal the learner confirms on screen.",
        {
            "type": "object",
            "properties": {
                "target_role": {
                    "type": "string",
                    "enum": ["internship", "new-grad", "mid-level", "senior"],
                },
                "target_date": {
                    "type": "string",
                    "description": "YYYY-MM-DD, only if the learner gave one.",
                },
                "target_rating": {"type": "integer"},
                "focus": {"type": "array", "items": CONCEPT},
                "motivation": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["reason"],
        },
    ),
    ToolSpec(
        "record_observation",
        "Note a gap you saw in conversation (shaky or missing understanding of a concept) so "
        "the planner can adapt. It can only lower confidence a little and never marks anything "
        "as learned. Do not use it for things the learner got right.",
        {
            "type": "object",
            "properties": {
                "concept": CONCEPT,
                "understanding": {"type": "string", "enum": ["shaky", "missing"]},
                "note": {"type": "string", "description": "What you saw, in a few words."},
                "misconception": {
                    "type": "string",
                    "description": "Optional: the id of the misconception you saw, only one "
                    "listed for this concept in your context. Anything else is ignored.",
                },
            },
            "required": ["concept", "understanding", "note"],
        },
    ),
]
# Offered only when SOCRAT_LEARNER_PROFILE is on (socrat.learner_profile).
PROFILE_TOOLS: list[ToolSpec] = [
    ToolSpec(
        "suggest_preference",
        "Suggest a change to how the learner is taught in every course, when the conversation "
        "shows it (they keep asking for shorter answers, an example domain clicks). This changes "
        "NOTHING by itself: the learner accepts or declines it in their profile. Keys: "
        "explanation_length (short_3_sentences, medium_one_page, long_worked_examples), tone "
        "(direct, direct_and_encouraging, curious_and_thorough), analogy_domain (a few words), "
        "pace (fast, medium, slow), friction_limit (1-6 tries before you step in).",
        {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "enum": [
                        "explanation_length",
                        "tone",
                        "analogy_domain",
                        "pace",
                        "friction_limit",
                    ],
                },
                "value": {"type": ["string", "integer"]},
                "reason": {"type": "string", "description": "One sentence to the learner: why."},
            },
            "required": ["key", "value", "reason"],
        },
    ),
]
WRITE_TOOLS = {"propose_plan_change", "propose_goal"}  # the UI shows their proposal cards
OBSERVATIONS_PER_DAY = 3
LABELS = {
    "get_progress": "Checking your progress",
    "get_plan": "Looking at your plan",
    "get_recent_work": "Reviewing your recent work",
    "get_concept_guide": "Opening the lesson notes",
    "get_weekly_report": "Reading your weekly assessment",
    "get_learner_profile": "Looking at how you're progressing",
    "propose_plan_change": "Suggesting a change to your plan",
    "propose_goal": "Drafting your goal",
    "record_observation": "Noting that for your plan",
    "suggest_preference": "Suggesting a change to how you're taught",
    "math_check": "Checking the math",
}


def _clamp(value, low: int, high: int, default: int) -> int:
    return max(low, min(high, int(value))) if isinstance(value, int) else default


def lesson_link(catalog: Catalog, concept: str) -> str:
    return f"[{catalog.concept(concept).title}](/learn/{concept.replace(':', '/')})"


def resolve_concept(catalog: Catalog, value: str) -> str | None:
    value = value.strip().lower()
    if value in catalog.concepts:
        return value
    words = re.sub(r"[^a-z0-9]+", " ", value).strip()
    best = None
    for qualified, concept in catalog.concepts.items():
        title = re.sub(r"[^a-z0-9]+", " ", concept.title.lower()).strip()
        slug = qualified.split(":", 1)[1].replace("-", " ")
        if words in (title, slug):
            return qualified
        if words and (words in title or words in slug) and best is None:
            best = qualified
    return best


class Toolbox:
    def __init__(
        self,
        bind: Engine,
        catalog: Catalog,
        user_id: str,
        engine_tools: bool = False,
        profile_tools: bool = False,
    ):
        self.bind = bind
        self.catalog = catalog
        self.user_id = user_id
        self.profile_tools = profile_tools
        # The harness's verified capabilities (admins only while the engine is tested).
        self.verified = (
            {c.tool_name: c for c in harness.capabilities().values() if c.tutor}
            if engine_tools
            else {}
        )
        self.specs = [*TOOLS, *(PROFILE_TOOLS if profile_tools else [])] + [
            ToolSpec(c.tool_name, c.summary, c.parameters) for c in self.verified.values()
        ]

    async def run(self, name: str, arguments: dict) -> tuple[str, bool]:
        if name in self.verified:
            result = await asyncio.to_thread(harness.call, self.verified[name].name, arguments)
            if not result.ok:
                return f"Error: {result.error}", True
            return json.dumps(result.output, ensure_ascii=False, separators=(",", ":")), False
        return await asyncio.to_thread(self._run, name, arguments)

    def _run(self, name: str, arguments: dict) -> tuple[str, bool]:
        handler = getattr(self, f"_{name}", None)
        if handler is None:
            return f"Unknown tool {name!r}.", True
        with Session(self.bind) as db, db.begin():
            user = db.get(User, self.user_id)
            if user is None:
                return "Learner not found.", True
            enrollment = learn.active_enrollment(db, user.id)
            result = handler(db, user, enrollment, clock(), **arguments)
        if isinstance(result, str):
            return result, result.startswith("Error:")
        return json.dumps(result, ensure_ascii=False, separators=(",", ":")), False

    # ------------------------------------------------------------ helpers

    # ------------------------------------------------------------ tools

    def _get_progress(self, db, user, enrollment, now, concept: str = "", only_weak: bool = False):
        if enrollment is None:
            return "Error: the learner has not chosen a course yet."
        states = learn.states_for(db, enrollment)
        if concept:
            resolved = resolve_concept(self.catalog, concept)
            if resolved is None:
                return f"Error: no concept matches {concept!r}."
            if resolved not in learn.curriculum(self.catalog, enrollment):
                return "Error: that topic is outside your current course."
            targets = [resolved]
        else:
            targets = self.catalog.closure(self.catalog.course_concepts(enrollment.course_id))
        rows = []
        for qualified in targets:
            state = states.get(qualified, ConceptState())
            label = band(state, now)
            if only_weak and label not in {"needs_practice", "developing"}:
                continue
            rows.append(
                {
                    "concept": qualified,
                    "lesson": lesson_link(self.catalog, qualified),
                    "band": BAND_WORDS[label],
                    "evidence": state.evidence_count,
                    "misses": state.failures,
                    **(
                        {"review_in_days": round((state.next_review_at - now) / DAY, 1)}
                        if state.next_review_at
                        else {}
                    ),
                }
            )
        return {
            "course": self.catalog.course(enrollment.course_id).title,
            "concepts": rows,
        }

    def _get_plan(self, db, user, enrollment, now, days: int = 7):
        if enrollment is None:
            return "Error: the learner has not chosen a course yet."
        plan = learn.plan_for(db, self.catalog, user, enrollment, now, record=False)
        days = _clamp(days, 1, 14, 7)
        return {
            "pace": plan.pace,
            "pace_reason": plan.pace_reason,
            "projected_finish": plan.projected_finish,
            "minutes_per_day": enrollment.minutes_per_day,
            "days": [
                {"date": d["date"], "items": [f"{i['kind']}: {i['title']}" for i in d["items"]]}
                for d in plan.days[:days]
            ],
            "recent_changes": [
                r for rev in learn.latest_revisions(db, enrollment, 3) for r in rev["reasons"]
            ][:5],
        }

    def _get_recent_work(self, db, user, enrollment, now, days: int = 7):
        since = now - _clamp(days, 1, 30, 7) * DAY
        out: dict = {"since_days": (now - since) // DAY}
        if enrollment is not None:
            evidence = db.scalars(
                select(Evidence)
                .where(Evidence.enrollment_id == enrollment.id, Evidence.created_at >= since)
                .order_by(Evidence.created_at.desc())
                .limit(30)
            )
            out["scored"] = [
                {
                    "kind": e.kind,
                    "concept": self.catalog.concept(e.concept).title
                    if e.concept in self.catalog.concepts
                    else e.concept,
                    "score": round(e.score, 2),
                    "help_level": e.assistance or None,
                    "days_ago": round((now - e.created_at) / DAY, 1),
                }
                for e in evidence
            ]
        submissions = db.scalars(
            select(Submission)
            .where(
                Submission.user_id == user.id,
                Submission.mode == "submit",
                Submission.created_at >= since,
            )
            .order_by(Submission.created_at.desc())
            .limit(15)
        )
        out["submissions"] = [
            {
                "problem": self.catalog.problem(s.problem_id).title
                if s.problem_id in self.catalog.problems
                else s.problem_id,
                "verdict": s.verdict or s.status,
                "passed": f"{s.passed}/{s.total}",
                "language": s.language,
            }
            for s in submissions
        ]
        return out

    def _get_concept_guide(self, db, user, enrollment, now, concept: str):
        resolved = resolve_concept(self.catalog, concept)
        if resolved is None:
            return f"Error: no concept matches {concept!r}."
        if resolved not in learn.curriculum(self.catalog, enrollment):
            return "Error: that topic is outside your current course."
        learn.require_unlocked(db, self.catalog, enrollment, resolved, now)
        c = self.catalog.concept(resolved)
        states = learn.states_for(db, enrollment) if enrollment else {}
        language = enrollment.language if enrollment else "python"
        return {
            "concept": resolved,
            "lesson": lesson_link(self.catalog, resolved),
            "summary": c.summary,
            "key_points": c.key_points,
            "pitfalls": c.pitfalls,
            "learner_band": BAND_WORDS[band(states.get(resolved, ConceptState()), now)],
            "prerequisites": [
                self.catalog.concept(p).title for p in self.catalog.prerequisites[resolved]
            ],
            "reading": [
                f"[{r.title}]({r.url}) — {r.source}, {r.minutes} min"
                for r in c.resources
                if not r.languages or language in r.languages
            ][:5],
            "socrat_problems": [
                f"[{self.catalog.problem(p).title}](/problems/{p}) ({self.catalog.problem(p).difficulty})"
                for p in c.problems
            ],
        }

    def _get_weekly_report(self, db, user, enrollment, now):
        if enrollment is None:
            return "Error: the learner has not chosen a course yet."
        current = assessments.status(db, self.catalog, user, enrollment, now)
        latest = assessments.history(db, enrollment, limit=2)
        report = None
        if latest:
            row = db.get(WeeklyAssessment, latest[0]["id"])
            if row is not None:
                report = {
                    "week": row.iso_week,
                    "score": row.score,
                    "strengths": row.report.get("strengths", []),
                    "focus": [
                        lesson_link(self.catalog, f["id"]) for f in row.report.get("focus", [])
                    ],
                    "previous_score": row.report.get("previous_score"),
                }
        return {
            "this_week": {
                "state": current["state"],
                "topics": current["topics"],
                "where": "[Weekly assessment](/assessments)",
            },
            "latest_report": report or "No finished assessments yet.",
        }

    # ------------------------------------------------------------ adaptive

    def _get_learner_profile(self, db, user, enrollment, now):
        if enrollment is None or enrollment.status != "active":
            return "Error: the learner has no active plan yet."
        states = learn.states_for(db, enrollment)
        skill = adaptive.build_profiles(db, self.catalog, enrollment, states, now)
        stuck = adaptive.stuck_map(skill, now)
        plan = learn.plan_for(db, self.catalog, user, enrollment, now, record=False)
        active = sorted((p for p in skill.values() if p.attempts), key=lambda p: -p.last_seen_at)
        return {
            "level": adaptive.level_for(db, enrollment),
            "stuck": [
                {
                    "concept": lesson_link(self.catalog, c),
                    "why": s.summary,
                    "cause": s.failure_mode,
                    "severity": s.severity,
                }
                for c, s in stuck.items()
            ],
            "recent_concepts": [
                {
                    "concept": self.catalog.concept(p.concept).title,
                    "band": BAND_WORDS[p.band],
                    "trend": p.trend,
                    "hint_dependence": p.hint_dependence,
                    "speed_vs_plan": p.speed,
                    "recurring_mistakes": list(p.misconceptions),
                }
                for p in active[:10]
            ],
            "pace": plan.pace,
            "path_style": plan.style,
            "forecast": plan.forecast,
            "next_milestone": plan.milestones[0] if plan.milestones else None,
            "pending_changes": [
                {"title": p.title, "kind": p.kind} for p in plan_proposals.pending(db, enrollment)
            ],
        }

    def _in_course(self, enrollment, value: str) -> str | None:
        resolved = resolve_concept(self.catalog, value) if value else None
        if resolved and resolved in learn.curriculum(self.catalog, enrollment):
            return resolved
        return None

    def _propose(self, db, enrollment, now, kind, title, reason, payload):
        try:
            payload = plan_proposals.validate(self.catalog, enrollment, kind, payload)
        except Exception:
            return "Error: that change doesn't fit this learner's course; check the concept."
        key = f"tutor:{kind}:{json.dumps(payload, sort_keys=True)}"[:240]
        draft = Draft(kind, key, str(title)[:120], str(reason)[:600], payload)
        row = plan_proposals.add(db, enrollment, draft, "tutor", now)
        if row is None:
            return (
                "Not proposed: the same change is already waiting, was applied, or the learner "
                "declined it recently. Do not push it again."
            )
        return {
            "proposal": draft.title,
            "status": "pending: the learner sees Accept and Decline under your reply",
            "instruction": "Say what you suggest and why, and that it is their call. "
            "Never say it is done.",
        }

    def _propose_plan_change(
        self,
        db,
        user,
        enrollment,
        now,
        kind: str,
        title: str,
        reason: str,
        concept: str = "",
        for_concept: str = "",
        minutes_per_day: int | None = None,
        weekdays: list | None = None,
        style: str = "",
    ):
        if enrollment is None or enrollment.status != "active":
            return "Error: the learner has no active plan yet."
        if kind not in PROPOSAL_KINDS:
            return f"Error: unknown kind {kind!r}."
        target = self._in_course(enrollment, concept)
        options: dict[str, dict] = {
            "prioritize": {"concept": target},
            "defer": {"concept": target},
            "probe": {"concept": target},
            "repair": {"concept": target, "for": self._in_course(enrollment, for_concept)},
            "test_out": {"target": target},
            "skip": {"concepts": [target] if target else []},
            "budget": {"minutes_per_day": minutes_per_day, "weekdays": weekdays},
            "path_style": {"style": style},
            "stretch": {},
        }
        payload = options[kind]
        return self._propose(db, enrollment, now, kind, title, reason, payload)

    def _propose_goal(self, db, user, enrollment, now, reason: str = "", **fields):
        if enrollment is None:
            return "Error: the learner has not chosen a course yet."
        focus = [self._in_course(enrollment, str(c)) for c in fields.pop("focus", []) or []]
        payload = {**fields, "focus": [c for c in focus if c]}
        return self._propose(db, enrollment, now, "goal", "Set your goal", reason, payload)

    def _record_observation(
        self,
        db,
        user,
        enrollment,
        now,
        concept: str,
        understanding: str,
        note: str,
        misconception: str = "",
    ):
        if enrollment is None or enrollment.status != "active":
            return "Error: the learner has no active plan yet."
        resolved = self._in_course(enrollment, concept)
        if resolved is None:
            return f"Error: no concept in their course matches {concept!r}."
        recent = db.scalar(
            select(func.count())
            .select_from(Evidence)
            .where(
                Evidence.enrollment_id == enrollment.id,
                Evidence.concept == resolved,
                Evidence.kind == "tutor",
                Evidence.created_at >= now - DAY,
            )
        )
        if (recent or 0) >= OBSERVATIONS_PER_DAY:
            return "Already noted enough about this concept today."
        from socrat import learner

        # A misconception id is kept only when it is a known one: the catalog's own list, or
        # one of the root units this generated lesson was written from (learner-memory.md).
        allowed = self.catalog.misconceptions | set(learner.misconceptions_for(db, resolved))
        tag = misconception if misconception in allowed else ""
        tag = tag or f"{resolved.split(':', 1)[1]}-repair"
        learn.record_evidence(
            db,
            enrollment,
            resolved,
            "tutor",
            0.5 if understanding == "shaky" else 0.0,
            "tutor:observation",
            now,
            details={
                "note": str(note)[:200],
                **({"misconception": tag} if tag in allowed else {}),
            },
        )
        return {"noted": self.catalog.concept(resolved).title, "understanding": understanding}

    def _suggest_preference(self, db, user, enrollment, now, key: str, value, reason: str):
        if not self.profile_tools:
            return "Error: unknown tool."
        from socrat import learner_profile

        try:
            item = learner_profile.suggest(user, key, value, reason, now)
        except ValueError:
            return "Error: that is not a preference value the learner can choose."
        return {
            "suggested": item["key"],
            "value": item["value"],
            "status": "waiting for the learner",
        }
