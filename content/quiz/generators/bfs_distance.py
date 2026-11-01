"""Breadth-first search: fewest edges from node 0 to a target in an unweighted graph.

Wrong answers are the classic slips: the length of the first path a depth-first search
happens to find, counting nodes instead of edges, and counting everything visited.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, lines

CHECK = lines("if dist[y] == -1:", "if (dist[y] == -1) {")
STEP = lines("dist[y] = dist[x] + 1", "dist[y] = dist[x] + 1;")


def program(v: dict) -> dict[str, str]:
    adj, t = v["adj"], v["t"]
    py = ", ".join("[" + ", ".join(map(str, row)) + "]" for row in adj)
    braces = ", ".join("{" + ", ".join(map(str, row)) + "}" for row in adj)
    return {
        "python": (
            f"adj = [{py}]\nt = {t}\n"
            "dist = [-1] * len(adj)\n"
            "dist[0] = 0\n"
            "queue = [0]\n"
            "for x in queue:\n"
            "    for y in adj[x]:\n"
            "        if dist[y] == -1:\n"
            "            dist[y] = dist[x] + 1\n"
            "            queue.append(y)\n"
            "print(dist[t])"
        ),
        "cpp": (
            f"vector<vector<int>> adj = {{{braces}}};\nint t = {t};\n"
            "vector<int> dist(adj.size(), -1);\n"
            "dist[0] = 0;\n"
            "vector<int> q = {0};\n"
            "for (size_t i = 0; i < q.size(); i++) {\n"
            "    int x = q[i];\n"
            "    for (int y : adj[x]) {\n"
            "        if (dist[y] == -1) {\n"
            "            dist[y] = dist[x] + 1;\n"
            "            q.push_back(y);\n"
            "        }\n"
            "    }\n"
            "}\n"
            'cout << dist[t] << "\\n";'
        ),
        "java": (
            f"int[][] adj = {{{braces}}};\nint t = {t};\n"
            "int[] dist = new int[adj.length];\n"
            "Arrays.fill(dist, -1);\n"
            "dist[0] = 0;\n"
            "int[] queue = new int[adj.length];\n"
            "int size = 0;\n"
            "queue[size++] = 0;\n"
            "for (int i = 0; i < size; i++) {\n"
            "    int x = queue[i];\n"
            "    for (int y : adj[x]) {\n"
            "        if (dist[y] == -1) {\n"
            "            dist[y] = dist[x] + 1;\n"
            "            queue[size++] = y;\n"
            "        }\n"
            "    }\n"
            "}\n"
            "System.out.println(dist[t]);"
        ),
    }


def shortest(adj: list, t: int) -> int:
    """Independent check: try path lengths 0, 1, 2, ... by expanding reachable sets."""
    frontier, steps, seen = {0}, 0, {0}
    while frontier:
        if t in frontier:
            return steps
        nxt = {y for x in frontier for y in adj[x]} - seen
        seen |= nxt
        frontier, steps = nxt, steps + 1
    return -1


def dfs_first(adj: list, t: int) -> int:
    """Length of the first path a depth-first search following list order reaches t by."""
    seen = {0}
    stack = [(0, 0, iter(adj[0]))]
    while stack:
        x, d, it = stack[-1]
        if x == t:
            return d
        y = next(it, None)
        if y is None:
            stack.pop()
        elif y not in seen:
            seen.add(y)
            stack.append((y, d + 1, iter(adj[y])))
    return -1


def reachable(adj: list) -> int:
    seen, todo = {0}, [0]
    while todo:
        for y in adj[todo.pop()]:
            if y not in seen:
                seen.add(y)
                todo.append(y)
    return len(seen)


def wrong(v):
    adj, t = v["adj"], v["t"]
    d = shortest(adj, t)
    return [
        (str(dfs_first(adj, t)), "dfs-not-shortest"),
        (str(d + 1), "path-nodes-vs-edges"),
        (str(reachable(adj)), "bfs-count-visited"),
        (str(d - 1), "off-by-one-output"),
    ]


def sample(rng, params):
    n = rng.randint(*params["n"])
    edges: set[tuple[int, int]] = set()
    for node in range(1, n):  # a spanning tree keeps every node reachable
        edges.add(tuple(sorted((node, rng.randrange(node)))))
    while len(edges) < n - 1 + rng.randint(*params["extra"]):
        a, b = rng.sample(range(n), 2)
        edges.add((min(a, b), max(a, b)))
    adj: list[list[int]] = [[] for _ in range(n)]
    for a, b in sorted(edges):
        adj[a].append(b)
        adj[b].append(a)
    for row in adj:
        rng.shuffle(row)
    return {"adj": adj, "t": rng.randrange(2, n)}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(shortest(v["adj"], v["t"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should print the fewest edges from node 0 to node {v['t']}. "
        "Which line goes in the blank?"
    ),
    fix=lambda v: "",
    explain=lambda v, answer: (
        f"BFS settles nodes in order of distance: every node at distance d leaves the queue "
        f"before any at d + 1, and a node keeps the first distance it gets. Node {v['t']} is "
        f"{answer} edges from 0. A depth-first search may reach it first along a longer path."
    ),
    blanks=[
        Blank(
            CHECK,
            [
                (lines("if dist[y] != -1:", "if (dist[y] != -1) {"), "bfs-no-visited"),
                (lines("if dist[y] == 0:", "if (dist[y] == 0) {"), "bfs-no-visited"),
                (lines("if dist[x] == -1:", "if (dist[x] == -1) {"), "confuse-index-value"),
            ],
        ),
        Blank(
            STEP,
            [
                (lines("dist[y] = dist[x]", "dist[y] = dist[x];"), "dp-missing-plus-one"),
                (lines("dist[y] = dist[y] + 1", "dist[y] = dist[y] + 1;"), "bfs-dist-from-self"),
                (lines("dist[y] = x + 1", "dist[y] = x + 1;"), "confuse-index-value"),
            ],
        ),
    ],
    bands=(3, 4, 5),
)
HELPERS = {"shortest": shortest}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
