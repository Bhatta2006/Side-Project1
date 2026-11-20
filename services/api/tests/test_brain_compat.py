"""Backlog 3.4: a labelled gold set of request pairs for course reuse. The course was built for
the first request; would the brain serve it to the second? False reuse (serving a course that
breaks a hard requirement) must be 0. Pairs come from learner wording run through ``derive``
and ``compatible``, the same path ``route.decide`` takes, so wording normalisation is tested
too. Missed reuse (a pair labelled "reuse" that is not served) is reported."""

import pytest

from socrat.coursegen.brain.route import compatible
from socrat.coursegen.brain.spec import derive

SUBJECTS = {
    "algebra": ("Linear equations", "Teach me linear equations", "first-degree equations"),
    "probability": ("Conditional probability", "Teach me conditional probability", None),
    "sql": ("SQL queries", "Teach me SQL queries", None),
    "python": ("Python loops", "Teach me loops in Python", None),
    "chemistry": ("Chemical bonding", "Teach me chemical bonding", None),
    "music": ("Reading sheet music", "Teach me to read sheet music", None),
}
BASE = dict(desired_level="beginner", starting_level="none", language="en", minutes_per_day=10)

# (label, change to the second request's words, change to its intent, reuse?)
VARIANTS = [
    ("same words", "", {}, True),
    ("more time", " I have 25 minutes a day.", {"minutes_per_day": 25}, True),
    ("starts higher", "", {"starting_level": "beginner"}, True),
    ("synonym frame", "", {}, True),  # filled in per subject below when a synonym exists
    ("deeper", "", {"desired_level": "advanced"}, False),
    ("rigorous", " with formal proofs of every step", {}, False),
    ("intuitive", " in plain words, no formulas", {}, False),
    ("other language", "", {"language": "fr"}, False),
    ("for kids", "", {"register": "kid"}, False),
    ("other code language", "", {"code_languages": ["java"]}, False),
    ("timed drills", " through timed drills", {}, False),
    ("themed", " through detective cases", {}, False),
    ("shorter sessions", "", {"minutes_per_day": 5, "_course_minutes": 25}, False),
]


def pairs():
    for key, (subject, text, synonym) in SUBJECTS.items():
        for label, extra, change, reuse in VARIANTS:
            first_intent = BASE | {"subject": subject}
            if "_course_minutes" in change:
                first_intent["minutes_per_day"] = change["_course_minutes"]
                change = {k: v for k, v in change.items() if not k.startswith("_")}
            second_text, second_intent = text + extra, first_intent | change
            if label == "synonym frame":
                if synonym is None:
                    continue
                second_intent = second_intent | {"subject": synonym}
            if label == "shorter sessions":
                second_intent["minutes_per_day"] = 5
            yield pytest.param(
                text, first_intent, second_text, second_intent, reuse, id=f"{key}-{label}"
            )
    # Themed courses: a theme is matched by meaning, never served to a plain request.
    detective = "Teach me linear equations through detective cases"
    mystery = "Help me solve first-degree equations as mystery investigations"
    algebra = BASE | {"subject": "Linear equations"}
    yield pytest.param(detective, algebra, mystery, algebra, True, id="theme-synonyms")
    yield pytest.param(
        detective, algebra, "Teach me linear equations", algebra, False, id="theme-to-plain"
    )
    yield pytest.param(
        "Teach me linear equations as a game",
        algebra,
        detective,
        algebra,
        False,
        id="theme-mismatch",
    )


GOLD = list(pairs())


def test_the_gold_set_is_big_enough():
    assert len(GOLD) >= 60


@pytest.mark.parametrize(("course_text", "course_intent", "text", "intent", "reuse"), GOLD)
def test_no_false_reuse(course_text, course_intent, text, intent, reuse):
    course = derive(course_text, course_intent, "root")
    wanted = derive(text, intent, "root")
    failed = {k: why for k, (v, why) in compatible(course, wanted).items() if v != "pass"}
    if reuse:
        assert not failed, f"missed reuse: {failed}"
    else:
        assert failed, "false reuse: a course breaking a hard requirement would be served"
