"""Edit distance (insert, delete, replace) with the full prefix table.

Wrong answers are the classic slips: the LCS shortcut n + m - 2*LCS (no replace), comparing
positions one by one, and leaving the base row and column at zero.
"""

from functools import lru_cache

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

BASE_COL = lines("dp[i][0] = i", "dp[i][0] = i;")
BASE_ROW = lines("dp[0][j] = j", "dp[0][j] = j;")
ROWS = lines("for i in range(1, n + 1):", "for (int i = 1; i <= n; i++) {")
SAME = lines("dp[i][j] = dp[i - 1][j - 1]", "dp[i][j] = dp[i - 1][j - 1];")
DIFF = lines("dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])",
             "dp[i][j] = 1 + min(dp[i - 1][j], min(dp[i][j - 1], dp[i - 1][j - 1]));",
             "dp[i][j] = 1 + Math.min(dp[i - 1][j], Math.min(dp[i][j - 1], dp[i - 1][j - 1]));")
OUTPUT = lines("print(dp[n][m])", 'cout << dp[n][m] << "\\n";', "System.out.println(dp[n][m]);")


def program(v: dict) -> dict[str, str]:
    a, b = v["a"], v["b"]
    return {
        "python": (
            f'a = "{a}"\nb = "{b}"\n'
            "n, m = len(a), len(b)\n"
            "dp = [[0] * (m + 1) for _ in range(n + 1)]\n"
            "for i in range(n + 1):\n"
            "    dp[i][0] = i\n"
            "for j in range(m + 1):\n"
            "    dp[0][j] = j\n"
            "for i in range(1, n + 1):\n"
            "    for j in range(1, m + 1):\n"
            "        if a[i - 1] == b[j - 1]:\n"
            "            dp[i][j] = dp[i - 1][j - 1]\n"
            "        else:\n"
            "            dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])\n"
            "print(dp[n][m])"
        ),
        "cpp": (
            f'string a = "{a}";\nstring b = "{b}";\n'
            "int n = a.size(), m = b.size();\n"
            "vector<vector<int>> dp(n + 1, vector<int>(m + 1, 0));\n"
            "for (int i = 0; i <= n; i++) {\n"
            "    dp[i][0] = i;\n"
            "}\n"
            "for (int j = 0; j <= m; j++) {\n"
            "    dp[0][j] = j;\n"
            "}\n"
            "for (int i = 1; i <= n; i++) {\n"
            "    for (int j = 1; j <= m; j++) {\n"
            "        if (a[i - 1] == b[j - 1]) {\n"
            "            dp[i][j] = dp[i - 1][j - 1];\n"
            "        } else {\n"
            "            dp[i][j] = 1 + min(dp[i - 1][j], min(dp[i][j - 1], dp[i - 1][j - 1]));\n"
            "        }\n"
            "    }\n"
            "}\n"
            'cout << dp[n][m] << "\\n";'
        ),
        "java": (
            f'String a = "{a}";\nString b = "{b}";\n'
            "int n = a.length(), m = b.length();\n"
            "int[][] dp = new int[n + 1][m + 1];\n"
            "for (int i = 0; i <= n; i++) {\n"
            "    dp[i][0] = i;\n"
            "}\n"
            "for (int j = 0; j <= m; j++) {\n"
            "    dp[0][j] = j;\n"
            "}\n"
            "for (int i = 1; i <= n; i++) {\n"
            "    for (int j = 1; j <= m; j++) {\n"
            "        if (a.charAt(i - 1) == b.charAt(j - 1)) {\n"
            "            dp[i][j] = dp[i - 1][j - 1];\n"
            "        } else {\n"
            "            dp[i][j] = 1 + Math.min(dp[i - 1][j], Math.min(dp[i][j - 1], dp[i - 1][j - 1]));\n"
            "        }\n"
            "    }\n"
            "}\n"
            "System.out.println(dp[n][m]);"
        ),
    }


def distance(a: str, b: str) -> int:
    """Independent check: recursion on suffixes, memoised."""

    @lru_cache(maxsize=None)
    def go(i: int, j: int) -> int:
        if i == len(a) or j == len(b):
            return len(a) - i + len(b) - j
        if a[i] == b[j]:
            return go(i + 1, j + 1)
        return 1 + min(go(i + 1, j), go(i, j + 1), go(i + 1, j + 1))

    return go(0, 0)


def lcs(a, b):
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if x == y else max(prev[j], cur[j - 1]))
        prev = cur
    return prev[-1]


def wrong(v):
    a, b = v["a"], v["b"]
    positions = sum(x != y for x, y in zip(a, b)) + abs(len(a) - len(b))
    return [
        (str(len(a) + len(b) - 2 * lcs(a, b)), "pattern-edit-vs-lcs-deletions"),
        (str(positions), "edit-position-compare"),
        (str(abs(len(a) - len(b))), "edit-base-zero"),
        (str(max(len(a), len(b))), "edit-match-costs-one"),
    ]


def sample(rng, params):
    alphabet = "abcd"[: rng.randint(*params["letters"])]
    return {
        "a": "".join(rng.choice(alphabet) for _ in range(rng.randint(*params["length"]))),
        "b": "".join(rng.choice(alphabet) for _ in range(rng.randint(*params["length"]))),
    }


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(distance(v["a"], v["b"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f'This code should print the fewest inserts, deletes and replaces that turn "{v["a"]}" into '
        f'"{v["b"]}". Which line goes in the blank?'
    ),
    fix=lambda v: (
        f'This code should print the fewest inserts, deletes and replaces that turn "{v["a"]}" into '
        f'"{v["b"]}", but it prints the wrong answer. Which one-line change fixes it?'
    ),
    explain=lambda v, answer: (
        f"dp[i][j] turns the first i characters of a into the first j of b. Equal last characters "
        f"cost nothing; otherwise take 1 + the cheapest of delete, insert and replace. "
        f'The edit distance from "{v["a"]}" to "{v["b"]}" is {answer}.'
    ),
    blanks=[
        Blank(
            DIFF,
            [
                (lines("dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1])", "dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1]);",
                       "dp[i][j] = 1 + Math.min(dp[i - 1][j], dp[i][j - 1]);"), "edit-missing-replace"),
                (lines("dp[i][j] = min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])",
                       "dp[i][j] = min(dp[i - 1][j], min(dp[i][j - 1], dp[i - 1][j - 1]));",
                       "dp[i][j] = Math.min(dp[i - 1][j], Math.min(dp[i][j - 1], dp[i - 1][j - 1]));"),
                 "dp-missing-plus-one"),
                (lines("dp[i][j] = 1 + max(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])",
                       "dp[i][j] = 1 + max(dp[i - 1][j], max(dp[i][j - 1], dp[i - 1][j - 1]));",
                       "dp[i][j] = 1 + Math.max(dp[i - 1][j], Math.max(dp[i][j - 1], dp[i - 1][j - 1]));"),
                 "min-vs-max"),
            ],
        ),
        Blank(
            SAME,
            [
                (lines("dp[i][j] = dp[i - 1][j - 1] + 1", "dp[i][j] = dp[i - 1][j - 1] + 1;"), "edit-match-costs-one"),
                (lines("dp[i][j] = dp[i - 1][j]", "dp[i][j] = dp[i - 1][j];"), "dp-wrong-subproblem"),
                (lines("dp[i][j] = 0", "dp[i][j] = 0;"), "dp-wrong-base-case"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "edit-base-zero",
            edit(BASE_COL, lines("dp[i][0] = 0", "dp[i][0] = 0;")),
            "Set dp[i][0] = i",
            "Turning i characters into the empty string takes i deletions.",
        ),
        Fix(
            "edit-missing-replace",
            edit(DIFF, lines("dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1])", "dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1]);",
                             "dp[i][j] = 1 + Math.min(dp[i - 1][j], dp[i][j - 1]);")),
            "Include the replace option dp[i - 1][j - 1] in the minimum",
            "A wrong character can be fixed with one replace instead of a delete and an insert.",
        ),
        Fix(
            "edit-match-costs-one",
            edit(SAME, lines("dp[i][j] = dp[i - 1][j - 1] + 1", "dp[i][j] = dp[i - 1][j - 1] + 1;")),
            "Copy dp[i - 1][j - 1] without adding 1 when the characters are equal",
            "Equal last characters need no edit.",
        ),
    ],
    decoys=[
        Decoy(edit(OUTPUT, lines("print(dp[n - 1][m - 1])", 'cout << dp[n - 1][m - 1] << "\\n";',
                                 "System.out.println(dp[n - 1][m - 1]);")),
              "Print dp[n - 1][m - 1] instead", "loop-bound-off-by-one"),
        Decoy(edit(BASE_ROW, lines("dp[0][j] = j + 1", "dp[0][j] = j + 1;")),
              "Start the base row at 1", "dp-wrong-base-case"),
        Decoy(edit(ROWS, lines("for i in range(1, n):", "for (int i = 1; i < n; i++) {")),
              "Stop the row loop one earlier", "loop-bound-off-by-one"),
        Decoy(edit(DIFF, lines("dp[i][j] = 2 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])",
                               "dp[i][j] = 2 + min(dp[i - 1][j], min(dp[i][j - 1], dp[i - 1][j - 1]));",
                               "dp[i][j] = 2 + Math.min(dp[i - 1][j], Math.min(dp[i][j - 1], dp[i - 1][j - 1]));")),
              "Charge 2 for every mismatch", "edit-position-compare"),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"distance": distance}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
