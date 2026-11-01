"""Dijkstra with a min-heap: cheapest total weight from node 0 to a target.

Wrong answers are the classic slips: the cheapest of the fewest-edge paths (BFS thinking),
fixing a node's distance the first time it is discovered, and walking greedily along the
cheapest edge out of each node.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, lines

SET = lines("dist[y] = d + w", "dist[y] = d + w;")
INF = 1000000000


def program(v: dict) -> dict[str, str]:
    adj, t = v["adj"], v["t"]
    py = ", ".join("[" + ", ".join(f"({y}, {w})" for y, w in row) + "]" for row in adj)
    braces = ", ".join("{" + ", ".join(f"{{{y}, {w}}}" for y, w in row) + "}" for row in adj)
    return {
        "python": (
            "import heapq\n"
            f"adj = [{py}]  # adj[x] = [(neighbour, weight), ...]\nt = {t}\n"
            f"dist = [{INF}] * len(adj)\n"
            "dist[0] = 0\n"
            "heap = [(0, 0)]\n"
            "while heap:\n"
            "    d, x = heapq.heappop(heap)\n"
            "    if d > dist[x]:\n"
            "        continue\n"
            "    for y, w in adj[x]:\n"
            "        if d + w < dist[y]:\n"
            "            dist[y] = d + w\n"
            "            heapq.heappush(heap, (dist[y], y))\n"
            "print(dist[t])"
        ),
        "cpp": (
            f"vector<vector<pair<int, int>>> adj = {{{braces}}};  // {{neighbour, weight}}\n"
            f"int t = {t};\n"
            f"vector<int> dist(adj.size(), {INF});\n"
            "dist[0] = 0;\n"
            "priority_queue<pair<int, int>, vector<pair<int, int>>, greater<pair<int, int>>> heap;\n"
            "heap.push({0, 0});\n"
            "while (!heap.empty()) {\n"
            "    int d = heap.top().first, x = heap.top().second;\n"
            "    heap.pop();\n"
            "    if (d > dist[x]) continue;\n"
            "    for (auto& e : adj[x]) {\n"
            "        int y = e.first, w = e.second;\n"
            "        if (d + w < dist[y]) {\n"
            "            dist[y] = d + w;\n"
            "            heap.push({dist[y], y});\n"
            "        }\n"
            "    }\n"
            "}\n"
            'cout << dist[t] << "\\n";'
        ),
        "java": (
            f"int[][][] adj = {{{braces}}};  // {{neighbour, weight}}\nint t = {t};\n"
            "int[] dist = new int[adj.length];\n"
            f"Arrays.fill(dist, {INF});\n"
            "dist[0] = 0;\n"
            "PriorityQueue<int[]> heap = new PriorityQueue<>((p, q) -> p[0] - q[0]);\n"
            "heap.add(new int[]{0, 0});\n"
            "while (!heap.isEmpty()) {\n"
            "    int[] top = heap.poll();\n"
            "    int d = top[0], x = top[1];\n"
            "    if (d > dist[x]) continue;\n"
            "    for (int[] e : adj[x]) {\n"
            "        int y = e[0], w = e[1];\n"
            "        if (d + w < dist[y]) {\n"
            "            dist[y] = d + w;\n"
            "            heap.add(new int[]{dist[y], y});\n"
            "        }\n"
            "    }\n"
            "}\n"
            "System.out.println(dist[t]);"
        ),
    }


def cheapest(adj: list, t: int) -> int:
    """Independent check: Bellman-Ford, relaxing every edge n - 1 times."""
    dist = [INF] * len(adj)
    dist[0] = 0
    for _ in range(len(adj) - 1):
        for x, row in enumerate(adj):
            for y, w in row:
                if dist[x] + w < dist[y]:
                    dist[y] = dist[x] + w
    return dist[t]


def fewest_edges(adj: list, t: int) -> int:
    """Cheapest weight among the paths with the fewest edges."""
    best = {0: 0}
    frontier = {0: 0}
    while frontier and t not in best:
        nxt: dict[int, int] = {}
        for x, d in frontier.items():
            for y, w in adj[x]:
                if y not in best:
                    nxt[y] = min(nxt.get(y, INF), d + w)
        best.update(nxt)
        frontier = nxt
    return best.get(t, INF)


def settle_on_push(adj: list, t: int) -> int:
    dist = {0: 0}
    order = [0]
    for x in order:
        for y, w in adj[x]:
            if y not in dist:
                dist[y] = dist[x] + w
                order.append(y)
    return dist.get(t, INF)


def greedy_walk(adj: list, t: int) -> int:
    x, total, seen = 0, 0, {0}
    while x != t:
        options = [(w, y) for y, w in adj[x] if y not in seen]
        if not options:
            return -1
        w, x = min(options)
        seen.add(x)
        total += w
    return total


def wrong(v):
    adj, t = v["adj"], v["t"]
    return [
        (str(fewest_edges(adj, t)), "dijkstra-fewest-edges"),
        (str(settle_on_push(adj, t)), "dijkstra-settle-on-push"),
        (str(greedy_walk(adj, t)), "dijkstra-greedy-walk"),
        (str(cheapest(adj, t) + 1), "off-by-one-output"),
    ]


def sample(rng, params):
    n = rng.randint(*params["n"])
    edges: dict[tuple[int, int], int] = {}
    for node in range(1, n):
        edges[(rng.randrange(node), node)] = rng.randint(*params["weight"])
    while len(edges) < n - 1 + rng.randint(*params["extra"]):
        a, b = sorted(rng.sample(range(n), 2))
        edges.setdefault((a, b), rng.randint(*params["weight"]))
    adj: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    for (a, b), w in sorted(edges.items()):
        adj[a].append((b, w))
        adj[b].append((a, w))
    for row in adj:
        rng.shuffle(row)
    return {"adj": adj, "t": rng.randrange(2, n)}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(cheapest(v["adj"], v["t"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should print the cheapest total weight from node 0 to node {v['t']}. "
        "Which line goes in the blank?"
    ),
    fix=lambda v: "",
    explain=lambda v, answer: (
        "The heap always hands out the unsettled node with the smallest known distance, so when "
        "a node is popped with its current distance it is final. A path with more edges can be "
        f"cheaper, which is why BFS order is not enough. The cheapest cost to {v['t']} is {answer}."
    ),
    blanks=[
        Blank(
            SET,
            [
                (lines("dist[y] = w", "dist[y] = w;"), "dijkstra-edge-not-path"),
                (lines("dist[y] = d", "dist[y] = d;"), "dp-missing-plus-one"),
                (lines("dist[y] = d + 1", "dist[y] = d + 1;"), "dijkstra-fewest-edges"),
            ],
        ),
    ],
    bands=(5, 5, 6),
)
HELPERS = {"cheapest": cheapest}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
