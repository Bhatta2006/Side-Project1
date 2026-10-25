import re
import tempfile
from pathlib import Path

import yaml
from runner.local_backend import strip_directory

from socrat.catalog.schema import QuizItem

ROOT = Path(__file__).resolve().parents[3]
POSITIONAL = re.compile(
    r"\b(both|all|none|neither) of the (above|first|last|previous)|\b(first|last) two\b|\b(above|previous) options?\b",
    re.I,
)


def item(**extra):
    return QuizItem(
        id="x",
        prompt="Plain?",
        options=["a", "b"],
        answer=0,
        explanation="Because.",
        difficulty=2,
        **extra,
    )


def test_language_tagged_item_does_not_fit_other_languages():
    tagged = item(languages=["python"])
    assert tagged.fits("python") and not tagged.fits("cpp") and not tagged.fits("java")
    assert item().fits("cpp")


def test_no_positional_options_in_shipped_quizzes():
    bad = []
    for path in (ROOT / "content").rglob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        if "options" not in text:
            continue
        for line in text.splitlines():
            if POSITIONAL.search(line) and re.match(r"\s*- ", line) and "options" not in line:
                bad.append((path.name, line.strip()))
    for path in (ROOT / "content").rglob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                for o in node.get("options", []) if isinstance(node.get("options"), list) else []:
                    if POSITIONAL.search(str(o)):
                        bad.append((path.name, o))
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
    assert not [
        b
        for b in bad
        if re.search(r"both of the|of the (above|first)|first two options", b[1], re.I)
    ]


def without_sentinel(heights):
    best, stack = 0, []
    for i, h in enumerate(heights):
        while stack and heights[stack[-1]] >= h:
            top = stack.pop()
            best = max(best, heights[top] * (i - (stack[-1] if stack else -1) - 1))
        stack.append(i)
    return best


def test_histogram_sentinel_item_has_one_failing_option():
    data = yaml.safe_load(
        (ROOT / "content/quiz/dsa/monotonic-stack/histogram-area.yaml").read_text(encoding="utf-8")
    )
    options = next(i for i in data["items"] if i["id"] == "sentinel")["options"]
    wrong = []
    for index, option in enumerate(options):
        h = [int(x) for x in re.findall(r"\d+", option.split(",")[0])]
        truth = max(
            min(h[a : b + 1]) * (b - a + 1) for a in range(len(h)) for b in range(a, len(h))
        )
        if without_sentinel(h) != truth:
            wrong.append(index)
    assert wrong == [0]


def test_stderr_hides_the_temp_directory():
    d = Path(tempfile.gettempdir()) / "socrat-job-abc"
    text = f"{d}{'/' if False else __import__('os').sep}Solution.java:3: error\nat {d}"
    assert str(d) not in strip_directory(text, d)
    assert strip_directory(text, d).startswith("Solution.java:3")
