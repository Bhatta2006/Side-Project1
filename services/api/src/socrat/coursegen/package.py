"""Concept package: lesson, quiz and atoms for one planned concept, checked, then released.

Order per round: Lesson Author, then Quiz Builder and Atom Author together, then the
deterministic gates (schema, depth, links), then Fact Checker and Reviewer together. A
failing artifact goes back to its own author with the notes; the rest are kept. Release
needs every gate, no incorrect claim, and the reviewer's rubric (correctness 5, rest ≥ 4).
"""

import json
import re
from datetime import UTC, datetime

from pydantic import ValidationError

from socrat.catalog.atoms import AtomPack
from socrat.catalog.registry import Catalog
from socrat.catalog.schema import Concept, Course, Provenance, QuizItem
from socrat.coursegen import links

AI_AUTHOR = "Socrat AI course team"
GOLD = "dsa:sliding-window"  # a hand-authored lesson of typical depth, shown to authors
ATOM_KINDS = {"hook", "concept", "worked", "explanation", "reflection", "predict", "trace"}
MIN_LESSON = {"overview": 2000, "practitioner": 3000, "mastery": 4000}
DIMENSIONS = (
    "correctness",
    "depth",
    "continuity",
    "misconceptions",
    "assessment_alignment",
    "clarity",
    "accessibility",
)


def errors_of(exc: ValidationError, limit: int = 12) -> list[str]:
    return [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()[:limit]]


def context(catalog: Catalog, course: Course, brief: dict, concept: Concept) -> str:
    """What every author needs: the concept's contract, the course, and its neighbours."""
    prerequisites = []
    for ref in concept.prerequisites:
        key = ref if ":" in ref else f"{course.id}:{ref}"
        other = catalog.concepts.get(key) or next((c for c in course.concepts if c.id == ref), None)
        if other is not None:
            points = "; ".join(other.key_points) if other.key_points else other.summary
            prerequisites.append(f"- {key}: {other.title} — {points}")
    module = next(m for m in course.modules if m.id == concept.module)
    siblings = [
        f"- {c.title}: {c.summary}"
        for c in course.concepts
        if c.id in module.concepts and c.id != concept.id
    ]
    return "\n\n".join(
        [
            f"Course: {course.title} — {course.description}",
            f"Learners: {brief['audience']}\nAlready know: {brief.get('background') or 'see prerequisites'}",
            f"Course code languages: {', '.join(course.languages)}",
            "Concept to teach:\n"
            + json.dumps(
                {
                    "id": concept.id,
                    "title": concept.title,
                    "summary": concept.summary,
                    "difficulty": concept.difficulty,
                    "estimated_minutes": concept.estimated_minutes,
                    **(concept.outline.model_dump() if concept.outline else {}),
                },
                indent=1,
            ),
            "Prerequisites the learner has studied (build on them, do not re-teach):\n"
            + ("\n".join(prerequisites) or "- none"),
            "Other concepts in this module (stay out of their territory):\n"
            + ("\n".join(siblings) or "- none"),
        ]
    )


def gold(catalog: Catalog) -> Concept | None:
    return catalog.concepts.get(GOLD)


LESSON = """You are the Lesson Author for Socrat. Socrat lessons are deep enough to master a
skill, not summaries. Write one concept's lesson in Markdown, original prose only.

The lesson must:
- open with why the idea matters, then build intuition before formalism;
- work at least one concrete example step by step, showing intermediate values;
- explain why it works (the reasoning or invariant), not only how;
- cover edge cases and limits, and say when NOT to use the idea;
- confront each listed misconception directly and explain why it is wrong;
- teach every objective; finish with 3-5 self-check questions (answers in a <details> block);
- use "## " section headings; code (only if it helps) as fenced blocks, one per course
  language, equivalent across languages; no other languages.
Match the depth and style of the reference lesson shown. Never invent citations.

Reply with one JSON object only:
{"lesson": "markdown",
 "key_points": ["3-8 crisp takeaways"],
 "pitfalls": ["2-8 specific mistakes"],
 "resources": [{"title": "...", "url": "https://...", "kind": "article|video|docs|course|book|interactive|visualizer",
                "source": "publisher or site", "minutes": 1-600, "level": "intro|core|deep"}]}
Give 2-5 resources you are certain exist at exactly that URL: official documentation,
well-known textbooks' free pages, or major university course pages. Every link is checked."""

QUIZ = """You are the Quiz Builder for Socrat. From the lesson, write multiple-choice items
that check understanding, not recall of wording.

- 5-8 items; every objective tested at least once; difficulties spread from 1 to 5.
- Wrong options come from the listed misconceptions and realistic mistakes; never "all/none
  of the above"; 3-5 distinct options; vary the correct position.
- explanation says why the right answer is right and why the most tempting wrong one is wrong.
- Use only facts the lesson teaches.

Reply with one JSON object only:
{"quiz": [{"id": "kebab-case", "prompt": "...", "options": ["..."], "answer": 0,
           "explanation": "...", "difficulty": 1}]}"""

ATOMS = """You are the Atom Author for Socrat. Atoms are short teaching steps a session can
mix in: each takes 10-120 seconds and has one objective.

Allowed kinds: hook (at most 2 sentences), concept, worked, explanation, reflection,
predict, trace. explanation, predict and trace need "steps": checks with a state shown to
the learner, a prompt, 2-6 distinct options, the answer index and an explanation. Bodies are
at most 120 words. No code adapters. Write 4-8 atoms that together walk the concept, with
ids unique in kebab-case.

Reply with one JSON object only:
{"atoms": [{"id": "...", "kind": "...", "title": "...", "objective": "...", "body": "...",
            "why": "optional", "seconds": 60,
            "steps": [{"state": "...", "prompt": "...", "options": ["..."], "answer": 0,
                       "explanation": "..."}]}]}"""

FACTS = """You are the Fact Checker for Socrat. Check every substantive technical claim in
the package: lesson statements, worked-example numbers, code behaviour, quiz answer keys and
explanations, atom checks. Be precise; recompute numbers yourself.

Reply with one JSON object only:
{"claims": [{"where": "lesson | quiz:<id> | atom:<id>", "claim": "...",
             "verdict": "correct | imprecise | incorrect", "correction": "required unless correct"}]}
List every imprecise or incorrect claim, and at most 10 correct ones."""

REVIEW = """You are the Reviewer for Socrat. Judge a generated concept package against the
concept's contract and against the reference lesson's depth. Be demanding: learners rely on
this to master the skill.

Score 1-5 each: correctness, depth (worked example traced, why it works, edge cases,
self-checks), continuity (builds on prerequisites, no overlap with siblings),
misconceptions (each confronted), assessment_alignment (quiz and atoms test the
objectives), clarity, accessibility (plain language, terms defined, no reliance on colour).

Reply with one JSON object only:
{"scores": {"correctness": 1, "depth": 1, "continuity": 1, "misconceptions": 1,
            "assessment_alignment": 1, "clarity": 1, "accessibility": 1},
 "summary": "2-3 sentences",
 "lesson": ["specific fixes"], "quiz": ["..."], "atoms": ["..."]}"""


def lesson_prompt(ctx: str, reference: Concept | None, draft: dict | None, notes: list[str]) -> str:
    parts = [ctx]
    if reference is not None:
        parts.append(
            f"Reference lesson ({reference.title}) for depth and style:\n{reference.lesson}"
        )
    if draft is not None:
        parts.append("Your previous draft:\n" + json.dumps(draft, indent=1))
    if notes:
        parts.append("Fix all of these in a complete revised reply:\n- " + "\n- ".join(notes))
    return "\n\n".join(parts)


def part_prompt(ctx: str, lesson: dict, draft: dict | None, notes: list[str], example: str) -> str:
    parts = [ctx, "Lesson:\n" + lesson["lesson"]]
    if example:
        parts.append(example)
    if draft is not None:
        parts.append("Your previous draft:\n" + json.dumps(draft, indent=1))
    if notes:
        parts.append("Fix all of these in a complete revised reply:\n- " + "\n- ".join(notes))
    return "\n\n".join(parts)


def quiz_example(reference: Concept | None) -> str:
    if reference is None or not reference.quiz:
        return ""
    items = [q.model_dump(mode="json", exclude_none=True) for q in reference.quiz[:2]]
    return "Reference items for quality:\n" + json.dumps(items, indent=1)


def check_lesson(concept: Concept, course: Course, draft: dict) -> list[str]:
    """Deterministic lesson gates; links are checked separately (network)."""
    problems = []
    depth = concept.outline.depth if concept.outline else "practitioner"
    text = str(draft.get("lesson", ""))
    if len(text) < MIN_LESSON[depth]:
        problems.append(
            f"The lesson is {len(text)} characters; a {depth} concept needs at least "
            f"{MIN_LESSON[depth]}. Add worked examples, reasoning and edge cases, not padding."
        )
    if len(re.findall(r"^## ", text, re.MULTILINE)) < 3:
        problems.append("Use at least three '## ' section headings.")
    fences = set(re.findall(r"^```([a-zA-Z+#]*)", text, re.MULTILINE)) - {""}
    allowed = set(course.languages) | {"text", "math", "plaintext"}
    stray = {f for f in fences if f.lower() not in allowed}
    if stray:
        problems.append(f"Code blocks in {sorted(stray)} are outside the course languages.")
    if "<details" not in text:
        problems.append("End with self-check questions, answers inside a <details> block.")
    return problems


def build_concept(concept: Concept, lesson: dict, quiz: dict, version: int, attribution: str):
    """The live concept, or (None, problems by artifact)."""
    problems: dict[str, list[str]] = {"lesson": [], "quiz": []}
    items = quiz.get("quiz") if isinstance(quiz.get("quiz"), list) else []
    if not 4 <= len(items) <= 10:
        problems["quiz"].append(f"Write 5-8 items; got {len(items)}.")
    parsed = []
    for raw in items:
        try:
            parsed.append(QuizItem.model_validate({**raw, "kind": "mcq"}))
        except (ValidationError, TypeError) as exc:
            where = raw.get("id", "?") if isinstance(raw, dict) else "?"
            detail = errors_of(exc) if isinstance(exc, ValidationError) else [str(exc)]
            problems["quiz"].append(f"item {where}: {'; '.join(detail)}")
    if len({q.id for q in parsed}) != len(parsed):
        problems["quiz"].append("Quiz item ids must be unique.")
    if any(problems.values()):
        return None, problems
    try:
        live = concept.model_copy(
            update={
                "status": "live",
                "lesson": lesson["lesson"],
                "key_points": lesson["key_points"],
                "pitfalls": lesson.get("pitfalls", []),
                "quiz": parsed,
                "provenance": Provenance(
                    author=AI_AUTHOR, version=version, attribution_md=attribution
                ),
            }
        )
        # model_copy skips validation; round-trip to run every field and the live contract.
        return Concept.model_validate(
            {**live.model_dump(mode="json"), "resources": lesson.get("resources", [])}
        ), problems
    except (ValidationError, KeyError, TypeError) as exc:
        detail = errors_of(exc) if isinstance(exc, ValidationError) else [f"missing {exc}"]
        return None, {"lesson": detail, "quiz": []}


def build_atoms(course: Course, concept: Concept, atoms: dict, version: int):
    """A draft pack, or (None, problems)."""
    raw = atoms.get("atoms") if isinstance(atoms.get("atoms"), list) else []
    problems = []
    if not 3 <= len(raw) <= 8:
        problems.append(f"Write 4-8 atoms; got {len(raw)}.")
    kinds = {a.get("kind") for a in raw if isinstance(a, dict)}
    if kinds - ATOM_KINDS:
        problems.append(f"Kinds {sorted(kinds - ATOM_KINDS)} are not allowed here.")
    if any(isinstance(a, dict) and a.get("adapters") for a in raw):
        problems.append("Atoms carry no code adapters yet.")
    if problems:
        return None, problems
    try:
        pack = AtomPack.model_validate(
            {
                "concept": f"{course.id}:{concept.id}",
                "concept_version": course.version,
                "version": f"1.0.{version - 1}",
                "owner": AI_AUTHOR,
                "rights": "Socrat original, all rights reserved",
                "changelog": f"Generated package version {version}.",
                "rollback": f"quarantine:{course.id}:{concept.id}@{version}",
                "atoms": raw,
            }
        )
    except ValidationError as exc:
        return None, errors_of(exc)
    return pack, []


def release_pack(pack: AtomPack, reviewer: str, summary: str) -> AtomPack:
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    return AtomPack.model_validate(
        {
            **pack.model_dump(mode="json"),
            "status": "released",
            "review": {
                "by": f"{reviewer} via release gates"[:120],
                "at": today,
                "notes": summary[:2000],
            },
        }
    )


async def broken_links(lesson: dict, client=None) -> list[str]:
    urls = [r.get("url", "") for r in lesson.get("resources", []) if isinstance(r, dict)]
    return await links.broken(urls, client) if urls else []


def verdict(facts: dict | None, review: dict | None) -> tuple[bool, dict[str, list[str]], dict]:
    """Pass/fail from the fact claims and rubric, plus revision notes by artifact."""
    notes: dict[str, list[str]] = {"lesson": [], "quiz": [], "atoms": []}
    blocking = False
    for claim in (facts or {}).get("claims", []):
        if not isinstance(claim, dict) or claim.get("verdict") == "correct":
            continue
        where = str(claim.get("where", "lesson"))
        target = (
            "quiz"
            if where.startswith("quiz")
            else "atoms"
            if where.startswith("atom")
            else "lesson"
        )
        notes[target].append(
            f"[{claim.get('verdict')}] {where}: {claim.get('claim', '')} → {claim.get('correction', '')}"
        )
        blocking |= claim.get("verdict") == "incorrect"
    scores = {}
    for dim in DIMENSIONS:
        try:
            scores[dim] = int((review or {}).get("scores", {}).get(dim, 0))
        except (TypeError, ValueError):
            scores[dim] = 0
    for target in notes:
        notes[target] += [str(n) for n in (review or {}).get(target, []) if n][:10]
    passed = (
        not blocking
        and facts is not None
        and scores["correctness"] == 5
        and all(scores[d] >= 4 for d in DIMENSIONS)
    )
    return passed, notes, scores
