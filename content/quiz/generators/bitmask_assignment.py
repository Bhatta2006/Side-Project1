"""Assignment problem with bitmask DP: dp[mask] = cheapest cost for the jobs in mask.

Wrong answers are the classic slips: each worker greedily taking the cheapest free job,
ignoring that a job can only be used once, and taking the maximum instead of the minimum.
"""

from itertools import permutations

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

TABLE = lines("dp = [10**9] * (1 << n)", "vector<int> dp(1 << n, 1000000000);",
              "int[] dp = new int[1 << n]; java.util.Arrays.fill(dp, 1000000000);")
BASE = lines("dp[0] = 0", "dp[0] = 0;")
MASKS = lines("for mask in range(1 << n):", "for (int mask = 0; mask < (1 << n); mask++) {")
WORKER = lines('i = bin(mask).count("1")', "int i = __builtin_popcount(mask);", "int i = Integer.bitCount(mask);")
FREE = lines("if not mask & (1 << j):", "if (!(mask & (1 << j))) {", "if ((mask & (1 << j)) == 0) {")
UPDATE = lines("dp[mask | (1 << j)] = min(dp[mask | (1 << j)], dp[mask] + c[i][j])",
               "dp[mask | (1 << j)] = min(dp[mask | (1 << j)], dp[mask] + c[i][j]);",
               "dp[mask | (1 << j)] = Math.min(dp[mask | (1 << j)], dp[mask] + c[i][j]);")
OUTPUT = lines("print(dp[(1 << n) - 1])", 'cout << dp[(1 << n) - 1] << "\\n";', "System.out.println(dp[(1 << n) - 1]);")


def matrix(rows, open_, close):
    return ", ".join(open_ + ", ".join(map(str, r)) + close for r in rows)


def program(v: dict) -> dict[str, str]:
    c = v["c"]
    return {
        "python": (
            f"c = [{matrix(c, '[', ']')}]\n"
            "n = len(c)\n"
            "dp = [10**9] * (1 << n)\n"
            "dp[0] = 0\n"
            "for mask in range(1 << n):\n"
            '    i = bin(mask).count("1")\n'
            "    if i == n:\n"
            "        continue\n"
            "    for j in range(n):\n"
            "        if not mask & (1 << j):\n"
            "            dp[mask | (1 << j)] = min(dp[mask | (1 << j)], dp[mask] + c[i][j])\n"
            "print(dp[(1 << n) - 1])"
        ),
        "cpp": (
            f"vector<vector<int>> c = {{{matrix(c, '{', '}')}}};\n"
            "int n = c.size();\n"
            "vector<int> dp(1 << n, 1000000000);\n"
            "dp[0] = 0;\n"
            "for (int mask = 0; mask < (1 << n); mask++) {\n"
            "    int i = __builtin_popcount(mask);\n"
            "    if (i == n) continue;\n"
            "    for (int j = 0; j < n; j++) {\n"
            "        if (!(mask & (1 << j))) {\n"
            "            dp[mask | (1 << j)] = min(dp[mask | (1 << j)], dp[mask] + c[i][j]);\n"
            "        }\n"
            "    }\n"
            "}\n"
            'cout << dp[(1 << n) - 1] << "\\n";'
        ),
        "java": (
            f"int[][] c = {{{matrix(c, '{', '}')}}};\n"
            "int n = c.length;\n"
            "int[] dp = new int[1 << n]; java.util.Arrays.fill(dp, 1000000000);\n"
            "dp[0] = 0;\n"
            "for (int mask = 0; mask < (1 << n); mask++) {\n"
            "    int i = Integer.bitCount(mask);\n"
            "    if (i == n) continue;\n"
            "    for (int j = 0; j < n; j++) {\n"
            "        if ((mask & (1 << j)) == 0) {\n"
            "            dp[mask | (1 << j)] = Math.min(dp[mask | (1 << j)], dp[mask] + c[i][j]);\n"
            "        }\n"
            "    }\n"
            "}\n"
            "System.out.println(dp[(1 << n) - 1]);"
        ),
    }


def cheapest(c: list[list[int]]) -> int:
    """Independent check: try every assignment of workers to jobs."""
    n = len(c)
    return min(sum(c[i][p[i]] for i in range(n)) for p in permutations(range(n)))


def greedy(c):
    used, total = set(), 0
    for row in c:
        j = min((j for j in range(len(c)) if j not in used), key=lambda j: row[j])
        used.add(j)
        total += row[j]
    return total


def wrong(v):
    c, n = v["c"], len(v["c"])
    return [
        (str(greedy(c)), "bitmask-greedy-assign"),
        (str(sum(min(row) for row in c)), "bitmask-check-bit"),
        (str(max(sum(c[i][p[i]] for i in range(n)) for p in permutations(range(n)))), "min-vs-max"),
        (str(sum(c[i][i] for i in range(n))), "bitmask-greedy-assign"),
    ]


def sample(rng, params):
    n = rng.randint(*params["workers"])
    return {"c": [[rng.randint(*params["cost"]) for _ in range(n)] for _ in range(n)]}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(cheapest(v["c"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        "c[i][j] is the cost of giving job j to worker i; each worker gets exactly one job and each job "
        "one worker. This code should print the cheapest total. Which line goes in the blank?"
    ),
    fix=lambda v: (
        "c[i][j] is the cost of giving job j to worker i; each worker gets exactly one job and each job "
        "one worker. This code should print the cheapest total, but it prints the wrong answer. "
        "Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"dp[mask] is the cheapest way to give the jobs in mask to the first popcount(mask) workers; "
        f"the next worker takes one free job. The cheapest full assignment costs {answer}."
    ),
    blanks=[
        Blank(
            FREE,
            [
                (lines("if mask & (1 << j):", "if (mask & (1 << j)) {", "if ((mask & (1 << j)) != 0) {"), "bitmask-check-bit"),
                (lines("if not mask & j:", "if (!(mask & j)) {", "if ((mask & j) == 0) {"), "bit-test-wrong"),
                (lines("if j != i:", "if (j != i) {"), "confuse-index-value"),
            ],
        ),
        Blank(
            UPDATE,
            [
                (lines("dp[mask | (1 << j)] = min(dp[mask | (1 << j)], dp[mask] + c[0][j])",
                       "dp[mask | (1 << j)] = min(dp[mask | (1 << j)], dp[mask] + c[0][j]);",
                       "dp[mask | (1 << j)] = Math.min(dp[mask | (1 << j)], dp[mask] + c[0][j]);"), "bitmask-worker-index"),
                (lines("dp[mask | (1 << j)] = min(dp[mask | (1 << j)], dp[mask] + c[i][0])",
                       "dp[mask | (1 << j)] = min(dp[mask | (1 << j)], dp[mask] + c[i][0]);",
                       "dp[mask | (1 << j)] = Math.min(dp[mask | (1 << j)], dp[mask] + c[i][0]);"), "confuse-index-value"),
                (lines("dp[mask | (1 << j)] = dp[mask] + c[i][j]", "dp[mask | (1 << j)] = dp[mask] + c[i][j];"),
                 "overwrite-best"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "bitmask-check-bit",
            edit(FREE, lines("if mask & (1 << j):", "if (mask & (1 << j)) {", "if ((mask & (1 << j)) != 0) {")),
            "Only try jobs whose bit is not set yet",
            "A set bit means the job is already taken; the test was inverted.",
        ),
        Fix(
            "bitmask-worker-index",
            edit(UPDATE, lines("dp[mask | (1 << j)] = min(dp[mask | (1 << j)], dp[mask] + c[0][j])",
                               "dp[mask | (1 << j)] = min(dp[mask | (1 << j)], dp[mask] + c[0][j]);",
                               "dp[mask | (1 << j)] = Math.min(dp[mask | (1 << j)], dp[mask] + c[0][j]);")),
            "Charge the cost of worker i = popcount(mask): c[i][j]",
            "The next worker is the number of jobs already taken, not always worker 0.",
        ),
        Fix(
            "bitmask-start-zero",
            edit(TABLE, lines("dp = [0] * (1 << n)", "vector<int> dp(1 << n, 0);", "int[] dp = new int[1 << n];")),
            "Start every mask except 0 at a very large value",
            "Starting at 0 makes every minimum 0.",
        ),
    ],
    decoys=[
        Decoy(edit(OUTPUT, lines("print(dp[(1 << n) - 2])", 'cout << dp[(1 << n) - 2] << "\\n";',
                                 "System.out.println(dp[(1 << n) - 2]);")),
              "Print dp[(1 << n) - 2] instead", "loop-bound-off-by-one"),
        Decoy(edit(BASE, lines("dp[0] = 1", "dp[0] = 1;")),
              "Start dp[0] at 1", "dp-wrong-base-case"),
        Decoy(edit(MASKS, lines("for mask in range(1, 1 << n):", "for (int mask = 1; mask < (1 << n); mask++) {")),
              "Skip the empty mask", "skip-first-element"),
        Decoy(edit(WORKER, lines('i = bin(mask).count("1") % n', "int i = __builtin_popcount(mask) % n;",
                                 "int i = Integer.bitCount(mask) % n;")),
              "Take the worker index modulo n", "loop-bound-off-by-one"),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"cheapest": cheapest}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
