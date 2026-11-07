"""Lesson pages are sized for the learner by code (style/pages.py), not by one fixed rule.

The owner's rule (2026-11-05): length and style are learner-based, from children to university
and everything between, decided per learner, never one general size.
"""

from socrat.coursegen import intent as intents
from socrat.coursegen import package as pkg
from socrat.style import pages
from socrat.style.spec import PRESETS

L = pages.Learner


def size(p: pages.PageProfile) -> float:
    return sum(p.words) / 2


def test_page_size_follows_the_reader_not_one_band():
    readers = ["little-kid", "kid", "teen", "general", "university"]
    sizes = [size(pages.profile(L(register=r, starting_level="beginner"))) for r in readers]
    assert sizes == sorted(sizes) and len(set(sizes)) == len(sizes)
    # The same reader gets a different page when something else about them changes.
    base = size(pages.profile(L(register="teen")))
    assert size(pages.profile(L(register="teen", starting_level="none"))) < base
    assert size(pages.profile(L(register="teen", starting_level="advanced"))) > base
    assert size(pages.profile(L(register="teen", approach=["visual"]))) < base
    assert size(pages.profile(L(register="teen", balance="theory-heavy"))) > base
    assert size(pages.profile(L(register="teen", accessibility=["dyslexia"]))) < base
    rigorous = PRESETS["rigorous"]
    assert size(pages.profile(L(register="teen"), rigorous)) > base


def test_ideas_checks_pages_and_elements_fit_the_learner():
    child = pages.profile(L(register="kid", starting_level="none", minutes_per_day=10))
    expert = pages.profile(
        L(register="university", starting_level="advanced", minutes_per_day=60),
        PRESETS["rigorous"],
    )
    assert child.ideas == 1 and child.check_every == 1
    assert expert.ideas == 3 and expert.check_every == 2
    assert "story" in child.elements and "derivation" not in child.elements
    assert {"formula", "derivation", "compare"} <= set(expert.elements)
    # A longer sitting holds more pages; practice-heavy reads less and checks every page.
    short = pages.profile(L(register="general", minutes_per_day=10))
    long = pages.profile(L(register="general", minutes_per_day=45))
    assert short.pages[1] < long.pages[1]
    practice = pages.profile(L(register="general", balance="practice-heavy", minutes_per_day=45))
    assert practice.check_every == 1 and practice.pages[1] <= long.pages[1]
    assert all(p.reasons for p in (child, expert, short, long))


def test_the_profile_is_told_to_the_writer_and_checked_by_code():
    p = pages.profile(L(register="general", minutes_per_day=30))
    text = pages.block(p)
    assert f"{p.words[0]}-{p.words[1]} words" in text and "### Worked example" in text
    page = " ".join(["word"] * p.words[0])
    fine = "".join(f"## Page {i}\n\n{page}\n\n" for i in range(p.pages[0]))
    fine += "## Check yourself\n\n1. Why?\n\n<details>Because.</details>\n"
    assert pages.check(fine, p) == []
    huge = fine.replace(page, " ".join(["word"] * p.words[1] * 2), 1)
    assert any("Split it" in m for m in pages.check(huge, p))
    one = f"## Only\n\n{page}\n\n## Check yourself\n\n<details>x</details>"
    assert any("pages for this learner" in m for m in pages.check(one, p))


def test_the_lesson_gate_uses_pages_when_given():
    from test_coursegen import BRIEF, OUTLINE

    from socrat.coursegen.outline import Brief, to_course

    course = to_course(Brief.model_validate(BRIEF), OUTLINE)
    concept = course.concept("loss")
    p = pages.profile(L(register="kid", starting_level="none", minutes_per_day=10))
    short = "".join(
        f"## Page {i}\n\n{' '.join(['word'] * p.words[0])}\n\n" for i in range(p.pages[0])
    )
    short += "## Check yourself\n\n<details>x</details>"
    draft = {"lesson": short}
    # Too short for the default 3,000-character floor, right for this child.
    assert any("characters" in m for m in pkg.check_lesson(concept, course, draft))
    assert pkg.check_lesson(concept, course, draft, None, p) == []


def test_a_learner_request_carries_its_reader_into_the_brief():
    got = intents.from_rules("Teach me fractions, I am 9 and like games")
    got = intents.apply_choices(got, ["reg-kid", "time-15"])
    brief = intents.to_brief(got, "fractions-x", 3.0)
    assert brief.learner is not None and brief.learner.register == "kid"
    assert brief.learner.minutes_per_day == 15
    # Briefs stored before this field still load, and the style alone then decides.
    assert pages.learner_of(None, PRESETS["kids"]).register == "kid"
    assert pages.learner_of(None, PRESETS["rigorous"]).register == "university"
    assert pages.learner_of(None, None) == L()
