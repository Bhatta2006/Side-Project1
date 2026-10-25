"""Split an array into at most k contiguous parts, minimising the largest part sum.

Binary search on the cap: lo = max(a) (a part holds at least one element), hi = sum(a); a
cap is feasible when greedy filling needs at most k parts. Wrong answers are the classic
slips: the average as the answer, the largest element as the answer, greedy cutting near
the average, a search that starts below max(a), and a strict parts < k check.
"""

from itertools import combinations

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

LO = lines("lo = max(a)", "int lo = *max_element(a.begin(), a.end());",
           "int lo = Arrays.stream(a).max().getAsInt();")
HI = lines("hi = sum(a)", "int hi = accumulate(a.begin(), a.end(), 0);", "int hi = Arrays.stream(a).sum();")
PARTS = lines("parts = 1", "int parts = 1;")
CUT = lines("if run + x > mid:", "if (run + x > mid) {")
CHECK = lines("if parts <= k:", "if (parts <= k) {")
KEEP = lines("hi = mid", "hi = mid;")
OUTPUT = lines("print(lo)", 'cout << lo << "\\n";', "System.out.println(lo);")


def arr(xs):
    return ", ".join(map(str, xs))


def program(v: dict) -> dict[str, str]:
    a, k = arr(v["a"]), v["k"]
    return {
        "python": (
            f"a = [{a}]\nk = {k}\n"
            "lo = max(a)\n"
            "hi = sum(a)\n"
            "while lo < hi:\n"
            "    mid = (lo + hi) // 2\n"
            "    parts = 1\n"
            "    run = 0\n"
            "    for x in a:\n"
            "        if run + x > mid:\n"
            "            parts += 1\n"
            "            run = 0\n"
            "        run += x\n"
            "    if parts <= k:\n"
            "        hi = mid\n"
            "    else:\n"
            "        lo = mid + 1\n"
            "print(lo)"
        ),
        "cpp": (
            f"vector<int> a = {{{a}}};\nint k = {k};\n"
            "int lo = *max_element(a.begin(), a.end());\n"
            "int hi = accumulate(a.begin(), a.end(), 0);\n"
            "while (lo < hi) {\n"
            "    int mid = (lo + hi) / 2;\n"
            "    int parts = 1;\n"
            "    int run = 0;\n"
            "    for (int x : a) {\n"
            "        if (run + x > mid) {\n"
            "            parts += 1;\n"
            "            run = 0;\n"
            "        }\n"
            "        run += x;\n"
            "    }\n"
            "    if (parts <= k) {\n"
            "        hi = mid;\n"
            "    } else {\n"
            "        lo = mid + 1;\n"
            "    }\n"
            "}\n"
            'cout << lo << "\\n";'
        ),
        "java": (
            f"int[] a = {{{a}}};\nint k = {k};\n"
            "int lo = Arrays.stream(a).max().getAsInt();\n"
            "int hi = Arrays.stream(a).sum();\n"
            "while (lo < hi) {\n"
            "    int mid = (lo + hi) / 2;\n"
            "    int parts = 1;\n"
            "    int run = 0;\n"
            "    for (int x : a) {\n"
            "        if (run + x > mid) {\n"
            "            parts += 1;\n"
            "            run = 0;\n"
            "        }\n"
            "        run += x;\n"
            "    }\n"
            "    if (parts <= k) {\n"
            "        hi = mid;\n"
            "    } else {\n"
            "        lo = mid + 1;\n"
            "    }\n"
            "}\n"
            "System.out.println(lo);"
        ),
    }


def split_brute(a, k):
    """Independent check: every way to place at most k - 1 cuts."""
    n, best = len(a), sum(a)
    for parts in range(1, min(k, n) + 1):
        for cuts in combinations(range(1, n), parts - 1):
            b = [0, *cuts, n]
            best = min(best, max(sum(a[b[i]:b[i + 1]]) for i in range(parts)))
    return best


def search(a, k, lo, strict):
    hi = sum(a)
    while lo < hi:
        mid = (lo + hi) // 2
        parts, run = 1, 0
        for x in a:
            if run + x > mid:
                parts, run = parts + 1, 0
            run += x
        if (parts < k) if strict else (parts <= k):
            hi = mid
        else:
            lo = mid + 1
    return lo


def average_greedy(a, k):
    target, parts, run = -(-sum(a) // k), [], 0
    for x in a:
        if run + x > target and len(parts) < k - 1:
            parts.append(run)
            run = 0
        run += x
    return max(parts + [run])


def wrong(v):
    a, k = v["a"], v["k"]
    return [
        (str(-(-sum(a) // k)), "predicate-average-shortcut"),
        (str(average_greedy(a, k)), "split-average-greedy"),
        (str(search(a, k, 1, False)), "search-range-confusion"),
        (str(max(a)), "split-lower-bound-answer"),
        (str(search(a, k, max(a), True)), "predicate-boundary"),
    ]


def sample(rng, params):
    n = rng.randint(*params["length"])
    return {"a": [rng.randint(*params["value"]) for _ in range(n)], "k": rng.randint(*params["parts"])}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(split_brute(v["a"], v["k"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should split a into at most {v['k']} contiguous parts and print the smallest "
        "possible largest part sum. Which line goes in the blank?"
    ),
    fix=lambda v: (
        f"This code should split a into at most {v['k']} contiguous parts and print the smallest "
        "possible largest part sum, but it prints the wrong answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        "A cap works when greedy filling needs at most k parts, and every larger cap works too, so "
        "binary search finds the smallest cap that works. It starts at the largest element, since "
        f"every element sits in some part. The smallest largest part is {answer}."
    ),
    blanks=[
        Blank(
            LO,
            [
                (lines("lo = 1", "int lo = 1;"), "search-range-confusion"),
                (lines("lo = min(a)", "int lo = *min_element(a.begin(), a.end());",
                       "int lo = Arrays.stream(a).min().getAsInt();"), "search-range-confusion"),
                (lines("lo = sum(a) // k", "int lo = accumulate(a.begin(), a.end(), 0) / k;",
                       "int lo = Arrays.stream(a).sum() / k;"), "predicate-average-shortcut"),
            ],
        ),
        Blank(
            CHECK,
            [
                (lines("if parts < k:", "if (parts < k) {"), "predicate-boundary"),
                (lines("if parts >= k:", "if (parts >= k) {"), "predicate-inverted"),
                (lines("if parts > k:", "if (parts > k) {"), "predicate-inverted"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "split-low-start",
            edit(LO, lines("lo = 1", "int lo = 1;")),
            "Start the search at the largest element: lo = max(a)",
            "Below the largest element a part would have to hold more than the cap, and the greedy "
            "count does not notice.",
        ),
        Fix(
            "split-strict-parts",
            edit(CHECK, lines("if parts < k:", "if (parts < k) {")),
            "Accept the cap when it needs at most k parts: parts <= k",
            "Exactly k parts is allowed, so a cap that needs k parts works.",
        ),
        Fix(
            "bs-skip-mid",
            edit(KEEP, lines("hi = mid - 1", "hi = mid - 1;")),
            "Keep mid when it works: hi = mid",
            "mid itself may be the smallest cap that works.",
        ),
    ],
    decoys=[
        Decoy(edit(OUTPUT, lines("print(lo + 1)", 'cout << lo + 1 << "\\n";', "System.out.println(lo + 1);")),
              "Print lo + 1", "off-by-one-output"),
        Decoy(edit(OUTPUT, lines("print(lo - 1)", 'cout << lo - 1 << "\\n";', "System.out.println(lo - 1);")),
              "Print lo - 1", "off-by-one-output"),
        Decoy(edit(CUT, lines("if run + x >= mid:", "if (run + x >= mid) {")),
              "Cut when the part would reach the cap: >=", "predicate-boundary"),
        Decoy(edit(OUTPUT, lines("print(hi + 1)", 'cout << hi + 1 << "\\n";', "System.out.println(hi + 1);")),
              "Print hi + 1", "lo-hi-confusion"),
        Decoy(edit(PARTS, lines("parts = 0", "int parts = 0;")),
              "Start the part count at 0", "accumulator-init-one"),
        Decoy(edit(HI, lines("hi = sum(a) - 1", "int hi = accumulate(a.begin(), a.end(), 0) - 1;",
                             "int hi = Arrays.stream(a).sum() - 1;")),
              "End the search one below the total", "search-range-confusion"),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"split_brute": split_brute}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
