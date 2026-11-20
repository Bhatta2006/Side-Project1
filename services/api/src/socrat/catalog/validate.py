"""Quality gates for judge problems (drafted or authored).

Each gate reports pass, warn, fail or skip with a one-line detail:

- schema       the YAML validates against `catalog.schema.Problem`
- examples     the Python reference reproduces every example output
- brute        the reference agrees with a brute-force solution on many small inputs
- timing       the reference handles the largest generated input well inside the limit
- languages    C++ / Java references (when present) agree with the Python reference
- originality  no near-identical title in the practice library, no near-duplicate statement
- difficulty   the difficulty label fits the concept's tier and the constraint sizes

Drafted problems run in strict mode: a brute force is required. Problem code is authoring
code run on a content machine (never on the API host), with timeouts.
"""

import difflib
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from pydantic import ValidationError

from socrat.catalog.schema import Problem

SMALL_CASES = 300
MAX_GENERATED = 14
TITLE_SAME, TITLE_WARN = 0.92, 0.82
STATEMENT_FAIL, STATEMENT_WARN = 0.8, 0.5
LABEL_RANK = {"easy": 1, "medium": 2, "hard": 3}

# Runs a solution once per input inside one interpreter: stdin/stdout are swapped per case.
_HARNESS = r"""
import io, json, sys
code, inputs = json.loads(sys.stdin.read())
compiled = compile(code, "<solution>", "exec")
out = []
real_stdout = sys.stdout
for text in inputs:
    # Byte-backed streams so solutions may use sys.stdin.buffer / sys.stdout.buffer.
    sys.stdin = io.TextIOWrapper(io.BytesIO(text.encode()), encoding="utf-8")
    sink = io.BytesIO()
    sys.stdout = io.TextIOWrapper(sink, encoding="utf-8", newline="", write_through=True)
    try:
        exec(compiled, {"__name__": "__main__"})
        ok = True
    except SystemExit:
        ok = True
    except BaseException as exc:
        ok, error = False, f"{type(exc).__name__}: {exc}"
    wrapper = sys.stdout
    try:
        wrapper.flush()
    except Exception:
        pass
    printed = sink.getvalue().decode("utf-8", "replace")
    sys.stdout = real_stdout
    try:
        wrapper.detach()  # keep the wrapper from closing anything when collected
    except Exception:
        pass
    out.append([True, printed] if ok else [False, error])
real_stdout.write(json.dumps(out))
"""


@dataclass
class Gate:
    name: str
    status: str  # pass | warn | fail | skip
    detail: str


def normalize(text: str) -> str:
    """Mirror the judge: trailing spaces and blank edges never matter."""
    lines = text.replace("\r\n", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip("\n")


def run_many(code: str, inputs: list[str], timeout: float = 120) -> list[tuple[bool, str]]:
    result = subprocess.run(
        [sys.executable, "-I", "-c", _HARNESS],
        input=json.dumps([code, inputs]).encode(),
        capture_output=True,
        timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace")[-600:])
    return [(ok, text) for ok, text in json.loads(result.stdout)]


def run_once(
    command: list[str], stdin: str, timeout: float, env: dict | None = None
) -> tuple[str, float]:
    start = time.perf_counter()
    result = subprocess.run(
        command, input=stdin.encode(), capture_output=True, timeout=timeout, env=env
    )
    elapsed = time.perf_counter() - start
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace")[-600:])
    return result.stdout.decode(), elapsed


def cases(generator: str, seed: str, limit: int) -> list[str]:
    if not generator:
        return []
    namespace: dict = {}
    exec(generator, namespace)  # Authoring code, reviewed before it ships.
    rng = random.Random(seed)
    out: list[str] = []
    for value in namespace["cases"](rng):
        out.append(value if value.endswith("\n") else value + "\n")
        if len(out) >= limit:
            break
    return out


def _shingles(text: str) -> set[tuple[str, ...]]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {tuple(words[i : i + 3]) for i in range(max(0, len(words) - 2))}


def _title_key(title: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", title.lower()))


SIZE_LINE = re.compile(r"\b[nmqkt]\b|length|\|s\||number of|size", re.IGNORECASE)
VALUE_LINE = re.compile(r"_i\b|\[i\]|\beach\b|value", re.IGNORECASE)


def max_constraint(constraints: list[str]) -> int:
    """Largest input-size bound (n, q, |s|, …) written as 10^k, 2 * 10^5, 1e9 or a number.

    Value bounds such as `|a_i| ≤ 10^9` are ignored: they say nothing about running time.
    """
    best = 0
    for line in constraints:
        if not SIZE_LINE.search(line) or VALUE_LINE.search(line):
            continue
        text = line.replace(",", "").replace("·", "*").replace("×", "*")
        for coef, exp in re.findall(r"(?:(\d+)\s*\*\s*)?10\s*\^\s*\{?(\d+)\}?", text):
            best = max(best, int(coef or 1) * 10 ** int(exp))
        for coef, exp in re.findall(r"(\d+)e(\d+)", text):
            best = max(best, int(coef) * 10 ** int(exp))
        for number in re.findall(r"\b\d{2,}\b", text):
            best = max(best, int(number))
    return best


def check_schema(raw: dict) -> tuple[Gate, Problem | None]:
    try:
        return Gate("schema", "pass", "Valid problem YAML."), Problem.model_validate(raw)
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(str(p) for p in first["loc"])
        return Gate("schema", "fail", f"{where}: {first['msg']}"), None


def check_examples(problem: Problem) -> Gate:
    inputs = [e.input if e.input.endswith("\n") else e.input + "\n" for e in problem.examples]
    results = run_many(problem.reference, inputs)
    for example, (ok, output) in zip(problem.examples, results, strict=True):
        if not ok:
            return Gate("examples", "fail", f"Reference crashed on an example: {output}")
        if normalize(output) != normalize(example.output):
            return Gate("examples", "fail", f"Example output differs for input {example.input!r}.")
    return Gate("examples", "pass", f"Reference reproduces all {len(inputs)} examples.")


def check_brute(problem: Problem, strict: bool, count: int = SMALL_CASES) -> Gate:
    if not problem.brute:
        status = "fail" if strict else "warn"
        return Gate("brute", status, "No brute-force solution to cross-check the reference.")
    small = cases(problem.small_generator, f"{problem.id}:small", count)
    if not small:
        small = [c for c in cases(problem.generator, problem.id, MAX_GENERATED) if len(c) < 400]
    if not small:
        return Gate("brute", "fail", "No small inputs: add a small_generator.")
    expected = run_many(problem.reference, small)
    actual = run_many(problem.brute, small)
    for text, (ok_ref, ref), (ok_brute, brute) in zip(small, expected, actual, strict=True):
        if not ok_ref:
            return Gate("brute", "fail", f"Reference crashed on {text!r}: {ref}")
        if not ok_brute:
            return Gate("brute", "fail", f"Brute force crashed on {text!r}: {brute}")
        if normalize(ref) != normalize(brute):
            return Gate("brute", "fail", f"Reference and brute force disagree on {text!r}.")
    return Gate("brute", "pass", f"Reference matches the brute force on {len(small)} inputs.")


def check_timing(problem: Problem) -> Gate:
    generated = cases(problem.generator, problem.id, MAX_GENERATED)
    if not generated:
        return Gate("timing", "warn", "No generator, so no large tests to time.")
    largest = max(generated, key=len)
    limit = problem.time_limit_ms / 1000
    try:
        _, elapsed = run_once([sys.executable, "-I", "-c", problem.reference], largest, limit * 3)
    except subprocess.TimeoutExpired:
        return Gate("timing", "fail", f"Reference exceeds {limit * 3:.1f}s on the largest test.")
    detail = f"{elapsed * 1000:.0f} ms on the largest test ({len(largest):,} chars), limit {problem.time_limit_ms} ms."
    if elapsed > limit:
        return Gate("timing", "fail", detail)
    return Gate("timing", "warn" if elapsed > limit / 2 else "pass", detail)


def _compile(language: str, source: str, folder: Path) -> list[str] | None:
    from runner.toolchains import toolchains

    tools = toolchains()
    if language not in tools:
        return None
    if language == "cpp":
        compiler = tools["cpp"][0]
        (folder / "main.cpp").write_text(source, encoding="utf-8")
        binary = folder / ("main.exe" if sys.platform == "win32" else "main")
        subprocess.run(
            [compiler, "-std=c++20", "-O2", "-o", str(binary), str(folder / "main.cpp")],
            check=True,
            capture_output=True,
            timeout=120,
            env={
                **os.environ,
                "PATH": str(Path(compiler).parent) + os.pathsep + os.environ.get("PATH", ""),
            },
        )
        return [str(binary)]
    if language == "python":
        (folder / "reference.py").write_text(source, encoding="utf-8")
        return [tools["python"][0], "-I", str(folder / "reference.py")]
    javac, java = tools["java"]
    match = re.search(r"public\s+class\s+([A-Za-z_$][\w$]*)", source)
    class_name = match.group(1) if match else "Main"
    (folder / f"{class_name}.java").write_text(source, encoding="utf-8")
    subprocess.run(
        [javac, str(folder / f"{class_name}.java")], check=True, capture_output=True, timeout=120
    )
    return [java, "-cp", str(folder), class_name]


def check_languages(problem: Problem) -> Gate:
    from runner.toolchains import toolchains

    if not problem.references:
        return Gate("languages", "skip", "No C++/Java references yet (Python reference only).")
    inputs = [e.input if e.input.endswith("\n") else e.input + "\n" for e in problem.examples]
    inputs += cases(problem.generator, problem.id, MAX_GENERATED)
    expected = run_many(problem.reference, inputs)
    checked, skipped = [], []
    for language, source in problem.references.items():
        with tempfile.TemporaryDirectory() as tmp:
            try:
                command = _compile(language, source, Path(tmp))
            except subprocess.CalledProcessError as exc:
                return Gate(
                    "languages",
                    "fail",
                    f"{language} reference does not compile: {exc.stderr.decode(errors='replace')[-300:]}",
                )
            if command is None:
                skipped.append(language)
                continue
            limit = problem.time_limit_ms / 1000
            for text, (_, want) in zip(inputs, expected, strict=True):
                try:
                    tool = toolchains()[language][0]
                    env = {
                        **os.environ,
                        "PATH": str(Path(tool).parent) + os.pathsep + os.environ.get("PATH", ""),
                    }
                    got, elapsed = run_once(command, text, limit * 3, env)
                except (RuntimeError, subprocess.TimeoutExpired) as exc:
                    return Gate("languages", "fail", f"{language} reference failed: {exc}")
                if normalize(got) != normalize(want):
                    return Gate(
                        "languages", "fail", f"{language} reference disagrees on {text[:60]!r}."
                    )
                if elapsed > limit:
                    return Gate(
                        "languages", "fail", f"{language} reference too slow ({elapsed:.2f}s)."
                    )
            checked.append(language)
    if not checked:
        return Gate("languages", "skip", f"No local toolchain for {', '.join(skipped)}.")
    note = f"; no toolchain for {', '.join(skipped)}" if skipped else ""
    return Gate("languages", "pass", f"{', '.join(checked)} agree on {len(inputs)} tests{note}.")


def check_originality(
    problem: Problem, library_titles: list[str], others: dict[str, str], strict: bool = True
) -> Gate:
    key = _title_key(problem.title)
    best, match = 0.0, ""
    matcher = difflib.SequenceMatcher(a=key)
    for title in library_titles:
        other = _title_key(title)
        matcher.set_seq2(other)
        if matcher.real_quick_ratio() < TITLE_WARN or matcher.quick_ratio() < TITLE_WARN:
            continue
        ratio = matcher.ratio()
        if ratio > best:
            best, match = ratio, title
    mine = _shingles(problem.statement)
    closest, closest_id = 0.0, ""
    for other_id, statement in others.items():
        if other_id == problem.id:
            continue
        theirs = _shingles(statement)
        if mine and theirs:
            overlap = len(mine & theirs) / len(mine | theirs)
            if overlap > closest:
                closest, closest_id = overlap, other_id
    if closest >= STATEMENT_FAIL:
        # Drafts must be new; authored sibling variants (range sum / range min) only warn.
        return Gate(
            "originality",
            "fail" if strict else "warn",
            f"Statement nearly duplicates Socrat problem '{closest_id}'.",
        )
    if closest >= STATEMENT_WARN:
        return Gate(
            "originality",
            "warn",
            f"Statement is close to Socrat problem '{closest_id}'; make sure it teaches something new.",
        )
    if best >= TITLE_WARN:
        # Classic names (N-Queens, LCS) are generic; the statement itself must be original.
        same = "matches" if best >= TITLE_SAME else "resembles"
        return Gate(
            "originality",
            "warn",
            f"Title {same} the library problem '{match}'; keep the statement original.",
        )
    return Gate("originality", "pass", "No similar library title or Socrat statement.")


def check_difficulty(problem: Problem, concept_difficulty: int | None) -> Gate:
    rank = LABEL_RANK[problem.difficulty]
    bound = max_constraint(problem.constraints)
    notes = []
    if concept_difficulty is not None:
        expected = 1 if concept_difficulty <= 2 else 2 if concept_difficulty == 3 else 3
        if abs(rank - expected) >= 2:
            notes.append(
                f"labelled {problem.difficulty} but the concept is tier {concept_difficulty} of 5"
            )
    if rank == 3 and 0 < bound <= 100:
        notes.append("labelled hard with tiny inputs (≤100)")
    if notes:
        return Gate("difficulty", "warn", "; ".join(notes).capitalize() + ".")
    size = f"max bound {bound:,}" if bound else "no numeric bound"
    return Gate(
        "difficulty", "pass", f"{problem.difficulty.capitalize()} fits the concept tier ({size})."
    )


def validate(
    raw: dict,
    *,
    strict: bool,
    library_titles: list[str],
    statements: dict[str, str],
    concept_difficulty: dict[str, int],
    run_code: bool = True,
) -> list[Gate]:
    """All gates for one problem; later gates are skipped when the schema fails."""
    schema, problem = check_schema(raw)
    if problem is None:
        return [schema]
    gates = [schema]
    if run_code:
        for check in (
            lambda: check_examples(problem),
            lambda: check_brute(problem, strict),
            lambda: check_timing(problem),
            lambda: check_languages(problem),
        ):
            try:
                gates.append(check())
            except (RuntimeError, subprocess.TimeoutExpired, SyntaxError, KeyError) as exc:
                name = ["examples", "brute", "timing", "languages"][len(gates) - 1]
                gates.append(Gate(name, "fail", f"{type(exc).__name__}: {str(exc)[:300]}"))
    gates.append(check_originality(problem, library_titles, statements, strict))
    tiers = [concept_difficulty[c] for c in problem.concepts if c in concept_difficulty]
    gates.append(check_difficulty(problem, max(tiers) if tiers else None))
    return gates


def verdict(gates: list[Gate]) -> str:
    if any(g.status == "fail" for g in gates):
        return "fail"
    return "warn" if any(g.status == "warn" for g in gates) else "pass"


def as_dicts(gates: list[Gate]) -> list[dict]:
    return [asdict(g) for g in gates]


def library_titles() -> list[str]:
    """Titles of known outside problems a new problem must not copy: none are kept in the app."""
    return []


def statements_of(catalog, extra: dict[str, str] | None = None) -> dict[str, str]:
    out = {pid: problem.statement for pid, (_, problem) in catalog.problems.items()}
    out.update(extra or {})
    return out


def concept_tiers(catalog, course_id: str) -> dict[str, int]:
    if course_id not in catalog.courses:
        return {}
    return {c.id: c.difficulty for c in catalog.course(course_id).concepts}


def validate_file(
    path: Path, catalog, *, strict: bool, titles: list[str], statements: dict[str, str]
) -> dict:
    """Validate one problem YAML whose course is the folder two levels up (…/<course>/…)."""
    import yaml

    course_id = path.parent.parent.name if path.parent.name == "problems" else path.parent.name
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        gates = [Gate("schema", "fail", f"YAML does not parse: {str(exc)[:200]}")]
        return dict(
            id=path.stem, course=course_id, path=str(path), gates=as_dicts(gates), verdict="fail"
        )
    gates = validate(
        raw,
        strict=strict,
        library_titles=titles,
        statements=statements,
        concept_difficulty=concept_tiers(catalog, course_id),
    )
    return dict(
        id=raw.get("id", path.stem),
        title=raw.get("title", ""),
        course=course_id,
        path=str(path),
        gates=as_dicts(gates),
        verdict=verdict(gates),
    )
