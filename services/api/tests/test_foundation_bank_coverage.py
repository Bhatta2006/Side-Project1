"""Foundation checks can recover from a miss in every supported language."""

from socrat.catalog.registry import default_catalog
from socrat.quiz.config import DEFAULT
from socrat.quiz.pools import family_bank, keep_practice, legacy_bank
from socrat.quiz.selection import Context, Step, select


def test_zero_banks_have_language_coverage_and_a_question_after_one_miss():
    cat = default_catalog()
    items = keep_practice(legacy_bank(cat)) + family_bank(cat.quiz_families)
    expanded = {f.concept for f in cat.quiz_families.values() if f.family == "adaptive-foundations"}
    for concept in expanded:
        for language in ("python", "cpp", "java"):
            pool = [
                i
                for i in items
                if i.concept == concept
                and i.pool == "practice"
                and (not i.languages or language in i.languages)
            ]
            assert len(pool) >= 5, (concept, language)
            ctx = Context(
                "foundations",
                DEFAULT.modes["concept_check"],
                (concept,),
                language,
                {concept: 900},
                "coverage",
            )
            first = select(items, [], ctx)
            assert first.item is not None
            missed = Step(
                first.item.key, first.item.pattern, first.item.band, first.item.format, "wrong"
            )
            next_question = select(items, [missed], ctx)
            assert next_question.item is not None, (concept, language)
            assert next_question.item.key != first.item.key
