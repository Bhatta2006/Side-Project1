"""Deterministic safety (master prompt 15): high-stakes fields get a professional-advice
disclaimer, hazardous practice is simulated and supervised, and code only ever adds caution."""

from socrat.coursegen import intent as intents
from socrat.engine import safety


def test_high_stakes_fields_are_named_without_false_alarms():
    assert safety.fields("Teach me first aid and how to treat symptoms") == ["health"]
    assert safety.fields("Help me understand contract law") == ["law"]
    assert safety.fields("Teach me investing in stocks") == ["money"]
    # Physics laws and ordinary words are not legal or medical advice.
    assert safety.fields("Teach me Ohm's law and Newton's laws of motion") == []
    assert safety.fields("Teach me Python dictionaries") == []


def test_hazards_get_a_simulation_and_supervision_note():
    assert safety.HAZARD_NOTE in safety.notes("Teach me mains wiring at home")
    assert safety.notes("Teach me music theory") == []


def test_code_adds_notes_the_model_left_out_and_keeps_them_first():
    parsed = intents.from_rules("Teach me investing for retirement")
    stripped = parsed.model_copy(update={"safety_notes": ["A model note"]})
    applied = intents.apply_adapter(stripped, "Teach me investing for retirement")
    assert applied.safety_notes[0].startswith("This is education, not professional financial")
    assert "A model note" in applied.safety_notes
    assert "financial" in safety.disclaimer(applied.safety_notes)
    assert safety.disclaimer(["Hazardous practice is taught with simulations."]) == ""
