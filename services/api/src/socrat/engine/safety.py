"""Deterministic safety notes for a learning request (master prompt 15).

The intent parser (a model) may add safety notes; this code always runs after it and can only add
more. Two kinds: high-stakes fields, where Socrat teaches but must not stand in for a professional
(health, law, money), and hazardous practice, which is taught through simulation and needs
qualified supervision for anything real. A course carrying either note has every lesson marked as
needing a person's review (``coursegen.validation``), and its lessons carry the disclaimer.
"""

import re

HIGH_STAKES = {
    "health": r"medic(al|ine)|health|diagnos\w*|symptom\w*|drug|dosage|nursing|first aid|mental health|therapy|nutrition|diet",
    # Not the bare word "law": Ohm's law and Newton's laws are physics.
    "law": r"legal|lawyers?|court|(contract|criminal|tax|immigration|family|company|property) law|law school|study law|taxes",
    "money": r"invest\w*|trading|stocks?|crypto\w*|financ\w*|loans?|mortgage|retirement|forex",
}
HAZARDS = r"high[- ]voltage|mains (power|electricity|wiring)|electrical wiring|explosive\w*|firearms?|guns?|weapons?|hazardous chemicals?|chemistry (at home|experiments)|lathe|welding|power tools|chainsaw"

DISCLAIMER = "This is education, not professional {field} advice; check real decisions with a qualified professional."
HAZARD_NOTE = "Hazardous practice is taught with simulations; anything real needs qualified supervision and proper safety equipment."


def _word(pattern: str, text: str) -> bool:
    return re.search(rf"(?<![a-z])({pattern})(?![a-z])", text) is not None


def fields(text: str) -> list[str]:
    """High-stakes fields a request touches (health, law, money)."""
    low = text.lower()
    return [name for name, pattern in HIGH_STAKES.items() if _word(pattern, low)]


def notes(text: str) -> list[str]:
    """Safety notes this request needs, whatever the model said."""
    low = text.lower()
    out = [
        DISCLAIMER.format(field={"health": "medical", "law": "legal", "money": "financial"}[f])
        for f in fields(text)
    ]
    if _word(HAZARDS, low):
        out.append(HAZARD_NOTE)
    return out


def disclaimer(safety: list[str]) -> str:
    """The professional-advice disclaimers among a brief's safety notes, for the lesson credit."""
    return " ".join(n for n in safety if n.startswith("This is education, not professional"))
