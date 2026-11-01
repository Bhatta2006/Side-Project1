"""Which programming language a question's prose is written in.

Many items carry no code block and no ``languages`` tag, but their prompt still leans on one
language's syntax: ``int(math.sqrt(n))``, ``a = input()``, ``7 // 2``. A C++ learner must
never see those. ``spoken`` finds the languages a text clearly speaks; an item fits a
learner only when its text speaks no other language than theirs.

Markers are deliberately narrow: each one is something a learner of another language would
not recognise. Plain words ("list", "string", "true") are not markers.
"""

import re

_MARKERS: dict[str, tuple[str, ...]] = {
    "python": (
        r"\binput\(\)",
        r"\bprint\(",
        r"\bmath\.\w+\(",
        r"\b(?:int|float|str|len|range|isqrt|sorted|enumerate)\([^)]*\)",
        r"[\w)\]]\s*//\s*[\w(]",  # floor division; C++/Java comments never sit between operands
        r"\w\s*\*\*\s*\w",
        r"\bdef \w+\(",
        r"\belif\b",
        r"\bNone\b",
        r"\.append\(",
        r"\bf\"[^\"]*\{",
        r"\blambda \w*:",
        r"\bdict\b|\btuple\b",
        r"\[\s*-1\s*\]",  # negative indexing
        r"\[\s*::?-?\d*\s*\]",  # slicing like [::-1]
    ),
    "cpp": (
        r"\bstd::",
        r"\bcout\b",
        r"\bcin\b",
        r"\bvector<",
        r"#include",
        r"\blong long\b",
        r"\bnullptr\b",
        r"\bendl\b",
        r"\.push_back\(",
        r"\bunordered_map\b",
        r"\bsizeof\(",
    ),
    "java": (
        r"\bSystem\.out\b",
        r"\bScanner\b",
        r"\bArrayList\b",
        r"\bHashMap\b",
        r"\bInteger\.\w+",
        r"\bString\[\]",
        r"\bpublic static\b",
        r"\bMath\.\w+\(",
        r"\.length\(\)",
    ),
}
_COMPILED = {lang: re.compile("|".join(f"(?:{p})" for p in ps)) for lang, ps in _MARKERS.items()}


def spoken(*texts: str) -> set[str]:
    """Languages whose unmistakable syntax appears in any of ``texts``."""
    joined = "\n".join(t for t in texts if t)
    return {lang for lang, rx in _COMPILED.items() if rx.search(joined)}


def foreign(language: str, *texts: str) -> bool:
    """True when the text speaks a language and the learner's is not among them."""
    found = spoken(*texts)
    return bool(found) and language not in found
