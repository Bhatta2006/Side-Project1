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
