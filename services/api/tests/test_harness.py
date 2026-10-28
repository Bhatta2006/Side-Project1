"""The harness: verified capabilities, sandboxed, with one contract for every caller."""

import asyncio
import dataclasses
import json

from socrat import harness
from socrat.assistant.tools import Toolbox
from socrat.catalog.registry import default_catalog
from socrat.harness import registry, sandbox


def test_a_capability_checks_math_and_reports_the_slip():
    ok = harness.call(
        "math.check", {"op": "equivalent", "expected": "(x+1)^2", "given": "x^2+2x+1"}
    )
    assert ok.ok and ok.output["verdict"] == "correct"
    wrong = harness.call("math.check", {"op": "equivalent", "expected": "x^2", "given": "-x^2"})
    assert wrong.output["verdict"] == "incorrect" and wrong.output["hint"] == "sign"
    units = harness.call(
        "math.check", {"op": "numeric", "expected": "9.8", "given": "9.8", "unit": "m/s^2"}
    )
    assert units.output["hint"] == "missing_units"


def test_bad_requests_are_results_not_exceptions():
    assert "No capability" in harness.call("nope.nothing", {}).error
    bad = harness.call("math.check", {"op": "differentiate"})
    assert not bad.ok and bad.error.startswith("Invalid op")
    extra = harness.call("math.check", {"op": "equivalent", "evil": 1})
    assert not extra.ok
    hostile = harness.call(
        "math.check", {"op": "equivalent", "expected": "x", "given": "__import__('os')"}
    )
    assert hostile.ok and hostile.output["verdict"] == "unreadable"


def test_a_slow_call_is_killed_and_the_next_call_works(monkeypatch):
    sandbox.shutdown()
    monkeypatch.setattr(sandbox, "GRACE", 0.0)
    slow = dataclasses.replace(registry.capabilities()["math.check"], timeout=0.001)
    monkeypatch.setitem(registry._REGISTRY, "math.check", slow)
    result = harness.call("math.check", {"op": "equivalent", "expected": "x", "given": "x"})
    assert not result.ok and "longer than" in result.error
    monkeypatch.undo()
    again = harness.call("math.check", {"op": "equivalent", "expected": "x", "given": "x"})
    assert again.ok and again.output["verdict"] == "correct"


def test_the_tutor_gets_the_capability_as_a_tool_only_when_the_engine_is_on():
    plain = Toolbox(None, default_catalog(), "u")
    engineered = Toolbox(None, default_catalog(), "u", engine_tools=True)
    assert "math_check" not in {s.name for s in plain.specs}
    spec = next(s for s in engineered.specs if s.name == "math_check")
    assert spec.parameters["required"] == ["op"]
    text, failed = asyncio.run(
        engineered.run("math_check", {"op": "equation", "expected": "x=3", "given": "2x+1=7"})
    )
    assert not failed and json.loads(text)["verdict"] == "correct"
    text, failed = asyncio.run(engineered.run("math_check", {"op": "bogus"}))
    assert failed and text.startswith("Error:")
    text, failed = asyncio.run(plain.run("math_check", {"op": "equation"}))
    assert failed  # not offered, so not runnable
