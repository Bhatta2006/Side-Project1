"""Count subsequences with sum k by recursion: at each index, pick the element or skip it.

Wrong answers are the classic slips: a base case that ignores the target (counting every
subset), stopping as soon as the sum reaches k (missing later zeros), counting subarrays
instead of subsequences, counting each choice twice, and dropping the skip branch.
"""

from itertools import combinations

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

BASE = lines("return 1 if total == k else 0", "return total == k ? 1 : 0;")
TAKE = lines("take = count(i + 1, total + a[i])", "int take = count(i + 1, total + a[i]);")
SKIP = lines("skip = count(i + 1, total)", "int skip = count(i + 1, total);")
RET = lines("return take + skip", "return take + skip;")
OUTPUT = lines("print(count(0, 0))", 'cout << count(0, 0) << "\\n";', "System.out.println(new Rec().count(0, 0));")


def arr(xs):
    return ", ".join(map(str, xs))


def program(v: dict) -> dict[str, str]:
    a, k = arr(v["a"]), v["k"]
    return {
        "python": (
            f"a = [{a}]\nk = {k}\n"
            "def count(i, total):\n"
            "    if i == len(a):\n"
            "        return 1 if total == k else 0\n"
            "    take = count(i + 1, total + a[i])\n"
            "    skip = count(i + 1, total)\n"
            "    return take + skip\n"
            "print(count(0, 0))"
        ),
        "cpp": (
            f"vector<int> a = {{{a}}};\nint k = {k};\n"
            "function<int(int, int)> count = [&](int i, int total) -> int {\n"
            "    if (i == (int)a.size()) {\n"
            "        return total == k ? 1 : 0;\n"
            "    }\n"
            "    int take = count(i + 1, total + a[i]);\n"
            "    int skip = count(i + 1, total);\n"
            "    return take + skip;\n"
            "};\n"
            'cout << count(0, 0) << "\\n";'
        ),
        "java": (
            f"int[] a = {{{a}}};\nint k = {k};\n"
            "class Rec {\n"
            "    int count(int i, int total) {\n"
            "        if (i == a.length) {\n"
            "            return total == k ? 1 : 0;\n"
            "        }\n"
            "        int take = count(i + 1, total + a[i]);\n"
            "        int skip = count(i + 1, total);\n"
            "        return take + skip;\n"
            "    }\n"
            "}\n"
            "System.out.println(new Rec().count(0, 0));"
        ),
    }


def count_brute(a, k):
    """Independent check: every set of positions."""
    n = len(a)
    return sum(1 for r in range(n + 1) for pos in combinations(range(n), r) if sum(a[p] for p in pos) == k)


def stop_at_target(a, k):
    def go(i, total):
        if total == k:
            return 1
        if i == len(a):
            return 0
        return go(i + 1, total + a[i]) + go(i + 1, total)
    return go(0, 0)


def subarrays(a, k):
    return sum(1 for lo in range(len(a)) for hi in range(lo, len(a)) if sum(a[lo:hi + 1]) == k)


def wrong(v):
    a, k, answer = v["a"], v["k"], count_brute(v["a"], v["k"])
    return [
        (str(stop_at_target(a, k)), "pnp-stop-at-target"),
        (str(subarrays(a, k)), "pattern-subset-vs-subarray"),
        (str(2 ** len(a)), "pnp-base-ignores-target"),
        (str(2 * answer), "double-count"),
        (str(1 if sum(a) == k else 0), "pnp-forget-skip"),
    ]


def sample(rng, params):
    n = rng.randint(*params["length"])
    return {"a": [rng.randint(*params["value"]) for _ in range(n)], "k": rng.randint(*params["k"])}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(count_brute(v["a"], v["k"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should count the subsequences of a (any elements, kept in order) whose sum is "
        f"{v['k']}. Which line goes in the blank?"
    ),
    fix=lambda v: (
        f"This code should count the subsequences of a (any elements, kept in order) whose sum is "
        f"{v['k']}, but it prints the wrong answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        "Each call decides one index: take a[i] into the sum, or skip it. Only when every index is "
        "decided does the call check the sum, so every subsequence is counted exactly once. "
        f"The count is {answer}."
    ),
    blanks=[
        Blank(
            TAKE,
            [
                (lines("take = count(i + 1, total)", "int take = count(i + 1, total);"), "pnp-take-without-element"),
                (lines("take = count(i + 1, total + i)", "int take = count(i + 1, total + i);"), "confuse-index-value"),
                (lines("take = count(i + 1, total + a[i]) + 1", "int take = count(i + 1, total + a[i]) + 1;"),
                 "dp-missing-plus-one"),
            ],
        ),
        Blank(
            BASE,
            [
                (lines("return 1", "return 1;"), "pnp-base-ignores-target"),
                (lines("return 1 if total >= k else 0", "return total >= k ? 1 : 0;"), "exact-vs-at-least"),
                (lines("return total", "return total;"), "count-vs-sum"),
            ],
        ),
        Blank(
            SKIP,
            [
                (lines("skip = count(i + 1, total + a[i])", "int skip = count(i + 1, total + a[i]);"),
                 "pnp-take-without-element"),
                (lines("skip = 0", "int skip = 0;"), "pnp-forget-skip"),
                (lines("skip = count(i + 1, 0)", "int skip = count(i + 1, 0);"), "reset-inside-loop"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "pnp-forget-skip",
            edit(RET, lines("return take", "return take;")),
            "Add both branches: return take + skip",
            "Without the skip branch, only the subsequence that takes everything is ever counted.",
        ),
        Fix(
            "pnp-take-without-element",
            edit(TAKE, lines("take = count(i + 1, total)", "int take = count(i + 1, total);")),
            "Add the element when taking it: count(i + 1, total + a[i])",
            "Taking a[i] must add it to the sum; otherwise both branches are the same.",
        ),
        Fix(
            "pnp-base-ignores-target",
            edit(BASE, lines("return 1", "return 1;")),
            "Count a finished choice only if its sum is k",
            "Returning 1 for every finished choice counts all 2^n subsequences.",
        ),
    ],
    decoys=[
        Decoy(edit(OUTPUT, lines("print(count(0, 0) + 1)", 'cout << count(0, 0) + 1 << "\\n";',
                                 "System.out.println(new Rec().count(0, 0) + 1);")),
              "Print one more, for the empty subsequence", "subset-count-off-by-one"),
        Decoy(edit(OUTPUT, lines("print(count(0, 0) - 1)", 'cout << count(0, 0) - 1 << "\\n";',
                                 "System.out.println(new Rec().count(0, 0) - 1);")),
              "Print one less", "off-by-one-output"),
        Decoy(edit(OUTPUT, lines("print(count(1, 0))", 'cout << count(1, 0) << "\\n";',
                                 "System.out.println(new Rec().count(1, 0));")),
              "Start the recursion at index 1", "skip-first-element"),
        Decoy(edit(OUTPUT, lines("print(count(0, 0) // 2)", 'cout << count(0, 0) / 2 << "\\n";',
                                 "System.out.println(new Rec().count(0, 0) / 2);")),
              "Halve the count, since each choice is made twice", "double-count"),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"count_brute": count_brute}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
