"""Concept package: lesson, quiz and atoms for one planned concept, checked, then released.

Order per round: Lesson Author, then Quiz Builder and Atom Author together, then the
deterministic gates (schema, depth, links, and running any code in the execution plane),
then Fact Checker and Reviewer together. A
failing artifact goes back to its own author with the notes; the rest are kept. Release
needs every gate, no incorrect claim, and the reviewer's rubric (correctness 5, rest ≥ 4).
"""

import json
import re
from collections.abc import Sequence
from datetime import UTC, datetime

from pydantic import ValidationError

from socrat import harness
from socrat.catalog import dialect, shape
from socrat.catalog.atoms import Atom, AtomPack, Step
from socrat.catalog.registry import Catalog
from socrat.catalog.schema import (
    Concept,
    Course,
    Exercise,
    Experiment,
    Prompt,
    Provenance,
    QuizItem,
    Task,
)
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
If "visuals" are present, each must serve a stated objective, its params must make sense for the
idea, and its fallback_text must teach the same thing without the visual; list any that do not
under "lesson". Decorative visuals count against clarity.

What a score means, in every dimension: 5 = meets the contract, nothing to fix there; 4 = one
specific fix needed; 3 = several fixes or one real gap; 2 = a serious problem; 1 = unusable.
Correctness is 5 when you find no factual error or misleading statement. Any score below 5 must
come with the exact fix under "lesson", "quiz" or "atoms" (for correctness: the claim and its
correction), so the author can make it; a lower score with no fix named is not allowed.

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
find the length, register, tone, examples and rigor right for them? Add "style_fit" to scores,
on the same 1-5 meaning, with the fix named when it is below 5."""

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
- plot: up to 3 expressions in x worth drawing for this problem (the learner sees the graph). A letter
  a, b or c in a plot becomes a slider the learner drags (e.g. "a*x^2 + b"), so use them when the
  point is how a parameter changes the curve.
- points: optional, up to 12 [x, y] data points the learner fits a line to by dragging two handles
  (they read the slope off their line). Put them exactly on a line with simple numbers (steps
  of 0.5) and ask for the slope or intercept as the numeric answer.
- Use only `x`, `y`, `t`, `a`, `b`, `c`, numbers, + - * / ^, parentheses, sqrt, sin, cos, tan, exp, ln, pi.
- Each problem has one answer, no trick wording, and hints that teach without giving it away."""

EXPERIMENTS = """This course practises in a physics lab: the learner predicts one result, a vetted
simulation runs, and they compare and explain. Add "experiments": 2-4, easy to hard. The
simulation (not you) computes the true result, so never write the answer in the prompt.
"experiments": [{{"id": "kebab-case", "prompt": "the scenario, ending with what to predict",
  "model": "projectile|free_fall|pendulum|spring_mass|circuit|wave|refraction|heating", "params": {{"name": number}},
  "predict": "a quantity this model reports", "tolerance": 0.05, "vary": "a parameter or empty",
  "hints": ["nudge", "bigger nudge"], "difficulty": 1, "explanation": "why, using the model",
  "rubric": [{{"criterion": "short name", "points": 2, "look_for": "what a good explanation says"}}]}}]
Models, their parameters and what they report:
{models}
- params must give every parameter of the model, inside its limits, with the units shown.
- The prompt states the setup in plain words and units and asks for the "predict" quantity.
- vary: one parameter the learner may change afterwards to see its effect (or empty).
- explanation: the physics reasoning (which law or formula, what depends on what).
- rubric: 2-4 criteria (points 1-4) a grader uses on the learner's own written explanation of why
  the result came out as it did; each says what a good explanation contains."""

QUIZ_CODE = """Code items are allowed. Up to 3 items may be "kind": "output" with
"code": {{"<language>": "complete program"}} for each of: {languages}. Each program reads no
input and prints exactly the text of the correct option; it is run, and the item is
rejected if the output differs or matches another option. Under 15 lines, equivalent in
every language; Java uses "public class Solution". Other items are "kind": "mcq" without code,
and every learner sees them whatever their language, so they must hold in each of: {languages}.
Never lean on syntax only one language has (input(), math.sqrt, a // b, std::cout,
System.out); describe the idea in words, or make it an "output" item."""

PROMPTS = """This concept is also assessed by free-text answers. Add "prompts": 1-3 questions
the learner answers in their own words (explain why, compare, apply to a new case; never
recall of a definition), each with a rubric of 2-6 criteria worth 1-4 points that a grader
can apply to any wording, and a model answer that would earn every point:
"prompts": [{{"id": "kebab-case", "prompt": "...", "max_words": 150,
             "rubric": [{{"criterion": "...", "points": 2, "look_for": "what earns the points"}}],
             "model_answer": "..."}}]"""

TASKS = """This concept is also practised beyond a quiz. Add "tasks": 1-2 of the kinds the
practice calls for: "reflection" or "case-study" (the learner checks their own work against the
rubric) or "oral", "performance", "portfolio", "practical" (a person judges the real work; say
what to record or hand in). Each has a rubric of 2-6 criteria worth 1-4 points. For anything
physical, "safety" says what to do or avoid; never ask for anything dangerous without a
qualified person present. Also give "sequence": the order the learner meets this concept's
activities, using "lesson", "quiz", "visual:0", "prompt:<id>", "task:<id>" (only ids you wrote).
"tasks": [{{"id": "kebab-case", "kind": "reflection|case-study|oral|performance|portfolio|practical",
  "prompt": "...", "rubric": [{{"criterion": "...", "points": 2, "look_for": "..."}}], "safety": ""}}],
"sequence": ["lesson", "quiz", "task:<id>"]"""

DOING = {"performance", "reflection", "discussion", "project", "lab"}


def wants_tasks(concept, adapter=None) -> bool:
    """Tasks are asked for when the competency is practised by doing or reflecting."""
    practice = set(concept.outline.practice) if concept.outline else set()
    hands_on = adapter is not None and (
        adapter.needs_physical_practice or adapter.needs_external_evaluator
    )
    return bool(practice & DOING) or hands_on


ATOMS_CODE = """Code adapters are allowed on worked, predict and trace atoms:
"adapters": {{"<language>": {{"code": "complete program", "stdin": ""}}}} with one for each of:
{languages}. The programs are run and must print the same output in every language;
learners see that output. At most 25 lines (trace 15, predict 10); Java uses
"public class Solution"."""


# A revision edits, it does not rewrite: in live runs a full rewrite fixed the named problems
# and brought new ones, so no lesson converged within its rounds.
REVISE = (
    "Revise your previous draft. Apply each fix below exactly where it applies and keep every "
    "other sentence, item and field as it is, word for word. Add no new claims. Where a note says "
    "a source does not support a claim, remove that marker (or the claim). Reply with the complete "
    "revised JSON.\nFixes:\n- "
)


def lesson_prompt(ctx: str, reference: Concept | None, draft: dict | None, notes: list[str]) -> str:
    parts = [ctx]
    if reference is not None:
        parts.append(
            f"Reference lesson ({reference.title}) for depth and style:\n{reference.lesson}"
        )
    if draft is not None:
        parts.append("Your previous draft:\n" + json.dumps(draft, indent=1))
    if notes:
        intro = REVISE if draft is not None else "Fix all of these in a complete reply:\n- "
        parts.append(intro + "\n- ".join(notes))
    return "\n\n".join(parts)


def part_prompt(ctx: str, lesson: dict, draft: dict | None, notes: list[str], example: str) -> str:
    parts = [ctx, "Lesson:\n" + lesson["lesson"]]
    if example:
        parts.append(example)
    if draft is not None:
        parts.append("Your previous draft:\n" + json.dumps(draft, indent=1))
    if notes:
        intro = REVISE if draft is not None else "Fix all of these in a complete reply:\n- "
        parts.append(intro + "\n- ".join(notes))
    return "\n\n".join(parts)


def quiz_example(reference: Concept | None) -> str:
    if reference is None or not reference.quiz:
        return ""
    items = [q.model_dump(mode="json", exclude_none=True) for q in reference.quiz[:2]]
    return "Reference items for quality:\n" + json.dumps(items, indent=1)


SHELL_FENCES = {"bash", "sh", "shell", "console", "zsh", "powershell", "ps", "cmd", "terminal"}
# A style's upper bound is guidance for the author; the gate allows this much over it, since
# a model cannot count characters and a lesson 10% long is not a reason to discard it. Live runs
# wrote bite lessons 30-45% over while the reviewer scored their style fit 4, so the reviewer's
# style_fit (>= 4 to pass) judges the length the learner meets; this only stops a runaway.
CEILING_SLACK = 1.5


def teaching_length(text: str) -> int:
    """Characters of the lesson itself: the self-check answers in <details> and a trailing
    sources list are not what the length bounds are about."""
    body = re.sub(r"<details.*?</details>", "", text, flags=re.DOTALL | re.IGNORECASE)
    body = re.split(r"^#{1,3}\s*(?:Sources|References|Further reading)\b", body, flags=re.M | re.I)[
        0
    ]
    return len(body.strip())


def tidy_lesson(draft: dict, sources: list[dict]) -> dict:
    """Deterministic repairs instead of a new round: shell commands are fenced as text (they
    are not course code), and citation markers that match no source are dropped."""
    text = draft.get("lesson")
    if not isinstance(text, str):
        return draft
    text = re.sub(
        r"^```([a-zA-Z]+)",
        lambda m: "```text" if m.group(1).lower() in SHELL_FENCES else m.group(0),
        text,
        flags=re.MULTILINE,
    )
    if sources:
        valid = {s["n"] for s in sources}
        text = re.sub(
            r"\s?\[(\d{1,2})\]", lambda m: m.group(0) if int(m.group(1)) in valid else "", text
        )
    # Lists over their limit keep their first eight instead of failing the round.
    capped = {k: draft[k][:8] for k in ("key_points", "pitfalls") if isinstance(draft.get(k), list)}
    return {**draft, **capped, "lesson": text}


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
    taught = teaching_length(text)
    if ceiling and taught > ceiling * CEILING_SLACK:
        problems.append(
            f"The lesson (without the self-check answers and sources) is {taught} characters, "
            f"about {taught // 6} words; this style allows at most {ceiling} characters "
            f"(about {ceiling // 6} words). Keep one idea and cut the rest."
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


def models_text() -> str:
    """The lab's experiment models for the author's prompt."""
    from socrat.harness import physics

    lines = []
    for name, m in physics.MODELS.items():
        params = ", ".join(f"{k} ({p.unit}, {p.low:g}-{p.high:g})" for k, p in m.params.items())
        reports = ", ".join(f"{k} ({u})" for k, u in m.outputs.items())
        lines.append(f"- {name}: params {params}; reports {reports}")
    return "\n".join(lines)


def check_experiments(raw) -> tuple[list[Experiment], list[str]]:
    """Experiments that parse and that the vetted simulation actually runs."""
    from socrat.lab import service as lab

    items = raw if isinstance(raw, list) else []
    if not 2 <= len(items) <= 5:
        return [], [f"Write 2-4 experiments; got {len(items)}."]
    problems: list[str] = []
    parsed = []
    for entry in items:
        where = entry.get("id", "?") if isinstance(entry, dict) else "?"
        try:
            ex = Experiment.model_validate(entry)
        except (ValidationError, TypeError) as exc:
            detail = errors_of(exc) if isinstance(exc, ValidationError) else [str(exc)]
            problems.append(f"experiment {where}: {'; '.join(detail)}")
            continue
        if not 2 <= len(ex.rubric) <= 4:
            problems.append(f"experiment {ex.id}: add a rubric of 2-4 criteria")
            continue
        if bad := lab.problems(ex):
            problems.append(f"experiment {ex.id}: {'; '.join(bad)}")
            continue
        run = harness.call("physics.simulate", dict(model=ex.model, params=ex.params))
        if not run.ok:
            problems.append(f"experiment {ex.id}: the simulation did not run ({run.error})")
            continue
        answer = run.output["outputs"][ex.predict]["value"]
        stated = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", ex.prompt.replace(",", ""))]
        if any(
            abs(n - answer) <= 0.005 * abs(answer)
            for n in stated
            if answer and n not in ex.params.values()
        ):
            problems.append(f"experiment {ex.id}: the prompt gives away the result; remove it")
            continue
        parsed.append(ex)
    if len({e.id for e in parsed}) != len(parsed):
        problems.append("Experiment ids must be unique.")
    return parsed, problems


def build_concept(
    concept: Concept,
    lesson: dict,
    quiz: dict,
    version: int,
    attribution: str,
    languages: Sequence[str] = (),
    workbench: bool = False,
    lab: bool = False,
):
    """The live concept, or (None, problems by artifact). ``languages``: code items allowed
    (and required in each of them), verified later by ``run_code``. Free-text prompts are
    required when the outline assesses by "explain"."""
    problems: dict[str, list[str]] = {"lesson": [], "quiz": []}
    found = quiz.get("quiz")
    # Items past the tenth are dropped rather than failing a whole round (a live run wrote 11).
    items: list = found[:10] if isinstance(found, list) else []
    if not 4 <= len(items) <= 10:
        problems["quiz"].append(f"Write 5-8 items; got {len(items)}.")
    parsed, broken = [], []
    for raw in items:
        try:
            item = {**raw, "kind": raw.get("kind", "mcq")} if languages else {**raw, "kind": "mcq"}
            if item["kind"] not in {"mcq", "output"}:
                raise TypeError(f"kind {item['kind']} is not allowed; use mcq or output")
            if item["kind"] == "mcq":
                item.pop("code", None)
                spoken = dialect.spoken(
                    str(item.get("prompt", "")),
                    *[str(o) for o in item.get("options") or []],
                    str(item.get("explanation", "")),
                )
                if len(languages) > 1 and spoken and not set(languages) <= spoken:
                    raise TypeError(
                        f"uses {', '.join(sorted(spoken))} syntax, but learners of "
                        f"{', '.join(languages)} all see it; keep it language-neutral"
                    )
            elif set(item.get("code") or {}) != set(languages):
                raise TypeError(f"an output item needs code in exactly: {', '.join(languages)}")
            parsed.append(QuizItem.model_validate(item))
        except (ValidationError, TypeError) as exc:
            where = raw.get("id", "?") if isinstance(raw, dict) else "?"
            detail = errors_of(exc) if isinstance(exc, ValidationError) else [str(exc)]
            broken.append(f"item {where}: {'; '.join(detail)}")
    # A malformed item is dropped (never repaired into a question nobody wrote) while the
    # quiz keeps enough sound items; otherwise it goes back to the author.
    if len(parsed) < 4:
        problems["quiz"] += broken
    if len({q.id for q in parsed}) != len(parsed):
        problems["quiz"].append("Quiz item ids must be unique.")
    found = quiz.get("prompts")
    raw_prompts: list = found if isinstance(found, list) else []
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
    tasks: list[Task] = []
    bad_tasks = []
    for raw in quiz.get("tasks", []) if isinstance(quiz.get("tasks"), list) else []:
        try:
            tasks.append(Task.model_validate(raw))
        except (ValidationError, TypeError) as exc:
            where = raw.get("id", "?") if isinstance(raw, dict) else "?"
            detail = errors_of(exc) if isinstance(exc, ValidationError) else [str(exc)]
            bad_tasks.append(f"task {where}: {'; '.join(detail)}")
    if not tasks:  # one sound task is enough; a malformed extra is dropped
        problems["quiz"] += bad_tasks
    sequence = [s for s in quiz.get("sequence", []) if isinstance(s, str)][:24]
    exercises: list[Exercise] = []
    if workbench:
        exercises, bad = check_exercises(quiz.get("exercises"))
        problems["quiz"].extend(bad)
    experiments: list[Experiment] = []
    if lab:
        experiments, bad = check_experiments(quiz.get("experiments"))
        problems["quiz"].extend(bad)
    # The sequence only orders activities. One naming an activity that is not there (a typo,
    # or one dropped above as malformed) is left out instead of failing the whole package: a
    # live run spent all three rounds rewriting the lesson over a quiz-side slip.
    made = {f"prompt:{x.id}" for x in prompts} | {f"task:{x.id}" for x in tasks}
    made |= {f"exercise:{x.id}" for x in exercises} | {f"experiment:{x.id}" for x in experiments}
    # Visuals are drawn after this check, so a "visual:0" the model sequenced is not there yet.
    made |= {f"visual:{i}" for i in range(len(concept.visuals))}
    sequence = [
        s
        for s in sequence
        if s in made
        or s.split(":", 1)[0] not in {"prompt", "task", "exercise", "experiment", "visual"}
    ]
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
                "tasks": tasks,
                "sequence": sequence,
                "exercises": exercises,
                "experiments": experiments,
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


_ATOM_KEYS = set(Atom.model_fields)
_STEP_KEYS = set(Step.model_fields)
INTERACTIVE = {"faded", "visualizer", "trace", "predict", "debug", "explanation", "classify"}


def tidy_atom(atom):
    """Deterministic repairs of an atom the model got almost right, instead of a new round:
    unknown keys dropped, a missing or out-of-range duration set within bounds, a hook cut to
    its first two sentences, checks too short to be questions dropped, and an interactive
    atom left without any check (or a micro-lesson without a misconception) shown as a plain
    concept card. Nothing a learner is graded on is invented."""
    if not isinstance(atom, dict):
        return atom
    out = {k: v for k, v in atom.items() if k in _ATOM_KEYS}
    if isinstance(out.get("id"), str):  # "Hook_1" or "atom 2" -> a valid kebab-case id
        slug = re.sub(r"[^a-z0-9]+", "-", out["id"].lower()).strip("-")
        out["id"] = (slug if slug[:1].isalpha() else f"a-{slug}")[:64] or "atom"
    seconds = out.get("seconds")
    out["seconds"] = min(120, max(10, seconds)) if isinstance(seconds, int) else 60
    if isinstance(out.get("steps"), list):
        out["steps"] = [
            {k: v for k, v in s.items() if k in _STEP_KEYS}
            for s in out["steps"]
            if isinstance(s, dict) and len(str(s.get("prompt", "")).strip()) >= 5
        ]
    if out.get("kind") == "hook" and isinstance(out.get("body"), str):
        sentences = re.split(r"(?<=[.!?])\s+", out["body"].strip())
        out["body"] = " ".join(sentences[:2])
    if not str(out.get("body", "")).strip() and str(out.get("why", "")).strip():
        out["body"] = out["why"]
    limit = 80 if out.get("kind") == "pattern" else 120
    if isinstance(out.get("body"), str) and len(out["body"].split()) > limit:
        kept: list[str] = []
        for sentence in re.split(r"(?<=[.!?])\s+", out["body"].strip()):
            if len(" ".join([*kept, sentence]).split()) > limit:
                break
            kept.append(sentence)
        out["body"] = " ".join(kept) or " ".join(out["body"].split()[:limit])
    if (out.get("kind") in INTERACTIVE and not out.get("steps")) or (
        out.get("kind") == "micro" and not out.get("misconception")
    ):
        out["kind"] = "concept"
        out.pop("adapters", None)
    return out


def build_atoms(
    course: Course, concept: Concept, atoms: dict, version: int, languages: Sequence[str] = ()
):
    """A draft pack, or (None, problems). ``languages``: code adapters allowed (and needed in
    each of them); their output is filled in by ``run_code``."""
    found = atoms.get("atoms")
    raw: list = [tidy_atom(a) for a in found[:8]] if isinstance(found, list) else []
    # An atom with nothing for the learner to read is dropped while enough remain.
    filled = [a for a in raw if not isinstance(a, dict) or str(a.get("body", "")).strip()]
    if len(filled) >= 3:
        raw = filled
    problems: list[str] = []
    if not 3 <= len(raw) <= 8:
        problems.append(f"Write 4-8 atoms; got {len(raw)}.")
    kinds = {a.get("kind") for a in raw if isinstance(a, dict)}
    if kinds - ATOM_KINDS:
        problems.append(f"Kinds {sorted(map(str, kinds - ATOM_KINDS))} are not allowed here.")
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


def imprecise_notes(facts: dict | None) -> dict[str, list[str]]:
    """Revision notes for fact claims judged imprecise: wording that overstates or leaves a
    wrong impression, but is not wrong. A package carrying only these passes ``verdict``; it is
    worth one more round (``jobs.run_package``), not a block. Incorrect claims are not here:
    they fail the package outright."""
    notes: dict[str, list[str]] = {"lesson": [], "quiz": [], "atoms": []}
    for claim in (facts or {}).get("claims", []):
        if not isinstance(claim, dict) or claim.get("verdict") != "imprecise":
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
            f"[imprecise] {where}: {claim.get('claim', '')} → {claim.get('correction', '')}"
        )
    return notes


def verdict(
    facts: dict | None, review: dict | None, style: bool = False, floor: int = 3
) -> tuple[bool, dict[str, list[str]], dict]:
    """Pass/fail from the fact claims and rubric, plus revision notes by artifact.
    ``style``: the course has a learning style, so style_fit is scored too. A lesson passes when
    nothing is defective: no ``incorrect`` claim and every rubric score at or above ``floor``.
    Scores under target but at the floor are warnings (see validation), not blockers."""
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
    passed = not blocking and facts is not None and all(scores[d] >= floor for d in dimensions)
    return passed, notes, scores
