"""Deterministic reading of a finished submission: why hidden tests failed, and how fast the code is.

Nothing here calls a model. The server keeps every test's expected output, so it can say
*why* a hidden case failed without showing the case. The complexity figure is an estimate read
from the loop structure of the learner's code, and says so.
"""

import ast
import re

from socrat.models import Submission

INT32_MAX = 2**31 - 1
_INTEGER = re.compile(r"-?\d+")
_INT_TYPE = re.compile(r"\bint\b")
_SORTS = re.compile(
    r"\b(?:sort|stable_sort|sorted|Arrays\.sort|Collections\.sort)\s*\(|\.sort\s*\("
)
_GROWING = re.compile(
    r"\b(?:vector|map|unordered_map|set|unordered_set|multiset|deque|priority_queue|"
    r"ArrayList|HashMap|HashSet|TreeMap|LinkedList|ArrayDeque|StringBuilder|new\s+\w+\s*\[)"
)
_LOOP_HEAD = re.compile(r"\b(for|while)\b")
LONG_TYPE = {"cpp": "long long", "java": "long"}


def diagnosis(job: Submission) -> str | None:
    """A plain cause for a failed submit when the evidence is certain, else None.

    The one cause found so far: the visible tests pass, a hidden test expects a number that does
    not fit in 32 bits, and the code uses ``int``. That is overflow, and the fix is the type.
    """
    if job.mode != "submit" or job.status != "done" or job.verdict != "wrong_answer":
        return None
    wide = LONG_TYPE.get(job.language)
    if wide is None or not _INT_TYPE.search(_strip(job.source, job.language)):
        return None
    public = [c for c in job.cases if c.get("public")]
    if not all(c["status"] == "passed" for c in public):
        return None  # The logic is wrong on a visible case; the type is not the first problem.
    for case, test in zip(job.cases, job.tests, strict=False):
        if case.get("public") or case["status"] == "passed":
            continue
        if any(abs(int(n)) > INT32_MAX for n in _INTEGER.findall(test.get("expected") or "")):
            return (
                "Your logic works on the visible tests. A hidden test expects a number larger "
                f"than 2,147,483,647, which a 32-bit `int` cannot hold, so the value overflows. "
                f"Change the variables that grow (sums, products, counters) to `{wide}`"
                + (" and multiply with `1LL *`." if job.language == "cpp" else ".")
            )
    return None


def complexity(job: Submission) -> dict | None:
    """Estimated time and space for an accepted solution, from its loops, sorts and containers."""
    if job.status != "done" or job.verdict != "accepted":
        return None
    depth, recursive = _loop_depth(job.source, job.language)
    code = _strip(job.source, job.language)
    sorts = bool(_SORTS.search(code))
    if recursive:
        time = "depends on the recursion"
    elif depth >= 2:
        time = "O(n²)" if depth == 2 else f"O(n^{depth})"
    elif sorts:
        time = "O(n log n)"
    elif depth == 1:
        time = "O(n)"
    else:
        time = "O(1)"
    if sorts and depth == 1 and not recursive:
        time = "O(n log n)"
    grows = bool(_GROWING.search(code)) or _python_collection(job.source, job.language)
    space = "O(n)" if grows else "O(1)"
    return {
        "time": time,
        "space": space,
        "basis": (
            "An estimate from your loops, sorts and containers, with n as the input size. "
            "Ask Soc to check it against your exact code."
        ),
    }


def _python_collection(source: str, language: str) -> bool:
    if language != "python":
        return False
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp):
            return True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"append", "add", "extend", "appendleft", "setdefault"}:
                return True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"list", "dict", "set", "sorted", "deque"}:
                return True
    return False


def _loop_depth(source: str, language: str) -> tuple[int, bool]:
    if language == "python":
        return _python_depth(source)
    return _brace_depth(_strip(source, language))


def _python_depth(source: str) -> tuple[int, bool]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0, False
    names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    recursive = any(
        isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == fn.name
        for fn in ast.walk(tree)
        if isinstance(fn, ast.FunctionDef)
        for call in ast.walk(fn)
    )
    loops = (ast.For, ast.While, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)

    def depth(node: ast.AST) -> int:
        inner = max((depth(c) for c in ast.iter_child_nodes(node)), default=0)
        if isinstance(node, ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp):
            return inner + len(node.generators)
        return inner + 1 if isinstance(node, loops) else inner

    return depth(tree), recursive and bool(names)


def _strip(source: str, language: str) -> str:
    """Comments and string contents removed so a word inside them is not read as code."""
    if language == "python":
        return re.sub(r"#.*", "", source)
    source = re.sub(r"/\*.*?\*/", " ", source, flags=re.S)
    source = re.sub(r"//[^\n]*", "", source)
    return re.sub(r'"(?:\\.|[^"\\])*"', '""', source)


def _brace_depth(code: str) -> tuple[int, bool]:
    """Deepest loop nesting in C-like code, counting braced bodies and one-statement bodies."""
    best = 0
    stack: list[str] = []  # "{" for a block, "L" for a braced loop body, "S" for a one-line loop
    i, n = 0, len(code)

    def current() -> int:
        return sum(1 for s in stack if s in {"L", "S"})

    while i < n:
        at_word = code[i].isalpha() and (
            i == 0 or not (code[i - 1].isalnum() or code[i - 1] == "_")
        )
        match = _LOOP_HEAD.match(code, i) if at_word else None
        if match:
            j = match.end()
            while j < n and code[j].isspace():
                j += 1
            if j < n and code[j] == "(":
                level = 0
                while j < n:
                    level += code[j] == "("
                    level -= code[j] == ")"
                    j += 1
                    if level == 0:
                        break
                while j < n and code[j].isspace():
                    j += 1
                if j < n and code[j] == ";":
                    i = j + 1  # `while (x);` or `for (...);` has no body.
                    continue
                if j < n and code[j] == "{":
                    stack.append("L")
                    j += 1
                else:
                    stack.append("S")
                best = max(best, current())
                i = j
                continue
        ch = code[i]
        if ch == "{":
            stack.append("{")
        elif ch == "}" and stack:
            stack.pop()
            while stack and stack[-1] == "S":
                stack.pop()
        elif ch == ";" and stack and stack[-1] == "S":
            while stack and stack[-1] == "S":
                stack.pop()
        i += 1
    return best, False
