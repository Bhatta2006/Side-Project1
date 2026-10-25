"""Bubble sort, stopped after a few passes: what does the array look like?

Each pass swaps neighbours that are out of order, which carries the largest remaining value
to the end. Wrong answers are the classic slips: expecting the array to be sorted already,
one pass too many or too few, selection sort's state instead, and sorting the wrong way.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

COMPARE = lines("if a[j] > a[j + 1]:", "if (a[j] > a[j + 1]) {")
SWAP = lines("a[j], a[j + 1] = a[j + 1], a[j]", "swap(a[j], a[j + 1]);",
             "int t = a[j]; a[j] = a[j + 1]; a[j + 1] = t;")
INNER = lines("for j in range(n - 1 - p):", "for (int j = 0; j < n - 1 - p; j++) {")
OUTER = lines("for p in range(passes):", "for (int p = 0; p < passes; p++) {")
OUTPUT = lines('print(" ".join(map(str, a)))',
               'for (int i = 0; i < n; i++) cout << a[i] << (i + 1 < n ? " " : "\\n");',
               "StringJoiner out = new StringJoiner(\" \"); for (int x : a) out.add(String.valueOf(x)); "
               "System.out.println(out);")


def arr(xs):
    return ", ".join(map(str, xs))


def program(v: dict) -> dict[str, str]:
    a, passes = arr(v["a"]), v["passes"]
    return {
        "python": (
            f"a = [{a}]\npasses = {passes}\n"
            "n = len(a)\n"
            "for p in range(passes):\n"
            "    for j in range(n - 1 - p):\n"
            "        if a[j] > a[j + 1]:\n"
            "            a[j], a[j + 1] = a[j + 1], a[j]\n"
            'print(" ".join(map(str, a)))'
        ),
        "cpp": (
            f"vector<int> a = {{{a}}};\nint passes = {passes};\n"
            "int n = a.size();\n"
            "for (int p = 0; p < passes; p++) {\n"
            "    for (int j = 0; j < n - 1 - p; j++) {\n"
            "        if (a[j] > a[j + 1]) {\n"
            "            swap(a[j], a[j + 1]);\n"
            "        }\n"
            "    }\n"
            "}\n"
            'for (int i = 0; i < n; i++) cout << a[i] << (i + 1 < n ? " " : "\\n");'
        ),
        "java": (
            f"int[] a = {{{a}}};\nint passes = {passes};\n"
            "int n = a.length;\n"
            "for (int p = 0; p < passes; p++) {\n"
            "    for (int j = 0; j < n - 1 - p; j++) {\n"
            "        if (a[j] > a[j + 1]) {\n"
            "            int t = a[j]; a[j] = a[j + 1]; a[j + 1] = t;\n"
            "        }\n"
            "    }\n"
            "}\n"
            'StringJoiner out = new StringJoiner(" "); for (int x : a) out.add(String.valueOf(x)); '
            "System.out.println(out);"
        ),
    }


def show(xs):
    return " ".join(map(str, xs))


def bubble(a, passes, descending=False):
    """Independent model: a pass walks left to right, swapping each out-of-order neighbour pair."""
    a = list(a)
    for p in range(passes):
        j = 0
        while j < len(a) - 1 - p:
            wrong_order = a[j] < a[j + 1] if descending else a[j] > a[j + 1]
            if wrong_order:
                a[j], a[j + 1] = a[j + 1], a[j]
            j += 1
    return a


def selection(a, passes):
    a = list(a)
    for p in range(passes):
        m = min(range(p, len(a)), key=lambda i: a[i])
        a[p], a[m] = a[m], a[p]
    return a


def wrong(v):
    a, k = v["a"], v["passes"]
    return [
        (show(sorted(a)), "sort-pass-equals-sorted"),
        (show(bubble(a, k + 1)), "loop-bound-off-by-one"),
        (show(bubble(a, k - 1)), "loop-bound-off-by-one"),
        (show(selection(a, k)), "sort-confuse-algorithms"),
        (show(bubble(a, k, descending=True)), "sort-wrong-direction"),
    ]


def sample(rng, params):
    n = rng.randint(*params["length"])
    return {"a": rng.sample(range(1, 20), n), "passes": rng.randint(*params["passes"])}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: show(bubble(v["a"], v["passes"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code runs {v['passes']} passes of bubble sort (ascending) and prints the array. "
        "Which line goes in the blank?"
    ),
    fix=lambda v: (
        f"This code should run {v['passes']} passes of bubble sort (ascending) and print the array, "
        "but it prints the wrong result. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        "Each pass walks left to right and swaps every pair of neighbours that is out of order, so "
        "the largest value not yet in place moves to the end. After "
        f"{v['passes']} passes the array is {answer}."
    ),
    blanks=[
        Blank(
            COMPARE,
            [
                (lines("if a[j] < a[j + 1]:", "if (a[j] < a[j + 1]) {"), "sort-wrong-direction"),
                (lines("if a[j] > a[j + 1] + 1:", "if (a[j] > a[j + 1] + 1) {"), "filter-boundary"),
                (lines("if a[j + 1] > a[j]:", "if (a[j + 1] > a[j]) {"), "sort-wrong-direction"),
            ],
        ),
        Blank(
            INNER,
            [
                (lines("for j in range(n - 2 - p):", "for (int j = 0; j < n - 2 - p; j++) {"),
                 "sort-inner-bound-short"),
                (lines("for j in range(p, n - 1):", "for (int j = p; j < n - 1; j++) {"), "sort-confuse-algorithms"),
                (lines("for j in range(1, n - 1 - p):", "for (int j = 1; j < n - 1 - p; j++) {"),
                 "skip-first-element"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "sort-wrong-direction",
            edit(COMPARE, lines("if a[j] < a[j + 1]:", "if (a[j] < a[j + 1]) {")),
            "Swap when the left value is bigger: a[j] > a[j + 1]",
            "With <, the bigger values are pushed to the front, which sorts in descending order.",
        ),
        Fix(
            "sort-inner-bound-short",
            edit(INNER, lines("for j in range(n - 2 - p):", "for (int j = 0; j < n - 2 - p; j++) {")),
            "Compare up to the last unsorted pair: j < n − 1 − p",
            "Stopping one pair early never compares the last two unsorted values.",
        ),
        Fix(
            "sort-overwrite-not-swap",
            edit(SWAP, lines("a[j] = a[j + 1]", "a[j] = a[j + 1];")),
            "Swap the two values instead of copying one over the other",
            "Copying loses a[j]; the array ends up with a value twice and another missing.",
        ),
    ],
    decoys=[
        Decoy(edit(OUTER, lines("for p in range(passes + 1):", "for (int p = 0; p < passes + 1; p++) {")),
              "Run one more pass", "loop-bound-off-by-one"),
        Decoy(edit(OUTER, lines("for p in range(passes - 1):", "for (int p = 0; p < passes - 1; p++) {")),
              "Run one pass fewer", "loop-bound-off-by-one"),
        Decoy(edit(INNER, lines("for j in range(1, n - 1 - p):", "for (int j = 1; j < n - 1 - p; j++) {")),
              "Start each pass at index 1", "skip-first-element"),
        Decoy(edit(COMPARE, lines("if a[j] >= a[j + 1] + 1:", "if (a[j] >= a[j + 1] + 1) {")),
              "Swap only when the left value is bigger by at least 1", "filter-boundary"),
    ],
)
DEFECTS = SPEC.defects


def bubble_text(a, passes):
    return show(bubble(a, passes))


HELPERS = {"bubble_text": bubble_text}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
