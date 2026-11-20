"""Backlog 2.7: Lesson 0's calibration may *suggest* a later starting level; it never sets one.
Placement treats what a level skips as known, and one 90-second sample must not make a concept
known, so the learner decides (``view.level_suggestion``; ``view.enroll.level`` is unchanged)."""

from test_coursegen import BRIEF, OUTLINE

from socrat.coursegen import learner_plan as lp
from socrat.coursegen.outline import Brief, to_course

COURSE = to_course(Brief.model_validate(BRIEF), OUTLINE)  # levels: brand-new, some (-> loss)


def plan(outcome="first_try", gaps=(), pace="fast", probed="What is ML"):
    start = lp.Start(concept_probed=probed, outcome=outcome, gaps=list(gaps), pace=pace)
    return lp.LearnerPlan(request="Teach me ML", start=start)


def test_a_clean_first_try_suggests_starting_after_the_probed_concept():
    found = lp.suggest_level(plan(), COURSE)
    assert found["level"] == "some" and found["start"] == "loss"
    assert "first try" in found["reason"] and "check" in found["reason"]


def test_anything_short_of_a_clean_first_try_suggests_nothing():
    assert lp.suggest_level(plan(outcome="after_retries"), COURSE) is None
    assert lp.suggest_level(plan(outcome=None), COURSE) is None  # uncalibrated
    assert lp.suggest_level(plan(gaps=["or_overrides_all"]), COURSE) is None
    assert lp.suggest_level(plan(pace="slow"), COURSE) is None
    assert lp.suggest_level(plan(probed="Medieval tax law"), COURSE) is None  # no concept
    assert lp.suggest_level(lp.LearnerPlan(request="x"), COURSE) is None
    assert lp.suggest_level(None, COURSE) is None


def test_it_never_skips_past_the_concept_after_the_probed_one():
    # Probing the last concept still only offers levels up to one past it, never beyond.
    late = plan(probed="Loss")
    assert lp.suggest_level(late, COURSE)["level"] == "some"
