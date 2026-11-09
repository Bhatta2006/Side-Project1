"""Pick the practice problems the library shows: about ten per concept, the well-known ones.

The imported index (content/practice/problems.jsonl, ~14,000 problems) stays as it is, so
company lists and a learner's earlier marks still resolve. This script writes
content/practice/curated.json, the short list the library, recommendations and concept
pages serve. Deterministic: the same index gives the same list.

    python scripts/dev/curate_practice.py          # rewrite curated.json
    python scripts/dev/curate_practice.py --check  # fail if curated.json is out of date

Rules, in order:
1. Every problem a pattern file names is kept (lessons link to them).
2. Each concept gets TARGET more of its best-known problems, spread over easy, medium, hard.
   A problem counts for a concept only when that concept is one of its first two tags, so
   a loosely tagged problem does not stand in for a topic.
3. Among candidates, the well-known go first: the Striver A2Z sheet, the CSES problem set,
   how many companies ask it, then how many people solved it.
"""

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRACTICE = ROOT / "content" / "practice"
PATTERNS = ROOT / "content" / "patterns"
TARGET = {"easy": 1, "medium": 2, "hard": 1}  # best-known core per concept, beyond pattern problems
CAP = 15  # most problems listed for one concept
RELEVANT = 2  # a problem stands for its first two concepts only


def fame(p: dict) -> float:
    score = 0.0
    if "striver-a2z" in p["sheets"]:
        score += 6
    if "cses" in p["sheets"]:
        score += 4
    score += 2.5 * math.log1p(p.get("companies", 0))
    score += 0.5 * math.log1p(p.get("solvers", 0) / 100)
    return score


def pattern_ids(known: set[str]) -> set[str]:
    found: set[str] = set()
    for path in PATTERNS.rglob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        found |= set(re.findall(r"\b(?:cf|leetcode|cses):[A-Za-z0-9_\-]+", text)) & known
    return found


def curate(problems: list[dict]) -> dict[str, list[str]]:
    by_id = {p["id"]: p for p in problems}
    concepts = sorted({c for p in problems for c in p["concepts"]})
    named = pattern_ids(set(by_id))
    chosen: set[str] = set(named)

    def stands_for(p: dict) -> list[str]:
        return p["concepts"][:RELEVANT]

    def counts(concept: str) -> Counter:
        # Only problems mainly about this concept fill its quota. Pattern problems are kept
        # anyway, so they do not take the places of the classics.
        return Counter(
            by_id[i]["difficulty"] for i in chosen - named if by_id[i]["concepts"][0] == concept
        )

    for concept in concepts:
        pool = sorted(
            (p for p in problems if concept in stands_for(p) and p["id"] not in chosen),
            key=lambda p: (p["concepts"][0] != concept, -fame(p), p["id"]),
        )
        have = counts(concept)
        for p in pool:
            if sum(have.values()) >= sum(TARGET.values()):
                break
            if have[p["difficulty"]] < TARGET[p["difficulty"]]:
                chosen.add(p["id"])
                have[p["difficulty"]] += 1
        # The index lacks one difficulty for this concept: fill up with the best of the rest.
        for p in pool:
            if sum(have.values()) >= sum(TARGET.values()):
                break
            if p["id"] not in chosen:
                chosen.add(p["id"])
                have[p["difficulty"]] += 1

    listed: dict[str, list[str]] = {}
    for concept in concepts:
        ids = [i for i in chosen if concept in by_id[i]["concepts"]]
        # Keep the most relevant and best-known first, then show them easiest first.
        best = sorted(
            ids,
            key=lambda i: (concept not in stands_for(by_id[i]), -fame(by_id[i]), i),
        )[:CAP]
        listed[concept] = sorted(
            best,
            key=lambda i: (
                ["easy", "medium", "hard"].index(by_id[i]["difficulty"]),
                -fame(by_id[i]),
                i,
            ),
        )
    return listed


def build() -> dict:
    lines = (PRACTICE / "problems.jsonl").read_text(encoding="utf-8").splitlines()
    problems = [json.loads(line) for line in lines if line.strip()]
    listed = curate(problems)
    ids = sorted(
        {i for group in listed.values() for i in group} | pattern_ids({p["id"] for p in problems})
    )
    return {
        "about": "The practice problems the library shows; written by scripts/dev/curate_practice.py.",
        "total": len(ids),
        "problems": ids,
        "by_concept": listed,
    }


def main() -> int:
    out = PRACTICE / "curated.json"
    data = build()
    text = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
    if "--check" in sys.argv:
        current = out.read_text(encoding="utf-8") if out.exists() else ""
        if current != text:
            print("curated.json is out of date: run scripts/dev/curate_practice.py")
            return 1
        print(f"curated.json is current ({data['total']} problems)")
        return 0
    out.write_text(text, encoding="utf-8", newline="\n")
    sizes = [len(v) for v in data["by_concept"].values()]
    print(f"{data['total']} problems, {len(sizes)} concepts, {min(sizes)}-{max(sizes)} per concept")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
