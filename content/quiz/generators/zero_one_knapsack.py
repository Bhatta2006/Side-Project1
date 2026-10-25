"""0/1 knapsack with one capacity row filled backwards: best value within capacity W.

Wrong answers are the classic slips: looping the capacity forwards (items reused), greedy by
value per weight, and stopping the capacity loop one short of the item's weight.
"""

from itertools import combinations

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

ITEMS = lines("for i in range(len(w)):", "for (int i = 0; i < (int)w.size(); i++) {",
              "for (int i = 0; i < w.length; i++) {")
CAPACITY = lines("for c in range(W, w[i] - 1, -1):", "for (int c = W; c >= w[i]; c--) {")
UPDATE = lines("dp[c] = max(dp[c], dp[c - w[i]] + v[i])", "dp[c] = max(dp[c], dp[c - w[i]] + v[i]);",
               "dp[c] = Math.max(dp[c], dp[c - w[i]] + v[i]);")
TABLE = lines("dp = [0] * (W + 1)", "vector<int> dp(W + 1, 0);", "int[] dp = new int[W + 1];")
OUTPUT = lines("print(dp[W])", 'cout << dp[W] << "\\n";', "System.out.println(dp[W]);")


def program(v: dict) -> dict[str, str]:
    w, val, W = ", ".join(map(str, v["w"])), ", ".join(map(str, v["v"])), v["W"]
    return {
        "python": (
            f"w = [{w}]\nv = [{val}]\nW = {W}\n"
            "dp = [0] * (W + 1)\n"
            "for i in range(len(w)):\n"
            "    for c in range(W, w[i] - 1, -1):\n"
            "        dp[c] = max(dp[c], dp[c - w[i]] + v[i])\n"
            "print(dp[W])"
        ),
        "cpp": (
            f"vector<int> w = {{{w}}};\nvector<int> v = {{{val}}};\nint W = {W};\n"
            "vector<int> dp(W + 1, 0);\n"
            "for (int i = 0; i < (int)w.size(); i++) {\n"
            "    for (int c = W; c >= w[i]; c--) {\n"
            "        dp[c] = max(dp[c], dp[c - w[i]] + v[i]);\n"
            "    }\n"
            "}\n"
            'cout << dp[W] << "\\n";'
        ),
        "java": (
            f"int[] w = {{{w}}};\nint[] v = {{{val}}};\nint W = {W};\n"
            "int[] dp = new int[W + 1];\n"
            "for (int i = 0; i < w.length; i++) {\n"
            "    for (int c = W; c >= w[i]; c--) {\n"
            "        dp[c] = Math.max(dp[c], dp[c - w[i]] + v[i]);\n"
            "    }\n"
            "}\n"
            "System.out.println(dp[W]);"
        ),
    }


def best_subset(w: list[int], v: list[int], W: int) -> int:
    """Independent check: try every subset of items."""
    best = 0
    for size in range(len(w) + 1):
        for chosen in combinations(range(len(w)), size):
            if sum(w[i] for i in chosen) <= W:
                best = max(best, sum(v[i] for i in chosen))
    return best


def unbounded(w, v, W):
    dp = [0] * (W + 1)
    for i in range(len(w)):
        for c in range(w[i], W + 1):
            dp[c] = max(dp[c], dp[c - w[i]] + v[i])
    return dp[W]


def greedy_ratio(w, v, W):
    total = 0
    for i in sorted(range(len(w)), key=lambda i: v[i] / w[i], reverse=True):
        if w[i] <= W:
            W -= w[i]
            total += v[i]
    return total


def wrong(v):
    w, val, W = v["w"], v["v"], v["W"]
    return [
        (str(unbounded(w, val, W)), "knapsack-forward-capacity-loop"),
        (str(greedy_ratio(w, val, W)), "knapsack-greedy-ratio"),
        (str(sum(val[i] for i in range(len(w)) if w[i] <= W)), "knapsack-ignore-capacity"),
        (str(max(val)), "knapsack-single-item"),
    ]


def sample(rng, params):
    n = rng.randint(*params["items"])
    return {
        "w": [rng.randint(*params["weight"]) for _ in range(n)],
        "v": [rng.randint(*params["value"]) for _ in range(n)],
        "W": rng.randint(*params["capacity"]),
    }


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(best_subset(v["w"], v["v"], v["W"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"Each item may be taken at most once. This code should print the best total value "
        f"within capacity {v['W']}. Which line goes in the blank?"
    ),
    fix=lambda v: (
        f"Each item may be taken at most once. This code should print the best total value within "
        f"capacity {v['W']}, but it prints the wrong answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"dp[c] is the best value within capacity c. Each item is tried once, filling c from W "
        f"down so the item is not reused. The best value within {v['W']} is {answer}."
    ),
    blanks=[
        Blank(
            UPDATE,
            [
                (lines("dp[c] = max(dp[c], dp[c - w[i]] + w[i])", "dp[c] = max(dp[c], dp[c - w[i]] + w[i]);",
                       "dp[c] = Math.max(dp[c], dp[c - w[i]] + w[i]);"), "knapsack-weight-for-value"),
                (lines("dp[c] = dp[c - w[i]] + v[i]", "dp[c] = dp[c - w[i]] + v[i];"), "knapsack-always-take"),
                (lines("dp[c] = max(dp[c], dp[c - 1] + v[i])", "dp[c] = max(dp[c], dp[c - 1] + v[i]);",
                       "dp[c] = Math.max(dp[c], dp[c - 1] + v[i]);"), "dp-wrong-subproblem"),
            ],
        ),
        Blank(
            CAPACITY,
            [
                (lines("for c in range(w[i], W + 1):", "for (int c = w[i]; c <= W; c++) {"),
                 "knapsack-forward-capacity-loop"),
                (lines("for c in range(W, w[i], -1):", "for (int c = W; c > w[i]; c--) {"),
                 "knapsack-capacity-boundary"),
                (lines("for c in range(W - 1, w[i] - 1, -1):", "for (int c = W - 1; c >= w[i]; c--) {"),
                 "loop-bound-off-by-one"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "knapsack-forward-loop",
            edit(CAPACITY, lines("for c in range(w[i], W + 1):", "for (int c = w[i]; c <= W; c++) {")),
            "Loop the capacity from W down to w[i]",
            "Going upwards reads cells that already include item i, so it can be taken twice.",
        ),
        Fix(
            "knapsack-capacity-boundary",
            edit(CAPACITY, lines("for c in range(W, w[i], -1):", "for (int c = W; c > w[i]; c--) {")),
            "Include capacity c equal to w[i] (use >=)",
            "An item that exactly fills capacity c must still be considered.",
        ),
        Fix(
            "knapsack-weight-for-value",
            edit(UPDATE, lines("dp[c] = max(dp[c], dp[c - w[i]] + w[i])", "dp[c] = max(dp[c], dp[c - w[i]] + w[i]);",
                               "dp[c] = Math.max(dp[c], dp[c - w[i]] + w[i]);")),
            "Add the item's value v[i], not its weight",
            "Taking the item adds its value; its weight only reduces the capacity left.",
        ),
    ],
    decoys=[
        Decoy(edit(OUTPUT, lines("print(dp[W - 1])", 'cout << dp[W - 1] << "\\n";', "System.out.println(dp[W - 1]);")),
              "Print dp[W - 1] instead", "loop-bound-off-by-one"),
        Decoy(edit(TABLE, lines("dp = [0] * (W + 2)", "vector<int> dp(W + 2, 0);", "int[] dp = new int[W + 2];")),
              "Make the table one cell longer", "loop-bound-off-by-one"),
        Decoy(edit(ITEMS, lines("for i in range(len(w) - 1):", "for (int i = 0; i < (int)w.size() - 1; i++) {",
                                "for (int i = 0; i < w.length - 1; i++) {")),
              "Skip the last item", "loop-bound-off-by-one"),
        Decoy(edit(UPDATE, lines("dp[c] = max(dp[c], dp[c - w[i]] + v[i] + 1)", "dp[c] = max(dp[c], dp[c - w[i]] + v[i] + 1);",
                                 "dp[c] = Math.max(dp[c], dp[c - w[i]] + v[i] + 1);")),
              "Add 1 for every item taken", "dp-missing-plus-one"),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"best_subset": best_subset}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
