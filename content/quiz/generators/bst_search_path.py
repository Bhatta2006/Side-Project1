"""Binary search tree built by insertion order; how many nodes a search visits.

The tree's shape comes from the insertion order, not from sorted order. Wrong answers count
edges instead of nodes, assume a balanced tree, or use the value's rank or insertion position.
"""

import math

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, lines

STEER = lines(
    "x = left[x] if q < key[x] else right[x]", "x = q < key[x] ? left[x] : right[x];"
)
PLACE = lines("if v < key[x]:", "if (v < key[x]) {")


def program(v: dict) -> dict[str, str]:
    vals, q, n = ", ".join(map(str, v["vals"])), v["q"], len(v["vals"])
    return {
        "python": (
            f"vals = [{vals}]\nq = {q}\n"
            "key, left, right = [0], [0], [0]  # node 0 is null; node 1 is the root\n"
            "for v in vals:\n"
            "    key.append(v)\n"
            "    left.append(0)\n"
            "    right.append(0)\n"
            "    node = len(key) - 1\n"
            "    x = 1\n"
            "    while node != 1:\n"
            "        if v < key[x]:\n"
            "            if left[x] == 0:\n"
            "                left[x] = node\n"
            "                break\n"
            "            x = left[x]\n"
            "        else:\n"
            "            if right[x] == 0:\n"
            "                right[x] = node\n"
            "                break\n"
            "            x = right[x]\n"
            "x = 1\n"
            "visited = 0\n"
            "while x != 0:\n"
            "    visited += 1\n"
            "    if key[x] == q:\n"
            "        break\n"
            "    x = left[x] if q < key[x] else right[x]\n"
            "print(visited)"
        ),
        "cpp": (
            f"vector<int> vals = {{{vals}}};\nint q = {q};\n"
            f"vector<int> key({n + 1}, 0), left({n + 1}, 0), right({n + 1}, 0);  // node 0 is null\n"
            "for (int i = 0; i < (int)vals.size(); i++) {\n"
            "    int v = vals[i], node = i + 1;\n"
            "    key[node] = v;\n"
            "    int x = 1;\n"
            "    while (node != 1) {\n"
            "        if (v < key[x]) {\n"
            "            if (left[x] == 0) { left[x] = node; break; }\n"
            "            x = left[x];\n"
            "        } else {\n"
            "            if (right[x] == 0) { right[x] = node; break; }\n"
            "            x = right[x];\n"
            "        }\n"
            "    }\n"
            "}\n"
            "int x = 1;\n"
            "int visited = 0;\n"
            "while (x != 0) {\n"
            "    visited++;\n"
            "    if (key[x] == q) break;\n"
            "    x = q < key[x] ? left[x] : right[x];\n"
            "}\n"
            'cout << visited << "\\n";'
        ),
        "java": (
            f"int[] vals = {{{vals}}};\nint q = {q};\n"
            f"int[] key = new int[{n + 1}], left = new int[{n + 1}], right = new int[{n + 1}];  // node 0 is null\n"
            "for (int i = 0; i < vals.length; i++) {\n"
            "    int v = vals[i], node = i + 1;\n"
            "    key[node] = v;\n"
            "    int x = 1;\n"
            "    while (node != 1) {\n"
            "        if (v < key[x]) {\n"
            "            if (left[x] == 0) { left[x] = node; break; }\n"
            "            x = left[x];\n"
            "        } else {\n"
            "            if (right[x] == 0) { right[x] = node; break; }\n"
            "            x = right[x];\n"
            "        }\n"
            "    }\n"
            "}\n"
            "int x = 1;\n"
            "int visited = 0;\n"
            "while (x != 0) {\n"
            "    visited++;\n"
            "    if (key[x] == q) break;\n"
            "    x = q < key[x] ? left[x] : right[x];\n"
            "}\n"
            "System.out.println(visited);"
        ),
    }


def depth(vals: list, q: int) -> int:
    """Independent check: q's depth is 1 + the number of earlier-inserted values that are
    its BST ancestors (an earlier value is an ancestor iff no value inserted before it lies
    strictly between it and q)."""
    pos = vals.index(q)
    count = 0
    for i in range(pos):
        a = vals[i]
        lo, hi = min(a, q), max(a, q)
        if not any(lo < vals[j] < hi for j in range(i)):
            count += 1
    return count + 1


def wrong(v):
    vals, q = v["vals"], v["q"]
    d = depth(vals, q)
    return [
        (str(d - 1), "path-nodes-vs-edges"),
        (str(math.ceil(math.log2(len(vals) + 1))), "bst-assume-balanced"),
        (str(sorted(vals).index(q) + 1), "bst-rank-not-depth"),
        (str(vals.index(q) + 1), "bst-insertion-position"),
        (str(d + 1), "off-by-one-output"),
    ]


def sample(rng, params):
    n = rng.randint(*params["n"])
    vals = rng.sample(range(params["value"][0], params["value"][1] + 1), n)
    if rng.random() < 0.3:  # sometimes nearly sorted input: a degenerate, deep tree
        vals = sorted(vals)
        i = rng.randrange(n - 1)
        vals[i], vals[i + 1] = vals[i + 1], vals[i]
    return {"vals": vals, "q": rng.choice(vals[2:])}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(depth(v["vals"], v["q"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should print how many nodes a search for {v['q']} visits (the root counts "
        "as 1). Which line goes in the blank?"
    ),
    fix=lambda v: "",
    explain=lambda v, answer: (
        f"Inserting {', '.join(map(str, v['vals']))} in that order fixes the tree's shape: each "
        f"value goes left of smaller keys' parents and right otherwise. Searching for {v['q']} "
        f"walks root to node and visits {answer} nodes."
    ),
    blanks=[
        Blank(
            STEER,
            [
                (lines("x = right[x] if q < key[x] else left[x]",
                       "x = q < key[x] ? right[x] : left[x];"), "bst-direction-swapped"),
                (lines("x = left[x] if q > key[x] else right[x]",
                       "x = q > key[x] ? left[x] : right[x];"), "bst-direction-swapped"),
                (lines("x = left[x] if q < x else right[x]",
                       "x = q < x ? left[x] : right[x];"), "confuse-index-value"),
            ],
        ),
        Blank(
            PLACE,
            [
                (lines("if v > key[x]:", "if (v > key[x]) {"), "bst-direction-swapped"),
                (lines("if v < key[1]:", "if (v < key[1]) {"), "bst-compare-root-only"),
                (lines("if v < x:", "if (v < x) {"), "confuse-index-value"),
            ],
        ),
    ],
    bands=(4, 4, 5),
)
HELPERS = {"depth": depth}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
