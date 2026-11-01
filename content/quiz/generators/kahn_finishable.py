"""Kahn's algorithm: how many tasks can be finished when prerequisites may form a cycle.

A cycle blocks its own tasks and everything that depends on them. Wrong answers ignore
the cycle, count only the tasks with no prerequisites, or block the cycle but not what
comes after it.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, lines

READY = lines(
    "if indeg[y] == 0:", "if (indeg[y] == 0) order.push_back(y);", "if (indeg[y] == 0) order.add(y);"
)
DROP = lines("indeg[y] -= 1", "indeg[y]--;")


def program(v: dict) -> dict[str, str]:
    n = v["n"]
    py_edges = ", ".join(f"({a}, {b})" for a, b in v["edges"])
    flat = ", ".join(f"{a}, {b}" for a, b in v["edges"])
    return {
        "python": (
            f"n = {n}\nedges = [{py_edges}]  # (a, b): a must be done before b\n"
            "adj = [[] for _ in range(n)]\n"
            "indeg = [0] * n\n"
            "for a, b in edges:\n"
            "    adj[a].append(b)\n"
            "    indeg[b] += 1\n"
            "order = [x for x in range(n) if indeg[x] == 0]\n"
            "for x in order:\n"
            "    for y in adj[x]:\n"
            "        indeg[y] -= 1\n"
            "        if indeg[y] == 0:\n"
            "            order.append(y)\n"
            "print(len(order))"
        ),
        "cpp": (
            f"int n = {n};\nvector<int> e = {{{flat}}};  // pairs (a, b): a before b\n"
            "vector<vector<int>> adj(n);\n"
            "vector<int> indeg(n, 0);\n"
            "for (size_t i = 0; i < e.size(); i += 2) {\n"
            "    adj[e[i]].push_back(e[i + 1]);\n"
            "    indeg[e[i + 1]]++;\n"
            "}\n"
            "vector<int> order;\n"
            "for (int x = 0; x < n; x++) {\n"
            "    if (indeg[x] == 0) order.push_back(x);\n"
            "}\n"
            "for (size_t i = 0; i < order.size(); i++) {\n"
            "    int x = order[i];\n"
            "    for (int y : adj[x]) {\n"
            "        indeg[y]--;\n"
            "        if (indeg[y] == 0) order.push_back(y);\n"
            "    }\n"
            "}\n"
            'cout << order.size() << "\\n";'
        ),
        "java": (
            f"int n = {n};\nint[] e = {{{flat}}};  // pairs (a, b): a before b\n"
            "List<List<Integer>> adj = new ArrayList<>();\n"
            "for (int i = 0; i < n; i++) adj.add(new ArrayList<>());\n"
            "int[] indeg = new int[n];\n"
            "for (int i = 0; i < e.length; i += 2) {\n"
            "    adj.get(e[i]).add(e[i + 1]);\n"
            "    indeg[e[i + 1]]++;\n"
            "}\n"
            "List<Integer> order = new ArrayList<>();\n"
            "for (int x = 0; x < n; x++) {\n"
            "    if (indeg[x] == 0) order.add(x);\n"
            "}\n"
            "for (int i = 0; i < order.size(); i++) {\n"
            "    int x = order.get(i);\n"
            "    for (int y : adj.get(x)) {\n"
            "        indeg[y]--;\n"
            "        if (indeg[y] == 0) order.add(y);\n"
            "    }\n"
            "}\n"
            "System.out.println(order.size());"
        ),
    }


def closure(n: int, edges: list) -> list[list[bool]]:
    reach = [[False] * n for _ in range(n)]
    for a, b in edges:
        reach[a][b] = True
    for k in range(n):
        for i in range(n):
            if reach[i][k]:
                for j in range(n):
                    if reach[k][j]:
                        reach[i][j] = True
    return reach


def finishable(n: int, edges: list) -> int:
    """Independent check: a task is blocked if it is on a cycle or a cycle reaches it."""
    reach = closure(n, edges)
    cyclic = [i for i in range(n) if reach[i][i]]
    blocked = {j for i in cyclic for j in range(n) if i == j or reach[i][j]}
    return n - len(blocked)


def wrong(v):
    n, edges = v["n"], v["edges"]
    reach = closure(n, edges)
    has_parent = {b for _, b in edges}
    return [
        (str(n), "topo-ignore-cycle"),
        (str(n - len(has_parent)), "topo-only-sources"),
        (str(n - sum(reach[i][i] for i in range(n))), "topo-cycle-blocks-only-itself"),
        (str(finishable(n, edges) + 1), "off-by-one-output"),
    ]


def sample(rng, params):
    n = rng.randint(*params["n"])
    perm = list(range(n))
    rng.shuffle(perm)
    edges: set[tuple[int, int]] = set()
    while len(edges) < rng.randint(*params["edges"]):
        i, j = sorted(rng.sample(range(n), 2))
        edges.add((perm[i], perm[j]))  # forward in a hidden order: no cycle yet
    if rng.random() < params["cycle"][0]:
        i, j = sorted(rng.sample(range(n - 1), 2))
        edges.add((perm[j], perm[i]))  # one backward edge may close a cycle
    out = sorted(edges)
    rng.shuffle(out)
    return {"n": n, "edges": out}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(finishable(v["n"], v["edges"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should print how many of the {v['n']} tasks can be finished, given that each "
        "edge (a, b) means a must be done before b. Which line goes in the blank?"
    ),
    fix=lambda v: "",
    explain=lambda v, answer: (
        "Kahn's algorithm only releases a task once every prerequisite is done. Tasks on a cycle "
        "never reach in-degree 0, and neither does anything that depends on them, so "
        f"{answer} of {v['n']} tasks finish."
    ),
    blanks=[
        Blank(
            READY,
            [
                (
                    lines(
                        "if indeg[y] == 1:",
                        "if (indeg[y] == 1) order.push_back(y);",
                        "if (indeg[y] == 1) order.add(y);",
                    ),
                    "topo-release-early",
                ),
                (
                    lines(
                        "if indeg[y] <= 1:",
                        "if (indeg[y] <= 1) order.push_back(y);",
                        "if (indeg[y] <= 1) order.add(y);",
                    ),
                    "topo-release-early",
                ),
                (
                    lines(
                        "if indeg[y] > 0:",
                        "if (indeg[y] > 0) order.push_back(y);",
                        "if (indeg[y] > 0) order.add(y);",
                    ),
                    "filter-inverted",
                ),
            ],
        ),
        Blank(
            DROP,
            [
                (lines("indeg[y] += 1", "indeg[y]++;"), "topo-indegree-direction"),
                (lines("indeg[y] -= 2", "indeg[y] -= 2;"), "double-count"),
                (lines("indeg[x] -= 1", "indeg[x]--;"), "confuse-index-value"),
            ],
        ),
    ],
    bands=(4, 4, 5),
)
HELPERS = {"finishable": finishable}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
