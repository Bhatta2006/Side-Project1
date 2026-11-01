"""Exercise Engineer: one judged problem for a live concept, verified by execution.

The engineer writes the problem with a Python reference, a brute force, two input
generators, a deliberately wrong solution, references in the course's other languages and
starters. Every piece runs in the execution plane (``execute``): generators make the inputs,
the reference makes the expected outputs, and release needs the documented examples to
match, the brute force to agree on small inputs, every language to agree, and the wrong
solution to fail. A reviewer then checks the statement against the lesson. The tests are
stored with the problem, so learners are judged exactly as on hand-authored problems.
"""

import json

from pydantic import ValidationError
from sqlalchemy.orm import Session

from socrat.catalog import generated
from socrat.catalog.registry import Catalog
from socrat.catalog.schema import Course, Problem, Provenance
from socrat.coursegen import execute, roles
from socrat.coursegen import package as pkg
from socrat.judge.service import normalized
from socrat.models import GeneratedCourse, GenerationJob, need

GENERATED = 14  # hidden tests from the generator, as for hand-authored problems
SMALL = 10  # small inputs for the brute-force check
WRAP = """
import json as _json
import random as _random

_rng = _random.Random({seed})
_out = []
for _case in cases(_rng):
    _case = str(_case)
    _out.append(_case if _case.endswith("\\n") else _case + "\\n")
    if len(_out) >= {limit}:
        break
print(_json.dumps(_out))
"""
DIMENSIONS = ("correctness", "alignment", "clarity", "difficulty")

ENGINEER = """You are the Exercise Engineer for Socrat. Write one programming problem that
makes the learner apply this concept, judged by stdin/stdout tests like an online judge.

- The statement is self-contained: story-free unless it helps, exact input and output
  formats, constraints, 1-3 worked examples whose outputs you have computed carefully.
- Difficulty fits the concept; it needs the concept's idea, not unrelated tricks.
- hints: 2-5, from a nudge to nearly the idea. approach: how and why the solution works.
- reference: a correct, clear Python 3 program reading stdin and printing stdout.
- brute: an obviously correct slow Python program (it only meets small inputs).
- generator and small_generator: Python defining cases(rng) that yields input strings,
  using only rng (a random.Random); generator covers edge cases and stays small enough
  that all its inputs together are under 10000 characters; small_generator yields tiny cases.
- wrong: a plausible Python solution with the mistake learners make most (from the
  misconceptions); the tests must catch it.
- references: the same program in each course language other than Python; starter: a
  short skeleton per course language that reads the input and leaves the logic to the
  learner. Standard library only. Output is deterministic; no floating-point output
  unless it is rounded to a stated precision.

Reply with one JSON object only:
{"problem": {"id": "kebab-case", "title": "...", "difficulty": "easy|medium|hard",
             "statement": "...", "input_format": "...", "output_format": "...",
             "constraints": ["..."], "examples": [{"input": "...", "output": "...", "explanation": "..."}],
             "hints": ["..."], "approach": "...", "reference": "...", "brute": "...",
             "generator": "...", "small_generator": "...",
             "references": {"cpp": "..."}, "starter": {"python": "..."}},
 "wrong": "python program"}"""

REVIEW = """You are the Reviewer for Socrat's judged exercises. The code has already run:
the reference agrees with a brute force and the tests catch a wrong solution. Judge what
execution cannot: does the problem exercise the concept's objectives, is the statement
exact and unambiguous, are hints and approach correct and helpful, does the difficulty fit.

Score 1-5 each: correctness (statement, examples, approach), alignment (needs this
concept), clarity, difficulty (fits the learner at this point).

Reply with one JSON object only:
{"scores": {"correctness": 1, "alignment": 1, "clarity": 1, "difficulty": 1},
 "summary": "2-3 sentences", "fixes": ["specific fixes"]}"""


def engineer_prompt(
    ctx: str, lesson: str, course: Course, draft: dict | None, notes: list[str]
) -> str:
    parts = [ctx, "Lesson:\n" + lesson]
    if course.problems:
        titles = "\n".join(f"- {p.title}: {p.statement[:160]}" for p in course.problems)
        parts.append("Problems the course already has (write a different one):\n" + titles)
    if draft is not None:
        parts.append("Your previous draft:\n" + json.dumps(draft, indent=1))
    if notes:
        parts.append("Fix all of these in a complete revised reply:\n- " + "\n- ".join(notes))
    return "\n\n".join(parts)


def line(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


async def _inputs(executor, code: str, seed: str, limit: int) -> tuple[list[str], str]:
    [case] = await executor.run("python", code + WRAP.format(seed=repr(seed), limit=limit), [""])
    if not execute.ok(case):
        return [], execute.describe(case)
    try:
        values = json.loads(case["stdout"])
    except ValueError:
        return [], "it did not yield strings"
    if not isinstance(values, list) or not values or not all(isinstance(v, str) for v in values):
        return [], "it yielded no input strings"
    return values, ""


async def verify(executor, course: Course, concept_id: str, reply: dict, taken: set[str]):
    """The problem with its tests, or (None, problems for the engineer)."""
    raw = reply.get("problem") if isinstance(reply.get("problem"), dict) else None
    wrong = reply.get("wrong")
    if raw is None or not isinstance(wrong, str) or not wrong.strip():
        return None, ['Reply with {"problem": {...}, "wrong": "python program"}.']
    try:
        problem = Problem.model_validate(
            {**raw, "concepts": [concept_id], "tests": [], "review": None, "provenance": None}
        )
    except ValidationError as exc:
        return None, pkg.errors_of(exc)
    problems = []
    if problem.id in taken:
        problems.append(f"The id {problem.id} is taken; choose another.")
    for name in ("brute", "generator", "small_generator"):
        if not getattr(problem, name).strip():
            problems.append(f"{name} is required.")
    missing = [lang for lang in course.languages if lang not in problem.starter]
    missing_refs = [lang for lang in course.languages if lang != "python"]
    missing_refs = [lang for lang in missing_refs if lang not in problem.references]
    if missing:
        problems.append(f"Add a starter for {', '.join(missing)}.")
    if missing_refs:
        problems.append(f"Add references for {', '.join(missing_refs)}.")
    if problems:
        return None, problems

    generated_inputs, why = await _inputs(executor, problem.generator, problem.id, GENERATED)
    if why:
        return None, [f"The generator failed ({why})."]
    small, why = await _inputs(executor, problem.small_generator, problem.id + ":small", SMALL)
    if why:
        return None, [f"The small generator failed ({why})."]
    examples = [line(e.input) for e in problem.examples]
    inputs = list(dict.fromkeys([*examples, *generated_inputs, *small]))
    if sum(map(len, inputs)) > 200_000:
        return None, ["The inputs are too large; keep all generated inputs small."]

    outputs = await executor.run("python", problem.reference, inputs)
    failed = [(i, o) for i, o in zip(inputs, outputs, strict=True) if not execute.ok(o)]
    if failed:
        shown = "; ".join(f"input {i[:80]!r}: {execute.describe(o)}" for i, o in failed[:3])
        return None, [f"The reference fails on {len(failed)} inputs: {shown}"]
    expected = dict(zip(inputs, outputs, strict=True))
    for example in problem.examples:
        actual = expected[line(example.input)]
        if not execute.agree(actual, {**actual, "stdout": example.output}):
            problems.append(
                f"Example input {example.input[:80]!r}: the statement says "
                f"{example.output[:80]!r} but the reference prints {actual['stdout'][:80]!r}."
            )
    checked = list(dict.fromkeys([*examples, *small]))
    brute = await executor.run("python", problem.brute, checked)
    for stdin, result in zip(checked, brute, strict=True):
        if not execute.agree(result, expected[stdin]):
            problems.append(
                f"The brute force and the reference disagree on {stdin[:80]!r}: "
                f"brute {execute.describe(result) if not execute.ok(result) else result['stdout'][:80]!r}, "
                f"reference {expected[stdin]['stdout'][:80]!r}."
            )
            break
    for lang, source in problem.references.items():
        if lang not in course.languages:
            continue
        results = await executor.run(lang, source, inputs)
        bad = [i for i, r in zip(inputs, results, strict=True) if not execute.agree(r, expected[i])]
        if bad:
            problems.append(
                f"The {lang} reference differs from the Python one on {len(bad)} inputs, "
                f"e.g. {bad[0][:80]!r}."
            )
    caught = await executor.run("python", wrong, inputs)
    if all(execute.agree(r, expected[i]) for i, r in zip(inputs, caught, strict=True)):
        problems.append(
            "The wrong solution passes every test: make the generator produce the cases "
            "that expose the mistake."
        )
    public = set(examples)
    tests = [
        {
            "input": stdin,
            "expected": normalized(expected[stdin]["stdout"]) + "\n",
            "public": stdin in public,
        }
        for stdin in inputs
    ]
    if sum(not t["public"] for t in tests) < 3:
        problems.append("Generate more distinct inputs: at least 3 hidden tests are needed.")
    if problems:
        return None, problems
    return Problem.model_validate({**problem.model_dump(mode="json"), "tests": tests}), []


def passed(review: dict | None) -> tuple[bool, dict, list[str]]:
    scores = {}
    for dim in DIMENSIONS:
        try:
            scores[dim] = int((review or {}).get("scores", {}).get(dim, 0))
        except (TypeError, ValueError):
            scores[dim] = 0
    fixes = [str(f) for f in (review or {}).get("fixes", []) if f][:10]
    ok = scores["correctness"] == 5 and all(scores[d] >= 4 for d in DIMENSIONS)
    return ok, scores, fixes


async def run_exercise(engine, settings, base: Catalog, job_id: str, make, executor) -> None:
    from socrat.coursegen import jobs
    from socrat.coursegen.outline import Brief

    with Session(engine) as db:
        job = need(db.get(GenerationJob, job_id))
        course_id, concept_id = job.course_id, job.target
        brief = Brief.model_validate(need(db.get(GeneratedCourse, course_id)).brief)
        course = need(generated.course(db, course_id))
    concept = course.concept(concept_id)
    if concept.status != "live":
        raise ValueError(f"{course_id}:{concept_id} is not live")
    needed = sorted({"python", *course.languages})
    missing = sorted(set(needed) - set(executor.available(needed)))
    if missing:
        jobs._note(
            engine,
            job_id,
            {"role": "system", "event": "execution_unavailable", "languages": missing},
            state="failed",
            error=f"No execution worker for {', '.join(missing)}; exercises need one to "
            "verify their tests. Try again when the execution service is up.",
        )
        return
    ctx = pkg.context(base, course, brief.model_dump(), concept)
    taken = set(base.problems) | {p.id for p in course.problems}
    draft, notes = None, list[str]()
    for attempt in range(1, jobs.ROUNDS + 1):
        if jobs._over_budget(engine, course_id, brief.budget_usd):
            jobs.pause_for_budget(engine, course_id, job_id)
            return
        if jobs._job_cost(engine, job_id) >= brief.concept_budget_usd:
            jobs._note(engine, job_id, {"role": "system", "event": "concept_budget_reached"})
            break
        prompt = engineer_prompt(ctx, concept.lesson, course, draft, notes)
        reply = await roles.ask(engine, settings, "engineer", ENGINEER, prompt, 16000, make)
        if reply.data is None:
            notes = [reply.problem]
            entry = {"role": "engineer", "round": attempt, "issues": notes}
            jobs._note(engine, job_id, entry, reply.cost_usd)
            continue
        draft = reply.data
        problem, notes = await verify(executor, course, concept_id, draft, taken)
        entry = {
            "role": "engineer",
            "round": attempt,
            "tests": len(problem.tests) if problem else 0,
            "issues": notes,
        }
        jobs._note(engine, job_id, entry, reply.cost_usd, output={"exercise": draft})
        if problem is None:
            continue
        shown = problem.model_dump(mode="json", exclude={"tests"})
        review_prompt = (
            f"{ctx}\n\nLesson:\n{concept.lesson}\n\nProblem:\n{json.dumps(shown, indent=1)}"
        )
        review = await roles.ask(engine, settings, "reviewer", REVIEW, review_prompt, 4000, make)
        ok, scores, notes = passed(review.data)
        summary = str((review.data or {}).get("summary", review.problem))[:1000]
        entry = {
            "role": "reviewer",
            "round": attempt,
            "verdict": "pass" if ok else "revise",
            "scores": scores,
            "summary": summary,
            "issues": notes,
        }
        jobs._note(engine, job_id, entry, review.cost_usd)
        if not ok:
            notes = notes or ["The reviewer asked for a revision; tighten the statement."]
            continue
        released = problem.model_copy(
            update={
                "provenance": Provenance(
                    author=pkg.AI_AUTHOR,
                    attribution_md=(
                        f"Written by the {pkg.AI_AUTHOR}; its tests were generated and "
                        "verified by running the code, then reviewed by an AI model. "
                        "Not reviewed by a person."
                    ),
                )
            }
        )
        with Session(engine) as db, db.begin():
            generated.add_problem(db, base, course_id, concept_id, released)
        entry = {"role": "system", "event": "released", "problem": released.id}
        jobs._note(engine, job_id, entry, state="done")
        return
    jobs._note(
        engine,
        job_id,
        {"role": "system", "event": "not_released"},
        state="failed",
        error="The exercise did not pass every gate; see the log.",
    )
