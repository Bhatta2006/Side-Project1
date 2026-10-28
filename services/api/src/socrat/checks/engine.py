"""Answer checking for math and physics: is what the learner typed right, and if not, how.

Pure Python and SymPy with no socrat imports, so the very same file runs unchanged in the
browser (Pyodide) and under pytest. Four checks: symbolic equivalence, equation equivalence,
derivation steps, and numbers with units. Every check returns plain data
``{"verdict": "correct" | "incorrect" | "unreadable", "reason": ..., "hint": ...}`` where
``hint`` names a common slip (sign, constant, units, power of ten) so a mentor can see why.

Learner text is untrusted. It is checked against a character and name whitelist and parsed
with an empty global namespace, so nothing but math can be evaluated.
"""

import json
import math
import random
import re

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)
from sympy.physics import units as u

MAX_LENGTH = 200
SAMPLES = 8

FUNCTIONS = {
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "asin": sp.asin,
    "acos": sp.acos,
    "atan": sp.atan,
    "sinh": sp.sinh,
    "cosh": sp.cosh,
    "tanh": sp.tanh,
    "exp": sp.exp,
    "log": sp.log,
    "ln": sp.log,
    "sqrt": sp.sqrt,
    "abs": sp.Abs,
}
CONSTANTS = {"pi": sp.pi, "e": sp.E}  # e is Euler's number, as in a math course
GREEK = {
    name: sp.Symbol(name)
    for name in (
        "alpha beta gamma delta epsilon eta theta kappa mu nu rho sigma tau phi chi psi omega"
    ).split()
}

# Learner-typed units -> SymPy units. Temperatures are kelvin only (no offset scales).
UNITS = {
    "m": u.meter,
    "km": u.kilometer,
    "cm": u.centimeter,
    "mm": u.millimeter,
    "s": u.second,
    "ms": u.millisecond,
    "min": u.minute,
    "h": u.hour,
    "kg": u.kilogram,
    "g": u.gram,
    "N": u.newton,
    "J": u.joule,
    "kJ": 1000 * u.joule,
    "W": u.watt,
    "kW": 1000 * u.watt,
    "Pa": u.pascal,
    "Hz": u.hertz,
    "V": u.volt,
    "A": u.ampere,
    "C": u.coulomb,
    "K": u.kelvin,
    "L": u.liter,
    "eV": u.electronvolt,
    "rad": u.radian,
}
BASE = [u.meter, u.kilogram, u.second, u.ampere, u.kelvin]

_ALLOWED = re.compile(r"^[0-9A-Za-z_+\-*/^().,\s=]+$")
MAX_EXPONENT = 1000
_TOWER = re.compile(r"\^\s*[A-Za-z0-9.]+\s*\^")
_EXPONENT = re.compile(r"\^\s*\(?\s*(\d+)")
_NUMBER = re.compile(r"(?<![A-Za-z_])\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_SYMBOL = re.compile(r"[A-Za-z](?:[0-9]|_[A-Za-z0-9]{1,3})?")
_TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)
_UNIT_TRANSFORMS = standard_transformations + (convert_xor,)
_QUANTITY = re.compile(
    r"^\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:\s*(?:[eE]|(?:x|×|\*)\s*10\s*\^?)\s*[+-]?\d+)?)\s*(.*?)\s*$"
)


class Unreadable(ValueError):
    """The text is not something this checker can read; the message is shown to the learner."""


def _result(verdict: str, reason: str = "", hint: str = "", **extra) -> dict:
    return {"verdict": verdict, "reason": reason, "hint": hint, **extra}


def parse(text: str) -> sp.Expr:
    text = (text or "").strip()
    if not text:
        raise Unreadable("Type an answer first.")
    if len(text) > MAX_LENGTH:
        raise Unreadable("That is too long to check.")
    text = text.replace("**", "^")
    if not _ALLOWED.match(text) or "__" in text or "==" in text:
        raise Unreadable("Use only numbers, letters, + - * / ^ ( ) and =.")
    # A tower like 9^9^9 or 10^100000 would make SymPy build a gigantic integer and hang.
    if _TOWER.search(text) or any(int(n) > MAX_EXPONENT for n in _EXPONENT.findall(text)):
        raise Unreadable("That power is too large to check.")
    for name in _NAME.findall(_NUMBER.sub(" ", text)):
        known = name in FUNCTIONS or name in CONSTANTS or name in GREEK
        if not (known or _SYMBOL.fullmatch(name) or re.fullmatch(r"[A-Za-z]{2,3}", name)):
            raise Unreadable(f"I do not know what '{name}' means here.")
    local = {**FUNCTIONS, **CONSTANTS, **GREEK}
    namespace = {
        "Symbol": sp.Symbol,
        "Integer": sp.Integer,
        "Float": sp.Float,
        "Rational": sp.Rational,
        "__builtins__": {},
    }
    try:
        value = parse_expr(
            text, local_dict=local, global_dict=namespace, transformations=_TRANSFORMS
        )
    except Exception as exc:  # SyntaxError, TokenError, TypeError ... all mean "not math"
        raise Unreadable("I could not read that as an expression.") from exc
    if not isinstance(value, sp.Expr) or value.has(sp.zoo, sp.nan, sp.oo):
        raise Unreadable("That is not a usable expression.")
    return value


def _real(x: complex) -> bool:
    return abs(x.imag) <= 1e-9 * (1 + abs(x.real))


def _values(a: sp.Expr, b: sp.Expr, rng: random.Random):
    """Pairs of (a, b) evaluated at random points where both are defined and finite."""
    symbols = sorted(a.free_symbols | b.free_symbols, key=str)
    found, attempts = [], 0
    while len(found) < SAMPLES and attempts < SAMPLES * 6:
        attempts += 1
        point = {s: sp.Float(rng.uniform(-3.0, 3.0) + 0.0137, 15) for s in symbols}
        try:
            va, vb = complex(a.evalf(subs=point)), complex(b.evalf(subs=point))
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        if any(math.isnan(x.real) or math.isnan(x.imag) or math.isinf(abs(x)) for x in (va, vb)):
            continue
        if _real(va) != _real(vb):
            continue  # one side leaves the real numbers here (log of a negative): not a test
        found.append((va, vb))
    return found


def _close(x: complex, y: complex) -> bool:
    return abs(x - y) <= 1e-8 * (1 + abs(x) + abs(y))


def _same(a: sp.Expr, b: sp.Expr) -> bool | None:
    """True/False when decided by sampling, None when too few valid points exist."""
    pairs = _values(a, b, random.Random(7))
    if len(pairs) < 3:
        return None
    return all(_close(x, y) for x, y in pairs)


def _slip(expected: sp.Expr, given: sp.Expr) -> str:
    pairs = _values(expected, given, random.Random(11))
    if len(pairs) < 3:
        return ""
    if all(_close(x, -y) for x, y in pairs):
        return "sign"
    diffs = [y - x for x, y in pairs]
    if abs(diffs[0]) > 1e-9 and all(abs(d - diffs[0]) <= 1e-8 * (1 + abs(d)) for d in diffs):
        return "constant"
    return ""


HINTS = {
    "sign": "Your answer is the negative of the right one: check a sign.",
    "constant": "Your answer differs from the right one by a constant: check for a missing +C or term.",
}


def equivalent(expected: str, given: str) -> dict:
    """Are two expressions equal for every value of their variables?"""
    try:
        want, got = parse(expected), parse(given)
    except Unreadable as exc:
        return _result("unreadable", str(exc))
    same = _same(want, got)
    if same is None:
        same = sp.simplify(want - got) == 0
    if same:
        return _result("correct", method="sampling")
    slip = _slip(want, got)
    return _result(
        "incorrect",
        "That is not equivalent to the expected answer.",
        slip,
        hint_text=HINTS.get(slip, ""),
    )


def _equation(text: str) -> sp.Expr:
    sides = text.split("=")
    if len(sides) != 2:
        raise Unreadable("An equation has exactly one '=' sign.")
    return parse(sides[0]) - parse(sides[1])


def _equations_match(a: sp.Expr, b: sp.Expr) -> bool:
    """Same solutions: compare solution sets for one variable, else check a constant ratio."""
    symbols = a.free_symbols | b.free_symbols
    if len(symbols) == 1:
        (x,) = symbols
        sa = {sp.nsimplify(s) for s in sp.solve(a, x)}
        sb = {sp.nsimplify(s) for s in sp.solve(b, x)}
        return len(sa) == len(sb) and all(any(sp.simplify(p - q) == 0 for q in sb) for p in sa)
    pairs = _values(a, b, random.Random(5))
    ratios = [x / y for x, y in pairs if abs(y) > 1e-9]
    return len(ratios) >= 3 and all(_close(r, ratios[0]) for r in ratios) and abs(ratios[0]) > 1e-9


def equation_equivalent(expected: str, given: str) -> dict:
    """Do two equations say the same thing (x = 3 and 2x + 1 = 7 do)?"""
    try:
        want, got = _equation(expected), _equation(given)
    except Unreadable as exc:
        return _result("unreadable", str(exc))
    if _equations_match(want, got):
        return _result("correct", method="solutions")
    return _result("incorrect", "That equation does not have the same solutions.")


def _line(text: str):
    """(kind, value) for one derivation line: an equation or an expression."""
    return ("equation", _equation(text)) if "=" in text else ("expression", parse(text))


def steps(lines: list[str], expected_final: str | None = None) -> dict:
    """Does each line follow from the one before? Reports the first line that does not."""
    lines = [x for x in (lines or []) if x.strip()]
    if not lines:
        return _result("unreadable", "Write at least one line.")
    if len(lines) > 25:
        return _result("unreadable", "That is too many lines to check.")
    try:
        parsed = [_line(x) for x in lines]
    except Unreadable as exc:
        return _result("unreadable", str(exc))
    for i in range(1, len(parsed)):
        (kind_a, a), (kind_b, b) = parsed[i - 1], parsed[i]
        if kind_a != kind_b:
            return _result(
                "incorrect",
                f"Line {i + 1} changes between an equation and an expression.",
                step=i + 1,
            )
        ok = _equations_match(a, b) if kind_a == "equation" else _same(a, b)
        if not ok:
            return _result("incorrect", f"Line {i + 1} does not follow from line {i}.", step=i + 1)
    if expected_final:
        check = equation_equivalent if "=" in expected_final else equivalent
        final = check(expected_final, lines[-1])
        if final["verdict"] != "correct":
            return _result(
                final["verdict"],
                "Every step follows, but the result is not the expected one.",
                step=len(lines),
                final=False,
            )
    return _result("correct", method="steps", final=True if expected_final else None)


def _unit(text: str) -> sp.Expr:
    text = text.replace("·", "*").replace("²", "^2").replace("³", "^3").strip()
    if not text:
        return sp.Integer(1)
    if not re.fullmatch(r"[A-Za-z0-9^*/().\s-]+", text) or "__" in text:
        raise Unreadable("I could not read those units.")
    for name in _NAME.findall(text):
        if name not in UNITS:
            raise Unreadable(f"I do not know the unit '{name}'.")
    try:
        value = parse_expr(
            text,
            local_dict=UNITS,
            global_dict={
                "Integer": sp.Integer,
                "Float": sp.Float,
                "Rational": sp.Rational,
                "Symbol": sp.Symbol,
                "__builtins__": {},
            },
            transformations=_UNIT_TRANSFORMS,
        )
    except Exception as exc:
        raise Unreadable("I could not read those units.") from exc
    return value


def _si(unit: sp.Expr) -> tuple[float, sp.Expr]:
    """(factor, dimension) of a unit expression in SI base units."""
    coeff, rest = u.convert_to(unit, BASE).as_coeff_Mul()
    return float(coeff), rest


def _quantity(text: str) -> tuple[float, str]:
    match = _QUANTITY.match(text or "")
    if not match:
        raise Unreadable("Start with a number, then the units.")
    number = re.sub(r"\s*(?:x|×|\*)\s*10\s*\^?\s*", "e", match.group(1)).replace(" ", "")
    return float(number), match.group(2)


def numeric(
    expected: float, given: str, unit: str = "", rel_tol: float = 0.01, abs_tol: float = 0.0
) -> dict:
    """Is the number (with units) right to within a tolerance? Units are converted, so 3.6 km/h
    is accepted for 1 m/s. Says why when wrong: missing or wrong units, a sign, a power of ten."""
    try:
        value, unit_text = _quantity(given)
        want_unit, got_unit = _unit(unit), _unit(unit_text)
        want_factor, want_dim = _si(want_unit)
        got_factor, got_dim = _si(got_unit)
    except (Unreadable, ValueError) as exc:
        return _result(
            "unreadable",
            str(exc) if isinstance(exc, Unreadable) else "I could not read that number.",
        )
    if unit and not unit_text.strip():
        return _result("incorrect", f"Include the units ({unit}).", "missing_units")
    if got_dim != want_dim:
        return _result(
            "incorrect",
            f"Those units do not measure the same thing as {unit or 'a pure number'}.",
            "wrong_units",
        )
    given_si, expected_si = value * got_factor, expected * want_factor
    error = abs(given_si - expected_si)
    if error <= max(abs_tol * want_factor, rel_tol * abs(expected_si)):
        return _result("correct", error=error)
    if expected_si and abs(given_si + expected_si) <= rel_tol * abs(expected_si):
        return _result("incorrect", "The size is right but the sign is wrong.", "sign")
    if expected_si and given_si:
        exponent = math.log10(abs(given_si / expected_si))
        if abs(exponent - round(exponent)) < 0.02 and round(exponent) != 0:
            return _result(
                "incorrect",
                f"Off by a factor of 10^{round(exponent)}: check the units or the decimal point.",
                "power_of_ten",
            )
    return _result("incorrect", "That value is outside the allowed range.", "")


def run(request: str) -> str:
    """JSON in, JSON out: the single entry point the browser worker calls."""
    try:
        r = json.loads(request)
        op = r["op"]
        if op == "equivalent":
            out = equivalent(r["expected"], r["given"])
        elif op == "equation":
            out = equation_equivalent(r["expected"], r["given"])
        elif op == "steps":
            out = steps(r["lines"], r.get("expected"))
        elif op == "numeric":
            out = numeric(
                float(r["expected"]),
                r["given"],
                r.get("unit", ""),
                float(r.get("rel_tol", 0.01)),
                float(r.get("abs_tol", 0)),
            )
        else:
            out = _result("unreadable", "Unknown check.")
    except (KeyError, TypeError, ValueError) as exc:
        out = _result("unreadable", f"Bad request: {exc}")
    return json.dumps(out)
