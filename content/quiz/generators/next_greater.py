"""Next greater element to the right with a monotonic stack of waiting indexes.

Wrong answers are the classic slips: the maximum to the right instead of the nearest greater,
popping on <= (equal values answer each other), the wrong direction (next smaller), and
recording the index instead of the value.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

INIT = lines("res = [-1] * n", "vector<int> res(n, -1);", "int[] res = new int[n]; java.util.Arrays.fill(res, -1);")
LOOP = lines("for i in range(n):", "for (int i = 0; i < n; i++) {")
COMPARE = lines("while stack and a[stack[-1]] < a[i]:", "while (!st.empty() && a[st.back()] < a[i]) {",
                "while (!st.isEmpty() && a[st.peek()] < a[i]) {")
RESULT = lines("res[stack.pop()] = a[i]", "res[st.back()] = a[i];", "res[st.pop()] = a[i];")


def program(v: dict) -> dict[str, str]:
    a = ", ".join(map(str, v["a"]))
    return {
        "python": (
            f"a = [{a}]\n"
            "n = len(a)\n"
            "res = [-1] * n\n"
            "stack = []\n"
            "for i in range(n):\n"
            "    while stack and a[stack[-1]] < a[i]:\n"
            "        res[stack.pop()] = a[i]\n"
            "    stack.append(i)\n"
            "print(*res)"
        ),
        "cpp": (
            f"vector<int> a = {{{a}}};\n"
            "int n = a.size();\n"
            "vector<int> res(n, -1);\n"
            "vector<int> st;\n"
            "for (int i = 0; i < n; i++) {\n"
            "    while (!st.empty() && a[st.back()] < a[i]) {\n"
            "        res[st.back()] = a[i];\n"
            "        st.pop_back();\n"
            "    }\n"
            "    st.push_back(i);\n"
            "}\n"
            'for (int i = 0; i < n; i++) cout << res[i] << (i + 1 < n ? " " : "\\n");'
        ),
        "java": (
            f"int[] a = {{{a}}};\n"
            "int n = a.length;\n"
            "int[] res = new int[n]; java.util.Arrays.fill(res, -1);\n"
            "java.util.ArrayDeque<Integer> st = new java.util.ArrayDeque<>();\n"
            "for (int i = 0; i < n; i++) {\n"
            "    while (!st.isEmpty() && a[st.peek()] < a[i]) {\n"
            "        res[st.pop()] = a[i];\n"
            "    }\n"
            "    st.push(i);\n"
            "}\n"
            "StringBuilder out = new StringBuilder();\n"
            'for (int i = 0; i < n; i++) out.append(res[i]).append(i + 1 < n ? " " : "");\n'
            "System.out.println(out);"
        ),
    }


def scan(a, better):
    """Independent check: for each i, the first later value that is `better`."""
    out = []
    for i, x in enumerate(a):
        out.append(next((y for y in a[i + 1:] if better(y, x)), -1))
    return " ".join(map(str, out))


def next_greater_ref(a):
    return scan(a, lambda y, x: y > x)


def max_right(a):
    out, best = [], -1
    for x in reversed(a):
        out.append(best if best > x else -1)
        best = max(best, x)
    return " ".join(map(str, reversed(out)))


def first_index(a):
    out = []
    for i, x in enumerate(a):
        out.append(next((j for j in range(i + 1, len(a)) if a[j] > x), -1))
    return " ".join(map(str, out))


def wrong(v):
    a = v["a"]
    return [
        (max_right(a), "mono-max-to-the-right"),
        (scan(a, lambda y, x: y >= x), "mono-strictness"),
        (scan(a, lambda y, x: y < x), "mono-wrong-direction"),
        (first_index(a), "confuse-index-value"),
        (" ".join(str(a[i + 1] if i + 1 < len(a) and a[i + 1] > a[i] else -1) for i in range(len(a))),
         "mono-neighbour-only"),
    ]


def sample(rng, params):
    return {"a": [rng.randint(*params["value"]) for _ in range(rng.randint(*params["length"]))]}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: next_greater_ref(v["a"]),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        "For every element, this code should print the first strictly greater value to its right, "
        "or -1. Which line goes in the blank?"
    ),
    fix=lambda v: (
        "For every element, this code should print the first strictly greater value to its right, "
        "or -1, but it prints the wrong answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        "The stack holds indexes still waiting for an answer, with values decreasing upwards. When a[i] "
        f"is bigger than the top, it is the top's answer, so pop and record it. The result is {answer}."
    ),
    blanks=[
        Blank(
            COMPARE,
            [
                (lines("while stack and a[stack[-1]] <= a[i]:", "while (!st.empty() && a[st.back()] <= a[i]) {",
                       "while (!st.isEmpty() && a[st.peek()] <= a[i]) {"), "mono-strictness"),
                (lines("while stack and a[stack[-1]] > a[i]:", "while (!st.empty() && a[st.back()] > a[i]) {",
                       "while (!st.isEmpty() && a[st.peek()] > a[i]) {"), "mono-wrong-direction"),
                (lines("while stack and a[stack[0]] < a[i]:", "while (!st.empty() && a[st.front()] < a[i]) {",
                       "while (!st.isEmpty() && a[st.peekLast()] < a[i]) {"), "mono-top-vs-bottom"),
            ],
        ),
        Blank(
            RESULT,
            [
                (lines("res[stack.pop()] = i", "res[st.back()] = i;", "res[st.pop()] = i;"), "confuse-index-value"),
                (lines("res[stack.pop()] = a[i - 1]", "res[st.back()] = a[i - 1];", "res[st.pop()] = a[i - 1];"),
                 "off-by-one-output"),
                (lines("res[i] = a[stack.pop()]", "res[i] = a[st.back()];", "res[i] = a[st.pop()];"),
                 "mono-answer-wrong-element"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "mono-non-strict-pop",
            edit(COMPARE, lines("while stack and a[stack[-1]] <= a[i]:", "while (!st.empty() && a[st.back()] <= a[i]) {",
                                "while (!st.isEmpty() && a[st.peek()] <= a[i]) {")),
            "Pop only while the top is strictly smaller: a[top] < a[i]",
            "With <=, an equal value is recorded as the next greater one.",
        ),
        Fix(
            "mono-wrong-direction",
            edit(COMPARE, lines("while stack and a[stack[-1]] > a[i]:", "while (!st.empty() && a[st.back()] > a[i]) {",
                                "while (!st.isEmpty() && a[st.peek()] > a[i]) {")),
            "Pop while the top is smaller than a[i], not larger",
            "Popping larger values finds the next smaller element instead.",
        ),
        Fix(
            "mono-stores-index",
            edit(RESULT, lines("res[stack.pop()] = i", "res[st.back()] = i;", "res[st.pop()] = i;")),
            "Record the value a[i], not the index i",
            "The question asks for the next greater value.",
        ),
    ],
    decoys=[
        Decoy(edit(INIT, lines("res = [0] * n", "vector<int> res(n, 0);", "int[] res = new int[n];")),
              "Start every answer at 0", "dp-wrong-base-case"),
        Decoy(edit(LOOP, lines("for i in range(1, n):", "for (int i = 1; i < n; i++) {")),
              "Start the scan at index 1", "skip-first-element"),
        Decoy(edit(COMPARE, lines("while stack and a[stack[-1]] < a[i] - 1:", "while (!st.empty() && a[st.back()] < a[i] - 1) {",
                                  "while (!st.isEmpty() && a[st.peek()] < a[i] - 1) {")),
              "Pop only when a[i] is at least 2 bigger", "off-by-one-output"),
        Decoy(edit(RESULT, lines("res[stack.pop()] = a[i] + 1", "res[st.back()] = a[i] + 1;", "res[st.pop()] = a[i] + 1;")),
              "Record a[i] + 1", "dp-missing-plus-one"),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"next_greater_ref": next_greater_ref}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
