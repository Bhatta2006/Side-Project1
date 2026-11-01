"""Answer checking: equivalence, equations, derivation steps, numbers with units."""

import json

import pytest

pytest.importorskip("sympy")

from socrat.checks import engine  # noqa: E402


@pytest.mark.parametrize(
    ("expected", "given"),
    [
        ("(x+1)^2", "x^2+2x+1"),
        ("(x+1)**2", "x^2 + 2*x + 1"),
        ("1", "sin(x)^2+cos(x)^2"),
        ("log(x*y)", "log(x)+log(y)"),  # sampled on positive values only
        ("sqrt(x^2)*0+2x", "x*2"),
        ("1/2", "0.5"),
        ("v_0*t + a*t^2/2", "t*v_0 + (a*t^2)/2"),
        ("theta^2", "theta*theta"),
    ],
)
def test_equivalent_expressions_are_accepted(expected, given):
    assert engine.equivalent(expected, given)["verdict"] == "correct"


def test_wrong_expressions_say_what_kind_of_slip_it_is():
    wrong = engine.equivalent("x^2", "-x^2")
    assert wrong["verdict"] == "incorrect" and wrong["hint"] == "sign"
    constant = engine.equivalent("x^3/3", "x^3/3 + 5")
    assert constant["hint"] == "constant" and "constant" in constant["hint_text"]
    assert engine.equivalent("x^2", "x^3")["hint"] == ""
    assert engine.equivalent("sqrt(x^2)", "x")["verdict"] == "incorrect"  # |x| is not x


@pytest.mark.parametrize(
    "text",
    [
        "",
        "x+",
        "__import__('os').system('x')",
        "open(1)",
        "x.free_symbols",
        "lambda: 1",
        "9^9^9^9",
        "10^100000",
        "x" * 300,
        "1/0",
        "x; y",
    ],
)
def test_unreadable_or_hostile_text_is_refused_not_evaluated(text):
    assert engine.equivalent("x", text)["verdict"] == "unreadable"
    assert engine.equivalent(text, "x")["verdict"] == "unreadable"


def test_equations_match_by_their_solutions():
    assert engine.equation_equivalent("x=3", "2x+1=7")["verdict"] == "correct"
    assert engine.equation_equivalent("x=3", "3=x")["verdict"] == "correct"
    assert engine.equation_equivalent("x^2=4", "x^2-4=0")["verdict"] == "correct"
    assert engine.equation_equivalent("x=3", "2x+1=8")["verdict"] == "incorrect"
    assert engine.equation_equivalent("y=2x+1", "2y=4x+2")["verdict"] == "correct"  # same line
    assert engine.equation_equivalent("y=2x+1", "y=2x+2")["verdict"] == "incorrect"
    assert engine.equation_equivalent("x=3", "x=3=3")["verdict"] == "unreadable"


def test_a_derivation_is_checked_line_by_line():
    good = engine.steps(["2x+3=7", "2x=4", "x=2"], expected_final="x=2")
    assert good["verdict"] == "correct" and good["final"] is True
    bad = engine.steps(["2x+3=7", "2x=10", "x=5"])
    assert bad["verdict"] == "incorrect" and bad["step"] == 2
    short = engine.steps(["2x+3=7", "2x=4", "x=2"], expected_final="x=3")
    assert short["verdict"] == "incorrect" and short["final"] is False
    expr = engine.steps(["(x+1)^2-1", "x^2+2x+1-1", "x^2+2x"])
    assert expr["verdict"] == "correct"
    mixed = engine.steps(["2x+3=7", "2x+3-7"])
    assert mixed["verdict"] == "incorrect" and mixed["step"] == 2
    assert engine.steps([])["verdict"] == "unreadable"


@pytest.mark.parametrize(
    ("expected", "given", "unit", "verdict", "hint"),
    [
        (9.8, "9.81 m/s^2", "m/s^2", "correct", ""),
        (1, "3.6 km/h", "m/s", "correct", ""),  # converted, not just compared
        (3e8, "3.0 x 10^8 m/s", "m/s", "correct", ""),
        (3e8, "3e8 m/s", "m/s", "correct", ""),
        (10, "10 kg*m/s^2", "N", "correct", ""),
        (2.5, "2.5", "", "correct", ""),
        (9.8, "9.8", "m/s^2", "incorrect", "missing_units"),
        (9.8, "9.8 kg", "m/s^2", "incorrect", "wrong_units"),
        (9.8, "-9.8 m/s^2", "m/s^2", "incorrect", "sign"),
        (9.8, "98 m/s^2", "m/s^2", "incorrect", "power_of_ten"),
        (9.8, "12 m/s^2", "m/s^2", "incorrect", ""),
        (2.5, "2.5 m", "", "incorrect", "wrong_units"),
        (9.8, "nine m/s", "m/s", "unreadable", ""),
        (9.8, "9.8 parsecs", "m/s", "unreadable", ""),
        (9.8, "9.8 m/__x", "m/s", "unreadable", ""),
    ],
)
def test_numbers_are_checked_with_units_and_tolerance(expected, given, unit, verdict, hint):
    result = engine.numeric(expected, given, unit)
    assert (result["verdict"], result["hint"]) == (verdict, hint), result


def test_tolerance_can_be_tightened_or_absolute():
    assert engine.numeric(100, "103", "", rel_tol=0.01)["verdict"] == "incorrect"
    assert engine.numeric(100, "103", "", rel_tol=0.05)["verdict"] == "correct"
    assert engine.numeric(0, "0.001", "", rel_tol=0.0, abs_tol=0.01)["verdict"] == "correct"


def test_every_mapped_unit_converts_to_si():
    for name, unit in engine.UNITS.items():
        factor, _ = engine._si(unit)
        assert factor > 0, name


def test_run_is_the_json_entry_point_the_browser_uses():
    ask = {"op": "equivalent", "expected": "2x", "given": "x+x"}
    assert json.loads(engine.run(json.dumps(ask)))["verdict"] == "correct"
    num = {"op": "numeric", "expected": 1, "given": "3.6 km/h", "unit": "m/s"}
    assert json.loads(engine.run(json.dumps(num)))["verdict"] == "correct"
    assert (
        json.loads(engine.run(json.dumps({"op": "steps", "lines": ["x+1=2", "x=1"]})))["verdict"]
        == "correct"
    )
    assert json.loads(engine.run("not json"))["verdict"] == "unreadable"
    assert json.loads(engine.run(json.dumps({"op": "nope"})))["verdict"] == "unreadable"
    assert json.loads(engine.run(json.dumps({"op": "equivalent"})))["verdict"] == "unreadable"
