"""Longest common subsequence with the full prefix table: LCS length of two short strings.

Wrong answers are the classic slips: greedy matching with a pointer, taking up-left on a
mismatch, and resetting to 0 on a mismatch (which computes the common substring instead).
"""

from itertools import combinations

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

ROWS = lines("for i in range(1, n + 1):", "for (int i = 1; i <= n; i++) {")
MATCH = lines("dp[i][j] = dp[i - 1][j - 1] + 1", "dp[i][j] = dp[i - 1][j - 1] + 1;")
MISMATCH = lines("dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])", "dp[i][j] = max(dp[i - 1][j], dp[i][j - 1]);",
                 "dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);")
OUTPUT = lines("print(dp[n][m])", 'cout << dp[n][m] << "\\n";', "System.out.println(dp[n][m]);")
TABLE = lines("dp = [[0] * (m + 1) for _ in range(n + 1)]", "vector<vector<int>> dp(n + 1, vector<int>(m + 1, 0));",
              "int[][] dp = new int[n + 1][m + 1];")


def program(v: dict) -> dict[str, str]:
    a, b = v["a"], v["b"]
    return {
        "python": (
            f'a = "{a}"\nb = "{b}"\n'
            "n, m = len(a), len(b)\n"
            "dp = [[0] * (m + 1) for _ in range(n + 1)]\n"
            "for i in range(1, n + 1):\n"
            "    for j in range(1, m + 1):\n"
            "        if a[i - 1] == b[j - 1]:\n"
            "            dp[i][j] = dp[i - 1][j - 1] + 1\n"
            "        else:\n"
            "            dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])\n"
            "print(dp[n][m])"
        ),
        "cpp": (
            f'string a = "{a}";\nstring b = "{b}";\n'
            "int n = a.size(), m = b.size();\n"
            "vector<vector<int>> dp(n + 1, vector<int>(m + 1, 0));\n"
            "for (int i = 1; i <= n; i++) {\n"
            "    for (int j = 1; j <= m; j++) {\n"
            "        if (a[i - 1] == b[j - 1]) {\n"
            "            dp[i][j] = dp[i - 1][j - 1] + 1;\n"
            "        } else {\n"
            "            dp[i][j] = max(dp[i - 1][j], dp[i][j - 1]);\n"
            "        }\n"
            "    }\n"
            "}\n"
            'cout << dp[n][m] << "\\n";'
        ),
        "java": (
            f'String a = "{a}";\nString b = "{b}";\n'
            "int n = a.length(), m = b.length();\n"
            "int[][] dp = new int[n + 1][m + 1];\n"
            "for (int i = 1; i <= n; i++) {\n"
            "    for (int j = 1; j <= m; j++) {\n"
            "        if (a.charAt(i - 1) == b.charAt(j - 1)) {\n"
            "            dp[i][j] = dp[i - 1][j - 1] + 1;\n"
            "        } else {\n"
            "            dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);\n"
            "        }\n"
            "    }\n"
            "}\n"
            "System.out.println(dp[n][m]);"
        ),
    }


def is_subsequence(s: str, t: str) -> bool:
    it = iter(t)
    return all(ch in it for ch in s)


def lcs_brute(a: str, b: str) -> int:
    """Independent check: the longest subset of a's positions that is a subsequence of b."""
    for size in range(len(a), 0, -1):
        if any(is_subsequence("".join(a[i] for i in keep), b) for keep in combinations(range(len(a)), size)):
            return size
    return 0


def greedy(a, b):
    pos, length = 0, 0
    for ch in a:
        k = b.find(ch, pos)
        if k != -1:
            length, pos = length + 1, k + 1
    return length


def table(a, b, mismatch):
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if a[i - 1] == b[j - 1] else mismatch(dp, i, j)
    return dp


def wrong(v):
    a, b = v["a"], v["b"]
    substring = max(max(row) for row in table(a, b, lambda dp, i, j: 0))
    return [
        (str(greedy(a, b)), "lcs-greedy-match"),
        (str(greedy(b, a)), "lcs-greedy-match"),
        (str(table(a, b, lambda dp, i, j: dp[i - 1][j - 1])[-1][-1]), "lcs-mismatch-diagonal"),
        (str(substring), "pattern-subsequence-vs-substring"),
        (str(min(len(a), len(b))), "lcs-index-offset"),
    ]


def sample(rng, params):
    alphabet = "abc"[: rng.randint(*params["letters"])]
    return {
        "a": "".join(rng.choice(alphabet) for _ in range(rng.randint(*params["length"]))),
        "b": "".join(rng.choice(alphabet) for _ in range(rng.randint(*params["length"]))),
    }


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(lcs_brute(v["a"], v["b"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f'This code should print the length of the longest common subsequence of "{v["a"]}" and '
        f'"{v["b"]}". Which line goes in the blank?'
    ),
    fix=lambda v: (
        f'This code should print the length of the longest common subsequence of "{v["a"]}" and '
        f'"{v["b"]}", but it prints the wrong answer. Which one-line change fixes it?'
    ),
    explain=lambda v, answer: (
        f"dp[i][j] is the LCS of the first i and first j characters: a match extends the "
        f"up-left cell by 1, a mismatch keeps the better of up and left. "
        f'The LCS of "{v["a"]}" and "{v["b"]}" has length {answer}.'
    ),
    blanks=[
        Blank(
            MISMATCH,
            [
                (lines("dp[i][j] = dp[i - 1][j - 1]", "dp[i][j] = dp[i - 1][j - 1];"), "lcs-mismatch-diagonal"),
                (lines("dp[i][j] = 0", "dp[i][j] = 0;"), "pattern-subsequence-vs-substring"),
                (lines("dp[i][j] = min(dp[i - 1][j], dp[i][j - 1])", "dp[i][j] = min(dp[i - 1][j], dp[i][j - 1]);",
                       "dp[i][j] = Math.min(dp[i - 1][j], dp[i][j - 1]);"), "min-vs-max"),
            ],
        ),
        Blank(
            MATCH,
            [
                (lines("dp[i][j] = dp[i - 1][j - 1]", "dp[i][j] = dp[i - 1][j - 1];"), "dp-missing-plus-one"),
                (lines("dp[i][j] = dp[i - 1][j] + 1", "dp[i][j] = dp[i - 1][j] + 1;"), "dp-wrong-subproblem"),
                (lines("dp[i][j] = dp[i][j - 1] + 1", "dp[i][j] = dp[i][j - 1] + 1;"), "dp-wrong-subproblem"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "lcs-mismatch-diagonal",
            edit(MISMATCH, lines("dp[i][j] = dp[i - 1][j - 1]", "dp[i][j] = dp[i - 1][j - 1];")),
            "On a mismatch, take the larger of dp[i - 1][j] and dp[i][j - 1]",
            "Dropping both characters loses one that may still match later.",
        ),
        Fix(
            "lcs-mismatch-reset",
            edit(MISMATCH, lines("dp[i][j] = 0", "dp[i][j] = 0;")),
            "On a mismatch, keep the larger of dp[i - 1][j] and dp[i][j - 1] instead of 0",
            "Resetting to 0 measures contiguous blocks (substrings), not subsequences.",
        ),
        Fix(
            "lcs-match-no-plus-one",
            edit(MATCH, lines("dp[i][j] = dp[i - 1][j - 1]", "dp[i][j] = dp[i - 1][j - 1];")),
            "On a match, add 1 to dp[i - 1][j - 1]",
            "A matching pair of characters extends the common subsequence by one.",
        ),
    ],
    decoys=[
        Decoy(edit(OUTPUT, lines("print(dp[n - 1][m - 1])", 'cout << dp[n - 1][m - 1] << "\\n";',
                                 "System.out.println(dp[n - 1][m - 1]);")),
              "Print dp[n - 1][m - 1] instead", "lcs-index-offset"),
        Decoy(edit(TABLE, lines("dp = [[0] * (m + 2) for _ in range(n + 2)]", "vector<vector<int>> dp(n + 2, vector<int>(m + 2, 0));",
                                "int[][] dp = new int[n + 2][m + 2];")),
              "Make the table one row and column larger", "loop-bound-off-by-one"),
        Decoy(edit(ROWS, lines("for i in range(1, n):", "for (int i = 1; i < n; i++) {")),
              "Stop the row loop one earlier", "loop-bound-off-by-one"),
        Decoy(edit(MATCH, lines("dp[i][j] = dp[i - 1][j - 1] + 2", "dp[i][j] = dp[i - 1][j - 1] + 2;")),
              "Add 2 on a match, one for each string", "double-count"),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"lcs_brute": lcs_brute}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
