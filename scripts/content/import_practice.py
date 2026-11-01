"""Build Socrat's external practice index from pinned public sources.

Metadata and links only: titles, URLs, difficulty labels, topic tags and company
frequency. Problem statements, editorial text and solution code are never copied.

Sources (cloned/fetched into .cache/sources by --fetch):
  liquidslr/leetcode-company-wise-problems   LeetCode topic tags (joined by URL)
  snehasishroy/leetcode-companywise-...       company frequency and recency windows
  cses.fi/problemset                          CSES task index (titles, links, sections)
  codeforces.com/api/problemset.problems      Codeforces problem metadata (names, ratings, tags)
  Codensity30/Strivers-A2Z-DSA-Sheet          titles only, to flag A2Z-sheet problems
  TheAlgorithms/{C-Plus-Plus,Python,Java}     MIT reference implementations (links)
takeuforward.org forbids automated access in its terms, so it is not fetched.

Usage: python scripts/content/import_practice.py [--fetch]
Writes content/practice/{problems.jsonl,companies.json,implementations.jsonl,sources.json}.
"""

import csv
import html
import json
import re
import subprocess
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache" / "sources"
OUT = ROOT / "content" / "practice"
sys.path.insert(0, str(ROOT / "services" / "api" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

REPOS = {
    "liquidslr": "https://github.com/liquidslr/leetcode-company-wise-problems",
    "companywise": "https://github.com/snehasishroy/leetcode-companywise-interview-questions",
    "striver": "https://github.com/Codensity30/Strivers-A2Z-DSA-Sheet",
}
ALGORITHM_REPOS = {"cpp": "C-Plus-Plus", "python": "Python", "java": "Java"}
WINDOWS = ["thirty-days", "three-months", "six-months", "more-than-six-months"]

# LeetCode topic tag -> Socrat concept, most specific first. The first match is primary.
TAG_CONCEPTS: list[tuple[str, str]] = [
    ("Trie", "dsa:tries"),
    ("Topological Sort", "dsa:topological-sort"),
    ("Minimum Spanning Tree", "cp:mst"),
    ("Shortest Path", "dsa:shortest-paths"),
    ("Dijkstra's Algorithm", "dsa:shortest-paths"),
    ("Binary Lifting", "cp:lca"),
    ("Lowest Common Ancestor", "cp:lca"),
    ("Segment Tree", "cp:segment-tree"),
    ("Binary Indexed Tree", "cp:fenwick-tree"),
    ("String Matching", "cp:kmp"),
    ("Rolling Hash", "cp:string-hashing"),
    ("Hash Function", "cp:string-hashing"),
    ("Bitmask", "cp:bitmasks"),
    ("Binary Search Tree", "dsa:bst"),
    ("Heap (Priority Queue)", "dsa:heaps"),
    ("Monotonic Stack", "dsa:stacks"),
    ("Monotonic Queue", "dsa:stacks"),
    ("Sliding Window", "dsa:sliding-window"),
    ("Two Pointers", "dsa:two-pointers"),
    ("Prefix Sum", "dsa:prefix-sums"),
    ("Binary Search", "dsa:binary-search"),
    ("Backtracking", "dsa:backtracking"),
    ("Linked List", "dsa:linked-lists"),
    ("Doubly-Linked List", "dsa:linked-lists"),
    ("Binary Tree", "dsa:binary-trees"),
    ("Tree", "dsa:binary-trees"),
    ("Graph Theory", "dsa:graph-traversal"),
    ("Breadth-First Search", "dsa:graph-traversal"),
    ("Depth-First Search", "dsa:graph-traversal"),
    # After BFS/DFS: most union-find-tagged problems are taught as traversals first.
    ("Union-Find", "dsa:union-find"),
    ("Dynamic Programming", "dsa:dp-1d"),
    ("Memoization", "dsa:dp-1d"),
    ("Stack", "dsa:stacks"),
    ("Queue", "dsa:stacks"),
    ("Greedy", "dsa:greedy"),
    ("Bit Manipulation", "dsa:bit-manipulation"),
    ("Combinatorics", "cp:combinatorics"),
    ("Number Theory", "cp:number-theory"),
    ("Greatest Common Divisor", "cp:number-theory"),
    ("Sorting", "dsa:sorting"),
    ("Simulation", "cp:simulation"),
    ("Enumeration", "cp:complete-search"),
    ("Recursion", "zero:recursion"),
    ("Hash Table", "dsa:arrays-hashing"),
    ("Counting", "dsa:arrays-hashing"),
    ("Matrix", "zero:grids"),
    ("String", "dsa:arrays-hashing"),
    ("Array", "dsa:arrays-hashing"),
    ("Math", "cp:number-theory"),
]
OUT_OF_SCOPE_TAGS = {"Database", "Shell", "Concurrency", "Interactive"}
DP_2D_HINT = re.compile(
    r"grid|path|matrix|subsequence|edit distance|interleav|palindrom|knapsack|stock", re.I
)

CSES_SECTIONS = {
    "Introductory Problems": ["cp:complete-search"],
    "Sorting and Searching": ["dsa:sorting"],
    "Dynamic Programming": ["cp:dp-classics"],
    "Graph Algorithms": ["dsa:graph-traversal"],
    "Range Queries": ["cp:segment-tree"],
    "Tree Algorithms": ["cp:tree-techniques"],
    "Mathematics": ["cp:number-theory"],
    "String Algorithms": ["cp:kmp"],
    "Sliding Window Problems": ["dsa:sliding-window"],
    "Bitwise Operations": ["cp:bitmasks"],
    "Construction Problems": ["cp:greedy-cp"],
    "Advanced Graph Problems": ["cp:graph-techniques"],
    "Counting Problems": ["cp:combinatorics"],
}
CSES_HARD = {"Advanced Techniques", "Advanced Graph Problems", "Additional Problems II"}
CSES_EASY = {"Introductory Problems"}
CSES_SKIP = {"General", "Interactive Problems", "Geometry"}
# Title keywords that pin a CSES task to a more specific concept.
CSES_TITLE_CONCEPTS = [
    (r"static range sum", "cp:prefix-difference"),
    (r"dynamic range (sum|minimum)", "cp:fenwick-tree"),
    (r"range update", "cp:prefix-difference"),
    (r"company queries|distance queries", "cp:lca"),
    (r"road reparation|road construction", "cp:mst"),
    (r"shortest routes|flight discount|cheapest", "dsa:shortest-paths"),
    (r"course schedule|longest flight route|game routes", "dsa:topological-sort"),
    (r"exponentiation", "cp:modular-arithmetic"),
    (r"binomial|creating strings ii|distributing apples", "cp:combinatorics"),
    (r"apartments|ferris wheel|concert tickets|sum of two values|playlist", "dsa:two-pointers"),
    (r"factory machines|array division", "cp:binary-search-answer"),
    (r"hamming|xor", "cp:bitmasks"),
    (r"string hashing|finding borders|finding periods", "cp:string-hashing"),
    (r"string matching", "cp:kmp"),
    (r"elevator rides|counting tilings|hamiltonian", "cp:bitmask-dp"),
    (r"subordinates|tree diameter|tree distances|tree matching", "cp:tree-techniques"),
]

# Codeforces tag -> concept, most specific first. Problems with no mapped tag are dropped.
CF_TAG_CONCEPTS: list[tuple[str, str]] = [
    ("shortest paths", "dsa:shortest-paths"),
    ("dsu", "dsa:union-find"),
    ("trees", "cp:tree-techniques"),
    ("string suffix structures", "cp:string-hashing"),
    ("hashing", "cp:string-hashing"),
    ("bitmasks", "cp:bitmasks"),
    ("number theory", "cp:number-theory"),
    ("chinese remainder theorem", "cp:number-theory"),
    ("combinatorics", "cp:combinatorics"),
    ("probabilities", "cp:combinatorics"),
    ("dp", "cp:dp-classics"),
    ("binary search", "cp:binary-search-answer"),
    ("ternary search", "dsa:binary-search"),
    ("two pointers", "dsa:two-pointers"),
    ("dfs and similar", "dsa:graph-traversal"),
    ("graphs", "cp:graph-techniques"),
    ("data structures", "cp:segment-tree"),
    ("sortings", "dsa:sorting"),
    ("greedy", "cp:greedy-cp"),
    ("constructive algorithms", "cp:greedy-cp"),
    ("meet-in-the-middle", "cp:complete-search"),
    ("brute force", "cp:complete-search"),
    ("strings", "zero:strings"),
    ("implementation", "cp:simulation"),
    ("math", "cp:number-theory"),
]
CF_SKIP_TAGS = {"*special"}


# TheAlgorithms filename keywords -> concept. Unmatched files are skipped.
IMPLEMENTATION_CONCEPTS: list[tuple[str, str]] = [
    (r"dijkstra|bellman|floyd_?warshall|shortest_path", "dsa:shortest-paths"),
    (r"kruskal|prim|minimum_spanning", "cp:mst"),
    (r"topolog", "dsa:topological-sort"),
    (r"union_?find|disjoint_?set|dsu", "dsa:union-find"),
    (r"segment_?tree", "cp:segment-tree"),
    (r"fenwick|binary_?indexed", "cp:fenwick-tree"),
    (r"lowest_common_ancestor|\blca\b|binary_lifting", "cp:lca"),
    (r"knuth_morris|\bkmp\b|prefix_function", "cp:kmp"),
    (r"rabin_karp|rolling_hash|polynomial_hash", "cp:string-hashing"),
    (r"\btrie", "dsa:tries"),
    (r"heap|priority_queue", "dsa:heaps"),
    (r"binary_search_tree|\bbst\b|avl|red_black", "dsa:bst"),
    (
        r"breadth_first|depth_first|\bbfs\b|\bdfs\b|graph_search|connected_components",
        "dsa:graph-traversal",
    ),
    (r"linked_?list", "dsa:linked-lists"),
    (r"\bstack|\bqueue|monotonic", "dsa:stacks"),
    (r"binary_search|ternary_search|lower_bound", "dsa:binary-search"),
    (r"sliding_window", "dsa:sliding-window"),
    (r"two_pointer", "dsa:two-pointers"),
    (r"prefix_sum|difference_array", "dsa:prefix-sums"),
    (
        r"merge_sort|quick_sort|heap_sort|counting_sort|insertion_sort|radix_sort|bubble_sort|selection_sort",
        "dsa:sorting",
    ),
    (r"n_queens|sudoku|permutation|subset|backtrack|combination_sum", "dsa:backtracking"),
    (r"bit|xor|gray_code", "dsa:bit-manipulation"),
    (r"sieve|prime|gcd|lcm|euler|totient|divisor|factori[sz]", "cp:number-theory"),
    (
        r"modular|fast_power|binary_exponent|power_mod|mod_inverse|exponentiation",
        "cp:modular-arithmetic",
    ),
    (r"binomial|ncr|catalan|pascal", "cp:combinatorics"),
    (
        r"longest_increasing|edit_distance|longest_common|knapsack|coin_change|rod_cutting|matrix_chain",
        "cp:dp-classics",
    ),
    (r"fibonacci|climbing|house_robber|kadane|max(imum)?_subarray", "dsa:dp-1d"),
    (r"activity_selection|huffman|job_sequenc|fractional_knapsack", "dsa:greedy"),
    (r"binary_tree|tree_traversal|inorder|preorder|postorder|level_order", "dsa:binary-trees"),
]
IMPLEMENTATION_SKIP_DIRS = re.compile(
    r"ciphers|machine_?learning|neural|physics|audio|graphics|computer_vision|blockchain|quantum|"
    r"web_programming|financial|electronics|fractals|fuzzy|genetic|geodesy|digital_image|"
    r"cellular|networking|file_transfer|scripts|docs|tests?/|project_euler|conversions|"
    r"cpu_scheduling|scheduling|boolean_algebra|linear_programming|numerical|/test/",
    re.I,
)


def run(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def fetch() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    for name, url in REPOS.items():
        target = CACHE / name
        if target.exists():
            run("git", "pull", "--ff-only", "-q", cwd=target)
        else:
            run("git", "clone", "-q", "--depth", "1", url, str(target))
    request = urllib.request.Request(
        "https://cses.fi/problemset/", headers={"User-Agent": "Socrat content import"}
    )
    (CACHE / "cses.html").write_bytes(urllib.request.urlopen(request, timeout=60).read())
    # One call; the public API allows one request per two seconds.
    request = urllib.request.Request(
        "https://codeforces.com/api/problemset.problems",
        headers={"User-Agent": "Socrat content import"},
    )
    (CACHE / "cf-problemset.json").write_bytes(urllib.request.urlopen(request, timeout=120).read())
    for repo in ALGORITHM_REPOS.values():
        api = f"https://api.github.com/repos/TheAlgorithms/{repo}/git/trees/master?recursive=1"
        request = urllib.request.Request(api, headers={"User-Agent": "Socrat content import"})
        (CACHE / f"thealg-{repo}.json").write_bytes(
            urllib.request.urlopen(request, timeout=60).read()
        )


def slug_of(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def norm_title(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def leetcode_concepts(title: str, tags: list[str]) -> list[str]:
    concepts: list[str] = []
    tag_set = set(tags)
    for tag, concept in TAG_CONCEPTS:
        if tag not in tag_set:
            continue
        if concept == "dsa:dp-1d" and ("Matrix" in tag_set or DP_2D_HINT.search(title)):
            concept = "dsa:dp-2d"
        if concept == "cp:bitmasks" and "Dynamic Programming" in tag_set:
            concept = "cp:bitmask-dp"
        if concept not in concepts:
            concepts.append(concept)
    if re.search(r"\binterval", title, re.I) and "dsa:intervals" not in concepts:
        concepts.insert(0, "dsa:intervals")
    return concepts[:3]


def load_leetcode(striver_titles: set[str]) -> tuple[dict, dict]:
    topics: dict[str, list[str]] = {}
    titles: dict[str, str] = {}
    difficulty: dict[str, str] = {}
    for path in sorted((CACHE / "liquidslr").glob("*/5. All.csv")):
        for row in csv.DictReader(path.open(encoding="utf-8")):
            slug = slug_of(row["Link"])
            topics[slug] = [t.strip() for t in row["Topics"].split(",") if t.strip()]
            titles[slug] = row["Title"].strip()
            difficulty[slug] = row["Difficulty"].strip().lower()
    companies: dict[str, dict] = {}
    seen: dict[str, dict] = {}
    company_dirs = sorted(p for p in (CACHE / "companywise").iterdir() if (p / "all.csv").exists())
    for folder in company_dirs:
        recency: dict[str, str] = {}
        for window in WINDOWS:
            path = folder / f"{window}.csv"
            if path.exists():
                for row in csv.DictReader(path.open(encoding="utf-8")):
                    recency.setdefault(slug_of(row["URL"]), window)
        rows = []
        for row in csv.DictReader((folder / "all.csv").open(encoding="utf-8")):
            slug = slug_of(row["URL"])
            titles.setdefault(slug, row["Title"].strip())
            difficulty.setdefault(slug, row["Difficulty"].strip().lower())
            freq = float(row["Frequency %"].rstrip("%") or 0)
            rows.append([f"leetcode:{slug}", round(freq, 1), recency.get(slug, "all")])
            entry = seen.setdefault(slug, {"companies": 0, "recent": 0})
            entry["companies"] += 1
            entry["recent"] += recency.get(slug) in {"thirty-days", "three-months"}
        rows.sort(key=lambda r: (-r[1], r[0]))
        companies[folder.name] = {"name": folder.name.replace("-", " ").title(), "problems": rows}
    problems = {}
    for slug, title in titles.items():
        tags = topics.get(slug, [])
        if OUT_OF_SCOPE_TAGS & set(tags):
            continue
        stats = seen.get(slug, {"companies": 0, "recent": 0})
        problems[f"leetcode:{slug}"] = {
            "id": f"leetcode:{slug}",
            "title": title,
            "url": f"https://leetcode.com/problems/{slug}/",
            "platform": "LeetCode",
            "difficulty": difficulty.get(slug, "medium"),
            "tags": tags,
            "concepts": leetcode_concepts(title, tags),
            "companies": stats["companies"],
            "recent_companies": stats["recent"],
            "sheets": ["striver-a2z"] if norm_title(title) in striver_titles else [],
        }
    return problems, companies


def load_cses() -> dict:
    text = (CACHE / "cses.html").read_text(encoding="utf-8")
    problems = {}
    for section, body in re.findall(
        r"<h2>([^<]+)</h2>\s*<ul class=\"task-list\">(.*?)</ul>", text, re.S
    ):
        section = html.unescape(section)
        if section in CSES_SKIP:
            continue
        pattern = r'href="/problemset/task/(\d+)/?">([^<]+)</a><span class="detail">(\d+) / (\d+)'
        for task, title, solvers, _ in re.findall(pattern, body):
            title = html.unescape(title).strip()
            solvers = int(solvers)
            concepts = list(CSES_SECTIONS.get(section, []))
            for pattern, concept in CSES_TITLE_CONCEPTS:
                if re.search(pattern, title, re.I) and concept not in concepts:
                    concepts.insert(0, concept)
            problems[f"cses:{task}"] = {
                "id": f"cses:{task}",
                "title": title,
                "url": f"https://cses.fi/problemset/task/{task}",
                "platform": "CSES",
                # Solver counts are a better difficulty signal than the section name.
                "difficulty": "easy"
                if solvers >= 40000 or section in CSES_EASY
                else "medium"
                if solvers >= 6000 and section not in CSES_HARD
                else "hard",
                "solvers": solvers,
                "tags": [section],
                "concepts": concepts[:3],
                "companies": 0,
                "recent_companies": 0,
                "sheets": ["cses"],
            }
    return problems


def cf_concepts(tags: list[str], rating: int) -> list[str]:
    tag_set = set(tags)
    concepts: list[str] = []
    for tag, concept in CF_TAG_CONCEPTS:
        if tag not in tag_set:
            continue
        if concept == "cp:bitmasks" and "dp" in tag_set:
            concept = "cp:bitmask-dp"
        if concept == "cp:segment-tree" and rating < 1700:
            concept = "dsa:arrays-hashing"  # easy "data structures" are maps, sets and stacks
        if concept == "cp:dp-classics" and rating <= 1200:
            concept = "dsa:dp-1d"
        if concept == "cp:number-theory" and tag == "math" and rating <= 1000:
            concept = "zero:input-and-arithmetic"
        if concept not in concepts:
            concepts.append(concept)
    return concepts[:3]


def load_codeforces() -> dict:
    path = CACHE / "cf-problemset.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))["result"]
    solved = {(s["contestId"], s["index"]): s["solvedCount"] for s in data["problemStatistics"]}
    problems = {}
    for p in data["problems"]:
        rating = p.get("rating")
        if not rating or p.get("type") != "PROGRAMMING" or CF_SKIP_TAGS & set(p["tags"]):
            continue
        key = f"cf:{p['contestId']}{p['index']}"
        problems[key] = {
            "id": key,
            "title": p["name"],
            "url": f"https://codeforces.com/problemset/problem/{p['contestId']}/{p['index']}",
            "platform": "Codeforces",
            "difficulty": "easy" if rating <= 1200 else "medium" if rating <= 1700 else "hard",
            "rating": rating,
            "solvers": solved.get((p["contestId"], p["index"]), 0),
            "tags": p["tags"],
            "concepts": cf_concepts(p["tags"], rating),
            "companies": 0,
            "recent_companies": 0,
            "sheets": [],
        }
    return problems


def load_striver_titles() -> set[str]:
    titles = set()
    for path in (CACHE / "striver").rglob("*"):
        if path.is_file() and ".git" not in path.parts and path.suffix in {".cpp", ".java", ".py"}:
            name = re.sub(r"^\d+[._ -]*", "", path.stem).replace("_", " ")
            titles.add(norm_title(name))
    return titles


def load_implementations() -> list[dict]:
    items = []
    for language, repo in ALGORITHM_REPOS.items():
        data = json.loads((CACHE / f"thealg-{repo}.json").read_text(encoding="utf-8"))
        extension = {"cpp": ".cpp", "python": ".py", "java": ".java"}[language]
        for node in data["tree"]:
            path = node["path"]
            if (
                node["type"] != "blob"
                or not path.endswith(extension)
                or IMPLEMENTATION_SKIP_DIRS.search(path)
            ):
                continue
            stem = Path(path).stem
            if stem.startswith("__") or stem.lower().endswith("test"):
                continue
            key = re.sub(r"(?<!^)(?=[A-Z])", "_", stem).lower()
            concept = next((c for p, c in IMPLEMENTATION_CONCEPTS if re.search(p, key)), None)
            if concept is None:
                continue
            title = key.replace("_", " ").strip().capitalize()
            items.append(
                {
                    "id": f"thealgorithms:{language}:{path}",
                    "title": title,
                    "url": f"https://github.com/TheAlgorithms/{repo}/blob/{data['sha']}/{path}",
                    "language": language,
                    "concept": concept,
                }
            )
    return items


def main() -> int:
    if "--fetch" in sys.argv or not (CACHE / "cses.html").exists():
        fetch()
    from socrat.catalog.registry import load

    known = set(load(tests_root=None).concepts)
    striver_titles = load_striver_titles()
    leetcode, companies = load_leetcode(striver_titles)
    cses = load_cses()
    codeforces = load_codeforces()
    # Only keep problems Socrat can tie to a concept (drops JS-only and untagged items).
    problems = {k: v for k, v in {**leetcode, **cses, **codeforces}.items() if v["concepts"]}
    # Narrow concepts (DP families, monotonic stack, …) by title and tag; see the module.
    from practice_routing import route

    for item in problems.values():
        item["concepts"] = [c for c in route(item) if c in known]
    for item in problems.values():
        unknown = [c for c in item["concepts"] if c not in known]
        if unknown:
            raise SystemExit(f"{item['id']}: unknown concepts {unknown}")
    implementations = load_implementations()
    for item in implementations:
        if item["concept"] not in known:
            raise SystemExit(f"{item['id']}: unknown concept {item['concept']}")
    kept = set(problems)
    for company in companies.values():
        company["problems"] = [row for row in company["problems"] if row[0] in kept]
    companies = {k: v for k, v in companies.items() if v["problems"]}

    OUT.mkdir(parents=True, exist_ok=True)
    ordered = sorted(problems.values(), key=lambda p: p["id"])
    (OUT / "problems.jsonl").write_text(
        "".join(json.dumps(p, ensure_ascii=False, separators=(",", ":")) + "\n" for p in ordered),
        encoding="utf-8",
    )
    (OUT / "companies.json").write_text(
        json.dumps(companies, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    (OUT / "implementations.jsonl").write_text(
        "".join(
            json.dumps(i, separators=(",", ":")) + "\n"
            for i in sorted(implementations, key=lambda i: i["id"])
        ),
        encoding="utf-8",
    )
    sources = {
        "policy": "Metadata and links only. No problem statements, editorials or solution code are stored.",
        "snapshots": {name: run("git", "rev-parse", "HEAD", cwd=CACHE / name) for name in REPOS}
        | {
            f"thealgorithms-{lang}": json.loads((CACHE / f"thealg-{repo}.json").read_text())["sha"]
            for lang, repo in ALGORITHM_REPOS.items()
        },
        "codeforces_problems": sum(1 for k in problems if k.startswith("cf:")),
        "excluded": {"takeuforward.org": "terms of service prohibit automated access"},
    }
    (OUT / "sources.json").write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")

    concept_counts = Counter(c for p in ordered for c in p["concepts"][:1])
    unmapped = sum(not p["concepts"] for p in ordered)
    print(
        f"{len(ordered)} problems ({len(leetcode)} LeetCode, {len(cses)} CSES, {len(codeforces)} CF), "
        f"{len(companies)} companies, {len(implementations)} implementations, {unmapped} unmapped"
    )
    print("striver-flagged:", sum("striver-a2z" in p["sheets"] for p in ordered))
    thin = sorted(c for c in known if concept_counts[c] < 5)
    print("concepts with <5 primary problems:", thin)
    by_lang = defaultdict(Counter)
    for item in implementations:
        by_lang[item["language"]][item["concept"]] += 1
    print({lang: sum(c.values()) for lang, c in by_lang.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
