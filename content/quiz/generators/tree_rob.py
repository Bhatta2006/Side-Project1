"""Rob or skip on a binary tree: take[x] and skip[x], children before parents.

Wrong answers are the classic slips: alternating levels, robbing adjacent nodes (take adds
take of the children), forcing children to be taken when the parent is skipped, and
answering with take of the root only.
"""

from itertools import combinations

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

TAKE = lines("take[x] = val[x] + skip[l] + skip[r]", "take[x] = val[x] + skip[l] + skip[r];")
SKIP = lines("skip[x] = max(take[l], skip[l]) + max(take[r], skip[r])",
             "skip[x] = max(take[l], skip[l]) + max(take[r], skip[r]);",
             "skip[x] = Math.max(take[l], skip[l]) + Math.max(take[r], skip[r]);")
TABLE = lines("take = [0] * len(val)", "vector<int> take(val.size(), 0);", "int[] take = new int[val.length];")
OUTPUT = lines("print(max(take[1], skip[1]))", 'cout << max(take[1], skip[1]) << "\\n";',
               "System.out.println(Math.max(take[1], skip[1]));")


def arr(xs):
    return ", ".join(map(str, xs))


def program(v: dict) -> dict[str, str]:
    val, left, right = arr([0] + v["val"]), arr([0] + v["left"]), arr([0] + v["right"])
    return {
        "python": (
            f"val = [{val}]\nleft = [{left}]\nright = [{right}]\n"
            "order = [1]\n"
            "for x in order:\n"
            "    order.extend(c for c in (left[x], right[x]) if c)\n"
            "take = [0] * len(val)\n"
            "skip = [0] * len(val)\n"
            "for x in reversed(order):\n"
            "    l, r = left[x], right[x]\n"
            "    take[x] = val[x] + skip[l] + skip[r]\n"
            "    skip[x] = max(take[l], skip[l]) + max(take[r], skip[r])\n"
            "print(max(take[1], skip[1]))"
        ),
        "cpp": (
            f"vector<int> val = {{{val}}};\nvector<int> left = {{{left}}};\nvector<int> right = {{{right}}};\n"
            "vector<int> order = {1};\n"
            "for (size_t k = 0; k < order.size(); k++) {\n"
            "    for (int c : {left[order[k]], right[order[k]]}) if (c) order.push_back(c);\n"
            "}\n"
            "vector<int> take(val.size(), 0);\n"
            "vector<int> skip(val.size(), 0);\n"
            "for (int k = (int)order.size() - 1; k >= 0; k--) {\n"
            "    int x = order[k], l = left[x], r = right[x];\n"
            "    take[x] = val[x] + skip[l] + skip[r];\n"
            "    skip[x] = max(take[l], skip[l]) + max(take[r], skip[r]);\n"
            "}\n"
            'cout << max(take[1], skip[1]) << "\\n";'
        ),
        "java": (
            f"int[] val = {{{val}}};\nint[] left = {{{left}}};\nint[] right = {{{right}}};\n"
            "int[] order = new int[val.length - 1];\n"
            "int size = 1;\n"
            "order[0] = 1;\n"
            "for (int k = 0; k < size; k++) {\n"
            "    for (int c : new int[] {left[order[k]], right[order[k]]}) if (c != 0) order[size++] = c;\n"
            "}\n"
            "int[] take = new int[val.length];\n"
            "int[] skip = new int[val.length];\n"
            "for (int k = size - 1; k >= 0; k--) {\n"
            "    int x = order[k], l = left[x], r = right[x];\n"
            "    take[x] = val[x] + skip[l] + skip[r];\n"
            "    skip[x] = Math.max(take[l], skip[l]) + Math.max(take[r], skip[r]);\n"
            "}\n"
            "System.out.println(Math.max(take[1], skip[1]));"
        ),
    }


def edges(v):
    out = []
    for i in range(1, len(v["val"]) + 1):
        out += [(i, c) for c in (v["left"][i - 1], v["right"][i - 1]) if c]
    return out


def rob_brute(val, left, right):
    """Independent check: try every set of nodes with no two joined by an edge."""
    v = {"val": val, "left": left, "right": right}
    e, n, best = edges(v), len(val), 0
    for k in range(n + 1):
        for chosen in combinations(range(1, n + 1), k):
            s = set(chosen)
            if all(not (a in s and b in s) for a, b in e):
                best = max(best, sum(val[i - 1] for i in chosen))
    return best


def levels(v):
    totals, level, depth = [0, 0], [1], 0
    while level:
        totals[depth % 2] += sum(v["val"][x - 1] for x in level)
        level = [c for x in level for c in (v["left"][x - 1], v["right"][x - 1]) if c]
        depth += 1
    return max(totals)


def take_root(v):
    val, left, right = [0] + v["val"], [0] + v["left"], [0] + v["right"]
    order = [1]
    for x in order:
        order.extend(c for c in (left[x], right[x]) if c)
    take, skip = [0] * len(val), [0] * len(val)
    for x in reversed(order):
        lc, rc = left[x], right[x]
        take[x] = val[x] + skip[lc] + skip[rc]
        skip[x] = max(take[lc], skip[lc]) + max(take[rc], skip[rc])
    return take[1]


def wrong(v):
    return [
        (str(levels(v)), "rob-alternate-levels"),
        (str(sum(v["val"])), "tree-sum-all"),
        (str(take_root(v)), "rob-answer-take-only"),
        (str(max(v["val"])), "knapsack-single-item"),
    ]


def sample(rng, params):
    n = rng.randint(*params["nodes"])
    left, right = [0] * n, [0] * n
    for node in range(2, n + 1):
        while True:
            parent = rng.randint(1, node - 1)
            side = left if rng.random() < 0.5 else right
            if side[parent - 1] == 0:
                side[parent - 1] = node
                break
    return {"val": [rng.randint(*params["value"]) for _ in range(n)], "left": left, "right": right}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(rob_brute(v["val"], v["left"], v["right"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        "Node values are house values; no two houses joined by an edge may both be robbed. This code "
        "should print the most money. Which line goes in the blank?"
    ),
    fix=lambda v: (
        "Node values are house values; no two houses joined by an edge may both be robbed. This code "
        "should print the most money, but it prints the wrong answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        "take[x] robs x, so its children must be skipped; skip[x] lets each child be taken or skipped, "
        f"whichever is better. The root may be either, so the answer is the larger: {answer}."
    ),
    blanks=[
        Blank(
            TAKE,
            [
                (lines("take[x] = val[x] + take[l] + take[r]", "take[x] = val[x] + take[l] + take[r];"),
                 "rob-take-adds-take"),
                (lines("take[x] = val[x]", "take[x] = val[x];"), "dp-wrong-subproblem"),
                (lines("take[x] = skip[l] + skip[r]", "take[x] = skip[l] + skip[r];"), "dp-missing-plus-one"),
            ],
        ),
        Blank(
            SKIP,
            [
                (lines("skip[x] = take[l] + take[r]", "skip[x] = take[l] + take[r];"), "rob-skip-forces-take"),
                (lines("skip[x] = skip[l] + skip[r]", "skip[x] = skip[l] + skip[r];"), "rob-skip-forces-take"),
                (lines("skip[x] = max(take[l], take[r])", "skip[x] = max(take[l], take[r]);",
                       "skip[x] = Math.max(take[l], take[r]);"), "count-vs-sum"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "rob-take-adds-take",
            edit(TAKE, lines("take[x] = val[x] + take[l] + take[r]", "take[x] = val[x] + take[l] + take[r];")),
            "When x is robbed, add skip of the children: val[x] + skip[l] + skip[r]",
            "Robbing x and a child robs two adjacent houses.",
        ),
        Fix(
            "rob-skip-forces-take",
            edit(SKIP, lines("skip[x] = take[l] + take[r]", "skip[x] = take[l] + take[r];")),
            "When x is skipped, let each child be either: max(take, skip) per child",
            "Skipping x does not force its children to be robbed.",
        ),
        Fix(
            "rob-answer-take-only",
            edit(OUTPUT, lines("print(take[1])", 'cout << take[1] << "\\n";', "System.out.println(take[1]);")),
            "Print max(take[1], skip[1])",
            "The root may also be skipped.",
        ),
    ],
    decoys=[
        Decoy(edit(TABLE, lines("take = [0] * (len(val) + 1)", "vector<int> take(val.size() + 1, 0);",
                                "int[] take = new int[val.length + 1];")),
              "Make the take table one cell longer", "loop-bound-off-by-one"),
        Decoy(edit(TAKE, lines("take[x] = val[x] + skip[l] + skip[r] + 1", "take[x] = val[x] + skip[l] + skip[r] + 1;")),
              "Add 1 for every robbed house", "dp-missing-plus-one"),
        Decoy(edit(SKIP, lines("skip[x] = max(take[l], skip[l]) + max(take[r], skip[r]) + 1",
                               "skip[x] = max(take[l], skip[l]) + max(take[r], skip[r]) + 1;",
                               "skip[x] = Math.max(take[l], skip[l]) + Math.max(take[r], skip[r]) + 1;")),
              "Add 1 for every skipped house", "dp-missing-plus-one"),
        Decoy(edit(OUTPUT, lines("print(max(take[1], skip[1]) - 1)", 'cout << max(take[1], skip[1]) - 1 << "\\n";',
                                 "System.out.println(Math.max(take[1], skip[1]) - 1);")),
              "Print one less", "off-by-one-output"),
        Decoy(edit(OUTPUT, lines("print(skip[1])", 'cout << skip[1] << "\\n";', "System.out.println(skip[1]);")),
              "Print skip[1] only", "rob-answer-take-only"),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"rob_brute": rob_brute}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
