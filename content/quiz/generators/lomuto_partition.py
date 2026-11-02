"""One Lomuto partition pass (quicksort / quickselect) with the last element as pivot.

The pass is not stable and does not sort: values smaller than the pivot are swapped
forward in scan order. Wrong answers assume a sorted result, a stable split, or that the
pivot simply moves to the front.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, lines

TEST = lines("if a[j] < pivot:", "if (a[j] < pivot) {")


def program(v: dict) -> dict[str, str]:
    a = ", ".join(map(str, v["a"]))
    return {
        "python": (
            f"a = [{a}]\n"
            "pivot = a[-1]\n"
            "i = 0  # a[0:i] holds the values smaller than the pivot\n"
            "for j in range(len(a) - 1):\n"
            "    if a[j] < pivot:\n"
            "        a[i], a[j] = a[j], a[i]\n"
            "        i += 1\n"
            "a[i], a[-1] = a[-1], a[i]\n"
            'print(" ".join(map(str, a)))'
        ),
        "cpp": (
            f"vector<int> a = {{{a}}};\n"
            "int n = a.size();\n"
            "int pivot = a[n - 1];\n"
            "int i = 0;  // a[0..i) holds the values smaller than the pivot\n"
            "for (int j = 0; j < n - 1; j++) {\n"
            "    if (a[j] < pivot) {\n"
            "        swap(a[i], a[j]);\n"
            "        i++;\n"
            "    }\n"
            "}\n"
            "swap(a[i], a[n - 1]);\n"
            "for (int k = 0; k < n; k++) {\n"
            '    cout << (k ? " " : "") << a[k];\n'
            "}\n"
            'cout << "\\n";'
        ),
        "java": (
            f"int[] a = {{{a}}};\n"
            "int n = a.length;\n"
            "int pivot = a[n - 1];\n"
            "int i = 0;  // a[0..i) holds the values smaller than the pivot\n"
            "for (int j = 0; j < n - 1; j++) {\n"
            "    if (a[j] < pivot) {\n"
            "        int s = a[i]; a[i] = a[j]; a[j] = s;\n"
            "        i++;\n"
            "    }\n"
            "}\n"
            "int t = a[i]; a[i] = a[n - 1]; a[n - 1] = t;\n"
            "StringBuilder out = new StringBuilder();\n"
            "for (int k = 0; k < n; k++) {\n"
            '    out.append(k > 0 ? " " : "").append(a[k]);\n'
            "}\n"
            "System.out.println(out);"
        ),
    }


def show(a: list) -> str:
    return " ".join(map(str, a))


def lomuto(a: list) -> str:
    """The specification, step by step: scan, swap smaller values forward, then the pivot."""
    a = list(a)
    pivot, i = a[-1], 0
    for j in range(len(a) - 1):
        if a[j] < pivot:
            a[i], a[j] = a[j], a[i]
            i += 1
    a[i], a[-1] = a[-1], a[i]
    return show(a)


def wrong(v):
    a = v["a"]
    pivot = a[-1]
    small = [x for x in a[:-1] if x < pivot]
    big = [x for x in a[:-1] if x > pivot]
    return [
        (show(sorted(a)), "sort-pass-equals-sorted"),
        (show(small + [pivot] + big), "partition-assumed-stable"),
        (show([pivot] + a[:-1]), "partition-pivot-to-front"),
        (show(small + [pivot] + sorted(big)), "sort-pass-equals-sorted"),
    ]


def sample(rng, params):
    n = rng.randint(*params["n"])
    a = rng.sample(range(params["value"][0], params["value"][1] + 1), n)
    return {"a": a}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: lomuto(v["a"]),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        "This code should partition the array around its last element (Lomuto). "
        "Which line goes in the blank?"
    ),
    fix=lambda v: "",
    explain=lambda v, answer: (
        f"Pivot {v['a'][-1]}. Each value smaller than the pivot is swapped to position i, which "
        "can throw a larger value further right, so the larger side does not keep its order. "
        f"Finally the pivot swaps into position i: {answer}."
    ),
    blanks=[
        Blank(
            TEST,
            [
                (lines("if a[j] > pivot:", "if (a[j] > pivot) {"), "sort-wrong-direction"),
                (lines("if a[i] < pivot:", "if (a[i] < pivot) {"), "confuse-index-value"),
                (lines("if j < pivot:", "if (j < pivot) {"), "confuse-index-value"),
            ],
        ),
    ],
    bands=(5, 5, 6),
)
HELPERS = {"lomuto": lomuto}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
