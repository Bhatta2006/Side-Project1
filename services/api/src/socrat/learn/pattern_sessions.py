"""Database side of the pattern planner (behind ``pattern_planner_enabled``).

Builds a ``PatternView`` per pilot pattern from the learner's evidence, abilities, solved
problems and adaptive-quiz steps, ranks them with ``planner.patterns``, and lays out the
session. Returns None whenever no valid plan exists, so the caller keeps the existing
composer: the flag can only add pattern sessions, never take a session away.
"""

import math
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog import practice
from socrat.catalog.registry import Catalog
from socrat.mastery.model import DAY, ConceptState
from socrat.models import (
    Enrollment,
    LearnerAbility,
    LearningSession,
    QuizEngineSession,
    QuizResponse,
)
from socrat.planner import patterns as planner
from socrat.quiz.config import COURSE_TRACK
from socrat.quiz.config import DEFAULT as QUIZ
from socrat.quiz.rating import p_correct

CONTRASTS_FILE = "contrasts.yaml"


@dataclass(frozen=True)
class Plan:
    pattern: str
    concept: str
    kind: planner.SessionType
    fired: list[planner.Trigger]
    blocks: list[dict]
    scores: list[planner.Score]


@lru_cache(maxsize=4)
def contrasts(path: str) -> dict[str, dict]:
    file = Path(path)
    return yaml.safe_load(file.read_text(encoding="utf-8")) if file.exists() else {}


def relevance(catalog: Catalog, track: str) -> dict[str, float]:
    """Track relevance per pattern, scaled to 0..1 across the pilot patterns."""
    raw: dict[str, float] = {}
    if track == "foundations":
        order = {concept: i for i, concept in enumerate(catalog.order)}
        for pid, pattern in catalog.patterns.items():
            raw[pid] = len(order) - order.get(pattern.concept, len(order))
    else:
        index = practice.default_index().problems
        for pid, pattern in catalog.patterns.items():
            linked = [index[p] for p in pattern.problems.external if p in index]
            if track == "interview":
                raw[pid] = sum(math.log1p(p.get("companies", 0)) for p in linked)
            else:  # competitive: contest problems, weighted by how many people solve them
                raw[pid] = sum(
                    math.log1p(p.get("solvers", 0))
                    for p in linked
                    if p["id"].startswith(("cf:", "cses:"))
                ) + len(pattern.problems.native)
    top = max(raw.values(), default=0) or 1
    return {pid: value / top for pid, value in raw.items()}


def views(
    db: Session,
    catalog: Catalog,
    enrollment: Enrollment,
    states: dict[str, ConceptState],
    locked: dict[str, str],
    curriculum: set[str],
    solved: set[str],
    now: int,
    w: planner.Weights = planner.DEFAULT,
) -> list[planner.PatternView]:
    track = (enrollment.goal or {}).get("track") or COURSE_TRACK.get(
        enrollment.course_id, "interview"
    )
    scale = relevance(catalog, track)
    mine = [p for p in catalog.patterns.values() if p.concept in curriculum]
    abilities = {
        row.pattern: row
        for row in db.scalars(
            select(LearnerAbility).where(LearnerAbility.enrollment_id == enrollment.id)
        )
    }
    sessions = list(
        db.scalars(
            select(QuizEngineSession).where(QuizEngineSession.enrollment_id == enrollment.id)
        )
    )
    missed: dict[str, Counter[str]] = {}
    for session in sessions:
        for step in session.state.get("steps", []):
            if step.get("outcome") == "wrong" and step.get("misconception"):
                missed.setdefault(step["pattern"], Counter())[step["misconception"]] += 1
    past_patterns = {
        (row.payload.get("pattern_plan") or {}).get("pattern")
        for row in db.scalars(
            select(LearningSession).where(LearningSession.enrollment_id == enrollment.id)
        )
    }
    classify_keys = _classify_items(catalog)
    responses = list(
        db.scalars(
            select(QuizResponse).where(
                QuizResponse.enrollment_id == enrollment.id,
                QuizResponse.item_id.in_(list(classify_keys)),
            )
        )
    )

    course = set(catalog.course_concepts(enrollment.course_id))

    def known(concept: str) -> bool:
        state = states.get(concept, ConceptState())
        return state.assumed or state.mastered(now)

    def gated(concept: str) -> bool:
        # A pattern waits for its course prerequisites, so an unlocked module is still taught in order.
        prerequisites = catalog.prerequisites.get(concept, [])
        return (
            concept in locked
            or any(p in locked for p in prerequisites)
            or any(p in course and not known(p) for p in prerequisites)
        )

    blocked = [p for p in mine if gated(p.concept)]
    result = []
    for pattern in mine:
        state = states.get(pattern.concept, ConceptState())
        mastery = state.mean if state.evidence_count or state.assumed else 0.0
        ability = abilities.get(pattern.id)
        if ability is not None and ability.n:
            mastery = (mastery + p_correct(ability.theta, QUIZ.prior(4))) / 2
        done = tuple(v.id for v in pattern.variants if v.problem in solved)
        tags = missed.get(pattern.id, Counter())
        hits = sum(1 for r in responses if classify_keys.get(r.item_id) == pattern.id and r.correct)
        misses = sum(
            1 for r in responses if classify_keys.get(r.item_id) == pattern.id and not r.correct
        )
        leads_to = sum(
            1
            for other in blocked
            if pattern.concept in catalog.closure([other.concept]) and other is not pattern
        )
        result.append(
            planner.PatternView(
                pattern=pattern.id,
                concept=pattern.concept,
                gate=not gated(pattern.concept),
                mastery=round(mastery, 4),
                seen=bool(done or (ability and ability.n) or pattern.id in past_patterns),
                due=state.due(now),
                overdue_days=max(0.0, (now - state.next_review_at) / DAY)
                if state.due(now)
                else 0.0,
                idle_days=(now - state.last_evidence_at) / DAY if state.last_evidence_at else None,
                relevance=round(scale.get(pattern.id, 0.0), 4),
                unlock=leads_to / max(1, len(blocked)),
                solved=done,
                classify_hits=hits,
                classify_misses=misses,
                confusions=tuple(
                    sorted(t for t, n in tags.items() if t.startswith("pattern-") and n >= 2)
                ),
                pitfall_misses=tuple(
                    sorted(t for t in pattern.pitfalls if tags.get(t, 0) >= w.repair_after)
                ),
            )
        )
    return result


def _classify_items(catalog: Catalog) -> dict[str, str]:
    """Item key -> pattern, for quiz items that ask which pattern fits."""
    found = {}
    for family in catalog.quiz_families.values():
        if family.pattern:
            for item in family.items:
                if (item.format or family.format) == "classify":
                    found[family.item_key(item.id)] = family.pattern
    return found


def content(
    catalog: Catalog,
    pattern_id: str,
    concept_problems: list[str],
    unsolved: set[str],
    reviews: list[str],
    confusions: tuple[str, ...],
    allow_drafts: bool,
) -> planner.Content:
    pattern = catalog.patterns[pattern_id]
    pack = catalog.pattern_atoms.get(pattern_id)
    usable = pack is not None and (
        pack.status == "released" or (pack.status == "draft" and allow_drafts)
    )
    atoms: dict[str, dict] = {}
    if usable:
        assert pack is not None
        for atom in pack.atoms:
            atoms.setdefault(
                atom.kind,
                {**atom.model_dump(mode="json"), "version": pack.version, "status": pack.status},
            )
    status = pack.status if pack else "draft"
    version = pack.version if pack else "0.0.0"
    slug = pattern_id.split("/")[1]
    card = dict(
        id=f"{slug}-card",
        kind="pattern",
        title=pattern.title,
        objective=f"Recognise when to use {pattern.title.lower()} and how its template works.",
        body=" ".join(
            [f"Use it when: {'; '.join(pattern.recognise)}."]
            + ([f"Keep: {pattern.state}."] if pattern.state else [])
            + ([f"Each step: {pattern.transition}."] if pattern.transition else [])
            + [f"Cost: {pattern.complexity.time} time, {pattern.complexity.space} space."]
        ),
        why="A pattern card names the cues and the invariant, so you can recognise the next problem.",
        seconds=90,
        adapters={},
        steps=[],
        misconception=None,
        followup=None,
        version=version,
        status=status,
    )
    contrast = None
    table = contrasts(str(Path(catalog.quiz_root or ".").parent / "patterns" / CONTRASTS_FILE))
    for tag in confusions:
        if tag in table:
            contrast = dict(
                id=f"{slug}-contrast-{tag}",
                kind="pattern",
                title=table[tag]["title"],
                objective="Tell two similar patterns apart.",
                body=table[tag]["body"],
                why="Naming what separates two patterns prevents the next mix-up.",
                seconds=90,
                adapters={},
                steps=[],
                misconception=tag,
                followup=None,
                version=version,
                status=status,
            )
            break

    def info(pid: str) -> tuple[str, str]:
        course_id, problem = catalog.problems[pid]
        return problem.title, f"{course_id}:{problem.concepts[0]}"

    return planner.Content(
        pattern=pattern_id,
        concept=pattern.concept,
        title=pattern.title,
        card=card if usable else {},
        atoms=atoms,
        variants=[
            planner.Variant(v.id, v.band, v.problem if v.problem in catalog.problems else None)
            for v in pattern.variants
        ],
        unsolved=unsolved,
        concept_problems=concept_problems,
        problem_info=info,
        contrast=contrast if usable else None,
        reviews=reviews,
    )


def plan(
    db: Session,
    catalog: Catalog,
    enrollment: Enrollment,
    states: dict[str, ConceptState],
    locked: dict[str, str],
    curriculum: set[str],
    solved: set[str],
    helped: set[str],
    minutes: int,
    beginner: bool,
    recovery: bool,
    now: int,
    allow_drafts: bool,
    last_pattern: str | None,
) -> Plan | None:
    if not catalog.patterns:
        return None
    seen_views = views(db, catalog, enrollment, states, locked, curriculum, solved - helped, now)
    scores = planner.rank(seen_views, last_pattern)
    by_id = {v.pattern: v for v in seen_views}
    done = solved | helped
    due_concepts = [
        q
        for q, s in sorted(states.items(), key=lambda pair: pair[1].next_review_at)
        if s.due(now) and q not in locked
    ]
    due_patterns = sum(1 for v in seen_views if v.due)

    def open_problem(pid: str) -> bool:
        """Variant problems may sit in other concepts; those must be open to this learner too."""
        course_id, problem = catalog.problems[pid]
        concept = f"{course_id}:{problem.concepts[0]}"
        return (
            concept in curriculum
            and concept not in locked
            and not any(p in locked for p in catalog.prerequisites.get(concept, []))
        )

    for score in scores:
        view = by_id[score.pattern]
        if score.total <= 0:
            continue
        fired = planner.triggers(view)
        kind = planner.session_type(view, due_patterns, fired)
        concept_problems = sorted(
            (pid for pid in catalog.concept(view.concept).problems if pid not in done),
            key=lambda p: ({"easy": 0, "medium": 1, "hard": 2}[catalog.problem(p).difficulty], p),
        )
        reviews = due_concepts[: 3 if kind == "mixed_review" else 1]
        unsolved = {pid for pid in catalog.problems if pid not in done and open_problem(pid)}
        stuff = content(
            catalog,
            view.pattern,
            concept_problems,
            unsolved,
            reviews,
            view.confusions,
            allow_drafts,
        )
        if not stuff.card:
            continue  # no usable pack: this pattern cannot be taught yet
        blocks = planner.build(kind, view, stuff, fired, minutes, beginner, recovery)
        seen = {v.pattern for v in seen_views if v.seen}
        problems = planner.violations(
            blocks,
            gated={v.concept for v in seen_views if not v.gate},
            seen=seen,
            minutes=minutes,
            recovery=recovery,
            retention_due=bool(due_concepts),
            allow_drafts=allow_drafts,
        )
        if not problems:
            return Plan(view.pattern, view.concept, kind, fired, blocks, scores[:3])
    return None
