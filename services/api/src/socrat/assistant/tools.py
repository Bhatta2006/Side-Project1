"""Tools the tutor can call to personalise a reply. Every tool is scoped to one learner.

Tools read the learner's own data and the public library. The few that write never change
the roadmap directly: `propose_plan_change` and `propose_goal` only create *pending*
proposals the learner accepts or declines on screen, `record_observation` can only flag a
gap (it never raises mastery), and `save_problems` bookmarks problems. None of them return
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
from socrat.catalog import practice
from socrat.catalog.registry import Catalog
from socrat.learn import service as learn
from socrat.library import recommend
from socrat.library import service as library
from socrat.mastery.model import DAY, ConceptState, band
from socrat.models import Evidence, PracticeMark, Submission, User, WeeklyAssessment
from socrat.models import now as clock

PLATFORM = {"type": "string", "enum": ["Socrat", "LeetCode", "CSES", "Codeforces"]}
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
    "description": "Concept id like 'dsa:two-pointers', or its name like 'two pointers'.",
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
        "recommend_problems",
        "Personalised next problems, matched to the learner's level and mastery and skipping "
        "what they solved: Socrat's own problems (solved and judged in the app, where you can "
        "coach them) plus LeetCode, CSES and Codeforces. Each result has a ready Markdown link "
        "to show the learner.",
        {
            "type": "object",
            "properties": {
                "concept": {**CONCEPT, "description": "Optional: focus on one concept."},
                "count": {"type": "integer", "description": "1-8, default 4."},
                "platform": PLATFORM,
                "harder": {"type": "boolean", "description": "A step above their level."},
            },
            "required": [],
        },
    ),
    ToolSpec(
        "search_library",
        "Search the practice library by name, concept, platform, difficulty or rating range. "
        "Returns names, difficulty, rating, the learner's status and Markdown links.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Words in the problem name."},
                "concept": CONCEPT,
                "platform": PLATFORM,
                "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                "rating_min": {"type": "integer"},
                "rating_max": {"type": "integer"},
                "unsolved_only": {"type": "boolean"},
                "limit": {"type": "integer", "description": "1-10, default 6."},
            },
            "required": [],
        },
    ),
    ToolSpec(
        "next_topics",
        "What the learner should learn next and why, from their plan and mastery.",
        {"type": "object", "properties": {}, "required": []},
    ),
    ToolSpec(
        "get_concept_guide",
        "A concept's summary, key points, common pitfalls, curated reading (with links), "
        "handbook chapters and Socrat's own practice problems, plus the learner's band on it.",
        {"type": "object", "properties": {"concept": CONCEPT}, "required": ["concept"]},
    ),
    ToolSpec(
        "get_codeforces_profile",
        "The learner's linked Codeforces profile, if any: rating, rank, solved count and the "
        "tags where they most often fail.",
        {"type": "object", "properties": {}, "required": []},
    ),
    ToolSpec(
        "get_weekly_report",
        "The learner's latest weekly assessment: score, per-topic results, strengths, topics "
        "to focus on, and whether this week's assessment is available. Use when they ask how "
        "their week went or what to focus on next.",
        {"type": "object", "properties": {}, "required": []},
    ),
    ToolSpec(
        "save_problems",
        "Add library problems to the learner's practice list (bookmarked to-dos). Only call "
        "when the learner asks you to save or plan problems.",
        {
            "type": "object",
            "properties": {
                "problem_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ids from recommend_problems or search_library, at most 8.",
                }
            },
            "required": ["problem_ids"],
        },
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
            },
            "required": ["concept", "understanding", "note"],
        },
    ),
]
WRITE_TOOLS = {"propose_plan_change", "propose_goal"}  # the UI shows their proposal cards
OBSERVATIONS_PER_DAY = 3
LABELS = {
    "get_progress": "Checking your progress",
    "get_plan": "Looking at your plan",
    "get_recent_work": "Reviewing your recent work",
    "recommend_problems": "Picking problems for you",
    "search_library": "Searching the library",
    "next_topics": "Working out what's next",
    "get_concept_guide": "Opening the lesson notes",
    "get_codeforces_profile": "Checking your Codeforces profile",
    "save_problems": "Saving to your list",
    "get_weekly_report": "Reading your weekly assessment",
    "get_learner_profile": "Looking at how you're progressing",
    "propose_plan_change": "Suggesting a change to your plan",
    "propose_goal": "Drafting your goal",
    "record_observation": "Noting that for your plan",
    "math_check": "Checking the math",
}


def _clamp(value, low: int, high: int, default: int) -> int:
    return max(low, min(high, int(value))) if isinstance(value, int) else default


def link(problem: dict) -> str:
    return f"[{problem['title']}]({problem['url']})"


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
    def __init__(self, bind: Engine, catalog: Catalog, user_id: str, engine_tools: bool = False):
        self.bind = bind
        self.catalog = catalog
        self.user_id = user_id
        # The harness's verified capabilities (admins only while the engine is tested).
        self.verified = (
            {c.tool_name: c for c in harness.capabilities().values() if c.tutor}
            if engine_tools
            else {}
        )
        self.specs = TOOLS + [
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

    def _learner(self, db, user, enrollment, now) -> recommend.Learner:
        return library.learner_for(db, self.catalog, user, enrollment, now)

    def _problem_row(self, learner: recommend.Learner, problem: dict, **extra) -> dict:
        primary = problem["concepts"][0] if problem["concepts"] else None
        solved = problem["id"] in learner.solved or (
            problem["id"].removeprefix("socrat:") in learner.native_solved
        )
        row = dict(
            id=problem["id"],
            link=link(problem),
            platform=problem["platform"],
            difficulty=problem["difficulty"],
            rating=problem.get("rating"),
            concept=self.catalog.concept(primary).title
            if primary in self.catalog.concepts
            else None,
            solved=solved,
        )
        return {k: v for k, v in {**row, **extra}.items() if v not in (None, "")}

    # ------------------------------------------------------------ tools

    def _get_progress(self, db, user, enrollment, now, concept: str = "", only_weak: bool = False):
        if enrollment is None:
            return "Error: the learner has not chosen a course yet."
        learner = self._learner(db, user, enrollment, now)
        states = learner.states
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
        level = recommend.level_view(learner.rating)
        return {
            "course": self.catalog.course(enrollment.course_id).title,
            "practice_level": f"{level['name']} (~{level['rating']})",
            "solved_elsewhere": len(learner.solved),
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
        index = practice.default_index()
        marks = db.scalars(
            select(PracticeMark)
            .where(PracticeMark.user_id == user.id, PracticeMark.updated_at >= since)
            .order_by(PracticeMark.updated_at.desc())
            .limit(15)
        )
        out["external"] = [
            {"problem": index.problems[m.problem_id]["title"], "status": m.status}
            for m in marks
            if m.problem_id in index.problems
        ]
        return out

    def _recommend_problems(
        self,
        db,
        user,
        enrollment,
        now,
        concept: str = "",
        count: int = 4,
        platform: str = "",
        harder: bool = False,
    ):
        index = practice.default_index()
        learner = self._learner(db, user, enrollment, now)
        count = _clamp(count, 1, 8, 4)
        if concept:
            resolved = resolve_concept(self.catalog, concept)
            if resolved is None:
                return f"Error: no concept matches {concept!r}."
            native = [] if harder else recommend.native_for(self.catalog, learner, resolved)[:2]
            external = recommend.best_for(index, learner, resolved, count * 4, stretch=harder)
            picks = native + external
            if platform:
                picks = [p for p in picks if p["platform"] == platform]
            reason = (
                "a step above your level"
                if harder
                else f"fits where you are ({BAND_WORDS[learner.band(resolved)]})"
            )
            rows = [self._problem_row(learner, p, why=reason) for p in picks[:count]]
        else:
            plan = (
                learn.plan_for(db, self.catalog, user, enrollment, now, record=False)
                if enrollment
                else None
            )
            picks = recommend.next_problems(index, self.catalog, learner, plan, limit=count * 3)
            if platform:
                picks = [p for p in picks if p["platform"] == platform]
            if harder:
                picks = [p for p in picks if p["kind"] == "stretch"] or picks
            rows = [self._problem_row(learner, p, why=p["reason"]) for p in picks[:count]]
        if not rows:
            return "No unsolved matches; try another concept or platform."
        return {"practice_level": learner.rating, "problems": rows}

    def _search_library(
        self,
        db,
        user,
        enrollment,
        now,
        query: str = "",
        concept: str = "",
        platform: str = "",
        difficulty: str = "",
        rating_min: int = 0,
        rating_max: int = 0,
        unsolved_only: bool = False,
        limit: int = 6,
    ):
        index = practice.default_index()
        learner = self._learner(db, user, enrollment, now)
        resolved = resolve_concept(self.catalog, concept) if concept else ""
        if concept and resolved is None:
            return f"Error: no concept matches {concept!r}."
        items = index.search(
            query[:80],
            (platform,) if platform else (),
            resolved or "",
            difficulty,
            rating_min,
            rating_max,
        )
        items = [p for p in items if learner.can_practice(p)]
        if unsolved_only:
            items = [p for p in items if p["id"] not in learner.solved]
        items.sort(key=lambda p: (-p.get("companies", 0), -p.get("solvers", 0), p["id"]))
        limit = _clamp(limit, 1, 10, 6)
        return {
            "total": len(items),
            "problems": [self._problem_row(learner, p) for p in items[:limit]],
        }

    def _next_topics(self, db, user, enrollment, now):
        learner = self._learner(db, user, enrollment, now)
        plan = (
            learn.plan_for(db, self.catalog, user, enrollment, now, record=False)
            if enrollment
            else None
        )
        topics = recommend.next_topics(self.catalog, learner, plan, limit=4)
        return {
            "topics": [
                {
                    "lesson": lesson_link(self.catalog, t["id"]),
                    "why": t["reason"],
                    "band": BAND_WORDS[t["band"]],
                    "minutes": t["minutes"],
                }
                for t in topics
            ]
        }

    def _get_concept_guide(self, db, user, enrollment, now, concept: str):
        resolved = resolve_concept(self.catalog, concept)
        if resolved is None:
            return f"Error: no concept matches {concept!r}."
        if resolved not in learn.curriculum(self.catalog, enrollment):
            return "Error: that topic is outside your current course."
        learn.require_unlocked(db, self.catalog, enrollment, resolved, now)
        c = self.catalog.concept(resolved)
        index = practice.default_index()
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
            "handbook": [
                f"[§{h['chapter']} {h['title']}]({h['url']})" for h in index.book_for(resolved)
            ],
            "socrat_problems": [
                f"[{self.catalog.problem(p).title}](/problems/{p}) ({self.catalog.problem(p).difficulty})"
                for p in c.problems
            ],
        }

    def _get_codeforces_profile(self, db, user, enrollment, now):
        view = library.account_view(library.account_for(db, user.id))
        if view is None:
            return "The learner has not linked a Codeforces handle (they can in Settings)."
        view.pop("sync_error", None)
        synced = view.pop("synced_at", None)
        if synced:
            view["synced_days_ago"] = round((now - synced) / DAY, 1)
        return view

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

    def _save_problems(self, db, user, enrollment, now, problem_ids: list):
        index = practice.default_index()
        saved = []
        for problem_id in [str(p) for p in problem_ids][:8]:
            if problem_id in index.problems:
                library.mark(db, self.catalog, user, problem_id, now, bookmarked=True)
                saved.append(index.problems[problem_id]["title"])
        if not saved:
            return "Error: none of those ids are in the library."
        return {"saved": saved, "where": "[your practice list](/library?status=bookmarked)"}

    # ------------------------------------------------------------ adaptive

    def _get_learner_profile(self, db, user, enrollment, now):
        if enrollment is None or enrollment.status != "active":
            return "Error: the learner has no active plan yet."
        states = learn.states_for(db, enrollment)
        skill = adaptive.build_profiles(db, self.catalog, enrollment, states, now)
        stuck = adaptive.stuck_map(skill, now)
        plan = learn.plan_for(db, self.catalog, user, enrollment, now, record=False)
        learner = self._learner(db, user, enrollment, now)
        active = sorted((p for p in skill.values() if p.attempts), key=lambda p: -p.last_seen_at)
        return {
            "level": adaptive.level_for(db, user.id, learner.rating, enrollment),
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
        self, db, user, enrollment, now, concept: str, understanding: str, note: str
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
        tag = f"{resolved.split(':', 1)[1]}-repair"
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
                **({"misconception": tag} if tag in self.catalog.misconceptions else {}),
            },
        )
        return {"noted": self.catalog.concept(resolved).title, "understanding": understanding}
