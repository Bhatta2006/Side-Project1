"""Longest subarray with sum k: a hash map from each prefix sum to its FIRST index.

Wrong answers are the classic slips: a shrinking window (breaks with negatives), storing the
last index instead of the first, forgetting the empty prefix at index -1, a length that is
one too long, and counting the subarrays instead of measuring the longest.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

SEED = lines("first = {0: -1}", "unordered_map<int, int> first = {{0, -1}};",
             "Map<Integer, Integer> first = new HashMap<>(Map.of(0, -1));")
LENGTH = lines("best = max(best, i - first[total - k])",
               "if (first.count(total - k)) best = max(best, i - first[total - k]);",
               "if (first.containsKey(total - k)) best = Math.max(best, i - first.get(total - k));")
KEEP = lines("first.setdefault(total, i)", "first.insert({total, i});", "first.putIfAbsent(total, i);")
ADD = lines("total += a[i]", "total += a[i];")
OUTPUT = lines("print(best)", 'cout << best << "\\n";', "System.out.println(best);")


def arr(xs):
    return ", ".join(map(str, xs))


def program(v: dict) -> dict[str, str]:
    a, k = arr(v["a"]), v["k"]
    return {
        "python": (
            f"a = [{a}]\nk = {k}\n"
            "first = {0: -1}\n"
            "total = 0\n"
            "best = 0\n"
            "for i in range(len(a)):\n"
            "    total += a[i]\n"
            "    if total - k in first:\n"
            "        best = max(best, i - first[total - k])\n"
            "    first.setdefault(total, i)\n"
            "print(best)"
        ),
        "cpp": (
            f"vector<int> a = {{{a}}};\nint k = {k};\n"
            "unordered_map<int, int> first = {{0, -1}};\n"
            "int total = 0;\n"
            "int best = 0;\n"
            "for (int i = 0; i < (int)a.size(); i++) {\n"
            "    total += a[i];\n"
            "    if (first.count(total - k)) best = max(best, i - first[total - k]);\n"
            "    first.insert({total, i});\n"
            "}\n"
            'cout << best << "\\n";'
        ),
        "java": (
            f"int[] a = {{{a}}};\nint k = {k};\n"
            "Map<Integer, Integer> first = new HashMap<>(Map.of(0, -1));\n"
            "int total = 0;\n"
            "int best = 0;\n"
            "for (int i = 0; i < a.length; i++) {\n"
            "    total += a[i];\n"
            "    if (first.containsKey(total - k)) best = Math.max(best, i - first.get(total - k));\n"
            "    first.putIfAbsent(total, i);\n"
            "}\n"
            "System.out.println(best);"
        ),
    }


def longest_brute(a, k):
    """Independent check: every subarray."""
    best = 0
    for lo in range(len(a)):
        for hi in range(lo, len(a)):
            if sum(a[lo:hi + 1]) == k:
                best = max(best, hi - lo + 1)
    return best


def count_brute(a, k):
    return sum(1 for lo in range(len(a)) for hi in range(lo, len(a)) if sum(a[lo:hi + 1]) == k)


def window(a, k):
    """Shrink while the sum is too big: only right for non-negative numbers."""
    best, total, lo = 0, 0, 0
    for hi, x in enumerate(a):
        total += x
        while total > k and lo <= hi:
            total -= a[lo]
            lo += 1
        if total == k:
            best = max(best, hi - lo + 1)
    return best


def with_map(a, k, seed, keep_first, plus):
    first = {0: seed} if seed is not None else {}
    total = best = 0
    for i, x in enumerate(a):
        total += x
        if total - k in first:
            best = max(best, i - first[total - k] + plus)
        if keep_first:
            first.setdefault(total, i)
        else:
            first[total] = i
    return best


def wrong(v):
    a, k = v["a"], v["k"]
    return [
        (str(window(a, k)), "window-with-negatives"),
        (str(with_map(a, k, -1, False, 0)), "prefix-store-last-index"),
        (str(with_map(a, k, None, True, 0)), "prefix-missing-empty"),
        (str(with_map(a, k, -1, True, 1)), "window-length-off-by-one"),
        (str(count_brute(a, k)), "prefix-count-vs-longest"),
    ]


def sample(rng, params):
    n = rng.randint(*params["length"])
    return {"a": [rng.randint(*params["value"]) for _ in range(n)], "k": rng.randint(*params["k"])}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(longest_brute(v["a"], v["k"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should print the length of the longest subarray of a whose sum is {v['k']} "
        "(0 if there is none). Which line goes in the blank?"
    ),
    fix=lambda v: (
        f"This code should print the length of the longest subarray of a whose sum is {v['k']} "
        "(0 if there is none), but it prints the wrong answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        "A subarray ending at i sums to k when an earlier prefix sum equals total - k. Keeping the "
        "first index of each prefix sum makes that subarray as long as possible, and the empty "
        f"prefix sits at index -1. The longest has length {answer}."
    ),
    blanks=[
        Blank(
            KEEP,
            [
                (lines("first[total] = i", "first[total] = i;", "first.put(total, i);"), "prefix-store-last-index"),
                (lines("first[total - k] = i", "first[total - k] = i;", "first.put(total - k, i);"),
                 "confuse-index-value"),
                (lines("first[i] = total", "first[i] = total;", "first.put(i, total);"), "confuse-index-value"),
            ],
        ),
        Blank(
            LENGTH,
            [
                (lines("best = max(best, i - first[total - k] + 1)",
                       "if (first.count(total - k)) best = max(best, i - first[total - k] + 1);",
                       "if (first.containsKey(total - k)) best = Math.max(best, i - first.get(total - k) + 1);"),
                 "window-length-off-by-one"),
                (lines("best = i - first[total - k]",
                       "if (first.count(total - k)) best = i - first[total - k];",
                       "if (first.containsKey(total - k)) best = i - first.get(total - k);"),
                 "overwrite-best"),
                (lines("best = max(best, first[total - k])",
                       "if (first.count(total - k)) best = max(best, first[total - k]);",
                       "if (first.containsKey(total - k)) best = Math.max(best, first.get(total - k));"),
                 "confuse-index-value"),
            ],
        ),
        Blank(
            ADD,
            [
                (lines("total = a[i]", "total = a[i];"), "overwrite-not-accumulate"),
                (lines("total += i", "total += i;"), "confuse-index-value"),
                (lines("total += 1", "total += 1;"), "count-not-sum"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "prefix-store-last-index",
            edit(KEEP, lines("first[total] = i", "first[total] = i;", "first.put(total, i);")),
            "Keep the first index of each prefix sum: only store it if it is new",
            "Overwriting with a later index makes every subarray found from it shorter.",
        ),
        Fix(
            "prefix-missing-empty",
            edit(SEED, lines("first = {}", "unordered_map<int, int> first;",
                             "Map<Integer, Integer> first = new HashMap<>();")),
            "Start the map with the empty prefix: sum 0 at index -1",
            "Without it, no subarray that starts at index 0 is ever found.",
        ),
        Fix(
            "prefix-seed-index-zero",
            edit(SEED, lines("first = {0: 0}", "unordered_map<int, int> first = {{0, 0}};",
                             "Map<Integer, Integer> first = new HashMap<>(Map.of(0, 0));")),
            "The empty prefix ends before index 0: store it at -1, not 0",
            "Index 0 makes every subarray that starts at the front one element too short.",
        ),
    ],
    decoys=[
        Decoy(edit(OUTPUT, lines("print(best + 1)", 'cout << best + 1 << "\\n";', "System.out.println(best + 1);")),
              "Print best + 1", "window-length-off-by-one"),
        Decoy(edit(OUTPUT, lines("print(best - 1)", 'cout << best - 1 << "\\n";', "System.out.println(best - 1);")),
              "Print best - 1", "off-by-one-output"),
        Decoy(edit(ADD, lines("total += abs(a[i])", "total += abs(a[i]);", "total += Math.abs(a[i]);")),
              "Add the absolute value of each number", "window-with-negatives"),
        Decoy(edit(OUTPUT, lines("print(len(first))", 'cout << first.size() << "\\n";',
                                 "System.out.println(first.size());")),
              "Print the number of distinct prefix sums", "prefix-count-vs-longest"),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"longest_brute": longest_brute}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
