"""Vetted physics experiments: closed-form models the lab computes, so the truth is never a model's claim.

Each model declares its parameters (with units and limits) and the quantities it reports. The lab
asks the learner to predict one reported quantity; the harness then runs the experiment and
compares. Adding an experiment is adding an entry here with a test against a known result.
"""

import math
from dataclasses import dataclass

G = 9.81
POINTS = 60


@dataclass(frozen=True)
class Param:
    unit: str
    low: float
    high: float
    default: float


@dataclass(frozen=True)
class Model:
    title: str
    params: dict[str, Param]
    outputs: dict[str, str]  # reported quantity -> unit
    run: object  # (values) -> (outputs, trace)


def _projectile(p: dict) -> tuple[dict, list]:
    v, angle, h0, g = p["speed"], math.radians(p["angle"]), p["height"], p["gravity"]
    vx, vy = v * math.cos(angle), v * math.sin(angle)
    flight = (vy + math.sqrt(vy * vy + 2 * g * h0)) / g
    peak = h0 + vy * vy / (2 * g) if vy > 0 else h0
    out = dict(
        range=vx * flight,
        flight_time=flight,
        max_height=peak,
        impact_speed=math.hypot(vx, vy - g * flight),
    )
    trace = [
        [vx * t, h0 + vy * t - 0.5 * g * t * t]
        for t in (flight * i / POINTS for i in range(POINTS + 1))
    ]
    return out, trace


def _free_fall(p: dict) -> tuple[dict, list]:
    h, g = p["height"], p["gravity"]
    fall = math.sqrt(2 * h / g)
    trace = [[t, h - 0.5 * g * t * t] for t in (fall * i / POINTS for i in range(POINTS + 1))]
    return dict(fall_time=fall, impact_speed=g * fall), trace


def _pendulum(p: dict) -> tuple[dict, list]:
    length, g, amp = p["length"], p["gravity"], math.radians(p["amplitude"])
    period = 2 * math.pi * math.sqrt(length / g)  # small-angle model (amplitude <= 15 degrees)
    trace = [
        [t, math.degrees(amp * math.cos(2 * math.pi * t / period))]
        for t in (2 * period * i / POINTS for i in range(POINTS + 1))
    ]
    return dict(period=period, frequency=1 / period), trace


def _spring(p: dict) -> tuple[dict, list]:
    m, k, amp = p["mass"], p["stiffness"], p["amplitude"]
    omega = math.sqrt(k / m)
    period = 2 * math.pi / omega
    trace = [
        [t, amp * math.cos(omega * t)] for t in (2 * period * i / POINTS for i in range(POINTS + 1))
    ]
    return dict(
        period=period, frequency=1 / period, max_speed=amp * omega, energy=0.5 * k * amp * amp
    ), trace


def _circuit(p: dict) -> tuple[dict, list]:
    volts, ohms = p["voltage"], p["resistance"]
    amps = volts / ohms
    return dict(current=amps, power=volts * amps), []


MODELS: dict[str, Model] = {
    "projectile": Model(
        "Projectile launched from a height",
        {
            "speed": Param("m/s", 1, 100, 20),
            "angle": Param("deg", 0, 90, 45),
            "height": Param("m", 0, 100, 0),
            "gravity": Param("m/s^2", 1, 25, G),
        },
        {"range": "m", "flight_time": "s", "max_height": "m", "impact_speed": "m/s"},
        _projectile,
    ),
    "free_fall": Model(
        "Object dropped from rest",
        {"height": Param("m", 0.1, 1000, 20), "gravity": Param("m/s^2", 1, 25, G)},
        {"fall_time": "s", "impact_speed": "m/s"},
        _free_fall,
    ),
    "pendulum": Model(
        "Simple pendulum (small swings)",
        {
            "length": Param("m", 0.05, 20, 1),
            "gravity": Param("m/s^2", 1, 25, G),
            "amplitude": Param("deg", 1, 15, 10),
        },
        {"period": "s", "frequency": "Hz"},
        _pendulum,
    ),
    "spring_mass": Model(
        "Mass on a spring",
        {
            "mass": Param("kg", 0.01, 100, 1),
            "stiffness": Param("N/m", 1, 5000, 100),
            "amplitude": Param("m", 0.01, 2, 0.1),
        },
        {"period": "s", "frequency": "Hz", "max_speed": "m/s", "energy": "J"},
        _spring,
    ),
    "circuit": Model(
        "Resistor on a battery",
        {"voltage": Param("V", 0.1, 1000, 12), "resistance": Param("ohm", 0.1, 100000, 100)},
        {"current": "A", "power": "W"},
        _circuit,
    ),
}


def problems(model: str, params: dict) -> list[str]:
    """Why these parameters cannot run (unknown model, missing or out-of-range value)."""
    found = MODELS.get(model)
    if found is None:
        return [f"unknown experiment {model!r}; choose one of {sorted(MODELS)}"]
    out = []
    for name, spec in found.params.items():
        value = params.get(name)
        if not isinstance(value, int | float) or isinstance(value, bool):
            out.append(f"{name} ({spec.unit}) is needed")
        elif not spec.low <= value <= spec.high:
            out.append(f"{name} must be {spec.low:g} to {spec.high:g} {spec.unit}")
    out += [f"{name} is not a parameter of {model}" for name in params if name not in found.params]
    return out


def simulate(model: str, params: dict) -> dict:
    """Run one experiment: the reported quantities (value and unit) and a trace to draw."""
    if bad := problems(model, params):
        raise ValueError("; ".join(bad))
    found = MODELS[model]
    values = {k: float(v) for k, v in params.items()}
    outputs, trace = found.run(values)
    return dict(
        model=model,
        title=found.title,
        params={k: dict(value=values[k], unit=found.params[k].unit) for k in found.params},
        outputs={k: dict(value=round(v, 6), unit=found.outputs[k]) for k, v in outputs.items()},
        trace=[[round(x, 5), round(y, 5)] for x, y in trace],
    )
