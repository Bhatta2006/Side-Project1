"""Maximal square of ones: dp[i][j] = 1 + min(up, left, up-left), answer = side squared.

Wrong answers are the classic slips: leaving out the diagonal neighbour, printing the side
instead of the area, counting ones, and answering with the largest rectangle instead.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

LOOP_I = lines("for i in range(1, r + 1):", "for (int i = 1; i <= r; i++) {")
LOOP_J = lines("for j in range(1, c + 1):", "for (int j = 1; j <= c; j++) {")
UPDATE = lines("dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])",
               "dp[i][j] = 1 + min(dp[i - 1][j], min(dp[i][j - 1], dp[i - 1][j - 1]));",
               "dp[i][j] = 1 + Math.min(dp[i - 1][j], Math.min(dp[i][j - 1], dp[i - 1][j - 1]));")
BEST = lines("best = max(best, dp[i][j])", "best = max(best, dp[i][j]);", "best = Math.max(best, dp[i][j]);")
OUTPUT = lines("print(best * best)", 'cout << best * best << "\\n";', "System.out.println(best * best);")


def program(v: dict) -> dict[str, str]:
    rows = ", ".join(f'"{row}"' for row in v["g"])
    return {
        "python": (
            f"g = [{rows}]\n"
            "r, c = len(g), len(g[0])\n"
            "dp = [[0] * (c + 1) for _ in range(r + 1)]\n"
            "best = 0\n"
            "for i in range(1, r + 1):\n"
            "    for j in range(1, c + 1):\n"
            '        if g[i - 1][j - 1] == "1":\n'
            "            dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])\n"
            "            best = max(best, dp[i][j])\n"
            "print(best * best)"
        ),
        "cpp": (
            f"vector<string> g = {{{rows}}};\n"
            "int r = g.size(), c = g[0].size();\n"
            "vector<vector<int>> dp(r + 1, vector<int>(c + 1, 0));\n"
            "int best = 0;\n"
            "for (int i = 1; i <= r; i++) {\n"
            "    for (int j = 1; j <= c; j++) {\n"
            "        if (g[i - 1][j - 1] == '1') {\n"
            "            dp[i][j] = 1 + min(dp[i - 1][j], min(dp[i][j - 1], dp[i - 1][j - 1]));\n"
            "            best = max(best, dp[i][j]);\n"
            "        }\n"
            "    }\n"
            "}\n"
            'cout << best * best << "\\n";'
        ),
        "java": (
            f"String[] g = {{{rows}}};\n"
            "int r = g.length, c = g[0].length();\n"
            "int[][] dp = new int[r + 1][c + 1];\n"
            "int best = 0;\n"
            "for (int i = 1; i <= r; i++) {\n"
            "    for (int j = 1; j <= c; j++) {\n"
            "        if (g[i - 1].charAt(j - 1) == '1') {\n"
            "            dp[i][j] = 1 + Math.min(dp[i - 1][j], Math.min(dp[i][j - 1], dp[i - 1][j - 1]));\n"
            "            best = Math.max(best, dp[i][j]);\n"
            "        }\n"
            "    }\n"
            "}\n"
            "System.out.println(best * best);"
        ),
    }


def largest_square(g: list[str]) -> int:
    """Independent check: try every square and test every cell in it."""
    r, c, best = len(g), len(g[0]), 0
    for i in range(r):
        for j in range(c):
            k = 1
            while i + k <= r and j + k <= c and all(g[x][y] == "1" for x in range(i, i + k) for y in range(j, j + k)):
                best = max(best, k)
                k += 1
    return best * best


def no_diagonal(g):
    r, c = len(g), len(g[0])
    dp, best = [[0] * (c + 1) for _ in range(r + 1)], 0
    for i in range(1, r + 1):
        for j in range(1, c + 1):
            if g[i - 1][j - 1] == "1":
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1])
                best = max(best, dp[i][j])
    return best * best


def largest_rectangle(g):
    r, c, best = len(g), len(g[0]), 0
    for top in range(r):
        for left in range(c):
            for bottom in range(top, r):
                for right in range(left, c):
                    if all(g[x][y] == "1" for x in range(top, bottom + 1) for y in range(left, right + 1)):
                        best = max(best, (bottom - top + 1) * (right - left + 1))
    return best


def wrong(v):
    g = v["g"]
    side = int(largest_square(g) ** 0.5)
    return [
        (str(no_diagonal(g)), "sq-missing-diagonal"),
        (str(side), "sq-side-not-area"),
        (str(sum(row.count("1") for row in g)), "count-vs-sum"),
        (str(largest_rectangle(g)), "pattern-square-vs-rectangle"),
    ]


def sample(rng, params):
    rows, cols = rng.randint(*params["rows"]), rng.randint(*params["cols"])
    fill = rng.randint(*params["fill"])
    g = ["".join("1" if rng.randint(1, 100) <= fill else "0" for _ in range(cols)) for _ in range(rows)]
    return {"g": g}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(largest_square(v["g"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        "This code should print the area of the largest square made only of '1' cells. "
        "Which line goes in the blank?"
    ),
    fix=lambda v: (
        "This code should print the area of the largest square made only of '1' cells, but it "
        "prints the wrong answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"Grid {' / '.join(v['g'])}. dp[i][j] is the side of the largest all-ones square ending at "
        f"(i, j): 1 + the smallest of up, left and up-left. The largest area is {answer}."
    ),
    blanks=[
        Blank(
            UPDATE,
            [
                (lines("dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1])", "dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1]);",
                       "dp[i][j] = 1 + Math.min(dp[i - 1][j], dp[i][j - 1]);"), "sq-missing-diagonal"),
                (lines("dp[i][j] = 1 + max(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])",
                       "dp[i][j] = 1 + max(dp[i - 1][j], max(dp[i][j - 1], dp[i - 1][j - 1]));",
                       "dp[i][j] = 1 + Math.max(dp[i - 1][j], Math.max(dp[i][j - 1], dp[i - 1][j - 1]));"), "min-vs-max"),
                (lines("dp[i][j] = 1 + dp[i - 1][j - 1]", "dp[i][j] = 1 + dp[i - 1][j - 1];"), "sq-missing-diagonal"),
            ],
        ),
        Blank(
            BEST,
            [
                (lines("best = dp[i][j]", "best = dp[i][j];"), "overwrite-best"),
                (lines("best = best + dp[i][j]", "best = best + dp[i][j];"), "count-vs-sum"),
                (lines("best = max(best, dp[i - 1][j])", "best = max(best, dp[i - 1][j]);",
                       "best = Math.max(best, dp[i - 1][j]);"), "dp-wrong-subproblem"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "sq-missing-diagonal",
            edit(UPDATE, lines("dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1])", "dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1]);",
                               "dp[i][j] = 1 + Math.min(dp[i - 1][j], dp[i][j - 1]);")),
            "Include the up-left neighbour dp[i - 1][j - 1] in the minimum",
            "Only the diagonal neighbour checks the square's far corner.",
        ),
        Fix(
            "sq-side-not-area",
            edit(OUTPUT, lines("print(best)", 'cout << best << "\\n";', "System.out.println(best);")),
            "Print best * best, the area",
            "dp stores side lengths; the question asks for an area.",
        ),
        Fix(
            "sq-overwrite-best",
            edit(BEST, lines("best = dp[i][j]", "best = dp[i][j];")),
            "Keep the maximum: best = max(best, dp[i][j])",
            "The largest square can end anywhere, not only at the last 1 cell.",
        ),
    ],
    decoys=[
        Decoy(edit(LOOP_I, lines("for i in range(1, r):", "for (int i = 1; i < r; i++) {")),
              "Stop the row loop one earlier", "loop-bound-off-by-one"),
        Decoy(edit(LOOP_J, lines("for j in range(2, c + 1):", "for (int j = 2; j <= c; j++) {")),
              "Start the columns at 2", "skip-first-element"),
        Decoy(edit(OUTPUT, lines("print(best * best - 1)", 'cout << best * best - 1 << "\\n";',
                                 "System.out.println(best * best - 1);")),
              "Print one less", "off-by-one-output"),
        Decoy(edit(UPDATE, lines("dp[i][j] = 2 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])",
                                 "dp[i][j] = 2 + min(dp[i - 1][j], min(dp[i][j - 1], dp[i - 1][j - 1]));",
                                 "dp[i][j] = 2 + Math.min(dp[i - 1][j], Math.min(dp[i][j - 1], dp[i - 1][j - 1]));")),
              "Add 2 instead of 1", "dp-missing-plus-one"),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"largest_square": largest_square}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
