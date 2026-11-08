"""Run every code question in the placement bank and check its marked answer.

    uv run --project services/api python scripts/dev/verify_placement_bank.py [--no-run]

For each item in content/placement/*.yaml:
- "output" items: the code is executed in every language it is written for (Python, C++ with
  g++, Java with javac) and stdout must equal the marked option exactly.
- "bug" items with code: executed too; the report says whether it raised or printed, so an
  author can confirm the marked option. Infinite loops are cut off by the timeout.
- every item: which learner languages it fits (``QuizItem.fits``), so coverage gaps show.

Models explain; this script is the deterministic check that the answers are right.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "api" / "src"))

from socrat.catalog.schema import QuizItem  # noqa: E402

LANGUAGES = ("python", "cpp", "java")
TIMEOUT = 10

CPP = "#include <bits/stdc++.h>\nusing namespace std;\nint main() {\n%s\nreturn 0;\n}\n"
JAVA = (
    "import java.util.*;\npublic class Main {\n"
    "public static void main(String[] args) throws Exception {\n%s\n}\n}\n"
)


def run(language: str, code: str, work: Path) -> tuple[str, str]:
    """(stdout, status) where status is ok, error, timeout or skipped."""
    try:
        if language == "python":
            src = work / "main.py"
            src.write_text(code, encoding="utf-8")
            cmd = [sys.executable, "-I", str(src)]
        elif language == "cpp":
            if not shutil.which("g++"):
                return "", "skipped"
            src = work / "main.cpp"
            src.write_text(CPP % code, encoding="utf-8")
            exe = work / "main.exe"
            built = subprocess.run(
                ["g++", "-std=c++17", "-O0", "-o", str(exe), str(src)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if built.returncode:
                return built.stderr[-400:], "compile_error"
            cmd = [str(exe)]
        else:
            if not shutil.which("javac"):
                return "", "skipped"
            src = work / "Main.java"
            src.write_text(JAVA % code, encoding="utf-8")
            built = subprocess.run(
                ["javac", str(src)], capture_output=True, text=True, timeout=60, cwd=work
            )
            if built.returncode:
                return built.stderr[-400:], "compile_error"
            cmd = ["java", "-cp", str(work), "Main"]
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, cwd=work)
    except subprocess.TimeoutExpired:
        return "", "timeout"
    return done.stdout, "ok" if done.returncode == 0 else "error"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-run", action="store_true", help="only check fit and coverage")
    args = parser.parse_args()
    failures: list[str] = []
    coverage: dict[str, dict[str, int]] = defaultdict(lambda: dict.fromkeys(LANGUAGES, 0))
    count = 0
    for path in sorted((ROOT / "content" / "placement").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for concept, items in data["concepts"].items():
            qualified = concept if ":" in concept else f"{data['course']}:{concept}"
            for raw in items:
                item = QuizItem.model_validate(raw)
                count += 1
                for lang in LANGUAGES:
                    coverage[qualified][lang] += item.fits(lang)
                if args.no_run or not item.code or item.kind not in {"output", "bug"}:
                    continue
                expected = item.options[item.answer]
                for lang, code in item.code.items():
                    with tempfile.TemporaryDirectory() as tmp:
                        out, status = run(lang, code, Path(tmp))
                    label = f"{qualified}/{item.id} [{lang}]"
                    if status == "skipped":
                        print(f"skip  {label}: no compiler")
                    elif item.kind == "output":
                        if status != "ok" or out.rstrip() != expected.rstrip():
                            failures.append(f"{label}: {status} {out!r} != {expected!r}")
                    else:
                        print(f"bug   {label}: {status} {out.strip()[:60]!r} | marked: {expected}")
    for concept, langs in sorted(coverage.items()):
        thin = [lang for lang, n in langs.items() if n < 2]
        if thin:
            print(
                f"thin  {concept}: fewer than 2 items for {', '.join(thin)} (falls back to hard quiz items)"
            )
    print(f"{count} items checked")
    for failure in failures:
        print(f"FAIL  {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
