"""Route library problems to Socrat's specific concepts (DP families, monotonic stack, …).

The importer's tag table maps platform tags to broad concepts (every DP problem lands on
dsa:dp-1d, every stack problem on dsa:stacks). The syllabus has since grown narrower
concepts, and a learner on "Stock trading DP" should be offered stock problems, not any DP.
These rules look at titles (LeetCode titles are distinctive) and tags, put the specific
concept first and keep the broad ones behind it.

    python scripts/content/practice_routing.py      # re-route content/practice/problems.jsonl

Run again after the importer; it is idempotent.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROBLEMS = ROOT / "content" / "practice" / "problems.jsonl"
MAX_CONCEPTS = 4


def rx(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.I)


DP_TAGS = {"Dynamic Programming", "Memoization", "dp"}
TREE_TAGS = {"Tree", "Binary Tree", "trees"}

# (concept, title pattern or None, tags of which one is required or None, platforms or None)
RULES: list[tuple[str, re.Pattern | None, set[str] | None, set[str] | None]] = [
    ("dsa:dp-stocks", rx(r"\bstock"), None, {"LeetCode"}),
    (
        "dsa:dp-lis",
        rx(
            r"increasing subsequence|russian doll|largest divisible subset|longest string chain|bitonic|envelope|maximum length of pair chain|longest arithmetic subsequence"
        ),
        None,
        None,
    ),
    (
        "dsa:dp-lcs",
        rx(
            r"common subsequence|common substring|supersequence|palindromic subsequence|repeated subarray|uncrossed lines|minimum insertion steps|delete operation for two strings"
        ),
        None,
        None,
    ),
    (
        "dsa:dp-edit-distance",
        rx(
            r"edit distance|distinct subsequences|wildcard matching|regular expression matching|interleaving string|palindromic substrings|one edit distance|minimum ascii delete"
        ),
        None,
        None,
    ),
    (
        "dsa:dp-partition",
        rx(
            r"burst balloons|minimum cost to cut|matrix chain|boolean (evaluation|parenthes)|merge stones|triangulation|strange printer|guess number higher or lower ii|remove boxes|palindrome partitioning ii"
        ),
        None,
        None,
    ),
    (
        "dsa:dp-squares",
        rx(
            r"maximal square|maximal rectangle|count square submatrices|largest plus sign|largest 1-bordered"
        ),
        None,
        None,
    ),
    (
        "dsa:knapsack-01",
        rx(
            r"partition equal subset|target sum|last stone weight ii|ones and zeroes|subset sum|minimize the difference|profitable schemes|tallest billboard|partition array into two arrays"
        ),
        None,
        None,
    ),
    (
        "dsa:knapsack-unbounded",
        rx(
            r"coin change|combination sum iv|perfect squares|integer break|cutting a rod|minimum cost for tickets"
        ),
        None,
        None,
    ),
    (
        "dsa:dp-on-trees",
        rx(
            r"house robber iii|binary tree cameras|maximum path sum|sum of distances in tree|longest univalue path|distribute coins|maximum product of splitted"
        ),
        None,
        None,
    ),
    ("dsa:dp-on-trees", None, TREE_TAGS, None),  # tree + DP, checked below
    (
        "dsa:dp-introduction",
        rx(r"fibonacci|climbing stairs|tribonacci|min cost climbing"),
        None,
        None,
    ),
    (
        "dsa:dp-advanced-patterns",
        rx(
            r"stone game|predict the winner|can i win|numbers at most n given digit set|non-negative integers without consecutive|count numbers with unique digits|digit"
        ),
        DP_TAGS,
        None,
    ),
    (
        "dsa:monotonic-stack",
        rx(
            r"next greater|daily temperatures|stock spanner|largest rectangle in histogram|sliding window maximum|sum of subarray minimums|sum of subarray ranges|trapping rain water|132 pattern|remove k digits|car fleet|online stock span"
        ),
        None,
        None,
    ),
    ("dsa:monotonic-stack", None, {"Monotonic Stack", "Monotonic Queue"}, None),
    (
        "dsa:hashing",
        rx(
            r"two sum|group anagrams|longest consecutive sequence|subarray sum equals k|contiguous array|isomorphic|word pattern|happy number|contains duplicate|valid anagram|ransom note|4sum ii|nice subarrays|subarrays with k different"
        ),
        None,
        {"LeetCode"},
    ),
    (
        "dsa:design-data-structures",
        rx(
            r"\blru\b|\blfu\b|\bdesign\b|iterator|\bimplement\b|time based key-value|snapshot array|randomized set|min stack|data stream"
        ),
        None,
        {"LeetCode"},
    ),
    (
        "dsa:binary-search-on-answer",
        rx(
            r"koko|capacity to ship|split array largest sum|minimum number of days to make|magnetic force|smallest divisor|minimi[sz]ed maximum|maximum candies|minimum time to (complete|repair)|kth smallest number in multiplication|smallest distance pair|minimum speed to arrive|cutting ribbons|maximize the minimum|minimize the maximum"
        ),
        None,
        {"LeetCode"},
    ),
    (
        "dsa:recursion-patterns",
        rx(
            r"pow\(x|generate parentheses|letter combinations|k-th symbol|subsets|permutations|reverse (a )?stack|sort (a )?stack|different ways to add parentheses"
        ),
        None,
        {"LeetCode"},
    ),
    (
        "dsa:tree-patterns",
        rx(
            r"\bview\b|vertical order|lowest common ancestor|distance k|width of binary tree|path sum|zigzag|boundary of binary tree|level order|maximum depth|balanced binary tree|symmetric tree|invert binary tree|diameter of binary tree|serialize|flatten binary tree|construct binary tree|count good nodes|same tree|subtree of another"
        ),
        TREE_TAGS,
        None,
    ),
    (
        "cp:modular-arithmetic",
        rx(r"exponentiation|binomial|modular|inverse|super pow|count good numbers|pow\(x"),
        None,
        {"LeetCode", "CSES"},
    ),
    (
        "cp:prefix-difference",
        rx(
            r"range (sum|addition)|corporate flight|car pooling|zero array transformation|static range|forest queries|difference array"
        ),
        None,
        {"LeetCode", "CSES"},
    ),
]

# First steps in the zero course: easy LeetCode problems by tag, as extra (not primary) homes.
BEGINNER: list[tuple[str, set[str]]] = [
    ("zero:strings", {"String"}),
    ("zero:lists", {"Array"}),
    ("zero:maps", {"Hash Table"}),
    ("zero:math-on-numbers", {"Math"}),
    ("zero:nested-loops", {"Matrix"}),
    ("zero:searching-and-sorting", {"Sorting", "Binary Search"}),
    ("zero:classes-and-objects", {"Design"}),
    ("zero:conditionals", {"Simulation"}),
    ("zero:boolean-logic", {"Bit Manipulation"}),
]


# Codeforces tags at interview-level ratings, as homes for the interview course's concepts.
CF_INTERVIEW: list[tuple[str, str]] = [
    ("greedy", "dsa:greedy"),
    ("bitmasks", "dsa:bit-manipulation"),
    ("hashing", "dsa:hashing"),
    ("binary search", "dsa:binary-search-on-answer"),
    ("constructive algorithms", "dsa:greedy"),
]
CF_INTERVIEW_MAX_RATING = 1700


def specific(problem: dict) -> list[str]:
    title, tags, platform = problem["title"], set(problem.get("tags", [])), problem["platform"]
    found: list[str] = []
    for concept, title_rx, needed, platforms in RULES:
        if platforms and platform not in platforms:
            continue
        if concept == "dsa:dp-on-trees" and title_rx is None:
            if tags & TREE_TAGS and tags & DP_TAGS:
                found.append(concept)
            continue
        if title_rx is not None and not title_rx.search(title):
            continue
        if needed is not None and not tags & needed:
            continue
        if concept not in found:
            found.append(concept)
    return found


def route(problem: dict) -> list[str]:
    routed = {r[0] for r in RULES} | {
        c for _, c in CF_INTERVIEW if problem["platform"] == "Codeforces"
    }
    base = [c for c in problem["concepts"] if c not in routed]
    extra = specific(problem)
    concepts = extra + [c for c in base if c not in extra]
    if (
        problem["platform"] == "Codeforces"
        and (problem.get("rating") or 0) <= CF_INTERVIEW_MAX_RATING
    ):
        tags = set(problem.get("tags", []))
        # A secondary home: the problem keeps its competitive-programming concept first.
        for tag, concept in CF_INTERVIEW:
            if tag in tags and concept not in concepts:
                concepts.insert(1, concept)
                break
    if problem["platform"] == "LeetCode" and problem["difficulty"] == "easy":
        tags = set(problem.get("tags", []))
        for concept, needed in BEGINNER:
            if tags & needed and concept not in concepts and len(concepts) < MAX_CONCEPTS:
                concepts.append(concept)
                break
    return concepts[:MAX_CONCEPTS]


def main() -> int:
    sys.path.insert(0, str(ROOT / "services" / "api" / "src"))
    from socrat.catalog.registry import load

    known = set(load(tests_root=None).concepts)
    rows = [json.loads(line) for line in PROBLEMS.read_text(encoding="utf-8").splitlines() if line]
    before = Counter(c for r in rows for c in r["concepts"])
    for row in rows:
        row["concepts"] = [c for c in route(row) if c in known]
    after = Counter(c for r in rows for c in r["concepts"])
    PROBLEMS.write_text(
        "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows),
        encoding="utf-8",
        newline="\n",
    )
    changed = {c: (before[c], after[c]) for c in sorted(known) if before[c] != after[c]}
    print(f"{len(rows)} problems re-routed; concept counts changed: {changed}")
    empty = sorted(c for c in known if after[c] == 0)
    print("concepts with no library problems:", empty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
