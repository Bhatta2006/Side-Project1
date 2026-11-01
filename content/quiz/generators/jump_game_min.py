"""Fewest jumps to reach the last index (Jump Game II), greedy by reach windows.

Wrong answers take the longest jump from wherever you stand (a greedy that fails), step
one index at a time, or count one window too many.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, lines

BOUNDARY = lines("if i == end:", "if (i == end) {")
REACH = lines("far = max(far, i + nums[i])", "far = max(far, i + nums[i]);",
              "far = Math.max(far, i + nums[i]);")


def program(v: dict) -> dict[str, str]:
    nums = ", ".join(map(str, v["nums"]))
    return {
        "python": (
            f"nums = [{nums}]  # nums[i] = longest jump from index i\n"
            "jumps = 0\n"
            "end = 0\n"
            "far = 0\n"
            "for i in range(len(nums) - 1):\n"
            "    far = max(far, i + nums[i])\n"
            "    if i == end:\n"
            "        jumps += 1\n"
            "        end = far\n"
            "print(jumps)"
        ),
        "cpp": (
            f"vector<int> nums = {{{nums}}};  // longest jump from each index\n"
            "int jumps = 0;\n"
            "int end = 0;\n"
            "int far = 0;\n"
            "for (int i = 0; i < (int)nums.size() - 1; i++) {\n"
            "    far = max(far, i + nums[i]);\n"
            "    if (i == end) {\n"
            "        jumps++;\n"
            "        end = far;\n"
            "    }\n"
            "}\n"
            'cout << jumps << "\\n";'
        ),
        "java": (
            f"int[] nums = {{{nums}}};  // longest jump from each index\n"
            "int jumps = 0;\n"
            "int end = 0;\n"
            "int far = 0;\n"
            "for (int i = 0; i < nums.length - 1; i++) {\n"
            "    far = Math.max(far, i + nums[i]);\n"
            "    if (i == end) {\n"
            "        jumps++;\n"
            "        end = far;\n"
            "    }\n"
            "}\n"
            "System.out.println(jumps);"
        ),
    }


def fewest(nums: list) -> int:
    """Independent check: dynamic programming over every index."""
    n = len(nums)
    best = [0] + [10**9] * (n - 1)
    for i in range(n):
        for j in range(i + 1, min(n, i + nums[i] + 1)):
            best[j] = min(best[j], best[i] + 1)
    return best[-1]


def longest_each_time(nums: list) -> int:
    i, jumps = 0, 0
    while i < len(nums) - 1:
        i += max(1, nums[i])
        jumps += 1
    return jumps


def wrong(v):
    nums = v["nums"]
    right = fewest(nums)
    return [
        (str(longest_each_time(nums)), "greedy-max-step"),
        (str(len(nums) - 1), "greedy-one-step"),
        (str(right + 1), "off-by-one-output"),
        (str(right - 1), "off-by-one-output"),
    ]


def sample(rng, params):
    n = rng.randint(*params["n"])
    return {"nums": [rng.randint(1, params["jump"][0]) for _ in range(n)]}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(fewest(v["nums"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        "This code should print the fewest jumps from index 0 to the last index. "
        "Which line goes in the blank?"
    ),
    fix=lambda v: "",
    explain=lambda v, answer: (
        "Think in windows: every index reachable with j jumps forms a window, and the next "
        "window reaches as far as any index inside it can jump. A jump is counted each time the "
        f"scan leaves a window, giving {answer}. Taking the longest jump from where you stand "
        "can land on an index that jumps poorly."
    ),
    blanks=[
        Blank(
            BOUNDARY,
            [
                (lines("if i == far:", "if (i == far) {"), "greedy-window-confusion"),
                (lines("if i < end:", "if (i < end) {"), "greedy-window-confusion"),
                (lines("if nums[i] == end:", "if (nums[i] == end) {"), "confuse-index-value"),
            ],
        ),
        Blank(
            REACH,
            [
                (lines("far = max(far, nums[i])", "far = max(far, nums[i]);",
                       "far = Math.max(far, nums[i]);"), "confuse-index-value"),
                (lines("far = i + nums[i]", "far = i + nums[i];"), "overwrite-best"),
                (lines("far = max(far, i + 1)", "far = max(far, i + 1);",
                       "far = Math.max(far, i + 1);"), "greedy-one-step"),
            ],
        ),
    ],
    bands=(4, 4, 5),
)
HELPERS = {"fewest": fewest}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
