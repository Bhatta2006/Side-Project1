"""Count the divisors of n in O(sqrt n): every divisor i up to sqrt(n) pairs with n // i.

Wrong answers are the classic slips: counting the square root twice, stopping before the
square root, forgetting the partner divisors, leaving out n itself, and adding the divisors
instead of counting them.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

BOUND = lines("while i * i <= n:", "while (i * i <= n) {")
TEST = lines("if n % i == 0:", "if (n % i == 0) {")
PAIR = lines("if i != n // i:", "if (i != n / i) {")
START = lines("i = 1", "int i = 1;")
STEP = lines("i += 1", "i += 1;")
OUTPUT = lines("print(count)", 'cout << count << "\\n";', "System.out.println(count);")


def program(v: dict) -> dict[str, str]:
    n = v["n"]
    body = (
        "{decl}count = 0{semi}\n"
        "{decl}i = 1{semi}\n"
        "{loop}\n"
        "    {test}\n"
        "        count += 1{semi}  {c} i divides n\n"
        "        {pair}\n"
        "            count += 1{semi}  {c} so does its partner\n"
        "{close2}"
        "    i += 1{semi}\n"
        "{close1}"
    )
    py = body.format(decl="", semi="", c="#", loop="while i * i <= n:", test="if n % i == 0:",
                     pair="if i != n // i:", close2="", close1="")
    cpp = body.format(decl="int ", semi=";", c="//", loop="while (i * i <= n) {", test="if (n % i == 0) {",
                      pair="if (i != n / i) {", close2="        }\n    }\n", close1="}\n")
    return {
        "python": f"n = {n}\n{py}print(count)",
        "cpp": f"int n = {n};\n{cpp}" + 'cout << count << "\\n";',
        "java": f"int n = {n};\n{cpp}System.out.println(count);",
    }


def divisors(n):
    """Independent check: try every number from 1 to n."""
    return [d for d in range(1, n + 1) if n % d == 0]


def count_brute(n):
    return len(divisors(n))


def wrong(v):
    n = v["n"]
    ds = divisors(n)
    small = [d for d in ds if d * d <= n]
    square = any(d * d == n for d in ds)
    return [
        (str(len(ds) + 1 if square else len(ds) - 1), "div-square-twice" if square else "div-forget-self"),
        (str(len([d for d in ds if d * d < n]) * 2), "div-sqrt-bound-strict"),
        (str(len(small)), "div-no-partner"),
        (str(sum(ds)), "count-vs-sum"),
        (str(len(ds) - 1), "div-forget-self"),
    ]


def sample(rng, params):
    if rng.random() < 0.4:
        root = rng.randint(*params["root"])
        return {"n": root * root}
    return {"n": rng.randint(*params["n"])}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(count_brute(v["n"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: f"This code should count the divisors of {v['n']}. Which line goes in the blank?",
    fix=lambda v: (
        f"This code should count the divisors of {v['n']}, but it prints the wrong answer. Which one-line "
        "change fixes it?"
    ),
    explain=lambda v, answer: (
        "Every divisor i with i · i ≤ n has a partner n // i on the other side of the square root, so "
        "the loop stops at the square root and counts both, except when they are the same number. "
        f"{v['n']} has {answer} divisors."
    ),
    blanks=[
        Blank(
            BOUND,
            [
                (lines("while i * i < n:", "while (i * i < n) {"), "div-sqrt-bound-strict"),
                (lines("while i < n:", "while (i < n) {"), "div-square-twice"),
                (lines("while i * 2 <= n:", "while (i * 2 <= n) {"), "div-square-twice"),
            ],
        ),
        Blank(
            PAIR,
            [
                (lines("if i == n // i:", "if (i == n / i) {"), "div-no-partner"),
                (lines("if i <= n // i:", "if (i <= n / i) {"), "div-square-twice"),
                (lines("if n % i != 0:", "if (n % i != 0) {"), "div-no-partner"),
            ],
        ),
        Blank(
            TEST,
            [
                (lines("if i % n == 0:", "if (i % n == 0) {"), "mod-operands-swapped"),
                (lines("if n // i == 0:", "if (n / i == 0) {"), "mod-swap-div"),
                (lines("if n % i == 1:", "if (n % i == 1) {"), "filter-wrong-test"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "div-square-twice",
            edit(PAIR, lines("if i <= n // i:", "if (i <= n / i) {")),
            "Count the partner only when it is a different number: i != n // i",
            "When i · i = n, the partner is i itself and must not be counted again.",
        ),
        Fix(
            "div-sqrt-bound-strict",
            edit(BOUND, lines("while i * i < n:", "while (i * i < n) {")),
            "Keep going while i · i <= n, so the square root itself is tried",
            "With <, a perfect square never reaches its square root.",
        ),
        Fix(
            "mod-operands-swapped",
            edit(TEST, lines("if i % n == 0:", "if (i % n == 0) {")),
            "Test whether i divides n: n % i == 0",
            "i % n asks whether n divides i, which is the other way round.",
        ),
    ],
    decoys=[
        Decoy(edit(OUTPUT, lines("print(count + 1)", 'cout << count + 1 << "\\n";', "System.out.println(count + 1);")),
              "Print count + 1", "off-by-one-output"),
        Decoy(edit(START, lines("i = 2", "int i = 2;")), "Start i at 2", "skip-first-element"),
        Decoy(edit(STEP, lines("i += 2", "i += 2;")), "Step i by 2", "loop-bound-off-by-one"),
        Decoy(edit(OUTPUT, lines("print(count * 2)", 'cout << count * 2 << "\\n";', "System.out.println(count * 2);")),
              "Double the count for the partners", "double-count"),
        Decoy(edit(OUTPUT, lines("print(count - 1)", 'cout << count - 1 << "\\n";', "System.out.println(count - 1);")),
              "Print count − 1", "off-by-one-output"),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"count_brute": count_brute}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
