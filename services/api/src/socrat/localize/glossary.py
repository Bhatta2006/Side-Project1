"""The terms a translation must not change, and the preferred wording per language.

Programming and data-structure terms stay in English in every language: learners meet them in
documentation, interviews and code, and a clever local coinage hurts them there. Per-language
preferred wordings are added only for terms a native-speaking reviewer has agreed.
Bump VERSION when the lists change; stored translations record the version they used.
"""

VERSION = "1"

KEEP: tuple[str, ...] = (
    "array",
    "stack",
    "queue",
    "heap",
    "hash table",
    "linked list",
    "binary search",
    "recursion",
    "pointer",
    "algorithm",
    "Big-O",
    "API",
    "DFS",
    "BFS",
    "dynamic programming",
    "greedy",
    "two pointers",
    "sliding window",
    "tree",
    "graph",
)

PREFERRED: dict[str, dict[str, str]] = {
    "hi": {"variable": "वेरिएबल", "function": "फ़ंक्शन"},
    "te": {"variable": "వేరియబుల్", "function": "ఫంక్షన్"},
}


def preferred(tag: str) -> dict[str, str]:
    return PREFERRED.get(tag, {})


def must_keep(text: str) -> list[str]:
    """Glossary terms that occur in ``text`` (so must occur in its translation)."""
    import re

    return [
        t
        for t in KEEP
        if re.search(rf"(?<![A-Za-z]){re.escape(t)}(?![A-Za-z])", text, re.IGNORECASE)
    ]
