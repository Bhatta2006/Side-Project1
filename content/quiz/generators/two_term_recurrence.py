"""Two-term recurrence with two rolling variables: term n of a Fibonacci-style sequence.

Each item starts from term 0 = a and term 1 = b and steps n times. Wrong answers are the
classic slips: one step too few or too many, updating prev before saving it, and summing
the terms instead of reporting the last one.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

NEXT = lines("nxt = prev + cur", "long long nxt = prev + cur;", "long nxt = prev + cur;")
SHIFT = lines("prev = cur", "prev = cur;")
ADVANCE = lines("cur = nxt", "cur = nxt;")
LOOP = lines("for _ in range(n):", "for (int i = 0; i < n; i++) {")
OUTPUT = lines("print(prev)", 'cout << prev << "\\n";', "System.out.println(prev);")


def program(v: dict) -> dict[str, str]:
    a, b, n = v["a"], v["b"], v["n"]
    body = (
        "for (int i = 0; i < n; i++) {\n"
        "    {T} nxt = prev + cur;\n"
        "    prev = cur;\n"
        "    cur = nxt;\n"
        "}\n"
    )
    return {
        "python": (
            f"n = {n}\nprev = {a}  # term 0\ncur = {b}  # term 1\n"
            "for _ in range(n):\n"
            "    nxt = prev + cur\n"
            "    prev = cur\n"
            "    cur = nxt\n"
            "print(prev)"
        ),
        "cpp": (
            f"int n = {n};\nlong long prev = {a};  // term 0\nlong long cur = {b};  // term 1\n"
            + body.replace("{T}", "long long")
            + 'cout << prev << "\\n";'
        ),
        "java": (
            f"int n = {n};\nlong prev = {a};  // term 0\nlong cur = {b};  // term 1\n"
            + body.replace("{T}", "long")
            + "System.out.println(prev);"
        ),
    }


def term(a: int, b: int, n: int) -> int:
    """Independent check: build the whole list of terms."""
    terms = [a, b]
    while len(terms) <= n:
        terms.append(terms[-1] + terms[-2])
    return terms[n]


def wrong(v):
    a, b, n = v["a"], v["b"], v["n"]
    prev, cur = a, b
    for _ in range(n):  # prev is overwritten before cur uses it
        prev = cur
        cur = prev + cur
    return [
        (str(term(a, b, n - 1)), "loop-bound-off-by-one"),
        (str(term(a, b, n + 1)), "loop-bound-off-by-one"),
        (str(prev), "dp-rolling-update-order"),
        (str(sum(term(a, b, i) for i in range(n + 1))), "sum-instead-of-term"),
    ]


def sample(rng, params):
    return {"a": rng.randint(*params["a"]), "b": rng.randint(*params["b"]), "n": rng.randint(*params["n"])}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(term(v["a"], v["b"], v["n"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"Each term is the sum of the two before it. This code should print term {v['n']}. "
        "Which line goes in the blank?"
    ),
    fix=lambda v: (
        f"This code should print term {v['n']} of the sequence, where each term is the sum of "
        "the two before it, but it prints the wrong value. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"After each step prev holds the next term; after {v['n']} steps it holds term {v['n']}, "
        f"which is {answer}."
    ),
    blanks=[
        Blank(
            NEXT,
            [
                (lines("nxt = cur + cur", "long long nxt = cur + cur;", "long nxt = cur + cur;"),
                 "dp-wrong-subproblem"),
                (lines("nxt = prev + prev", "long long nxt = prev + prev;", "long nxt = prev + prev;"),
                 "dp-wrong-subproblem"),
                (lines("nxt = cur - prev", "long long nxt = cur - prev;", "long nxt = cur - prev;"),
                 "dp-wrong-subproblem"),
            ],
        ),
        Blank(
            SHIFT,
            [
                (lines("prev = nxt", "prev = nxt;"), "dp-rolling-update-order"),
                (lines("prev = cur + 1", "prev = cur + 1;"), "dp-missing-plus-one"),
                (lines("prev = prev + cur", "prev = prev + cur;"), "sum-instead-of-term"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "dp-rolling-update-order",
            edit(SHIFT, lines("prev = nxt", "prev = nxt;")),
            "Set prev to the old cur, not to the new term",
            "prev must take cur's value before cur moves on to the new term.",
        ),
        Fix(
            "dp-wrong-subproblem",
            edit(NEXT, lines("nxt = cur + cur", "long long nxt = cur + cur;", "long nxt = cur + cur;")),
            "Add the two previous terms: prev + cur",
            "The next term needs both earlier terms, not one of them twice.",
        ),
        Fix(
            "rec-print-next-term",
            edit(OUTPUT, lines("print(cur)", 'cout << cur << "\\n";', "System.out.println(cur);")),
            "Print prev, not cur",
            "After n steps prev is term n; cur is already term n + 1.",
        ),
    ],
    decoys=[
        Decoy(edit(LOOP, lines("for _ in range(n + 1):", "for (int i = 0; i <= n; i++) {")),
              "Run the loop one more time", "loop-bound-off-by-one"),
        Decoy(edit(ADVANCE, lines("cur = prev", "cur = prev;")),
              "Set cur to prev at the end of each step", "dp-rolling-update-order"),
        Decoy(edit(NEXT, lines("nxt = prev + cur + 1", "long long nxt = prev + cur + 1;", "long nxt = prev + cur + 1;")),
              "Add 1 to each new term", "dp-missing-plus-one"),
        Decoy(edit(LOOP, lines("for _ in range(n - 1):", "for (int i = 0; i < n - 1; i++) {")),
              "Run the loop one time fewer", "loop-bound-off-by-one"),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"term": term}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
