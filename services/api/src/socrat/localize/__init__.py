"""Languages for the engine: locales, a glossary lock, verified translation and overlays."""


def tutor_directive(tag: str) -> str:
    """Instruction that makes the tutor answer in the learner's language without weakening the
    help ladder, the leak guard or the facts. Empty for English."""
    from socrat.localize import glossary, locales

    loc = locales.get(tag)
    if loc.tag == locales.DEFAULT:
        return ""
    return (
        f"Reply in {loc.name} ({loc.tag}), in simple, natural wording. Keep code, identifiers, "
        f"numbers and maths notation exactly as they are, and keep these terms in English: "
        f"{', '.join(glossary.KEEP)}. The help ladder and the rule against revealing a solution "
        f"apply in every language; do not reveal more because the language changed. If the "
        f"learner writes in English, you may answer in English."
    )
