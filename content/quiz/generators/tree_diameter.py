"""Diameter of a binary tree (edges on the longest path), children before parents.

The longest path need not pass through the root. Wrong answers only look at the path
through the root, count nodes instead of edges, or report the height.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, lines

BEST = lines("best = max(best, h[left[x]] + h[right[x]])",
             "best = max(best, h[left[x]] + h[right[x]]);",
             "best = Math.max(best, h[left[x]] + h[right[x]]);")
HEIGHT = lines("h[x] = 1 + max(h[left[x]], h[right[x]])",
               "h[x] = 1 + max(h[left[x]], h[right[x]]);",
               "h[x] = 1 + Math.max(h[left[x]], h[right[x]]);")


def arr(xs):
    return ", ".join(map(str, xs))


def program(v: dict) -> dict[str, str]:
    left, right = arr([0] + v["left"]), arr([0] + v["right"])
    return {
        "python": (
            f"left = [{left}]\nright = [{right}]  # node 1 is the root, 0 = no child\n"
            "order = [1]\n"
            "for x in order:\n"
            "    for c in (left[x], right[x]):\n"
            "        if c:\n"
            "            order.append(c)\n"
            "h = [0] * len(left)  # h[x] = nodes on the longest downward path from x\n"
            "best = 0\n"
            "for x in reversed(order):\n"
            "    best = max(best, h[left[x]] + h[right[x]])\n"
            "    h[x] = 1 + max(h[left[x]], h[right[x]])\n"
            "print(best)"
        ),
        "cpp": (
            f"vector<int> left = {{{left}}};\nvector<int> right = {{{right}}};  // node 1 is the root\n"
            "vector<int> order = {1};\n"
            "for (size_t k = 0; k < order.size(); k++) {\n"
            "    int x = order[k];\n"
            "    if (left[x]) order.push_back(left[x]);\n"
            "    if (right[x]) order.push_back(right[x]);\n"
            "}\n"
            "vector<int> h(left.size(), 0);  // nodes on the longest downward path\n"
            "int best = 0;\n"
            "for (int k = (int)order.size() - 1; k >= 0; k--) {\n"
            "    int x = order[k];\n"
            "    best = max(best, h[left[x]] + h[right[x]]);\n"
            "    h[x] = 1 + max(h[left[x]], h[right[x]]);\n"
            "}\n"
            'cout << best << "\\n";'
        ),
        "java": (
            f"int[] left = {{{left}}};\nint[] right = {{{right}}};  // node 1 is the root\n"
            "int[] order = new int[left.length - 1];\n"
            "int size = 0;\n"
            "order[size++] = 1;\n"
            "for (int k = 0; k < size; k++) {\n"
            "    int x = order[k];\n"
            "    if (left[x] != 0) order[size++] = left[x];\n"
            "    if (right[x] != 0) order[size++] = right[x];\n"
            "}\n"
            "int[] h = new int[left.length];  // nodes on the longest downward path\n"
            "int best = 0;\n"
            "for (int k = size - 1; k >= 0; k--) {\n"
            "    int x = order[k];\n"
            "    best = Math.max(best, h[left[x]] + h[right[x]]);\n"
            "    h[x] = 1 + Math.max(h[left[x]], h[right[x]]);\n"
            "}\n"
            "System.out.println(best);"
        ),
    }


def adjacency(left: list, right: list) -> dict[int, list[int]]:
    n = len(left)
    adj: dict[int, list[int]] = {i: [] for i in range(1, n + 1)}
    for i in range(1, n + 1):
        for c in (left[i - 1], right[i - 1]):
            if c:
                adj[i].append(c)
                adj[c].append(i)
    return adj


def far(adj, start):
    dist = {start: 0}
    todo = [start]
    for x in todo:
        for y in adj[x]:
            if y not in dist:
                dist[y] = dist[x] + 1
                todo.append(y)
    end = max(dist, key=lambda k: (dist[k], -k))
    return end, dist[end]


def diameter(left: list, right: list) -> int:
    """Independent check: farthest node from anywhere, then farthest from it (two BFS)."""
    adj = adjacency(left, right)
    a, _ = far(adj, 1)
    _, d = far(adj, a)
    return d


def height(left, right, x=1) -> int:
    if x == 0:
        return 0
    return 1 + max(height(left, right, left[x - 1]), height(left, right, right[x - 1]))


def wrong(v):
    left, right = v["left"], v["right"]
    d = diameter(left, right)
    return [
        (str(height(left, right, left[0]) + height(left, right, right[0])), "tree-diameter-through-root"),
        (str(d + 1), "path-nodes-vs-edges"),
        (str(height(left, right) - 1), "tree-height-vs-diameter"),
        (str(len(left) - 1), "tree-sum-all"),
    ]


def sample(rng, params):
    n = rng.randint(*params["nodes"])
    left, right = [0] * n, [0] * n
    # Grow one deep side branch often, so the longest path avoids the root.
    for node in range(2, n + 1):
        while True:
            parent = rng.randint(max(1, node - 3), node - 1) if rng.random() < 0.7 else rng.randint(1, node - 1)
            side = left if rng.random() < 0.5 else right
            if side[parent - 1] == 0:
                side[parent - 1] = node
                break
    return {"left": left, "right": right}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(diameter(v["left"], v["right"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        "This code should print the number of edges on the longest path between any two nodes "
        "of the tree. Which line goes in the blank?"
    ),
    fix=lambda v: "",
    explain=lambda v, answer: (
        "Each node is the highest point of the paths that bend at it, of length h(left) + h(right) "
        "edges, and passes 1 + its taller side up. The best bend can sit below the root, so every "
        f"node is checked: the diameter is {answer}."
    ),
    blanks=[
        Blank(
            BEST,
            [
                (lines("best = max(best, h[x])", "best = max(best, h[x]);", "best = Math.max(best, h[x]);"),
                 "tree-height-vs-diameter"),
                (lines("best = h[left[x]] + h[right[x]]", "best = h[left[x]] + h[right[x]];"),
                 "tree-diameter-through-root"),
                (lines("best = max(best, h[left[x]] + h[right[x]] + 1)",
                       "best = max(best, h[left[x]] + h[right[x]] + 1);",
                       "best = Math.max(best, h[left[x]] + h[right[x]] + 1);"), "path-nodes-vs-edges"),
            ],
        ),
        Blank(
            HEIGHT,
            [
                (lines("h[x] = 1 + h[left[x]] + h[right[x]]", "h[x] = 1 + h[left[x]] + h[right[x]];"),
                 "tree-return-both-branches"),
                (lines("h[x] = max(h[left[x]], h[right[x]])", "h[x] = max(h[left[x]], h[right[x]]);",
                       "h[x] = Math.max(h[left[x]], h[right[x]]);"), "dp-missing-plus-one"),
                (lines("h[x] = 1 + min(h[left[x]], h[right[x]])", "h[x] = 1 + min(h[left[x]], h[right[x]]);",
                       "h[x] = 1 + Math.min(h[left[x]], h[right[x]]);"), "min-vs-max"),
            ],
        ),
    ],
    bands=(4, 5, 5),
)
HELPERS = {"diameter": diameter}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
