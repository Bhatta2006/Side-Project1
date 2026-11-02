"""Minimum path sum from the top-left to the bottom-right moving only right or down.

Wrong answers walk greedily to the cheaper neighbour, take the most expensive path, or
forget to include the start cell.
"""

from itertools import combinations

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, lines

MAIN = lines("dp[r][c] = min(dp[r - 1][c], dp[r][c - 1]) + grid[r][c]",
             "dp[r][c] = min(dp[r - 1][c], dp[r][c - 1]) + grid[r][c];",
             "dp[r][c] = Math.min(dp[r - 1][c], dp[r][c - 1]) + grid[r][c];")
ROW = lines("dp[r][c] = dp[r][c - 1] + grid[r][c]", "dp[r][c] = dp[r][c - 1] + grid[r][c];")


def program(v: dict) -> dict[str, str]:
    g = v["grid"]
    rows, cols = len(g), len(g[0])
    py = ", ".join("[" + ", ".join(map(str, row)) + "]" for row in g)
    braces = ", ".join("{" + ", ".join(map(str, row)) + "}" for row in g)
    body = (
        "if (r == 0 && c == 0) {\n"
        "            dp[r][c] = grid[r][c];\n"
        "        } else if (r == 0) {\n"
        "            dp[r][c] = dp[r][c - 1] + grid[r][c];\n"
        "        } else if (c == 0) {\n"
        "            dp[r][c] = dp[r - 1][c] + grid[r][c];\n"
        "        } else {\n"
    )
    return {
        "python": (
            f"grid = [{py}]\n"
            f"R, C = {rows}, {cols}\n"
            "dp = [[0] * C for _ in range(R)]\n"
            "for r in range(R):\n"
            "    for c in range(C):\n"
            "        if r == 0 and c == 0:\n"
            "            dp[r][c] = grid[r][c]\n"
            "        elif r == 0:\n"
            "            dp[r][c] = dp[r][c - 1] + grid[r][c]\n"
            "        elif c == 0:\n"
            "            dp[r][c] = dp[r - 1][c] + grid[r][c]\n"
            "        else:\n"
            "            dp[r][c] = min(dp[r - 1][c], dp[r][c - 1]) + grid[r][c]\n"
            "print(dp[R - 1][C - 1])"
        ),
        "cpp": (
            f"vector<vector<int>> grid = {{{braces}}};\n"
            f"int R = {rows}, C = {cols};\n"
            "vector<vector<int>> dp(R, vector<int>(C, 0));\n"
            "for (int r = 0; r < R; r++) {\n"
            "    for (int c = 0; c < C; c++) {\n"
            f"        {body}"
            "            dp[r][c] = min(dp[r - 1][c], dp[r][c - 1]) + grid[r][c];\n"
            "        }\n"
            "    }\n"
            "}\n"
            'cout << dp[R - 1][C - 1] << "\\n";'
        ),
        "java": (
            f"int[][] grid = {{{braces}}};\n"
            f"int R = {rows}, C = {cols};\n"
            "int[][] dp = new int[R][C];\n"
            "for (int r = 0; r < R; r++) {\n"
            "    for (int c = 0; c < C; c++) {\n"
            f"        {body}"
            "            dp[r][c] = Math.min(dp[r - 1][c], dp[r][c - 1]) + grid[r][c];\n"
            "        }\n"
            "    }\n"
            "}\n"
            "System.out.println(dp[R - 1][C - 1]);"
        ),
    }


def path_sums(grid: list) -> list[int]:
    """Every right/down path's sum: choose which of the R + C - 2 moves go down."""
    rows, cols = len(grid), len(grid[0])
    out = []
    for downs in combinations(range(rows + cols - 2), rows - 1):
        r = c = 0
        total = grid[0][0]
        for step in range(rows + cols - 2):
            if step in downs:
                r += 1
            else:
                c += 1
            total += grid[r][c]
        out.append(total)
    return out


def cheapest(grid: list) -> int:
    return min(path_sums(grid))


def greedy(grid: list) -> int:
    rows, cols = len(grid), len(grid[0])
    r = c = 0
    total = grid[0][0]
    while (r, c) != (rows - 1, cols - 1):
        if r == rows - 1:
            c += 1
        elif c == cols - 1:
            r += 1
        elif grid[r + 1][c] < grid[r][c + 1]:
            r += 1
        else:
            c += 1
        total += grid[r][c]
    return total


def wrong(v):
    g = v["grid"]
    return [
        (str(greedy(g)), "dp-greedy-local-choice"),
        (str(max(path_sums(g))), "min-vs-max"),
        (str(cheapest(g) - g[0][0]), "dp-wrong-base-case"),
        (str(cheapest(g) + 1), "off-by-one-output"),
    ]


def sample(rng, params):
    rows = rng.randint(*params["rows"])
    cols = rng.randint(*params["cols"])
    return {"grid": [[rng.randint(*params["value"]) for _ in range(cols)] for _ in range(rows)]}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(cheapest(v["grid"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        "This code should print the smallest sum along a path from the top-left to the "
        "bottom-right cell, moving only right or down. Which line goes in the blank?"
    ),
    fix=lambda v: "",
    explain=lambda v, answer: (
        "dp[r][c] is the cheapest way to reach (r, c): the first row and column have only one "
        "way in, every other cell takes the cheaper of the cell above and the cell to the left. "
        f"The bottom-right cell holds {answer}. Stepping to the cheaper neighbour each time can "
        "walk into an expensive region later."
    ),
    blanks=[
        Blank(
            MAIN,
            [
                (lines("dp[r][c] = max(dp[r - 1][c], dp[r][c - 1]) + grid[r][c]",
                       "dp[r][c] = max(dp[r - 1][c], dp[r][c - 1]) + grid[r][c];",
                       "dp[r][c] = Math.max(dp[r - 1][c], dp[r][c - 1]) + grid[r][c];"), "min-vs-max"),
                (lines("dp[r][c] = min(dp[r - 1][c - 1], dp[r][c - 1]) + grid[r][c]",
                       "dp[r][c] = min(dp[r - 1][c - 1], dp[r][c - 1]) + grid[r][c];",
                       "dp[r][c] = Math.min(dp[r - 1][c - 1], dp[r][c - 1]) + grid[r][c];"),
                 "dp-wrong-subproblem"),
                (lines("dp[r][c] = min(dp[r - 1][c], dp[r][c - 1])",
                       "dp[r][c] = min(dp[r - 1][c], dp[r][c - 1]);",
                       "dp[r][c] = Math.min(dp[r - 1][c], dp[r][c - 1]);"), "dp-missing-plus-one"),
            ],
        ),
        Blank(
            ROW,
            [
                (lines("dp[r][c] = grid[r][c]", "dp[r][c] = grid[r][c];"), "dp-wrong-base-case"),
                (lines("dp[r][c] = dp[r][c - 1]", "dp[r][c] = dp[r][c - 1];"), "dp-missing-plus-one"),
                (lines("dp[r][c] = 0", "dp[r][c] = 0;"), "dp-wrong-base-case"),
            ],
        ),
    ],
    bands=(4, 4, 5),
)
HELPERS = {"cheapest": cheapest}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
