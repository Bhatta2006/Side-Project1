"""Verify and splice hand-authored quiz items into a course concept file.

Authoring files live in .cache/quiz-authoring/<course>/<concept>.yaml: a list of quiz items in the
catalog schema, correct option FIRST (the engine shuffles at render time). Two extra keys are
accepted and stripped before splicing:

  verify:  a Python expression whose str() must equal options[answer] (computed answers)
  (code)   `output` and `bug` items are executed in every language they carry; each must print
           options[answer] (whitespace-normalised). `bug` items name the *fixed* behaviour.

Usage: python scripts/content/author_quiz.py <course> <concept> [--apply]
"""

import argparse
import bisect
import collections
import functools
import heapq
import itertools
import math
import re
import subprocess
import sys
import tempfile
from itertools import combinations, permutations
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "api" / "src"))
from socrat.catalog.schema import QuizItem  # noqa: E402

CPP_HEAD = "#include <bits/stdc++.h>\nusing namespace std;\nint main() {\n"
JAVA_HEAD = (
    "import java.util.*;\nimport java.util.stream.*;\n"
    "public class Main {\n    public static void main(String[] args) {\n"
)


def greedy_days(weights: list[int], cap: int) -> int:
    """Days needed to ship consecutive packages with a daily capacity (for verify expressions)."""
    days, cur = 1, 0
    for w in weights:
        if cur + w > cap:
            days, cur = days + 1, 0
        cur += w
    return days


def kruskal(n: int, edges: list[tuple[int, int, int]]) -> int:
    """Minimum spanning tree weight over vertices 0..n-1 (for verify expressions)."""
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    total = 0
    for a, b, w in sorted(edges, key=lambda e: e[2]):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            total += w
    return total


def cycle_edge(edges: list[list[int]]) -> list[int]:
    """First edge, in input order, whose endpoints are already connected (for verify expressions)."""
    parent: dict[int, int] = {}

    def find(x: int) -> int:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra == rb:
            return [a, b]
        parent[ra] = rb
    return []


def norm(text: str) -> str:
    return " ".join(str(text).split())


def run(language: str, code: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if language == "python":
            (tmp / "m.py").write_text(code, encoding="utf-8")
            cmd = [sys.executable, "-I", str(tmp / "m.py")]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        elif language == "cpp":
            (tmp / "m.cpp").write_text(CPP_HEAD + code + "\n}\n", encoding="utf-8")
            build = subprocess.run(
                ["g++", "-std=gnu++14", "-O1", "-o", str(tmp / "m.exe"), str(tmp / "m.cpp")],
                capture_output=True, text=True, timeout=120,
            )
            if build.returncode:
                return "COMPILE ERROR: " + build.stderr[:400]
            proc = subprocess.run([str(tmp / "m.exe")], capture_output=True, text=True, timeout=30)
        else:
            (tmp / "Main.java").write_text(
                JAVA_HEAD + code + "\n    }\n}\n", encoding="utf-8"
            )
            proc = subprocess.run(
                ["java", str(tmp / "Main.java")], capture_output=True, text=True, timeout=120
            )
        if proc.returncode:
            return f"RUNTIME ERROR: {proc.stderr[:400]}"
        return norm(proc.stdout)


def check(item: dict) -> list[str]:
    problems = []
    raw = {k: v for k, v in item.items() if k != "verify"}
    try:
        QuizItem(**raw)
    except Exception as exc:  # noqa: BLE001
        return [f"schema: {exc}"]
    answer = norm(item["options"][item["answer"]])
    if "verify" in item:
        env = dict(greedy_days=greedy_days, kruskal=kruskal, cycle_edge=cycle_edge,bisect=bisect, collections=collections, functools=functools, heapq=heapq, itertools=itertools, math=math, combinations=combinations, permutations=permutations)
        got = norm(eval(item["verify"], env))  # noqa: S307 - authored by us
        if got != answer:
            problems.append(f"verify gives {got!r}, answer option is {answer!r}")
    for language, code in (item.get("code", {}).items() if item["kind"] in ("output", "bug") else []):
        got = run(language, code)
        if got != answer:
            problems.append(f"{language} prints {got!r}, answer option is {answer!r}")
    return problems


def splice(path: Path, items: list[dict]) -> None:
    text = path.read_bytes().decode("utf-8")
    eol = "\r\n" if "\r\n" in text else "\n"
    body = text.replace("\r\n", "\n")
    clean = [{k: v for k, v in i.items() if k != "verify"} for i in items]
    dumped = yaml.safe_dump(
        clean, allow_unicode=True, sort_keys=False, width=100, default_flow_style=False
    )
    block = "quiz:\n" + "".join(f"  {ln}\n" if ln else "\n" for ln in dumped.splitlines())
    pattern = re.compile(r"(?m)^quiz:\n(?:(?: |- ).*\n|\n)*")
    if not pattern.search(body):
        raise SystemExit("no quiz block found")
    body = pattern.sub(lambda _: block, body, count=1)
    path.write_bytes(body.replace("\n", eol).encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("course")
    parser.add_argument("concept")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    src = ROOT / ".cache" / "quiz-authoring" / args.course / f"{args.concept}.yaml"
    items = yaml.safe_load(src.read_text(encoding="utf-8"))
    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids)), "duplicate ids"
    bad = 0
    for item in items:
        for problem in check(item):
            bad += 1
            print(f"FAIL {item['id']}: {problem}")
    bands = sorted(i["difficulty"] for i in items)
    print(f"{args.concept}: {len(items)} items, bands {bands}, failures {bad}")
    if bad or not args.apply:
        return 1 if bad else 0
    splice(ROOT / "content" / "courses" / args.course / "concepts" / f"{args.concept}.yaml", items)
    print("applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
