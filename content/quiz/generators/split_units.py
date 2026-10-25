"""Split a number of seconds into hours, minutes and seconds with whole-number division and %.

Wrong answers are the classic slips: minutes taken from the whole total instead of what is
left after the hours, division and remainder swapped, and the wrong divisor for the seconds.
Every value is non-negative, so Python's // and C++/Java's / agree.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

H = lines("h = t // 3600", "int h = t / 3600;")
M = lines("m = t % 3600 // 60", "int m = t % 3600 / 60;")
S = lines("s = t % 60", "int s = t % 60;")
OUTPUT = lines("print(h, m, s)", 'cout << h << " " << m << " " << s << "\\n";',
               'System.out.println(h + " " + m + " " + s);')


def program(v: dict) -> dict[str, str]:
    t = v["t"]
    return {
        "python": f"t = {t}\nh = t // 3600\nm = t % 3600 // 60\ns = t % 60\nprint(h, m, s)",
        "cpp": (f"int t = {t};\nint h = t / 3600;\nint m = t % 3600 / 60;\nint s = t % 60;\n"
                'cout << h << " " << m << " " << s << "\\n";'),
        "java": (f"int t = {t};\nint h = t / 3600;\nint m = t % 3600 / 60;\nint s = t % 60;\n"
                 'System.out.println(h + " " + m + " " + s);'),
    }


def split(t):
    """Independent check: count whole hours and minutes by repeated subtraction."""
    h = m = 0
    while t >= 3600:
        t, h = t - 3600, h + 1
    while t >= 60:
        t, m = t - 60, m + 1
    return f"{h} {m} {t}"


def wrong(v):
    t = v["t"]
    return [
        (f"{t // 3600} {t // 60} {t % 60}", "mod-chain-missing"),
        (f"{t % 3600} {t % 3600 // 60} {t % 60}", "mod-swap-div"),
        (f"{t // 3600} {t % 3600 // 60} {t % 3600}", "mod-wrong-divisor"),
        (f"{t // 3600} {t // 60} {t}", "mod-chain-missing"),
    ]


def sample(rng, params):
    return {"t": rng.randint(*params["seconds"])}


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: split(v["t"]),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"t = {v['t']} seconds. This code should print the hours, minutes and seconds in it, such as "
        "3725 → 1 2 5. Which line goes in the blank?"
    ),
    fix=lambda v: (
        f"t = {v['t']} seconds. This code should print the hours, minutes and seconds in it, such as "
        "3725 → 1 2 5, but it prints the wrong answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        "Whole-number division counts the full hours; the remainder t % 3600 is what is left, and "
        "dividing that by 60 counts the full minutes. t % 60 is the seconds left over. "
        f"The answer is {answer}."
    ),
    blanks=[
        Blank(
            M,
            [
                (lines("m = t // 60", "int m = t / 60;"), "mod-chain-missing"),
                (lines("m = t % 60", "int m = t % 60;"), "mod-swap-div"),
                (lines("m = t % 3600", "int m = t % 3600;"), "mod-wrong-divisor"),
            ],
        ),
        Blank(
            H,
            [
                (lines("h = t % 3600", "int h = t % 3600;"), "mod-swap-div"),
                (lines("h = t // 60", "int h = t / 60;"), "mod-wrong-divisor"),
                (lines("h = t - 3600", "int h = t - 3600;"), "mod-swap-div"),
            ],
        ),
        Blank(
            S,
            [
                (lines("s = t % 3600", "int s = t % 3600;"), "mod-wrong-divisor"),
                (lines("s = t // 60", "int s = t / 60;"), "mod-swap-div"),
                (lines("s = t", "int s = t;"), "mod-chain-missing"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "mod-chain-missing",
            edit(M, lines("m = t // 60", "int m = t / 60;")),
            "Take the minutes from what is left after the hours: t % 3600 // 60",
            "t // 60 counts every minute in t, including the ones already counted as hours.",
        ),
        Fix(
            "mod-swap-div",
            edit(H, lines("h = t % 3600", "int h = t % 3600;")),
            "Count the hours with whole-number division: t // 3600",
            "% gives what is left over, not how many whole hours fit.",
        ),
        Fix(
            "mod-wrong-divisor",
            edit(S, lines("s = t % 3600", "int s = t % 3600;")),
            "The seconds are what is left after whole minutes: t % 60",
            "t % 3600 still contains the minutes.",
        ),
    ],
    decoys=[
        Decoy(edit(OUTPUT, lines("print(s, m, h)", 'cout << s << " " << m << " " << h << "\\n";',
                                 'System.out.println(s + " " + m + " " + h);')),
              "Print the parts in the order s, m, h", "order-matters-assumption"),
        Decoy(edit(H, lines("h = t // 3600 + 1", "int h = t / 3600 + 1;")), "Add 1 to the hours",
              "off-by-one-output"),
        Decoy(edit(H, lines("h = t // 360", "int h = t / 360;")), "Divide the hours by 360",
              "mod-wrong-divisor"),
        Decoy(edit(S, lines("s = t % 59", "int s = t % 59;")), "Take the seconds modulo 59",
              "loop-bound-off-by-one"),
        Decoy(edit(M, lines("m = t % 60 // 60", "int m = t % 60 / 60;")), "Take the minutes from t % 60",
              "mod-swap-div"),
        Decoy(edit(S, lines("s = t % 600", "int s = t % 600;")), "Take the seconds modulo 600",
              "mod-wrong-divisor"),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"split": split}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
