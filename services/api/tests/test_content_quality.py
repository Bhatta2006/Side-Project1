"""Content quality guards.

A multiple-choice question whose correct option is much longer than every distractor can be
answered by length alone, without knowing anything. Every authored and family question was
rewritten so the answer is never 1.3x as long as the longest distractor; keep it that way by
making distractors as specific as the answer (a named mistake, not a bare phrase).
"""

from socrat.catalog.registry import default_catalog

CUE_RATIO = 1.3


def gives_away(options: list[str], answer: int) -> bool:
    lengths = [len(o) for o in options]
    others = lengths[:answer] + lengths[answer + 1 :]
    return bool(others) and lengths[answer] >= CUE_RATIO * max(others)


def test_no_authored_question_gives_its_answer_away_by_length():
    cat = default_catalog()
    cues = [
        f"{concept.id}/{q.id}"
        for course_id in ("zero", "dsa", "cp")
        for concept in cat.course(course_id).concepts
        for q in concept.quiz
        if gives_away(q.options, q.answer)
    ]
    assert not cues, f"answer much longer than every distractor: {cues}"


def test_no_family_item_gives_its_answer_away_by_length():
    cat = default_catalog()
    cues = [
        family.item_key(q.id)
        for family in cat.quiz_families.values()
        for q in family.items
        if gives_away(q.options, q.answer)
    ]
    assert not cues, f"answer much longer than every distractor: {cues}"
