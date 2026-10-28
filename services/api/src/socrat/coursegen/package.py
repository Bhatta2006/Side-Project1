"""Concept package: lesson, quiz and atoms for one planned concept, checked, then released.

Order per round: Lesson Author, then Quiz Builder and Atom Author together, then the
deterministic gates (schema, depth, links, and running any code in the execution plane),
then Fact Checker and Reviewer together. A
failing artifact goes back to its own author with the notes; the rest are kept. Release
needs every gate, no incorrect claim, and the reviewer's rubric (correctness 5, rest ≥ 4).
"""

import json
import re
from datetime import UTC, datetime

from pydantic import ValidationError

from socrat import harness
from socrat.catalog import shape
from socrat.catalog.atoms import AtomPack
from socrat.catalog.registry import Catalog
from socrat.catalog.schema import Concept, Course, Exercise, Prompt, Provenance, QuizItem
from socrat.coursegen import execute, links
from socrat.judge.service import normalized
from socrat.style import spec as styles

AI_AUTHOR = "Socrat AI course team"
GOLD = "dsa:sliding-window"  # a hand-authored lesson of typical depth, shown to authors
ATOM_KINDS = {"hook", "concept", "worked", "explanation", "reflection", "predict", "trace"}
CODE_ATOMS = {"worked", "predict", "trace"}
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
STYLE_DIMENSION = "style_fit"  # scored only when the course has a learning style


def errors_of(exc: ValidationError, limit: int = 12) -> list[str]:
    return [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()[:limit]]


def context(
    catalog: Catalog,
    course: Course,
    brief: dict,
    concept: Concept,
    style: styles.StyleSpec | None = None,
) -> str:
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
            *([styles.block(style)] if style else []),
            f"Course: {course.title} — {course.description}",
            f"Learners: {brief['audience']}\nAlready know: {brief.get('background') or 'see prerequisites'}",
            f"Course code languages: {', '.join(course.languages)}",
            practice_line(course),
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


def practice_line(course: Course) -> str:
    """How learners practise and prove this subject, so authors write for that studio."""
    s = shape.effective(course)
    tools = ", ".join(s.tools) or "none"
    return (
        f"Practice studio: {s.name} ({s.studio}); loop: {s.loop}; evidence: "
        f"{', '.join(s.evidence)}; tools: {tools}. Write for this: "
        + {
            "code": "worked examples in code, edge cases that break naive solutions.",
            "workbench": "derive step by step, show each algebra step, and give problems whose "
            "answers can be checked symbolically or numerically.",
            "lab": "start from a prediction the learner commits to, say what to vary and observe "
            "in a simulation, then explain the result with the model; use units.",
            "reading": "explain clearly with examples and ask the learner to explain back.",
        }[s.studio]
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


STYLE_NOTE = """

A LEARNING STYLE block is part of the context. Follow it: the lesson's length, register,
examples, tone and structure come from the style, not from the default rules above (the
"## " heading count, section list and reference lesson depth are defaults the style may
override). Quiz and atoms use the style's register too; item counts stay within 4-8."""

STYLE_REVIEW = """

A LEARNING STYLE block is part of the context. Judge depth and clarity against that style,
not against the reference lesson. Also score "style_fit" 1-5: would the learner described
find the length, register, tone, examples and rigor right for them? Add "style_fit" to scores."""

EXERCISES = """This course practises in a math workbench that checks answers with a computer
algebra system. Add "exercises": 3-6 problems the learner solves by typing an answer, easy to
hard. Each is checked by code, so the reference answer must be exactly right.
"exercises": [{{"id": "kebab-case", "prompt": "...", "check": "equivalent|equation|numeric|steps",
  "expected": "...", "unit": "", "hints": ["nudge", "bigger nudge"], "plot": [],
  "difficulty": 1, "explanation": "the worked solution"}}]
- equivalent: a formula or expression, written like (x+1)^2 or sin(x)^2 + cos(x)^2. The learner may
  write any equivalent form. equation: a solved equation such as x=3 (any equivalent equation is
  accepted). steps: the learner shows working line by line and the last line must equal expected.
- numeric: "expected" is a plain number such as 9.8 and "unit" its unit such as m/s^2.
- plot: up to 3 expressions in x worth drawing for this problem (the learner sees the graph).
- Use only `x`, `y`, `t`, numbers, + - * / ^, parentheses, sqrt, sin, cos, tan, exp, ln, pi.
- Each problem has one answer, no trick wording, and hints that teach without giving it away."""

QUIZ_CODE = """Code items are allowed. Up to 3 items may be "kind": "output" with
"code": {{"<language>": "complete program"}} for each of: {languages}. Each program reads no
input and prints exactly the text of the correct option; it is run, and the item is
rejected if the output differs or matches another option. Under 15 lines, equivalent in
every language; Java uses "public class Solution". Other items are "kind": "mcq" without code."""

PROMPTS = """This concept is also assessed by free-text answers. Add "prompts": 1-3 questions
the learner answers in their own words (explain why, compare, apply to a new case; never
recall of a definition), each with a rubric of 2-6 criteria worth 1-4 points that a grader
can apply to any wording, and a model answer that would earn every point:
"prompts": [{{"id": "kebab-case", "prompt": "...", "max_words": 150,
             "rubric": [{{"criterion": "...", "points": 2, "look_for": "what earns the points"}}],
             "model_answer": "..."}}]"""

ATOMS_CODE = """Code adapters are allowed on worked, predict and trace atoms:
"adapters": {{"<language>": {{"code": "complete program", "stdin": ""}}}} with one for each of:
{languages}. The programs are run and must print the same output in every language;
learners see that output. At most 25 lines (trace 15, predict 10); Java uses
"public class Solution"."""


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


def check_lesson(
    concept: Concept, course: Course, draft: dict, style: styles.StyleSpec | None = None
) -> list[str]:
    """Deterministic lesson gates; links are checked separately (network)."""
    problems = []
    depth = concept.outline.depth if concept.outline else "practitioner"
    text = str(draft.get("lesson", ""))
    floor, ceiling = MIN_LESSON[depth], None
    if style is not None and style.format != "standard":
        floor, ceiling = style.lesson_bounds()
    if len(text) < floor:
        problems.append(
            f"The lesson is {len(text)} characters; this concept needs at least "
            f"{floor}. Add worked examples, reasoning and edge cases, not padding."
        )
    if ceiling and len(text) > ceiling:
        problems.append(
            f"The lesson is {len(text)} characters; this style allows at most {ceiling}. "
            "Keep one idea and cut the rest."
        )
    wanted = style.min_headings() if style is not None else 3
    if len(re.findall(r"^## ", text, re.MULTILINE)) < wanted:
        problems.append(f"Use at least {wanted} '## ' section heading{'s' if wanted > 1 else ''}.")
    fences = set(re.findall(r"^```([a-zA-Z+#]*)", text, re.MULTILINE)) - {""}
    allowed = set(course.languages) | {"text", "math", "plaintext"}
    stray = {f for f in fences if f.lower() not in allowed}
    if stray:
        problems.append(f"Code blocks in {sorted(stray)} are outside the course languages.")
    if "<details" not in text:
        problems.append("End with self-check questions, answers inside a <details> block.")
    return problems


def check_exercises(raw) -> tuple[list[Exercise], list[str]]:
    """Exercises that parse, and whose reference answers the harness itself accepts."""
    problems: list[str] = []
    items = raw if isinstance(raw, list) else []
    if not 3 <= len(items) <= 8:
        return [], [f"Write 3-6 exercises; got {len(items)}."]
    parsed = []
    for entry in items:
        where = entry.get("id", "?") if isinstance(entry, dict) else "?"
        try:
            ex = Exercise.model_validate(entry)
        except (ValidationError, TypeError) as exc:
            detail = errors_of(exc) if isinstance(exc, ValidationError) else [str(exc)]
            problems.append(f"exercise {where}: {'; '.join(detail)}")
            continue
        if ex.check == "numeric":
            request = {
                "op": "numeric",
                "expected": ex.expected,
                "given": f"{ex.expected} {ex.unit}",
                "unit": ex.unit,
            }
        else:
            op = "equation" if ex.check == "equation" else "equivalent"
            request = {"op": op, "expected": ex.expected, "given": ex.expected}
        verdict = harness.call("math.check", request)
        if not verdict.ok or verdict.output.get("verdict") != "correct":
            why = verdict.error or verdict.output.get("reason", "")
            problems.append(
                f"exercise {ex.id}: the reference answer is not valid math the checker accepts ({why})"
            )
            continue
        for expr in ex.plot:
            seen = harness.call("math.check", {"op": "equivalent", "expected": expr, "given": expr})
            if not seen.ok or seen.output.get("verdict") != "correct":
                problems.append(
                    f"exercise {ex.id}: cannot plot {expr!r}; use x, numbers and basic functions"
                )
        parsed.append(ex)
    if len({e.id for e in parsed}) != len(parsed):
        problems.append("Exercise ids must be unique.")
    return parsed, problems


def build_concept(
    concept: Concept,
    lesson: dict,
    quiz: dict,
    version: int,
    attribution: str,
    languages: list[str] = (),
    workbench: bool = False,
):
    """The live concept, or (None, problems by artifact). ``languages``: code items allowed
    (and required in each of them), verified later by ``run_code``. Free-text prompts are
    required when the outline assesses by "explain"."""
    problems: dict[str, list[str]] = {"lesson": [], "quiz": []}
    items = quiz.get("quiz") if isinstance(quiz.get("quiz"), list) else []
    if not 4 <= len(items) <= 10:
        problems["quiz"].append(f"Write 5-8 items; got {len(items)}.")
    parsed = []
    for raw in items:
        try:
            item = {**raw, "kind": raw.get("kind", "mcq")} if languages else {**raw, "kind": "mcq"}
            if item["kind"] not in {"mcq", "output"}:
                raise TypeError(f"kind {item['kind']} is not allowed; use mcq or output")
            if item["kind"] == "mcq":
                item.pop("code", None)
            elif set(item.get("code") or {}) != set(languages):
                raise TypeError(f"an output item needs code in exactly: {', '.join(languages)}")
            parsed.append(QuizItem.model_validate(item))
        except (ValidationError, TypeError) as exc:
            where = raw.get("id", "?") if isinstance(raw, dict) else "?"
            detail = errors_of(exc) if isinstance(exc, ValidationError) else [str(exc)]
            problems["quiz"].append(f"item {where}: {'; '.join(detail)}")
    if len({q.id for q in parsed}) != len(parsed):
        problems["quiz"].append("Quiz item ids must be unique.")
    raw_prompts = quiz.get("prompts") if isinstance(quiz.get("prompts"), list) else []
    wants = concept.outline is not None and "explain" in concept.outline.assessment
    if wants and not 1 <= len(raw_prompts) <= 3:
        problems["quiz"].append(f"Write 1-3 free-text prompts; got {len(raw_prompts)}.")
    prompts = []
    for raw in raw_prompts if wants else []:
        try:
            prompts.append(Prompt.model_validate(raw))
        except (ValidationError, TypeError) as exc:
            where = raw.get("id", "?") if isinstance(raw, dict) else "?"
            detail = errors_of(exc) if isinstance(exc, ValidationError) else [str(exc)]
            problems["quiz"].append(f"prompt {where}: {'; '.join(detail)}")
    if len({x.id for x in prompts}) != len(prompts):
        problems["quiz"].append("Prompt ids must be unique.")
    exercises: list[Exercise] = []
    if workbench:
        exercises, bad = check_exercises(quiz.get("exercises"))
        problems["quiz"].extend(bad)
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
                "prompts": prompts,
                "exercises": exercises,
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


def build_atoms(
    course: Course, concept: Concept, atoms: dict, version: int, languages: list[str] = ()
):
    """A draft pack, or (None, problems). ``languages``: code adapters allowed (and needed in
    each of them); their output is filled in by ``run_code``."""
    raw = atoms.get("atoms") if isinstance(atoms.get("atoms"), list) else []
    problems = []
    if not 3 <= len(raw) <= 8:
        problems.append(f"Write 4-8 atoms; got {len(raw)}.")
    kinds = {a.get("kind") for a in raw if isinstance(a, dict)}
    if kinds - ATOM_KINDS:
        problems.append(f"Kinds {sorted(kinds - ATOM_KINDS)} are not allowed here.")
    for atom in raw:
        adapters = atom.get("adapters") if isinstance(atom, dict) else None
        if not adapters:
            continue
        if not languages:
            problems.append("Atoms carry no code adapters in this course.")
        elif atom.get("kind") not in CODE_ATOMS:
            problems.append(
                f"atom {atom.get('id')}: only worked, predict and trace atoms have code."
            )
        elif not isinstance(adapters, dict) or set(adapters) != set(languages):
            problems.append(f"atom {atom.get('id')}: give code in exactly {', '.join(languages)}.")
        elif any(isinstance(a, dict) and a.get("expected") for a in adapters.values()):
            problems.append(f"atom {atom.get('id')}: leave out expected; the code is run.")
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


async def run_code(executor, live: Concept, pack: AtomPack):
    """Run every output item and atom adapter. Returns the pack with each adapter's real
    output filled in, and problems by artifact."""
    problems: dict[str, list[str]] = {"quiz": [], "atoms": []}
    for item in live.quiz:
        if item.kind != "output":
            continue
        claimed = normalized(item.options[item.answer])
        for lang, code in item.code.items():
            [case] = await executor.run(lang, code, [""])
            if not execute.ok(case):
                problems["quiz"].append(f"item {item.id} ({lang}) {execute.describe(case)}")
            elif normalized(case["stdout"]) != claimed:
                problems["quiz"].append(
                    f"item {item.id}: the {lang} code prints {case['stdout'][:200]!r}, "
                    f"not the answer {item.options[item.answer][:200]!r}."
                )
            elif any(
                normalized(o) == claimed for i, o in enumerate(item.options) if i != item.answer
            ):
                problems["quiz"].append(f"item {item.id}: another option equals the answer.")
    atoms = []
    for atom in pack.atoms:
        outputs = {}
        for lang, adapter in atom.adapters.items():
            [case] = await executor.run(lang, adapter.code, [adapter.stdin])
            if not execute.ok(case):
                problems["atoms"].append(f"atom {atom.id} ({lang}) {execute.describe(case)}")
            else:
                outputs[lang] = normalized(case["stdout"]) + "\n"
        if len(set(outputs.values())) > 1:
            shown = "; ".join(f"{k}: {v[:120]!r}" for k, v in outputs.items())
            problems["atoms"].append(f"atom {atom.id}: languages print different output ({shown}).")
        adapters = {
            lang: a.model_copy(update={"expected": outputs.get(lang)})
            for lang, a in atom.adapters.items()
        }
        atoms.append(atom.model_copy(update={"adapters": adapters}))
    return pack.model_copy(update={"atoms": atoms}), problems


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


def verdict(
    facts: dict | None, review: dict | None, style: bool = False
) -> tuple[bool, dict[str, list[str]], dict]:
    """Pass/fail from the fact claims and rubric, plus revision notes by artifact.
    ``style``: the course has a learning style, so style_fit is scored and must be ≥ 4."""
    dimensions = (*DIMENSIONS, STYLE_DIMENSION) if style else DIMENSIONS
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
    for dim in dimensions:
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
        and all(scores[d] >= 4 for d in dimensions)
    )
    return passed, notes, scores
