"""The built-in capabilities. A new subject adds its own here (or in its own module imported here)."""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from socrat.checks import engine as checks
from socrat.harness.registry import Capability, register


class MathCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["equivalent", "equation", "steps", "numeric"]
    expected: str | None = Field(default=None, max_length=200)
    given: str | None = Field(default=None, max_length=200)
    lines: list[str] | None = Field(default=None, max_length=30)
    unit: str = Field(default="", max_length=40)
    rel_tol: float = Field(default=0.01, ge=0, le=1)
    abs_tol: float = Field(default=0, ge=0)


def _math_check(arguments: dict) -> dict:
    return json.loads(checks.run(json.dumps(arguments)))


MATH_CHECK = register(
    Capability(
        name="math.check",
        summary=(
            "Check math with a computer algebra system instead of guessing. op=equivalent: do "
            "`expected` and `given` mean the same expression? op=equation: same solution set? "
            "op=steps: does each line in `lines` follow from the one before (reports the first "
            "line that does not)? op=numeric: is the number in `given` (with units) equal to "
            "`expected` in `unit`? Use it before telling a learner their working is right or wrong."
        ),
        input=MathCheck,
        run=_math_check,
        parameters={
            "type": "object",
            "properties": {
                "op": {"type": "string", "enum": ["equivalent", "equation", "steps", "numeric"]},
                "expected": {"type": "string", "description": "The reference answer."},
                "given": {"type": "string", "description": "What the learner wrote."},
                "lines": {"type": "array", "items": {"type": "string"}},
                "unit": {"type": "string", "description": "Expected unit for numeric, e.g. m/s."},
            },
            "required": ["op"],
        },
    )
)


class PhysicsSimulate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = Field(min_length=1, max_length=40)
    params: dict[str, float] = Field(default_factory=dict, max_length=8)


def _physics_simulate(arguments: dict) -> dict:
    from socrat.harness import physics

    return physics.simulate(arguments["model"], arguments.get("params", {}))


PHYSICS_SIMULATE = register(
    Capability(
        name="physics.simulate",
        summary=(
            "Run a vetted physics experiment and get its true results with units, instead of "
            "estimating. model is one of projectile (speed m/s, angle deg, height m, gravity "
            "m/s^2), free_fall (height, gravity), pendulum (length m, gravity, amplitude deg), "
            "spring_mass (mass kg, stiffness N/m, amplitude m), circuit (voltage V, resistance "
            "ohm), wave (frequency Hz, wavelength m, amplitude m), refraction (n1, n2, angle_in deg), heating (mass kg, specific_heat J/kg/K, power W, start_temp C, rise K). Use it before telling a learner what an experiment will do."
        ),
        input=PhysicsSimulate,
        run=_physics_simulate,
        parameters={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "enum": [
                        "projectile",
                        "free_fall",
                        "pendulum",
                        "spring_mass",
                        "circuit",
                        "wave",
                        "refraction",
                        "heating",
                    ],
                },
                "params": {"type": "object", "additionalProperties": {"type": "number"}},
            },
            "required": ["model", "params"],
        },
    )
)


class JudgeCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected: str = Field(max_length=20_000)
    stdout: str = Field(default="", max_length=20_000)
    exit_code: int = 0
    timed_out: bool = False
    stderr: str = Field(default="", max_length=2_000)


class CodeJudge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cases: list[JudgeCase] = Field(min_length=1, max_length=50)


def _code_judge(arguments: dict) -> dict:
    """Verdicts for runs that already happened. Running code is the execution service's job (it
    isolates, limits and queues it); judging what came back is this deterministic step, with the
    same comparison the judge uses for learners' submissions."""
    from socrat.execution.protocol import same_output

    verdicts = []
    for i, case in enumerate(arguments["cases"]):
        if case.get("timed_out"):
            verdict = "time_limit"
        elif case.get("exit_code", 0) != 0:
            verdict = "runtime_error"
        elif same_output(case.get("stdout", ""), case["expected"]):
            verdict = "accepted"
        else:
            verdict = "wrong_answer"
        verdicts.append(dict(case=i, verdict=verdict))
    passed = sum(v["verdict"] == "accepted" for v in verdicts)
    first = next((v["case"] for v in verdicts if v["verdict"] != "accepted"), None)
    return dict(
        verdicts=verdicts,
        passed=passed,
        total=len(verdicts),
        score=round(passed / len(verdicts), 4),
        first_failure=first,
    )


CODE_JUDGE = register(
    Capability(
        name="code.judge",
        summary=(
            "Judge the outputs of code runs against expected outputs: accepted, wrong_answer, "
            "runtime_error or time_limit per case, with a pass count. It judges runs that "
            "already happened; it does not run code."
        ),
        input=CodeJudge,
        run=_code_judge,
        parameters={
            "type": "object",
            "properties": {
                "cases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "expected": {"type": "string"},
                            "stdout": {"type": "string"},
                            "exit_code": {"type": "integer"},
                            "timed_out": {"type": "boolean"},
                        },
                        "required": ["expected"],
                    },
                }
            },
            "required": ["cases"],
        },
        tutor=False,  # the tutor cannot run code, so it has nothing to judge
    )
)
