"""Longest strictly increasing subsequence with the O(n^2) table dp[i] = best chain ending at i.

Wrong answers are the classic slips: greedy extension from the first element, the longest
contiguous run, a non-strict comparison, and reading only the last cell.
"""

from itertools import combinations

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

INIT = lines("dp = [1] * n", "vector<int> dp(n, 1);", "int[] dp = new int[n]; java.util.Arrays.fill(dp, 1);")
OUTER = lines("for i in range(n):", "for (int i = 0; i < n; i++) {")
INNER = lines("for j in range(i):", "for (int j = 0; j < i; j++) {")
COMPARE = lines("if a[j] < a[i]:", "if (a[j] < a[i]) {")
UPDATE = lines("dp[i] = max(dp[i], dp[j] + 1)", "dp[i] = max(dp[i], dp[j] + 1);", "dp[i] = Math.max(dp[i], dp[j] + 1);")
BEST = lines("best = max(best, dp[i])", "best = max(best, dp[i]);", "best = Math.max(best, dp[i]);")
OUTPUT = lines("print(best)", 'cout << best << "\\n";', "System.out.println(best);")


def program(v: dict) -> dict[str, str]:
    a = ", ".join(map(str, v["a"]))
    return {
        "python": (
            f"a = [{a}]\n"
            "n = len(a)\n"
            "dp = [1] * n\n"
            "best = 0\n"
            "for i in range(n):\n"
            "    for j in range(i):\n"
            "        if a[j] < a[i]:\n"
            "            dp[i] = max(dp[i], dp[j] + 1)\n"
            "    best = max(best, dp[i])\n"
            "print(best)"
        ),
        "cpp": (
            f"vector<int> a = {{{a}}};\n"
            "int n = a.size();\n"
            "vector<int> dp(n, 1);\n"
            "int best = 0;\n"
            "for (int i = 0; i < n; i++) {\n"
            "    for (int j = 0; j < i; j++) {\n"
            "        if (a[j] < a[i]) {\n"
            "            dp[i] = max(dp[i], dp[j] + 1);\n"
            "        }\n"
            "    }\n"
            "    best = max(best, dp[i]);\n"
            "}\n"
            'cout << best << "\\n";'
        ),
        "java": (
            f"int[] a = {{{a}}};\n"
            "int n = a.length;\n"
            "int[] dp = new int[n]; java.util.Arrays.fill(dp, 1);\n"
            "int best = 0;\n"
            "for (int i = 0; i < n; i++) {\n"
            "    for (int j = 0; j < i; j++) {\n"
            "        if (a[j] < a[i]) {\n"
            "            dp[i] = Math.max(dp[i], dp[j] + 1);\n"
            "        }\n"
            "    }\n"
            "    best = Math.max(best, dp[i]);\n"
            "}\n"
            "System.out.println(best);"
        ),
    }


def lis_brute(a: list[int]) -> int:
    """Independent check: the largest subset of positions whose values strictly increase."""
    for size in range(len(a), 0, -1):
        for keep in combinations(range(len(a)), size):
            if all(a[x] < a[y] for x, y in zip(keep, keep[1:])):
                return size
    return 0


def greedy(a):
    last, length = a[0], 1
    for x in a[1:]:
        if x > last:
            last, length = x, length + 1
    return length


def longest_run(a):
    best = cur = 1
    for x, y in zip(a, a[1:]):
        cur = cur + 1 if y > x else 1
        best = max(best, cur)
    return best


def non_strict(a):
    dp = [1] * len(a)
    for i in range(len(a)):
        for j in range(i):
            if a[j] <= a[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)


def last_cell(a):
    dp = [1] * len(a)
    for i in range(len(a)):
        for j in range(i):
            if a[j] < a[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    return dp[-1]


def wrong(v):
    a = v["a"]
    return [
        (str(greedy(a)), "lis-greedy-extend"),
        (str(longest_run(a)), "pattern-subsequence-vs-substring"),
        (str(non_strict(a)), "lis-non-strict-compare"),
        (str(last_cell(a)), "lis-answer-last-cell"),
        (str(len(set(a))), "distinct-vs-frequency"),
    ]


def sample(rng, params):
    return {"a": [rng.randint(*params["value"]) for _ in range(rng.randint(*params["length"]))]}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(lis_brute(v["a"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        "This code should print the length of the longest strictly increasing subsequence. "
        "Which line goes in the blank?"
    ),
    fix=lambda v: (
        "This code should print the length of the longest strictly increasing subsequence, but it "
        "prints the wrong answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"dp[i] is the longest strictly increasing subsequence ending at a[i]: one more than the best "
        f"dp[j] over earlier, smaller a[j]. The best over all i is {answer}."
    ),
    blanks=[
        Blank(
            COMPARE,
            [
                (lines("if a[j] <= a[i]:", "if (a[j] <= a[i]) {"), "lis-non-strict-compare"),
                (lines("if a[j] > a[i]:", "if (a[j] > a[i]) {"), "lis-compare-direction"),
                (lines("if j < i:", "if (j < i) {"), "confuse-index-value"),
            ],
        ),
        Blank(
            UPDATE,
            [
                (lines("dp[i] = dp[j] + 1", "dp[i] = dp[j] + 1;"), "overwrite-best"),
                (lines("dp[i] = max(dp[i], dp[j])", "dp[i] = max(dp[i], dp[j]);", "dp[i] = Math.max(dp[i], dp[j]);"),
                 "dp-missing-plus-one"),
                (lines("dp[i] = max(dp[i], dp[i - 1] + 1)", "dp[i] = max(dp[i], dp[i - 1] + 1);",
                       "dp[i] = Math.max(dp[i], dp[i - 1] + 1);"), "dp-wrong-subproblem"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "lis-non-strict-compare",
            edit(COMPARE, lines("if a[j] <= a[i]:", "if (a[j] <= a[i]) {")),
            "Compare with a[j] < a[i]",
            "Strictly increasing means an equal value cannot extend the chain.",
        ),
        Fix(
            "lis-overwrite-best",
            edit(UPDATE, lines("dp[i] = dp[j] + 1", "dp[i] = dp[j] + 1;")),
            "Keep the larger: dp[i] = max(dp[i], dp[j] + 1)",
            "A later j with a shorter chain must not overwrite a better one.",
        ),
        Fix(
            "lis-answer-last-cell",
            edit(BEST, lines("best = dp[i]", "best = dp[i];")),
            "Keep the maximum: best = max(best, dp[i])",
            "The longest chain can end at any index, not only the last one.",
        ),
    ],
    decoys=[
        Decoy(edit(OUTPUT, lines("print(best + 1)", 'cout << best + 1 << "\\n";', "System.out.println(best + 1);")),
              "Print best + 1", "off-by-one-output"),
        Decoy(edit(INNER, lines("for j in range(1, i):", "for (int j = 1; j < i; j++) {")),
              "Start j at 1", "skip-first-element"),
        Decoy(edit(OUTER, lines("for i in range(1, n):", "for (int i = 1; i < n; i++) {")),
              "Start i at 1", "skip-first-element"),
        Decoy(edit(INIT, lines("dp = [0] * n", "vector<int> dp(n, 0);", "int[] dp = new int[n];")),
              "Start every dp[i] at 0", "dp-wrong-base-case"),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"lis_brute": lis_brute}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
