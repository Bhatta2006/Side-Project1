"""Stock trading with at most k transactions: the cash/hold state machine, one array per state.

Wrong answers are the classic slips: ignoring the limit (sum of every rise), keeping the k
biggest rising runs, selling before buying (max - min), and buying from cash[t] instead of
cash[t - 1].
"""

from functools import lru_cache

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

INIT = lines("hold = [-1000] * (k + 1)", "vector<int> hold(k + 1, -1000);",
             "int[] hold = new int[k + 1]; java.util.Arrays.fill(hold, -1000);")
CASH = lines("cash = [0] * (k + 1)", "vector<int> cash(k + 1, 0);", "int[] cash = new int[k + 1];")
DAYS = lines("for price in p:", "for (int price : p) {")
SELL = lines("cash[t] = max(cash[t], hold[t] + price)", "cash[t] = max(cash[t], hold[t] + price);",
             "cash[t] = Math.max(cash[t], hold[t] + price);")
BUY = lines("hold[t] = max(hold[t], cash[t - 1] - price)", "hold[t] = max(hold[t], cash[t - 1] - price);",
            "hold[t] = Math.max(hold[t], cash[t - 1] - price);")
OUTPUT = lines("print(cash[k])", 'cout << cash[k] << "\\n";', "System.out.println(cash[k]);")


def program(v: dict) -> dict[str, str]:
    p, k = ", ".join(map(str, v["p"])), v["k"]
    return {
        "python": (
            f"p = [{p}]\nk = {k}\n"
            "cash = [0] * (k + 1)\n"
            "hold = [-1000] * (k + 1)\n"
            "for price in p:\n"
            "    for t in range(k, 0, -1):\n"
            "        cash[t] = max(cash[t], hold[t] + price)\n"
            "        hold[t] = max(hold[t], cash[t - 1] - price)\n"
            "print(cash[k])"
        ),
        "cpp": (
            f"vector<int> p = {{{p}}};\nint k = {k};\n"
            "vector<int> cash(k + 1, 0);\n"
            "vector<int> hold(k + 1, -1000);\n"
            "for (int price : p) {\n"
            "    for (int t = k; t >= 1; t--) {\n"
            "        cash[t] = max(cash[t], hold[t] + price);\n"
            "        hold[t] = max(hold[t], cash[t - 1] - price);\n"
            "    }\n"
            "}\n"
            'cout << cash[k] << "\\n";'
        ),
        "java": (
            f"int[] p = {{{p}}};\nint k = {k};\n"
            "int[] cash = new int[k + 1];\n"
            "int[] hold = new int[k + 1]; java.util.Arrays.fill(hold, -1000);\n"
            "for (int price : p) {\n"
            "    for (int t = k; t >= 1; t--) {\n"
            "        cash[t] = Math.max(cash[t], hold[t] + price);\n"
            "        hold[t] = Math.max(hold[t], cash[t - 1] - price);\n"
            "    }\n"
            "}\n"
            "System.out.println(cash[k]);"
        ),
    }


def best_profit(p: list[int], k: int) -> int:
    """Independent check: recursion over (day, holding, buys left)."""

    @lru_cache(maxsize=None)
    def go(day: int, holding: bool, left: int) -> int:
        if day == len(p):
            return 0
        result = go(day + 1, holding, left)
        if holding:
            result = max(result, p[day] + go(day + 1, False, left))
        elif left:
            result = max(result, -p[day] + go(day + 1, True, left - 1))
        return result

    return go(0, False, k)


def runs(p, k):
    out, start = [], 0
    for i in range(1, len(p) + 1):
        if i == len(p) or p[i] < p[i - 1]:
            out.append(p[i - 1] - p[start])
            start = i
    return sum(sorted(out, reverse=True)[:k])


def wrong(v):
    p, k = v["p"], v["k"]
    return [
        (str(sum(max(0, b - a) for a, b in zip(p, p[1:]))), "stock-unlimited-when-limited"),
        (str(runs(p, k)), "stock-greedy-runs"),
        (str(max(p) - min(p)), "stock-sell-before-buy"),
        (str(best_profit(p, 1)), "stock-buy-wrong-count"),
        (str(max(0, p[-1] - p[0])), "stock-greedy-runs"),
    ]


def sample(rng, params):
    return {
        "p": [rng.randint(*params["price"]) for _ in range(rng.randint(*params["days"]))],
        "k": rng.randint(*params["trades"]),
    }


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(best_profit(v["p"], v["k"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should print the best profit from the prices with at most {v['k']} "
        f"buy-then-sell transactions. Which line goes in the blank?"
    ),
    fix=lambda v: (
        f"This code should print the best profit with at most {v['k']} buy-then-sell "
        f"transactions, but it prints the wrong answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"cash[t] is the best money holding nothing and hold[t] the best money holding a share, "
        f"with at most t buys. Selling adds the price; buying spends it and uses a transaction. "
        f"With at most {v['k']} transactions the best profit is {answer}."
    ),
    blanks=[
        Blank(
            SELL,
            [
                (lines("cash[t] = max(cash[t], hold[t] - price)", "cash[t] = max(cash[t], hold[t] - price);",
                       "cash[t] = Math.max(cash[t], hold[t] - price);"), "stock-sell-sign"),
                (lines("cash[t] = hold[t] + price", "cash[t] = hold[t] + price;"), "knapsack-always-take"),
                (lines("cash[t] = max(cash[t], hold[t - 1] + price)", "cash[t] = max(cash[t], hold[t - 1] + price);",
                       "cash[t] = Math.max(cash[t], hold[t - 1] + price);"), "stock-buy-wrong-count"),
            ],
        ),
        Blank(
            BUY,
            [
                (lines("hold[t] = max(hold[t], cash[t] - price)", "hold[t] = max(hold[t], cash[t] - price);",
                       "hold[t] = Math.max(hold[t], cash[t] - price);"), "stock-buy-wrong-count"),
                (lines("hold[t] = max(hold[t], cash[t - 1] + price)", "hold[t] = max(hold[t], cash[t - 1] + price);",
                       "hold[t] = Math.max(hold[t], cash[t - 1] + price);"), "stock-sell-sign"),
                (lines("hold[t] = cash[t - 1] - price", "hold[t] = cash[t - 1] - price;"), "knapsack-always-take"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "stock-buy-wrong-count",
            edit(BUY, lines("hold[t] = max(hold[t], cash[t] - price)", "hold[t] = max(hold[t], cash[t] - price);",
                            "hold[t] = Math.max(hold[t], cash[t] - price);")),
            "Buy from cash[t - 1], so each buy uses one transaction",
            "Buying from cash[t] never uses up a transaction, so the limit is ignored.",
        ),
        Fix(
            "stock-sell-sign",
            edit(SELL, lines("cash[t] = max(cash[t], hold[t] - price)", "cash[t] = max(cash[t], hold[t] - price);",
                             "cash[t] = Math.max(cash[t], hold[t] - price);")),
            "Add the price when selling: hold[t] + price",
            "Selling a share brings money in.",
        ),
        Fix(
            "stock-hold-init-zero",
            edit(INIT, lines("hold = [0] * (k + 1)", "vector<int> hold(k + 1, 0);", "int[] hold = new int[k + 1];")),
            "Start hold at a very negative value",
            "Holding a share you never paid for is impossible; 0 lets you sell it for free.",
        ),
    ],
    decoys=[
        Decoy(edit(OUTPUT, lines("print(cash[k - 1])", 'cout << cash[k - 1] << "\\n";', "System.out.println(cash[k - 1]);")),
              "Print cash[k - 1] instead", "loop-bound-off-by-one"),
        Decoy(edit(CASH, lines("cash = [0] * (k + 2)", "vector<int> cash(k + 2, 0);", "int[] cash = new int[k + 2];")),
              "Make the cash array one cell longer", "loop-bound-off-by-one"),
        Decoy(edit(DAYS, lines("for price in p[1:]:", "for (int price : vector<int>(p.begin() + 1, p.end())) {",
                               "for (int price : java.util.Arrays.copyOfRange(p, 1, p.length)) {")),
              "Skip the first day", "skip-first-element"),
        Decoy(edit(SELL, lines("cash[t] = max(cash[t], hold[t] + price + 1)", "cash[t] = max(cash[t], hold[t] + price + 1);",
                               "cash[t] = Math.max(cash[t], hold[t] + price + 1);")),
              "Add 1 for every sale", "dp-missing-plus-one"),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"best_profit": best_profit}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
