"""Seed two demo courses for trying the studios by hand: a physics lab and a math workbench.

Usage (from the repo root, with the demo environment loaded so SOCRAT_DATABASE_URL is set):
    python scripts/dev/seed_lab_demo.py

Safe to run again: it replaces the two demo courses. Sign in as an admin to see the studios.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "api" / "src"))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from socrat.catalog import generated  # noqa: E402
from socrat.catalog.registry import default_catalog  # noqa: E402
from socrat.catalog.schema import Course  # noqa: E402

LINKS = [
    dict(
        title="Physics overview",
        url="https://en.wikipedia.org/wiki/Physics",
        kind="article",
        source="Wikipedia",
        minutes=10,
    ),
    dict(
        title="PhET simulations",
        url="https://phet.colorado.edu/",
        kind="interactive",
        source="PhET",
        minutes=15,
    ),
]


def rubric(law: str, why: str) -> list[dict]:
    return [
        dict(criterion="Names the law", points=2, look_for=law),
        dict(criterion="Explains the result", points=2, look_for=why),
    ]


def experiment(id, prompt, model, params, predict, vary, explanation, law, why, hints=(), level=1):
    return dict(
        id=id,
        prompt=prompt,
        model=model,
        params=params,
        predict=predict,
        vary=vary,
        hints=list(hints),
        difficulty=level,
        explanation=explanation,
        rubric=rubric(law, why),
    )


def concept(id, title, module, lesson, experiments=(), exercises=()):
    return dict(
        id=id,
        title=title,
        summary=f"Hands-on: {title.lower()}.",
        module=module,
        difficulty=2,
        estimated_minutes=10,
        lesson=lesson,
        key_points=["Predict first", "Then compare"],
        resources=LINKS,
        quiz=[
            dict(
                id="q1",
                prompt=f"Which best describes {title.lower()}?",
                options=["A", "B"],
                answer=0,
                explanation="Option A is the standard description.",
                difficulty=1,
            ),
            dict(
                id="q2",
                prompt=f"What do you do first in the {title.lower()} lab?",
                options=["Predict", "Peek"],
                answer=0,
                explanation="You commit to a prediction.",
                difficulty=1,
            ),
        ],
        experiments=list(experiments),
        exercises=list(exercises),
        status="live",
    )


def lesson(topic: str, body: str) -> str:
    return (
        f"## {topic}\n\n{body}\n\nIn the lab you first predict a number, then the simulation runs "
        "and shows the true result. Move the sliders afterwards to see which quantities change, "
        "and explain why in your own words. The point is to build an intuition you can check."
    )


PHYSICS = [
    concept(
        "projectile-motion",
        "Projectile motion",
        "motion",
        lesson(
            "Projectile motion",
            "Sideways speed stays constant while gravity changes the vertical speed.",
        ),
        [
            experiment(
                "level-ground",
                "A ball is launched at 20 m/s at 45 degrees from level ground on Earth. How far does it land?",
                "projectile",
                dict(speed=20, angle=45, height=0, gravity=9.81),
                "range",
                "angle",
                "Range = v^2 sin(2 theta) / g, which is largest at 45 degrees on level ground.",
                "Uses range = v^2 sin(2 theta)/g or splits the motion into horizontal and vertical parts.",
                "Says 45 degrees maximises range because sin(2 theta) peaks there.",
                ["Split the speed into two parts."],
            ),
            experiment(
                "from-a-cliff",
                "A stone is thrown at 15 m/s at 30 degrees from a 10 m cliff. How long is it in the air?",
                "projectile",
                dict(speed=15, angle=30, height=10, gravity=9.81),
                "flight_time",
                "height",
                "Solve 10 + v sin(theta) t - g t^2 / 2 = 0 for t; the extra height adds time.",
                "Sets vertical position to zero and solves the quadratic in t.",
                "Says the cliff adds air time because it must fall further.",
                level=3,
            ),
        ],
    ),
    concept(
        "free-fall",
        "Free fall",
        "motion",
        lesson(
            "Free fall",
            "Without air, everything falls with the same acceleration, whatever its mass.",
        ),
        [
            experiment(
                "tall-drop",
                "A ball is dropped from rest from 45 m on Earth. How long until it lands?",
                "free_fall",
                dict(height=45, gravity=9.81),
                "fall_time",
                "height",
                "t = sqrt(2h/g): time grows with the square root of height, and mass does not appear.",
                "Uses h = g t^2 / 2 for a drop from rest.",
                "Says mass does not matter and time depends on height and g.",
                ["Start from rest."],
            ),
            experiment(
                "on-the-moon",
                "The same kind of drop is made from 10 m on the Moon (gravity 1.62). How fast is it going when it lands?",
                "free_fall",
                dict(height=10, gravity=1.62),
                "impact_speed",
                "gravity",
                "v = sqrt(2 g h): weaker gravity gives a lower landing speed from the same height.",
                "Uses v = sqrt(2 g h) or v = g t.",
                "Says lower g means less speed gained over the drop.",
                level=2,
            ),
        ],
    ),
    concept(
        "pendulum",
        "The pendulum",
        "oscillations",
        lesson(
            "The pendulum",
            "For small swings a pendulum's period depends on its length and gravity only.",
        ),
        [
            experiment(
                "one-metre",
                "A 1 m pendulum swings through a small angle on Earth. What is its period?",
                "pendulum",
                dict(length=1, gravity=9.81, amplitude=10),
                "period",
                "length",
                "T = 2 pi sqrt(L/g), about 2 s for 1 m.",
                "Uses T = 2 pi sqrt(L/g).",
                "Says period depends on length and g, not on the bob's mass.",
            ),
            experiment(
                "quarter-length",
                "Now the pendulum is only 0.25 m long. What is its period?",
                "pendulum",
                dict(length=0.25, gravity=9.81, amplitude=10),
                "period",
                "length",
                "A quarter of the length halves the period, since T goes as the square root of L.",
                "Uses T = 2 pi sqrt(L/g).",
                "Says quartering L halves T because of the square root.",
                level=2,
            ),
        ],
    ),
    concept(
        "spring-mass",
        "Mass on a spring",
        "oscillations",
        lesson("Mass on a spring", "A heavier mass on the same spring oscillates more slowly."),
        [
            experiment(
                "one-kilo",
                "A 1 kg mass hangs on a spring of stiffness 100 N/m and is pulled 0.1 m. What is its period?",
                "spring_mass",
                dict(mass=1, stiffness=100, amplitude=0.1),
                "period",
                "mass",
                "T = 2 pi sqrt(m/k), about 0.63 s.",
                "Uses T = 2 pi sqrt(m/k).",
                "Says period grows with mass and shrinks with stiffness, not amplitude.",
            ),
            experiment(
                "four-kilos",
                "The mass is now 4 kg on the same spring. What is the period?",
                "spring_mass",
                dict(mass=4, stiffness=100, amplitude=0.1),
                "period",
                "mass",
                "Four times the mass doubles the period.",
                "Uses T = 2 pi sqrt(m/k).",
                "Says four times the mass gives twice the period through the square root.",
                level=2,
            ),
        ],
    ),
    concept(
        "waves",
        "Waves",
        "waves-and-light",
        lesson("Waves", "A wave's speed is its frequency times its wavelength."),
        [
            experiment(
                "rope-wave",
                "A wave on a rope has frequency 2 Hz and wavelength 1.5 m. How fast does it travel?",
                "wave",
                dict(frequency=2, wavelength=1.5, amplitude=0.5),
                "speed",
                "wavelength",
                "v = f x wavelength = 3 m/s.",
                "Uses v = f times wavelength.",
                "Says each crest advances one wavelength per period.",
            ),
            experiment(
                "sound",
                "Sound from a 440 Hz note has wavelength 0.78 m. What is the speed of sound?",
                "wave",
                dict(frequency=440, wavelength=0.78, amplitude=0.1),
                "speed",
                "frequency",
                "v = f x wavelength = 343 m/s.",
                "Uses v = f times wavelength.",
                "Says the product of frequency and wavelength is the speed.",
                level=2,
            ),
        ],
    ),
    concept(
        "refraction",
        "Refraction of light",
        "waves-and-light",
        lesson(
            "Refraction", "Light bends towards the normal when it enters a slower, denser medium."
        ),
        [
            experiment(
                "air-to-glass",
                "Light in air hits glass (n = 1.5) at 30 degrees to the normal. At what angle does it travel inside the glass?",
                "refraction",
                dict(n1=1, n2=1.5, angle_in=30),
                "refracted_angle",
                "angle_in",
                "Snell's law: n1 sin(theta1) = n2 sin(theta2), so sin(theta2) = 0.5 / 1.5.",
                "Uses Snell's law n1 sin(theta1) = n2 sin(theta2).",
                "Says it bends towards the normal because the glass is optically denser.",
                ["Use Snell's law."],
            ),
            experiment(
                "glass-to-air",
                "Light inside glass (n = 1.5) hits the air at 20 degrees to the normal. At what angle does it leave? (Try bigger angles afterwards.)",
                "refraction",
                dict(n1=1.5, n2=1, angle_in=20),
                "refracted_angle",
                "angle_in",
                "Going from dense to less dense it bends away from the normal; past the critical angle it reflects totally.",
                "Uses Snell's law n1 sin(theta1) = n2 sin(theta2).",
                "Says it bends away from the normal, with total internal reflection past the critical angle.",
                level=3,
            ),
        ],
    ),
    concept(
        "circuits",
        "Simple circuits",
        "electricity-and-heat",
        lesson(
            "Simple circuits",
            "Current is voltage divided by resistance, and power is voltage times current.",
        ),
        [
            experiment(
                "battery-resistor",
                "A 12 V battery drives a 100 ohm resistor. What current flows?",
                "circuit",
                dict(voltage=12, resistance=100),
                "current",
                "resistance",
                "I = V / R = 0.12 A.",
                "Uses Ohm's law I = V/R.",
                "Says more resistance means less current for the same voltage.",
            ),
            experiment(
                "how-much-power",
                "A 9 V battery drives a 30 ohm resistor. How much power does it use?",
                "circuit",
                dict(voltage=9, resistance=30),
                "power",
                "voltage",
                "P = V I = V^2 / R = 2.7 W.",
                "Uses P = V times I together with Ohm's law.",
                "Says power grows with the square of voltage.",
                level=2,
            ),
        ],
    ),
    concept(
        "heating",
        "Heating water",
        "electricity-and-heat",
        lesson(
            "Heating water",
            "The energy needed is mass times specific heat times the temperature rise.",
        ),
        [
            experiment(
                "kettle",
                "A 1000 W heater warms 0.5 kg of water (specific heat 4186 J/kg/K) from 20 C by 40 K. How long does it take?",
                "heating",
                dict(mass=0.5, specific_heat=4186, power=1000, start_temp=20, rise=40),
                "time",
                "power",
                "Energy = m c delta-T = 83,720 J, and time = energy / power.",
                "Uses Q = m c delta-T and time = Q / P.",
                "Says doubling the power halves the time for the same energy.",
                ["Find the energy first."],
            ),
            experiment(
                "big-pot",
                "A 2000 W heater warms 2 kg of water by 30 K. How much energy does it deliver?",
                "heating",
                dict(mass=2, specific_heat=4186, power=2000, start_temp=20, rise=30),
                "energy",
                "mass",
                "Energy = m c delta-T = 251,160 J, whatever the power.",
                "Uses Q = m c delta-T.",
                "Says the power only changes how fast the energy arrives, not how much is needed.",
                level=2,
            ),
        ],
    ),
]


def exercise(
    id, prompt, check, expected, explanation, plot=(), points=(), unit="", hints=(), level=1
):
    return dict(
        id=id,
        prompt=prompt,
        check=check,
        expected=expected,
        explanation=explanation,
        plot=list(plot),
        points=[list(p) for p in points],
        unit=unit,
        hints=list(hints),
        difficulty=level,
    )


MATH = [
    concept(
        "straight-lines",
        "Straight lines",
        "graphs",
        lesson("Straight lines", "A line y = a x + b has slope a and crosses the y axis at b."),
        exercises=[
            exercise(
                "slider-line",
                "Drag the a and b sliders until the line has slope 2 and passes through (0, 1). Then type its equation (use x).",
                "equivalent",
                "2*x+1",
                "Slope 2 and intercept 1 give y = 2x + 1.",
                plot=["a*x+b"],
                hints=["a is the slope.", "b is where it crosses the y axis."],
            ),
            exercise(
                "fit-the-line",
                "Drag the two red handles onto the teal data points. What is the slope of your line?",
                "numeric",
                "2",
                "The points lie on y = 2x + 1, so the slope is 2.",
                points=[(-2, -3), (0, 1), (2, 5), (4, 9)],
                hints=["Rise over run between two points."],
                level=2,
            ),
            exercise(
                "fit-intercept",
                "Fit the line to this data. Where does it cross the y axis?",
                "numeric",
                "-1",
                "The points lie on y = x - 1, so the intercept is -1.",
                points=[(-2, -3), (0, -1), (2, 1), (4, 3)],
                level=2,
            ),
        ],
    ),
    concept(
        "quadratics",
        "Quadratics",
        "graphs",
        lesson(
            "Quadratics",
            "A quadratic a x^2 + b x + c is a parabola; a sets the opening, b and c shift it.",
        ),
        exercises=[
            exercise(
                "touch-axis",
                "Move the sliders until the parabola just touches the x axis at x = 1 and opens upward with a = 1. Type its equation.",
                "equivalent",
                "x^2-2*x+1",
                "Touching at x = 1 means a double root: (x-1)^2 = x^2 - 2x + 1.",
                plot=["a*x^2+b*x+c"],
                hints=["A double root means a perfect square."],
            ),
            exercise(
                "expand",
                "Expand (x + 3)^2. Your answer is drawn in red as you type; it should sit on the blue curve.",
                "equivalent",
                "x^2+6*x+9",
                "(x+3)(x+3) = x^2 + 6x + 9.",
                plot=["(x+3)^2"],
                level=2,
            ),
        ],
    ),
]


def course(id, title, tagline, description, shape, modules, concepts):
    return Course.model_validate(
        dict(
            id=id,
            title=title,
            tagline=tagline,
            description=description,
            version="0.1.0",
            languages=["python"],
            levels=[
                dict(id="brand-new", label="Brand new", description="Start at the beginning."),
                dict(
                    id="some",
                    label="Some experience",
                    description="Skip the first topic.",
                    start_concept=concepts[1]["id"],
                ),
            ],
            modules=modules,
            concepts=concepts,
            shape=shape,
        )
    )


def build() -> list[Course]:
    def modules(items):
        # One module, so no checkpoint gates stand between you and any topic.
        for c in items:
            c["module"] = "all"
        return [
            dict(
                id="all",
                title="All topics",
                summary="Every demo topic, all open.",
                concepts=[c["id"] for c in items],
            )
        ]

    return [
        course(
            "physics-lab-demo",
            "Physics Lab (demo)",
            "Predict, run, compare, explain.",
            "A demo course with one experiment topic per simulation model, for trying the lab studio.",
            dict(
                studio="lab",
                loop="predict-observe-explain",
                evidence=["numeric", "explanation"],
                tools=["simulation", "graph"],
            ),
            modules(PHYSICS),
            PHYSICS,
        ),
        course(
            "math-workbench-demo",
            "Math Workbench (demo)",
            "Graphs you can drag and fit.",
            "A demo course for trying the math workbench: parameter sliders, live answers and line fitting.",
            dict(
                studio="workbench",
                loop="solve",
                evidence=["numeric", "derivation"],
                tools=["graph", "cas"],
            ),
            modules(MATH),
            MATH,
        ),
    ]


def main() -> None:
    url = os.environ.get("SOCRAT_DATABASE_URL")
    if not url:
        raise SystemExit("Set SOCRAT_DATABASE_URL (load .env.local first).")
    base = default_catalog()
    with Session(create_engine(url)) as db, db.begin():
        for item in build():
            generated.save_course(db, base, item, status="published")
            print("seeded", item.id, f"({len(item.concepts)} topics)")


if __name__ == "__main__":
    main()
