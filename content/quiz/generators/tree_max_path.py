"""Binary tree maximum path sum, children before parents in reverse BFS order.

Wrong answers are the classic slips: returning both branches to the parent, keeping negative
branches, only counting paths that go straight down, and summing every value.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

GL = lines("gl = max(0, down[left[x]])", "int gl = max(0, down[left[x]]);", "int gl = Math.max(0, down[left[x]]);")
GR = lines("gr = max(0, down[right[x]])", "int gr = max(0, down[right[x]]);", "int gr = Math.max(0, down[right[x]]);")
RECORD = lines("best = max(best, val[x] + gl + gr)", "best = max(best, val[x] + gl + gr);",
               "best = Math.max(best, val[x] + gl + gr);")
RETURN = lines("down[x] = val[x] + max(gl, gr)", "down[x] = val[x] + max(gl, gr);", "down[x] = val[x] + Math.max(gl, gr);")
START = lines("best = -1000", "int best = -1000;")
OUTPUT = lines("print(best)", 'cout << best << "\\n";', "System.out.println(best);")


def arr(xs):
    return ", ".join(map(str, xs))


def program(v: dict) -> dict[str, str]:
    val, left, right = arr([0] + v["val"]), arr([0] + v["left"]), arr([0] + v["right"])
    return {
        "python": (
            f"val = [{val}]\nleft = [{left}]\nright = [{right}]\n"
            "order = [1]\n"
            "for x in order:\n"
            "    for c in (left[x], right[x]):\n"
            "        if c:\n"
            "            order.append(c)\n"
            "down = [0] * len(val)\n"
            "best = -1000\n"
            "for x in reversed(order):\n"
            "    gl = max(0, down[left[x]])\n"
            "    gr = max(0, down[right[x]])\n"
            "    best = max(best, val[x] + gl + gr)\n"
            "    down[x] = val[x] + max(gl, gr)\n"
            "print(best)"
        ),
        "cpp": (
            f"vector<int> val = {{{val}}};\nvector<int> left = {{{left}}};\nvector<int> right = {{{right}}};\n"
            "vector<int> order = {1};\n"
            "for (size_t k = 0; k < order.size(); k++) {\n"
            "    int x = order[k];\n"
            "    if (left[x]) order.push_back(left[x]);\n"
            "    if (right[x]) order.push_back(right[x]);\n"
            "}\n"
            "vector<int> down(val.size(), 0);\n"
            "int best = -1000;\n"
            "for (int k = (int)order.size() - 1; k >= 0; k--) {\n"
            "    int x = order[k];\n"
            "    int gl = max(0, down[left[x]]);\n"
            "    int gr = max(0, down[right[x]]);\n"
            "    best = max(best, val[x] + gl + gr);\n"
            "    down[x] = val[x] + max(gl, gr);\n"
            "}\n"
            'cout << best << "\\n";'
        ),
        "java": (
            f"int[] val = {{{val}}};\nint[] left = {{{left}}};\nint[] right = {{{right}}};\n"
            "int[] order = new int[val.length - 1];\n"
            "int size = 0;\n"
            "order[size++] = 1;\n"
            "for (int k = 0; k < size; k++) {\n"
            "    int x = order[k];\n"
            "    if (left[x] != 0) order[size++] = left[x];\n"
            "    if (right[x] != 0) order[size++] = right[x];\n"
            "}\n"
            "int[] down = new int[val.length];\n"
            "int best = -1000;\n"
            "for (int k = size - 1; k >= 0; k--) {\n"
            "    int x = order[k];\n"
            "    int gl = Math.max(0, down[left[x]]);\n"
            "    int gr = Math.max(0, down[right[x]]);\n"
            "    best = Math.max(best, val[x] + gl + gr);\n"
            "    down[x] = val[x] + Math.max(gl, gr);\n"
            "}\n"
            "System.out.println(best);"
        ),
    }


def neighbours(v):
    n = len(v["val"])
    adj = {i: [] for i in range(1, n + 1)}
    for i in range(1, n + 1):
        for c in (v["left"][i - 1], v["right"][i - 1]):
            if c:
                adj[i].append(c)
                adj[c].append(i)
    return adj


def best_path(val, left, right):
    """Independent check: the best sum over every simple path between two nodes."""
    v = {"val": val, "left": left, "right": right}
    adj, best = neighbours(v), -10**9
    for start in adj:
        stack = [(start, 0, val[start - 1])]
        while stack:
            x, came, s = stack.pop()
            best = max(best, s)
            stack.extend((y, x, s + val[y - 1]) for y in adj[x] if y != came)
    return best


def downward_only(v):
    val, adj, best = v["val"], neighbours(v), -10**9
    depth = {1: 0}
    order = [1]
    for x in order:
        for y in adj[x]:
            if y not in depth:
                depth[y] = depth[x] + 1
                order.append(y)
    for start in adj:
        stack = [(start, val[start - 1])]
        while stack:
            x, s = stack.pop()
            best = max(best, s)
            stack.extend((y, s + val[y - 1]) for y in adj[x] if depth[y] > depth[x])
    return best


def both_returned(v):
    val, left, right = [0] + v["val"], [0] + v["left"], [0] + v["right"]
    order = [1]
    for x in order:
        order.extend(c for c in (left[x], right[x]) if c)
    down, best = [0] * len(val), -10**9
    for x in reversed(order):
        gl, gr = max(0, down[left[x]]), max(0, down[right[x]])
        best = max(best, val[x] + gl + gr)
        down[x] = val[x] + gl + gr
    return best


def wrong(v):
    return [
        (str(both_returned(v)), "tree-return-both-branches"),
        (str(downward_only(v)), "tree-best-only-downward"),
        (str(sum(v["val"])), "tree-sum-all"),
        (str(max(v["val"])), "tree-negative-branch"),
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


def describe(v):
    parts = []
    for i in range(len(v["val"])):
        kids = [f"left {v['left'][i]}" if v["left"][i] else "", f"right {v['right'][i]}" if v["right"][i] else ""]
        kids = [k for k in kids if k]
        parts.append(f"node {i + 1} = {v['val'][i]}" + (f" ({', '.join(kids)})" if kids else ""))
    return "; ".join(parts)


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(best_path(v["val"], v["left"], v["right"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        "This code should print the largest sum of any path between two nodes of the tree (a single "
        "node counts). Which line goes in the blank?"
    ),
    fix=lambda v: (
        "This code should print the largest sum of any path between two nodes of the tree (a single "
        "node counts), but it prints the wrong answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"Tree: {describe(v)}. Each node returns its value plus its better branch, and records its value "
        f"plus both non-negative branches as a path bending there. The best path sum is {answer}."
    ),
    blanks=[
        Blank(
            RETURN,
            [
                (lines("down[x] = val[x] + gl + gr", "down[x] = val[x] + gl + gr;"), "tree-return-both-branches"),
                (lines("down[x] = max(gl, gr)", "down[x] = max(gl, gr);", "down[x] = Math.max(gl, gr);"),
                 "dp-missing-plus-one"),
                (lines("down[x] = val[x] + min(gl, gr)", "down[x] = val[x] + min(gl, gr);",
                       "down[x] = val[x] + Math.min(gl, gr);"), "min-vs-max"),
            ],
        ),
        Blank(
            RECORD,
            [
                (lines("best = max(best, val[x] + max(gl, gr))", "best = max(best, val[x] + max(gl, gr));",
                       "best = Math.max(best, val[x] + Math.max(gl, gr));"), "tree-best-only-downward"),
                (lines("best = max(best, val[x])", "best = max(best, val[x]);", "best = Math.max(best, val[x]);"),
                 "tree-best-only-downward"),
                (lines("best = val[x] + gl + gr", "best = val[x] + gl + gr;"), "overwrite-best"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "tree-return-both-branches",
            edit(RETURN, lines("down[x] = val[x] + gl + gr", "down[x] = val[x] + gl + gr;")),
            "Return only the better branch: val[x] + max(gl, gr)",
            "A parent can continue a path down one side only; both sides make an impossible path.",
        ),
        Fix(
            "tree-negative-branch",
            edit(GL, lines("gl = down[left[x]]", "int gl = down[left[x]];")),
            "Clamp the left branch at 0: max(0, down[left[x]])",
            "A branch with a negative sum should be left out of the path.",
        ),
        Fix(
            "tree-best-only-downward",
            edit(RECORD, lines("best = max(best, val[x] + max(gl, gr))", "best = max(best, val[x] + max(gl, gr));",
                               "best = Math.max(best, val[x] + Math.max(gl, gr));")),
            "Record the path that bends at x: val[x] + gl + gr",
            "The best path may use both children of its highest node.",
        ),
    ],
    decoys=[
        Decoy(edit(START, lines("best = 0", "int best = 0;")), "Start best at 0", "dp-wrong-base-case"),
        Decoy(edit(OUTPUT, lines("print(best + 1)", 'cout << best + 1 << "\\n";', "System.out.println(best + 1);")),
              "Print best + 1", "off-by-one-output"),
        Decoy(edit(GR, lines("gr = max(1, down[right[x]])", "int gr = max(1, down[right[x]]);",
                             "int gr = Math.max(1, down[right[x]]);")),
              "Clamp the right branch at 1 instead of 0", "off-by-one-output"),
        Decoy(edit(RETURN, lines("down[x] = val[x] + max(gl, gr) + 1", "down[x] = val[x] + max(gl, gr) + 1;",
                                 "down[x] = val[x] + Math.max(gl, gr) + 1;")),
              "Add 1 for every edge", "dp-missing-plus-one"),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"best_path": best_path}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
