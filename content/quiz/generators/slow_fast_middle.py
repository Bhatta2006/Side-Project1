"""Slow and fast pointers on a linked list stored in arrays (node 0 is null).

The nodes sit in memory in a scrambled order, so the list order only comes from following
``nxt``. Wrong answers take the first of two middles on an even length, read the middle of
the arrays instead of the list, or stop one step early.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, lines

GUARD = lines("while fast != 0 and nxt[fast] != 0:", "while (fast != 0 && nxt[fast] != 0) {")
JUMP = lines("fast = nxt[nxt[fast]]", "fast = nxt[nxt[fast]];")


def arr(xs):
    return ", ".join(map(str, xs))


def program(v: dict) -> dict[str, str]:
    val, nxt, head = arr(v["val"]), arr(v["nxt"]), v["head"]
    return {
        "python": (
            f"val = [{val}]\nnxt = [{nxt}]  # nxt[i] = next node, 0 = end\nhead = {head}\n"
            "slow = head\n"
            "fast = head\n"
            "while fast != 0 and nxt[fast] != 0:\n"
            "    slow = nxt[slow]\n"
            "    fast = nxt[nxt[fast]]\n"
            "print(val[slow])"
        ),
        "cpp": (
            f"vector<int> val = {{{val}}};\nvector<int> nxt = {{{nxt}}};  // 0 = end\n"
            f"int head = {head};\n"
            "int slow = head;\n"
            "int fast = head;\n"
            "while (fast != 0 && nxt[fast] != 0) {\n"
            "    slow = nxt[slow];\n"
            "    fast = nxt[nxt[fast]];\n"
            "}\n"
            'cout << val[slow] << "\\n";'
        ),
        "java": (
            f"int[] val = {{{val}}};\nint[] nxt = {{{nxt}}};  // 0 = end\nint head = {head};\n"
            "int slow = head;\n"
            "int fast = head;\n"
            "while (fast != 0 && nxt[fast] != 0) {\n"
            "    slow = nxt[slow];\n"
            "    fast = nxt[nxt[fast]];\n"
            "}\n"
            "System.out.println(val[slow]);"
        ),
    }


def walk(v) -> list[int]:
    out, x = [], v["head"]
    while x != 0:
        out.append(v["val"][x])
        x = v["nxt"][x]
    return out


def middle(val: list, nxt: list, head: int) -> int:
    """Independent check: list the values, take index len // 2 (the second middle)."""
    order = walk({"val": val, "nxt": nxt, "head": head})
    return order[len(order) // 2]


def wrong(v):
    order = walk(v)
    n = len(order)
    return [
        (str(order[(n - 1) // 2]), "ll-even-first-middle"),
        (str(v["val"][1 + (n - 1) // 2] if n > 1 else order[0]), "ll-memory-order"),
        (str(order[max(0, n // 2 - 1)]), "loop-bound-off-by-one"),
        (str(order[-1]), "ll-fast-pointer-value"),
    ]


def sample(rng, params):
    n = rng.randint(*params["n"])
    slots = list(range(1, n + 1))
    rng.shuffle(slots)
    values = rng.sample(range(params["value"][0], params["value"][1] + 1), n)
    val, nxt = [0] * (n + 1), [0] * (n + 1)
    for i, slot in enumerate(slots):
        val[slot] = values[i]
        nxt[slot] = slots[i + 1] if i + 1 < n else 0
    return {"val": val, "nxt": nxt, "head": slots[0]}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(middle(v["val"], v["nxt"], v["head"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        "This code should print the middle value of the linked list starting at head (the second "
        "middle when the length is even). Which line goes in the blank?"
    ),
    fix=lambda v: "",
    explain=lambda v, answer: (
        f"Following nxt from head gives {' → '.join(map(str, walk(v)))}. Fast moves two steps for "
        f"each step of slow, so when fast runs out slow is at the middle: {answer}."
    ),
    blanks=[
        Blank(
            GUARD,
            [
                (lines("while nxt[fast] != 0 and nxt[nxt[fast]] != 0:",
                       "while (nxt[fast] != 0 && nxt[nxt[fast]] != 0) {"), "ll-even-first-middle"),
                (lines("while fast != 0 and slow != 0:", "while (fast != 0 && slow != 0) {"),
                 "ll-fast-pointer-value"),
                (lines("while slow != fast:", "while (slow != fast) {"), "ll-cycle-check-confusion"),
                (lines("while nxt[slow] != 0:", "while (nxt[slow] != 0) {"), "ll-fast-pointer-value"),
            ],
        ),
        Blank(
            JUMP,
            [
                (lines("fast = nxt[fast]", "fast = nxt[fast];"), "ll-fast-pointer-value"),
                (lines("fast = nxt[slow]", "fast = nxt[slow];"), "confuse-index-value"),
                (lines("fast = nxt[nxt[slow]]", "fast = nxt[nxt[slow]];"), "confuse-index-value"),
            ],
        ),
    ],
    bands=(3, 4, 5),
)
HELPERS = {"middle": middle}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
