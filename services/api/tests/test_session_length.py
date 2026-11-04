"""A learner's stated session length decides lesson size, deterministically.

Before, "5 minutes a day" was only a sentence to the writer while the lesson gate still asked
for 2,000-4,000 characters, so a lesson as short as asked failed its gates every round.
"""

from socrat.coursegen import intent as intents
from socrat.coursegen import package as pkg
from socrat.style import spec as styles


def test_short_sessions_get_bite_sized_lessons_and_long_ones_keep_depth():
    assert styles.for_session(None, None) is None
    five = styles.for_session(None, 5)
    assert five is not None and five.format == "bite" and five.session_minutes == 5
    assert five.lesson_bounds() == styles.BITE_RANGE
    ten = styles.for_session(None, 10)
    assert ten is not None and ten.format == "bite"
    # A 15-minute or longer session fits a standard lesson: no style is invented for it.
    assert styles.for_session(None, 15) is None and styles.for_session(None, 60) is None
    chosen = styles.StyleSpec(name="Warm")
    hour = styles.for_session(chosen, 60)
    assert hour is not None and hour.format == "standard" and hour.session_minutes == 60
    # A learner who asked for deep lessons keeps them; the session length is still theirs.
    deep = styles.StyleSpec(name="Deep", format="deep")
    kept = styles.for_session(deep, 5)
    assert kept is not None and kept.format == "deep" and kept.session_minutes == 5
    assert styles.for_session(chosen, 480).session_minutes == 120  # the schema's ceiling


def test_the_learner_choice_travels_to_the_brief_as_data():
    parsed = intents.from_rules("teach me fractions, I have 5 minutes a day")
    parsed = parsed.model_copy(update={"minutes_per_day": 5})
    brief = intents.to_brief(parsed, "fractions-abc123", 5.0)
    assert brief.session_minutes == 5


def test_a_short_lesson_passes_for_a_five_minute_learner_and_fails_without_it():
    from test_coursegen import BRIEF
    from test_planning_fit import maths_outline

    from socrat.catalog.registry import default_catalog
    from socrat.coursegen.outline import Brief, tidy, to_course

    course = to_course(Brief.model_validate(BRIEF), tidy(maths_outline(), default_catalog()))
    concept = course.concepts[0]
    short = "## One idea\n" + "A fraction names equal parts of a whole. " * 25
    short += "\n<details>Check: what is 1/2 of 8? 4</details>"
    standard = pkg.check_lesson(concept, course, {"lesson": short}, None)
    assert any("needs at least" in i for i in standard)
    bite = pkg.check_lesson(concept, course, {"lesson": short}, styles.for_session(None, 5))
    assert bite == []
