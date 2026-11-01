"""Backtracking with duplicates (Combination Sum II), using an explicit stack.

Each number may be used once, the input has repeats, and combinations that differ only in
which copy was used count once. Wrong answers count copies separately, allow reuse, or count
orderings.
"""

from itertools import combinations

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, lines

SKIP = lines("if i > start and nums[i] == nums[i - 1]:",
             "if (i > start && nums[i] == nums[i - 1]) continue;")
PUSH = lines("stack.append((i + 1, rem - nums[i]))", "st.push_back({i + 1, rem - nums[i]});",
             "st.push(new int[]{i + 1, rem - nums[i]});")


def program(v: dict) -> dict[str, str]:
    nums, target = ", ".join(map(str, v["nums"])), v["target"]
    return {
        "python": (
            f"nums = [{nums}]  # sorted\ntarget = {target}\n"
            "count = 0\n"
            "stack = [(0, target)]  # (first index allowed, amount still needed)\n"
            "while stack:\n"
            "    start, rem = stack.pop()\n"
            "    if rem == 0:\n"
            "        count += 1\n"
            "        continue\n"
            "    for i in range(start, len(nums)):\n"
            "        if i > start and nums[i] == nums[i - 1]:\n"
            "            continue\n"
            "        if nums[i] > rem:\n"
            "            break\n"
            "        stack.append((i + 1, rem - nums[i]))\n"
            "print(count)"
        ),
        "cpp": (
            f"vector<int> nums = {{{nums}}};  // sorted\nint target = {target};\n"
            "int count = 0;\n"
            "vector<pair<int, int>> st = {{0, target}};  // (first index allowed, amount needed)\n"
            "while (!st.empty()) {\n"
            "    int start = st.back().first, rem = st.back().second;\n"
            "    st.pop_back();\n"
            "    if (rem == 0) {\n"
            "        count++;\n"
            "        continue;\n"
            "    }\n"
            "    for (int i = start; i < (int)nums.size(); i++) {\n"
            "        if (i > start && nums[i] == nums[i - 1]) continue;\n"
            "        if (nums[i] > rem) break;\n"
            "        st.push_back({i + 1, rem - nums[i]});\n"
            "    }\n"
            "}\n"
            'cout << count << "\\n";'
        ),
        "java": (
            f"int[] nums = {{{nums}}};  // sorted\nint target = {target};\n"
            "int count = 0;\n"
            "ArrayDeque<int[]> st = new ArrayDeque<>();  // (first index allowed, amount needed)\n"
            "st.push(new int[]{0, target});\n"
            "while (!st.isEmpty()) {\n"
            "    int[] top = st.pop();\n"
            "    int start = top[0], rem = top[1];\n"
            "    if (rem == 0) {\n"
            "        count++;\n"
            "        continue;\n"
            "    }\n"
            "    for (int i = start; i < nums.length; i++) {\n"
            "        if (i > start && nums[i] == nums[i - 1]) continue;\n"
            "        if (nums[i] > rem) break;\n"
            "        st.push(new int[]{i + 1, rem - nums[i]});\n"
            "    }\n"
            "}\n"
            "System.out.println(count);"
        ),
    }


def distinct_combos(nums: list, target: int) -> int:
    """Independent check: every index subset, deduplicated as a sorted tuple of values."""
    found = set()
    for k in range(1, len(nums) + 1):
        for pick in combinations(nums, k):
            if sum(pick) == target:
                found.add(tuple(sorted(pick)))
    return len(found)


def index_combos(nums, target) -> int:
    return sum(
        1 for k in range(1, len(nums) + 1) for pick in combinations(nums, k) if sum(pick) == target
    )


def with_reuse(nums, target) -> int:
    values = sorted(set(nums))
    ways = [1] + [0] * target
    for x in values:
        for s in range(x, target + 1):
            ways[s] += ways[s - x]
    return ways[target]


def wrong(v):
    nums, target = v["nums"], v["target"]
    return [
        (str(index_combos(nums, target)), "backtrack-duplicate-combos"),
        (str(with_reuse(nums, target)), "backtrack-reuse-element"),
        (str(distinct_combos(nums, target) + 1), "off-by-one-output"),
        (str(max(0, distinct_combos(nums, target) - 1)), "off-by-one-output"),
    ]


def sample(rng, params):
    n = rng.randint(*params["n"])
    nums = sorted(rng.randint(1, params["value"][0]) for _ in range(n))
    return {"nums": nums, "target": rng.randint(*params["target"])}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(distinct_combos(v["nums"], v["target"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should count the different combinations of the numbers (each used at most "
        f"once) that add up to {v['target']}, counting equal combinations once. "
        "Which line goes in the blank?"
    ),
    fix=lambda v: "",
    explain=lambda v, answer: (
        "With the input sorted, a level of the search may start a combination with a given value "
        "only once: later copies at the same level would rebuild the same combinations. Deeper "
        f"levels may still use the next copy. That gives {answer} distinct combinations."
    ),
    blanks=[
        Blank(
            SKIP,
            [
                (lines("if i > 0 and nums[i] == nums[i - 1]:",
                       "if (i > 0 && nums[i] == nums[i - 1]) continue;"), "backtrack-skip-all-duplicates"),
                (lines("if i > start and nums[i] != nums[i - 1]:",
                       "if (i > start && nums[i] != nums[i - 1]) continue;"), "filter-inverted"),
                (lines("if i > start + 1 and nums[i] == nums[i - 1]:",
                       "if (i > start + 1 && nums[i] == nums[i - 1]) continue;"), "loop-bound-off-by-one"),
            ],
        ),
        Blank(
            PUSH,
            [
                (lines("stack.append((i, rem - nums[i]))", "st.push_back({i, rem - nums[i]});",
                       "st.push(new int[]{i, rem - nums[i]});"), "backtrack-reuse-element"),
                (lines("stack.append((start + 1, rem - nums[i]))", "st.push_back({start + 1, rem - nums[i]});",
                       "st.push(new int[]{start + 1, rem - nums[i]});"), "confuse-index-value"),
                (lines("stack.append((i + 1, rem))", "st.push_back({i + 1, rem});",
                       "st.push(new int[]{i + 1, rem});"), "pnp-take-without-element"),
            ],
        ),
    ],
    bands=(5, 5, 6),
)
HELPERS = {"distinct_combos": distinct_combos}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
