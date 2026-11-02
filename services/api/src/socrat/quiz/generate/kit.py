"""One generator for a pattern's code items: predict (B2), fill the blank (B3), fix (B4).

A pattern module describes its correct program per language and what can go wrong; the
kit samples inputs, builds the item and checks it in Python before returning it, so the
verifier rarely has to reject anything. The verifier still re-runs every item in every
language: these checks only choose inputs.
"""

import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

from socrat.catalog.schema import Language
from socrat.quiz.generate import mutate
from socrat.quiz.generate.framework import BLANK, Draft, Option, run_python

Code = dict[str, str]
Lines = dict[str, str]  # language -> one whole line (stripped)


def typed(code: dict[str, str]) -> dict[Language, str]:
    """Code keyed by language, as the Draft model expects."""
    return cast(dict[Language, str], code)


def lines(python: str, cpp: str | None = None, java: str | None = None) -> Lines:
    """One line per language; C++ and Java share a line unless Java differs."""
    c = cpp if cpp is not None else python
    return {"python": python, "cpp": c, "java": java if java is not None else c}


def edit(old: Lines, new: Lines) -> mutate.Edit:
    return {lang: (old[lang], new[lang]) for lang in old}


@dataclass(frozen=True)
class Blank:
    """A line to blank out, and wrong lines (with their misconception) to offer instead."""

    line: Lines
    wrong: list[tuple[Lines, str]]


@dataclass(frozen=True)
class Fix:
    """A defect from the catalogue: the edit that introduces it, and how to describe the fix."""

    defect: str
    edit: mutate.Edit
    text: str
    why: str


@dataclass(frozen=True)
class Decoy:
    """An edit that looks like a fix but is not one."""

    edit: mutate.Edit
    text: str
    misconception: str


@dataclass
class Spec:
    sample: Callable[[Any, dict], dict]  # (rng, params) -> values
    program: Callable[[dict], Code]  # values -> correct snippet per language
    answer: Callable[[dict], str]  # values -> reference output (brute force)
    wrong: Callable[[dict], list[tuple[str, str]]]  # values -> (wrong output, misconception)
    predict: str  # prompt for B2
    fill: Callable[[dict], str]  # values -> prompt for B3
    fix: Callable[[dict], str]  # values -> prompt for B4
    explain: Callable[[dict, str], str]  # (values, answer) -> explanation
    blanks: list[Blank] = field(default_factory=list)
    fixes: list[Fix] = field(default_factory=list)
    decoys: list[Decoy] = field(default_factory=list)
    tries: int = 200
    # Bands of the three item kinds. Tracing a long algorithm by hand (Dijkstra, union-find
    # with path compression) is harder than the default predict/fill/fix ladder suggests.
    bands: tuple[int, int, int] = (2, 3, 4)

    @property
    def defects(self) -> dict[str, Fix]:
        return {f.defect: f for f in self.fixes}


def blank_out(code: Code, line: Lines) -> Code:
    """The snippet with ``line`` replaced by the blank, indentation kept."""
    return {lang: mutate.apply_line(text, line[lang], BLANK) for lang, text in code.items()}


STEP_LIMIT = 200_000


class TooManySteps(Exception):
    pass


def prints(code: str, limit: int = STEP_LIMIT) -> str | None:
    """Output of a Python variant, or None if it crashes or runs too long (likely forever)."""
    steps = 0

    def tracer(frame, event, arg):
        nonlocal steps
        steps += 1
        if steps > limit:
            raise TooManySteps
        return tracer

    previous = sys.gettrace()
    sys.settrace(tracer)
    try:
        return run_python(code)
    except Exception:  # noqa: BLE001 - a crashing or endless variant prints nothing useful
        return None
    finally:
        sys.settrace(previous)


def predict(spec: Spec, values: dict, code: Code, answer: str) -> Draft | None:
    distractors: list[tuple[str, str]] = []
    for value, tag in spec.wrong(values):
        if value != answer and value not in [v for v, _ in distractors]:
            distractors.append((value, tag))
    if len(distractors) < 3:
        return None
    options = [Option(text=answer)] + [Option(text=v, misconception=t) for v, t in distractors[:3]]
    return Draft(
        prompt=spec.predict,
        code=typed(code),
        options=options,
        answer=0,
        explanation=spec.explain(values, answer),
        band=spec.bands[0],
        format="output_prediction",
        values=values,
    )


def fill(spec: Spec, rng, values: dict, code: Code, answer: str, blank: Blank) -> Draft | None:
    if not mutate.applicable(code, {lang: (blank.line[lang], "") for lang in code}):
        return None
    shown = blank_out(code, blank.line)
    wrong: list[Option] = []
    for lines, tag in blank.wrong:
        if lines["python"] in [w.text for w in wrong] or lines["python"] == blank.line["python"]:
            continue
        printed = prints(shown["python"].replace(BLANK, lines["python"]))
        if printed is None or printed == answer:
            continue  # crashes, or is right on this input (ambiguous)
        wrong.append(Option(text=lines["python"], misconception=tag, fill=typed(dict(lines))))
    if len(wrong) < 3:
        return None
    rng.shuffle(wrong)
    right = Option(text=blank.line["python"], fill=typed(dict(blank.line)))
    return Draft(
        prompt=spec.fill(values),
        code=typed(shown),
        options=[right, *wrong[:3]],
        answer=0,
        explanation=spec.explain(values, answer),
        band=spec.bands[1],
        format="fill_blank",
        values=values,
    )


def fix(spec: Spec, rng, values: dict, code: Code, answer: str, chosen: Fix) -> Draft | None:
    if not mutate.applicable(code, chosen.edit):
        return None
    buggy = mutate.apply(code, chosen.edit)
    shown_output = prints(buggy["python"])
    if shown_output is None or shown_output == answer:
        return None  # the defect must run and be visible on this input
    decoys: list[Option] = []
    for decoy in spec.decoys:
        if decoy.text in [d.text for d in decoys] or not mutate.applicable(buggy, decoy.edit):
            continue
        changed = mutate.apply(buggy, decoy.edit)
        printed = prints(changed["python"])
        if printed is None or printed == answer:
            continue  # crashes, or actually fixes the bug on this input
        decoys.append(
            Option(text=decoy.text, misconception=decoy.misconception, variant=typed(changed))
        )
    if len(decoys) < 3:
        return None
    rng.shuffle(decoys)
    right = Option(
        text=chosen.text, variant=typed(mutate.apply(buggy, mutate.reverse(chosen.edit)))
    )
    return Draft(
        prompt=spec.fix(values),
        code=typed(buggy),
        options=[right, *decoys[:3]],
        answer=0,
        explanation=f"{chosen.why} {spec.explain(values, answer)}",
        band=spec.bands[2],
        format="bug_spot",
        values=values,
    )


def generate(spec: Spec, rng, params: dict) -> Draft:
    kinds = ["predict"] + (["fill"] if spec.blanks else []) + (["fix"] if spec.fixes else [])
    kind = rng.choice(kinds)
    # Pick the blank or defect once, then search for inputs that make it a good item;
    # re-picking per try would drift toward the easiest blanks and defects.
    blank = rng.choice(spec.blanks) if kind == "fill" else None
    chosen = rng.choice(spec.fixes) if kind == "fix" else None
    for _ in range(spec.tries):
        values = spec.sample(rng, params)
        code = spec.program(values)
        answer = spec.answer(values)
        # An author error (a line that is not in the program, e.g. because of a trailing
        # comment) would otherwise look like 200 unlucky samples.
        if blank is not None and not mutate.applicable(
            code, {k: (blank.line[k], "") for k in code}
        ):
            raise ValueError(f"blank line {blank.line['python']!r} is not in the program")
        if chosen is not None and not mutate.applicable(code, chosen.edit):
            raise ValueError(f"defect {chosen.defect}: its line is not in the program")
        if prints(code["python"]) != answer:
            raise ValueError(f"the Python program disagrees with the reference on {values}")
        if kind == "predict":
            made = predict(spec, values, code, answer)
        elif blank is not None:
            made = fill(spec, rng, values, code, answer, blank)
        else:
            assert chosen is not None
            made = fix(spec, rng, values, code, answer, chosen)
        if made is not None:
            return made
    what = blank.line["python"] if blank else chosen.defect if chosen else kind
    raise ValueError(f"no {kind} item for {what!r} after {spec.tries} tries; widen the parameters")
