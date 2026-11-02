"""Union-find: how many connected groups after a list of unions.

The trap is the redundant edge: an edge inside a group already joined must not merge
anything. Wrong answers count every edge as a merge, read the raw parent array instead of
finding roots, or merge without checking the roots first.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, lines

SAME = lines("if a == b:", "if (a == b) continue;")
LINK = lines("parent[a] = b", "parent[a] = b;")


def program(v: dict) -> dict[str, str]:
    n = v["n"]
    py_edges = ", ".join(f"({a}, {b})" for a, b in v["edges"])
    flat = ", ".join(f"{a}, {b}" for a, b in v["edges"])
    return {
        "python": (
            f"n = {n}\nedges = [{py_edges}]\n"
            "parent = list(range(n))\n"
            "groups = n\n"
            "for a, b in edges:\n"
            "    while parent[a] != a:\n"
            "        a = parent[a]\n"
            "    while parent[b] != b:\n"
            "        b = parent[b]\n"
            "    if a == b:\n"
            "        continue\n"
            "    parent[a] = b\n"
            "    groups -= 1\n"
            "print(groups)"
        ),
        "cpp": (
            f"int n = {n};\nvector<int> e = {{{flat}}};\n"
            "vector<int> parent(n);\n"
            "for (int i = 0; i < n; i++) parent[i] = i;\n"
            "int groups = n;\n"
            "for (size_t i = 0; i < e.size(); i += 2) {\n"
            "    int a = e[i], b = e[i + 1];\n"
            "    while (parent[a] != a) {\n"
            "        a = parent[a];\n"
            "    }\n"
            "    while (parent[b] != b) {\n"
            "        b = parent[b];\n"
            "    }\n"
            "    if (a == b) continue;\n"
            "    parent[a] = b;\n"
            "    groups--;\n"
            "}\n"
            'cout << groups << "\\n";'
        ),
        "java": (
            f"int n = {n};\nint[] e = {{{flat}}};\n"
            "int[] parent = new int[n];\n"
            "for (int i = 0; i < n; i++) parent[i] = i;\n"
            "int groups = n;\n"
            "for (int i = 0; i < e.length; i += 2) {\n"
            "    int a = e[i], b = e[i + 1];\n"
            "    while (parent[a] != a) {\n"
            "        a = parent[a];\n"
            "    }\n"
            "    while (parent[b] != b) {\n"
            "        b = parent[b];\n"
            "    }\n"
            "    if (a == b) continue;\n"
            "    parent[a] = b;\n"
            "    groups--;\n"
            "}\n"
            "System.out.println(groups);"
        ),
    }


def components(n: int, edges: list) -> int:
    """Independent check: count groups by graph search, not by union-find."""
    adj: dict[int, list[int]] = {i: [] for i in range(n)}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    seen: set[int] = set()
    count = 0
    for start in range(n):
        if start in seen:
            continue
        count += 1
        stack = [start]
        seen.add(start)
        while stack:
            x = stack.pop()
            for y in adj[x]:
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
    return count


def raw_parents(v) -> int:
    """Distinct values in the parent array: what you get by reading it without finding roots."""
    parent = list(range(v["n"]))
    for a, b in v["edges"]:
        while parent[a] != a:
            a = parent[a]
        while parent[b] != b:
            b = parent[b]
        if a != b:
            parent[a] = b
    return len(set(parent))


def wrong(v):
    n, edges = v["n"], v["edges"]
    right = components(n, edges)
    return [
        (str(max(1, n - len(edges))), "uf-count-redundant-edge"),
        (str(raw_parents(v)), "uf-parent-is-root"),
        (str(right + 1), "off-by-one-output"),
        (str(right - 1), "off-by-one-output"),
    ]


def sample(rng, params):
    n = rng.randint(*params["n"])
    edges: list[tuple[int, int]] = []
    for _ in range(rng.randint(*params["edges"])):
        a, b = rng.sample(range(n), 2)
        edges.append((a, b))
    # At least one edge inside an existing group: the case the check is for.
    if components(n, edges) == max(1, n - len(edges)):
        a, b = edges[0]
        edges.append((b, a))
    return {"n": n, "edges": edges}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(components(v["n"], v["edges"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should print how many separate groups {v['n']} people form after the "
        "listed friendships. Which line goes in the blank?"
    ),
    fix=lambda v: "",
    explain=lambda v, answer: (
        f"Each edge climbs both ends to their roots and merges only if the roots differ. "
        f"Edges inside an existing group change nothing, so {v['n']} people end in {answer} groups."
    ),
    blanks=[
        Blank(
            SAME,
            [
                (lines("if a != b:", "if (a != b) continue;"), "uf-count-redundant-edge"),
                (lines("if parent[a] == a:", "if (parent[a] == a) continue;"), "uf-parent-is-root"),
                (lines("if a == 0:", "if (a == 0) continue;"), "confuse-index-value"),
            ],
        ),
        Blank(
            LINK,
            [
                (lines("parent[b] = b", "parent[b] = b;"), "uf-link-wrong-node"),
                (lines("parent[a] = a", "parent[a] = a;"), "uf-link-wrong-node"),
                (lines("parent[b] = a + 1", "parent[b] = a + 1;"), "confuse-index-value"),
            ],
        ),
    ],
    bands=(4, 4, 5),
)
HELPERS = {"components": components}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
