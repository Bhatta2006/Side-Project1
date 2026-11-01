"""Content quality guards that only ratchet down.

A multiple-choice question whose correct option is much longer than every distractor can be
answered by length alone, without knowing anything. Existing questions are being rewritten;
these ceilings stop new ones from adding to the count. Lower a ceiling when you fix some.
"""

from socrat.catalog.registry import default_catalog

# Correct option at least 1.3x as long as the longest distractor, per course.
LENGTH_CUE_CEILING = {"zero": 29, "dsa": 91, "cp": 40}
CUE_RATIO = 1.3
# Family items whose answer is at least 1.6x the longest distractor (existing debt).
FAMILY_CUE_CEILING = 187


def length_cues(course) -> list[str]:
    found = []
    for concept in course.concepts:
        for q in concept.quiz:
            lengths = [len(o) for o in q.options]
            right = lengths[q.answer]
            others = lengths[: q.answer] + lengths[q.answer + 1 :]
            if others and right >= CUE_RATIO * max(others):
                found.append(f"{concept.id}/{q.id}")
    return found


def test_length_cues_never_grow():
    cat = default_catalog()
    for course_id, ceiling in LENGTH_CUE_CEILING.items():
        cues = length_cues(cat.course(course_id))
        assert len(cues) <= ceiling, (
            f"{course_id}: {len(cues)} questions give the answer away by length "
            f"(ceiling {ceiling}). Make the distractors as specific as the answer: {cues[-5:]}"
        )


def test_family_items_have_no_length_cue():
    """Family items: the count of strong length cues may only go down."""
    cat = default_catalog()
    leaks = []
    for family in cat.quiz_families.values():
        for q in family.items:
            lengths = [len(o) for o in q.options]
            others = lengths[: q.answer] + lengths[q.answer + 1 :]
            if others and lengths[q.answer] >= 1.6 * max(others):
                leaks.append(family.item_key(q.id))
    assert len(leaks) <= FAMILY_CUE_CEILING, leaks
