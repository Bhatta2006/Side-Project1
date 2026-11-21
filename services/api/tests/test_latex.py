"""Maths in generated text: backslashes survive JSON, and broken maths is a lesson issue."""

from socrat.catalog.registry import default_catalog
from socrat.coursegen import package as pkg
from socrat.coursegen.roles import parse_json


def test_single_backslash_latex_survives_json():
    # What a model often sends: one backslash, which JSON reads as \f, \b, \n, \r, \t.
    raw = r'{"lesson": "Ratio $\frac{a}{b}$ and $$\beta + \nabla f \rho \theta \text{x} \to 0$$"}'
    data, problem = parse_json(raw)
    assert problem == ""
    assert (
        data["lesson"] == r"Ratio $\frac{a}{b}$ and $$\beta + \nabla f \rho \theta \text{x} \to 0$$"
    )


def test_correct_json_and_prose_are_untouched():
    # Already doubled, and real newlines outside maths, stay as they are.
    data, _ = parse_json(r'{"lesson": "$\\frac{1}{2}$\ntext\tand\nbelow", "n": "\nto the end"}')
    assert data["lesson"] == "$\\frac{1}{2}$\ntext\tand\nbelow"
    assert data["n"] == "\nto the end"


def test_lesson_gate_catches_broken_maths():
    course = default_catalog().course("basics")
    concept = default_catalog().concept("basics:values")
    open_ = pkg.check_lesson(concept, course, {"lesson": "## a\n$$x^2\n"})
    assert any("not closed" in p for p in open_)
    lost = pkg.check_lesson(concept, course, {"lesson": "## a\n$\x0crac{a}{b}$"})
    assert any("lost its backslash" in p for p in lost)
    fine = pkg.check_lesson(concept, course, {"lesson": "## a\n$$x^2$$ and $y$"})
    assert not any("not closed" in p or "backslash" in p for p in fine)
    assert "KaTeX" in pkg.LESSON and "KaTeX" in pkg.QUIZ_MARKED and "KaTeX" in pkg.ATOMS_MARKED
