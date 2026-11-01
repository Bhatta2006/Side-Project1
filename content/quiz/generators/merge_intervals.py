"""Merge intervals after sorting by start; how many blocks remain.

Closed intervals: [1, 3] and [3, 5] touch and merge. Wrong answers skip the sort, treat
touching intervals as separate, or keep the last interval's end instead of the largest
end (a short interval inside a long one cuts the block off too early).
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, lines

OPEN_NEW = lines("if s > end:", "if (s > end) {")
EXTEND = lines("end = max(end, e)", "end = max(end, e);", "end = Math.max(end, e);")


def program(v: dict) -> dict[str, str]:
    py = ", ".join(f"[{s}, {e}]" for s, e in v["iv"])
    braces = ", ".join(f"{{{s}, {e}}}" for s, e in v["iv"])
    return {
        "python": (
            f"iv = [{py}]\n"
            "iv.sort()\n"
            "blocks = 0\n"
            "end = -1\n"
            "for s, e in iv:\n"
            "    if s > end:\n"
            "        blocks += 1\n"
            "        end = e\n"
            "    else:\n"
            "        end = max(end, e)\n"
            "print(blocks)"
        ),
        "cpp": (
            f"vector<pair<int, int>> iv = {{{braces}}};\n"
            "sort(iv.begin(), iv.end());\n"
            "int blocks = 0;\n"
            "int end = -1;\n"
            "for (auto& p : iv) {\n"
            "    int s = p.first, e = p.second;\n"
            "    if (s > end) {\n"
            "        blocks++;\n"
            "        end = e;\n"
            "    } else {\n"
            "        end = max(end, e);\n"
            "    }\n"
            "}\n"
            'cout << blocks << "\\n";'
        ),
        "java": (
            f"int[][] iv = {{{braces}}};\n"
            "Arrays.sort(iv, (a, b) -> a[0] != b[0] ? a[0] - b[0] : a[1] - b[1]);\n"
            "int blocks = 0;\n"
            "int end = -1;\n"
            "for (int[] p : iv) {\n"
            "    int s = p[0], e = p[1];\n"
            "    if (s > end) {\n"
            "        blocks++;\n"
            "        end = e;\n"
            "    } else {\n"
            "        end = Math.max(end, e);\n"
            "    }\n"
            "}\n"
            "System.out.println(blocks);"
        ),
    }


def blocks(iv: list) -> int:
    """Independent check: mark covered points (doubled, so touching ends meet) and count runs."""
    covered = set()
    for s, e in iv:
        covered.update(range(2 * s, 2 * e + 1))
    runs, prev = 0, None
    for x in sorted(covered):
        if prev is None or x != prev + 1:
            runs += 1
        prev = x
    return runs


def merged(iv: list, *, sort: bool, touch: bool, use_max: bool) -> int:
    count, end = 0, -1
    for s, e in sorted(iv) if sort else iv:
        if s > end or (not touch and s == end):
            count += 1
            end = e
        else:
            end = max(end, e) if use_max else e
    return count


def wrong(v):
    iv = v["iv"]
    return [
        (str(merged(iv, sort=False, touch=True, use_max=True)), "intervals-unsorted"),
        (str(merged(iv, sort=True, touch=False, use_max=True)), "intervals-touching-separate"),
        (str(merged(iv, sort=True, touch=True, use_max=False)), "intervals-end-not-max"),
        (str(len(iv)), "intervals-count-input"),
    ]


def sample(rng, params):
    iv = []
    for _ in range(rng.randint(*params["n"])):
        s = rng.randint(0, params["span"][0])
        iv.append((s, s + rng.randint(0, params["length"][0])))
    if rng.random() < 0.6:  # a long interval swallowing a short one
        s = rng.randint(0, params["span"][0] // 2)
        iv.append((s, s + params["length"][0] * 2))
    if rng.random() < 0.6:  # two intervals that only touch
        s = rng.randint(0, params["span"][0])
        iv += [(s, s + 2), (s + 2, s + 3)]
    rng.shuffle(iv)
    return {"iv": [list(p) for p in iv]}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(blocks(v["iv"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        "This code should print how many separate blocks the closed intervals form after "
        "merging every overlapping or touching pair. Which line goes in the blank?"
    ),
    fix=lambda v: "",
    explain=lambda v, answer: (
        "Sorted by start, an interval joins the current block when it starts at or before the "
        "block's end, and the block's end becomes the larger of the two ends (a short interval "
        f"inside a long one must not shrink it). That leaves {answer} blocks."
    ),
    blanks=[
        Blank(
            OPEN_NEW,
            [
                (lines("if s >= end:", "if (s >= end) {"), "intervals-touching-separate"),
                (lines("if e > end:", "if (e > end) {"), "confuse-index-value"),
                (lines("if s > e:", "if (s > e) {"), "confuse-index-value"),
            ],
        ),
        Blank(
            EXTEND,
            [
                (lines("end = e", "end = e;"), "intervals-end-not-max"),
                (lines("end = min(end, e)", "end = min(end, e);", "end = Math.min(end, e);"),
                 "min-vs-max"),
                (lines("end = max(end, s)", "end = max(end, s);", "end = Math.max(end, s);"),
                 "confuse-index-value"),
            ],
        ),
    ],
    bands=(3, 4, 5),
)
HELPERS = {"blocks": blocks}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
