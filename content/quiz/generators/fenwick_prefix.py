"""Fenwick tree: add values at positions, then read the sum of the first q positions.

Wrong answers are the classic slips: summing every update, stopping before position q,
summing from q onwards, and reading just the one cell tree[q].
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

UP = lines("i += i & -i", "i += i & -i;")
DOWN = lines("i -= i & -i", "i -= i & -i;")
ADD = lines("tree[i] += v", "tree[i] += v;")
SUM = lines("total += tree[i]", "total += tree[i];")
UPBOUND = lines("while i <= n:", "while (i <= n) {")
DOWNBOUND = lines("while i > 0:", "while (i > 0) {")


def prefix_sum(updates, q):
    """Independent check: add up the values whose position is at most q."""
    return sum(v for i, v in updates if i <= q)


def program(v: dict) -> dict[str, str]:
    n, q = v["n"], v["q"]
    idx = [i for i, _ in v["updates"]]
    val = [x for _, x in v["updates"]]
    m = len(idx)
    ij, vj = ", ".join(map(str, idx)), ", ".join(map(str, val))
    return {
        "python": (
            f"n, q = {n}, {q}\n"
            f"idx = [{ij}]\n"
            f"val = [{vj}]\n"
            "tree = [0] * (n + 1)\n"
            "for k in range(len(idx)):\n"
            "    i = idx[k]\n"
            "    v = val[k]\n"
            "    while i <= n:\n"
            "        tree[i] += v\n"
            "        i += i & -i\n"
            "total = 0\n"
            "i = q\n"
            "while i > 0:\n"
            "    total += tree[i]\n"
            "    i -= i & -i\n"
            "print(total)"
        ),
        "cpp": (
            f"int n = {n}, q = {q};\n"
            f"int idx[] = {{{ij}}};\n"
            f"int val[] = {{{vj}}};\n"
            "vector<int> tree(n + 1, 0);\n"
            f"for (int k = 0; k < {m}; k++) {{\n"
            "    int i = idx[k];\n"
            "    int v = val[k];\n"
            "    while (i <= n) {\n"
            "        tree[i] += v;\n"
            "        i += i & -i;\n"
            "    }\n"
            "}\n"
            "int total = 0;\n"
            "int i = q;\n"
            "while (i > 0) {\n"
            "    total += tree[i];\n"
            "    i -= i & -i;\n"
            "}\n"
            'cout << total << "\\n";'
        ),
        "java": (
            f"int n = {n}, q = {q};\n"
            f"int[] idx = {{{ij}}};\n"
            f"int[] val = {{{vj}}};\n"
            "int[] tree = new int[n + 1];\n"
            f"for (int k = 0; k < {m}; k++) {{\n"
            "    int i = idx[k];\n"
            "    int v = val[k];\n"
            "    while (i <= n) {\n"
            "        tree[i] += v;\n"
            "        i += i & -i;\n"
            "    }\n"
            "}\n"
            "int total = 0;\n"
            "int i = q;\n"
            "while (i > 0) {\n"
            "    total += tree[i];\n"
            "    i -= i & -i;\n"
            "}\n"
            "System.out.println(total);"
        ),
    }


def sample(rng, params):
    n = rng.randint(*params["n"])
    m = rng.randint(*params["updates"])
    updates = [(rng.randint(1, n), rng.randint(*params["value"])) for _ in range(m)]
    return {"n": n, "q": rng.randint(2, n), "updates": updates}


def wrong(v):
    ups, q = v["updates"], v["q"]
    return [
        (str(sum(x for _, x in ups)), "fenwick-sum-everything"),
        (str(sum(x for i, x in ups if i < q)), "off-by-one-output"),
        (str(sum(x for i, x in ups if i >= q)), "fenwick-suffix-not-prefix"),
        (str(len(ups)), "count-not-sum"),
        (str(sum(x for i, x in ups if i == q)), "fenwick-read-one-cell"),
    ]


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(prefix_sum(v["updates"], v["q"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should print the sum of the values added at positions 1 to {v['q']}. "
        "Which line goes in the blank?"
    ),
    fix=lambda v: (
        f"This code should print the sum of the values added at positions 1 to {v['q']}, but it "
        "prints the wrong answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"Each update touches the cells i, i + lowbit(i), … and the query adds the cells "
        f"q, q − lowbit(q), …: the sum of positions 1 to {v['q']} is {answer}."
    ),
    blanks=[
        Blank(
            UP,
            [
                (lines("i += 1", "i += 1;"), "fenwick-step-by-one"),
                (lines("i *= 2", "i *= 2;"), "fenwick-double-not-lowbit"),
                (lines("i += 2 * (i & -i)", "i += 2 * (i & -i);"), "fenwick-wrong-direction"),
            ],
        ),
        Blank(
            DOWN,
            [
                (lines("i -= 1", "i -= 1;"), "fenwick-step-by-one"),
                (lines("i //= 2", "i /= 2;"), "fenwick-double-not-lowbit"),
                (lines("i -= i & i", "i -= i & i;"), "fenwick-lowbit-typo"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "fenwick-down-step",
            edit(DOWN, lines("i -= 1", "i -= 1;")),
            "Remove the lowest set bit with i -= i & -i",
            "The cells to add are q, q minus its lowest set bit, and so on; stepping by 1 reads cells that cover other ranges.",
        ),
        Fix(
            "fenwick-up-step",
            edit(UP, lines("i += 1", "i += 1;")),
            "Move up by the lowest set bit with i += i & -i",
            "An update must reach every cell whose range contains position i; those are found by adding the lowest set bit.",
        ),
    ],
    decoys=[
        Decoy(
            edit(DOWN, lines("i -= i & i", "i -= i & i;")),
            "Subtract i & i instead of the lowest bit",
            "fenwick-lowbit-typo",
        ),
        Decoy(
            edit(SUM, lines("total = tree[i]", "total = tree[i];")),
            "Assign tree[i] to total instead of adding",
            "overwrite-not-accumulate",
        ),
        Decoy(
            edit(UPBOUND, lines("while i < n:", "while (i < n) {")),
            "Stop the update loop before n",
            "loop-bound-off-by-one",
        ),
        Decoy(
            edit(ADD, lines("tree[i] = v", "tree[i] = v;")),
            "Assign v to the cell instead of adding",
            "overwrite-not-accumulate",
        ),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"prefix_sum": prefix_sum}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
