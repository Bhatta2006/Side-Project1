"""Hamming distance: XOR the two numbers, then count set bits with x &= x - 1.

Wrong answers mix up XOR with AND/OR or with adding bit counts, or count the bit length
instead of the set bits.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, lines

DIFF = lines("x = a ^ b", "int x = a ^ b;")
CLEAR = lines("x &= x - 1", "x &= x - 1;")


def program(v: dict) -> dict[str, str]:
    a, b = v["a"], v["b"]
    return {
        "python": (
            f"a = {a}\nb = {b}\n"
            "x = a ^ b\n"
            "count = 0\n"
            "while x != 0:\n"
            "    x &= x - 1\n"
            "    count += 1\n"
            "print(count)"
        ),
        "cpp": (
            f"int a = {a};\nint b = {b};\n"
            "int x = a ^ b;\n"
            "int count = 0;\n"
            "while (x != 0) {\n"
            "    x &= x - 1;\n"
            "    count++;\n"
            "}\n"
            'cout << count << "\\n";'
        ),
        "java": (
            f"int a = {a};\nint b = {b};\n"
            "int x = a ^ b;\n"
            "int count = 0;\n"
            "while (x != 0) {\n"
            "    x &= x - 1;\n"
            "    count++;\n"
            "}\n"
            "System.out.println(count);"
        ),
    }


def ones(x: int) -> int:
    return bin(x).count("1")


def hamming(a: int, b: int) -> int:
    """Independent check: compare the binary digits position by position."""
    width = max(a, b).bit_length()
    return sum(1 for i in range(width) if (a >> i) % 2 != (b >> i) % 2)


def wrong(v):
    a, b = v["a"], v["b"]
    return [
        (str(ones(a) + ones(b)), "bit-xor-as-sum"),
        (str(ones(a & b)), "bit-and-vs-xor"),
        (str((a ^ b).bit_length()), "bit-length-vs-count"),
        (str(ones(a | b)), "bit-and-vs-xor"),
    ]


def sample(rng, params):
    a = rng.randint(*params["value"])
    b = rng.randint(*params["value"])
    return {"a": a, "b": b}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(hamming(v["a"], v["b"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should print how many bit positions differ between {v['a']} and {v['b']}. "
        "Which line goes in the blank?"
    ),
    fix=lambda v: "",
    explain=lambda v, answer: (
        f"{v['a']} = {v['a']:b} and {v['b']} = {v['b']:b} in binary. XOR keeps a 1 exactly where "
        f"they differ ({v['a'] ^ v['b']:b}), and x &= x - 1 clears the lowest 1 each round, so the "
        f"loop runs once per differing bit: {answer}."
    ),
    blanks=[
        Blank(
            DIFF,
            [
                (lines("x = a & b", "int x = a & b;"), "bit-and-vs-xor"),
                (lines("x = a | b", "int x = a | b;"), "bit-and-vs-xor"),
                (lines("x = a + b", "int x = a + b;"), "bit-xor-as-sum"),
            ],
        ),
        Blank(
            CLEAR,
            [
                (lines("x >>= 1", "x >>= 1;"), "bit-length-vs-count"),
                (lines("x -= 1", "x -= 1;"), "bit-clear-lowest-confusion"),
                (lines("x &= x >> 1", "x &= x >> 1;"), "bit-clear-lowest-confusion"),
            ],
        ),
    ],
    bands=(3, 3, 4),
)
HELPERS = {"hamming": hamming}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
