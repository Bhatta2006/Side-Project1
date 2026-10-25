"""Matrix chain multiplication: cheapest bracket order, table filled by range length.

Wrong answers are the classic slips: always multiplying left to right, cheapest pair first,
the wrong dimensions in the join cost, and taking the maximum instead of the minimum.
"""

from functools import lru_cache

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

LENGTH = lines("for length in range(2, n + 1):", "for (int length = 2; length <= n; length++) {")
SPLIT = lines("for k in range(i, j):", "for (int k = i; k < j; k++) {")
JOIN = lines("cost = dp[i][k] + dp[k + 1][j] + p[i] * p[k + 1] * p[j + 1]",
             "int cost = dp[i][k] + dp[k + 1][j] + p[i] * p[k + 1] * p[j + 1];")
KEEP = lines("dp[i][j] = min(dp[i][j], cost)", "dp[i][j] = min(dp[i][j], cost);", "dp[i][j] = Math.min(dp[i][j], cost);")
START = lines("dp[i][j] = 10**9", "dp[i][j] = 1000000000;")
OUTPUT = lines("print(dp[0][n - 1])", 'cout << dp[0][n - 1] << "\\n";', "System.out.println(dp[0][n - 1]);")


def program(v: dict) -> dict[str, str]:
    p = ", ".join(map(str, v["p"]))
    return {
        "python": (
            f"p = [{p}]\n"
            "n = len(p) - 1\n"
            "dp = [[0] * n for _ in range(n)]\n"
            "for length in range(2, n + 1):\n"
            "    for i in range(n - length + 1):\n"
            "        j = i + length - 1\n"
            "        dp[i][j] = 10**9\n"
            "        for k in range(i, j):\n"
            "            cost = dp[i][k] + dp[k + 1][j] + p[i] * p[k + 1] * p[j + 1]\n"
            "            dp[i][j] = min(dp[i][j], cost)\n"
            "print(dp[0][n - 1])"
        ),
        "cpp": (
            f"vector<int> p = {{{p}}};\n"
            "int n = p.size() - 1;\n"
            "vector<vector<int>> dp(n, vector<int>(n, 0));\n"
            "for (int length = 2; length <= n; length++) {\n"
            "    for (int i = 0; i + length - 1 < n; i++) {\n"
            "        int j = i + length - 1;\n"
            "        dp[i][j] = 1000000000;\n"
            "        for (int k = i; k < j; k++) {\n"
            "            int cost = dp[i][k] + dp[k + 1][j] + p[i] * p[k + 1] * p[j + 1];\n"
            "            dp[i][j] = min(dp[i][j], cost);\n"
            "        }\n"
            "    }\n"
            "}\n"
            'cout << dp[0][n - 1] << "\\n";'
        ),
        "java": (
            f"int[] p = {{{p}}};\n"
            "int n = p.length - 1;\n"
            "int[][] dp = new int[n][n];\n"
            "for (int length = 2; length <= n; length++) {\n"
            "    for (int i = 0; i + length - 1 < n; i++) {\n"
            "        int j = i + length - 1;\n"
            "        dp[i][j] = 1000000000;\n"
            "        for (int k = i; k < j; k++) {\n"
            "            int cost = dp[i][k] + dp[k + 1][j] + p[i] * p[k + 1] * p[j + 1];\n"
            "            dp[i][j] = Math.min(dp[i][j], cost);\n"
            "        }\n"
            "    }\n"
            "}\n"
            "System.out.println(dp[0][n - 1]);"
        ),
    }


def cheapest(p: list[int]) -> int:
    """Independent check: recursion over every bracketing, memoised."""

    @lru_cache(maxsize=None)
    def go(i: int, j: int) -> int:
        if i == j:
            return 0
        return min(go(i, k) + go(k + 1, j) + p[i] * p[k + 1] * p[j + 1] for k in range(i, j))

    return go(0, len(p) - 2)


def left_to_right(p):
    total, rows = 0, p[0]
    for k in range(1, len(p) - 1):
        total += rows * p[k] * p[k + 1]
    return total


def cheapest_pair_first(p):
    q, total = list(p), 0
    while len(q) > 2:
        k = min(range(1, len(q) - 1), key=lambda k: q[k - 1] * q[k] * q[k + 1])
        total += q[k - 1] * q[k] * q[k + 1]
        q.pop(k)
    return total


def costliest(p):
    @lru_cache(maxsize=None)
    def go(i, j):
        if i == j:
            return 0
        return max(go(i, k) + go(k + 1, j) + p[i] * p[k + 1] * p[j + 1] for k in range(i, j))

    return go(0, len(p) - 2)


def wrong(v):
    p = v["p"]
    return [
        (str(left_to_right(p)), "mcm-greedy-order"),
        (str(cheapest_pair_first(p)), "mcm-greedy-order"),
        (str(costliest(p)), "min-vs-max"),
        (str(sum(p[k] * p[k + 1] for k in range(len(p) - 1))), "mcm-cost-index"),
    ]


def sample(rng, params):
    return {"p": [rng.randint(*params["dim"]) for _ in range(rng.randint(*params["matrices"]) + 1)]}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(cheapest(v["p"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        "Matrix i has dimensions p[i] x p[i + 1]. This code should print the cheapest cost of "
        "multiplying the whole chain. Which line goes in the blank?"
    ),
    fix=lambda v: (
        "Matrix i has dimensions p[i] x p[i + 1]. This code should print the cheapest cost of "
        "multiplying the whole chain, but it prints the wrong answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"dp[i][j] is the cheapest cost for matrices i..j: try every last split k, add both halves "
        f"and p[i] * p[k + 1] * p[j + 1], and fill shorter ranges first. The cheapest order costs {answer}."
    ),
    blanks=[
        Blank(
            JOIN,
            [
                (lines("cost = dp[i][k] + dp[k + 1][j] + p[i] * p[k] * p[j]",
                       "int cost = dp[i][k] + dp[k + 1][j] + p[i] * p[k] * p[j];"), "mcm-cost-index"),
                (lines("cost = dp[i][k] + dp[k + 1][j]", "int cost = dp[i][k] + dp[k + 1][j];"), "dp-missing-plus-one"),
                (lines("cost = dp[i][k] + dp[k + 1][j] + p[i] * p[k + 1]",
                       "int cost = dp[i][k] + dp[k + 1][j] + p[i] * p[k + 1];"), "mcm-cost-index"),
            ],
        ),
        Blank(
            KEEP,
            [
                (lines("dp[i][j] = max(dp[i][j], cost)", "dp[i][j] = max(dp[i][j], cost);", "dp[i][j] = Math.max(dp[i][j], cost);"),
                 "min-vs-max"),
                (lines("dp[i][j] = cost", "dp[i][j] = cost;"), "overwrite-best"),
                (lines("dp[i][j] = min(dp[i][j], dp[i][k])", "dp[i][j] = min(dp[i][j], dp[i][k]);",
                       "dp[i][j] = Math.min(dp[i][j], dp[i][k]);"), "dp-wrong-subproblem"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "mcm-cost-index",
            edit(JOIN, lines("cost = dp[i][k] + dp[k + 1][j] + p[i] * p[k] * p[j]",
                             "int cost = dp[i][k] + dp[k + 1][j] + p[i] * p[k] * p[j];")),
            "Use p[i] * p[k + 1] * p[j + 1] for the last multiplication",
            "The left product is p[i] x p[k + 1] and the right one is p[k + 1] x p[j + 1].",
        ),
        Fix(
            "mcm-keep-last-split",
            edit(KEEP, lines("dp[i][j] = cost", "dp[i][j] = cost;")),
            "Keep the minimum: dp[i][j] = min(dp[i][j], cost)",
            "Every split must be compared; overwriting keeps only the last split tried.",
        ),
        Fix(
            "mcm-start-zero",
            edit(START, lines("dp[i][j] = 0", "dp[i][j] = 0;")),
            "Start dp[i][j] at a very large value before taking the minimum",
            "Starting at 0 makes every minimum 0.",
        ),
    ],
    decoys=[
        Decoy(edit(OUTPUT, lines("print(dp[0][n - 2])", 'cout << dp[0][n - 2] << "\\n";', "System.out.println(dp[0][n - 2]);")),
              "Print dp[0][n - 2] instead", "loop-bound-off-by-one"),
        Decoy(edit(LENGTH, lines("for length in range(3, n + 1):", "for (int length = 3; length <= n; length++) {")),
              "Start the lengths at 3", "loop-bound-off-by-one"),
        Decoy(edit(SPLIT, lines("for k in range(i + 1, j):", "for (int k = i + 1; k < j; k++) {")),
              "Skip the split right after i", "skip-first-element"),
        Decoy(edit(JOIN, lines("cost = dp[i][k] + dp[k + 1][j] + 2 * p[i] * p[k + 1] * p[j + 1]",
                               "int cost = dp[i][k] + dp[k + 1][j] + 2 * p[i] * p[k + 1] * p[j + 1];")),
              "Count each multiplication twice", "double-count"),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"cheapest": cheapest}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
