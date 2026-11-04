"""The whole learning loop, with the model played by hand.

Every model reply below is written as a careful model would write it for this subject: the
intent parser, course architect, critic, researcher, lesson author, quiz builder, atom author,
fact checker, reviewer, experience designer and diagnostic writer. The engine around them is
real: schemas, gates, domain adapter, renderer registry, ownership, diagnostic scoring, release
and the learner's view. Swap the provider and the same code path runs against a live model.
"""

# ruff: noqa: F811
import asyncio
import json

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_learner_api import client, login  # noqa: F401
from test_learning_requests import URL, on  # noqa: F401

from socrat.assistant.gateway import Event, usage_event
from socrat.catalog.registry import default_catalog
from socrat.coursegen import diagnostic, jobs, links, outline, research
from socrat.coursegen import intent as intents
from socrat.coursegen import package as pkg
from socrat.coursegen import requests as request_routes
from socrat.engine import design
from socrat.models import Enrollment, GeneratedConcept, GenerationJob, User

REQUEST = "Teach me how electric circuits work, starting with Ohm's law"

INTENT = dict(
    subject="Electric circuits and Ohm's law",
    domain="electronics",
    goal="Predict the current, voltage and resistance in simple series and parallel circuits.",
    desired_level="beginner",
    starting_level="none",
    approach=[],
    balance="balanced",
    language="en",
    stage="teen",
    register="teen",
    code_languages=[],
    preferences=[],
    needs_physical_practice=False,
    needs_external_evaluator=False,
    verifiable="fully",
    safety_notes=[],
    clarifications=[],
    blocked="",
)


def concept(cid, title, summary, prerequisites, difficulty, minutes, objectives, misconceptions):
    return dict(
        id=cid,
        title=title,
        summary=summary,
        prerequisites=prerequisites,
        difficulty=difficulty,
        estimated_minutes=minutes,
        depth="overview",
        objectives=objectives,
        misconceptions=misconceptions,
        assessment=["quiz", "explain"],
    )


CIRCUITS = dict(
    tagline="See how voltage, current and resistance fit together, then predict real circuits.",
    description=(
        "A first course on electric circuits for a teenager with no background: what voltage, "
        "current and resistance are, Ohm's law, and how series and parallel connections change them."
    ),
    shape=dict(studio="reading", loop="read-reflect", evidence=["quiz", "explanation"], tools=[]),
    levels=[
        dict(
            id="brand-new",
            label="New to circuits",
            description="Start with the three quantities.",
            start_concept=None,
        ),
        dict(
            id="know-basics",
            label="Know the basics",
            description="Start at Ohm's law.",
            start_concept="ohms-law",
        ),
    ],
    modules=[
        dict(
            id="foundations",
            title="Foundations",
            summary="The three quantities and the law that links them.",
            concepts=[
                concept(
                    "voltage-current-resistance",
                    "Voltage, current and resistance",
                    "What each of the three quantities measures and the units they use.",
                    [],
                    1,
                    25,
                    [
                        "Describe voltage, current and resistance with an everyday analogy",
                        "Name each unit and its symbol",
                    ],
                    ["Current is used up as it goes round a circuit"],
                ),
                concept(
                    "ohms-law",
                    "Ohm's law",
                    "The relationship V = I x R and how to rearrange it.",
                    ["voltage-current-resistance"],
                    2,
                    30,
                    ["Use V = I x R to find any one quantity from the other two"],
                    ["Resistance changes whenever the voltage changes"],
                ),
                concept(
                    "series-and-parallel",
                    "Series and parallel circuits",
                    "How resistors combine and how current and voltage share out.",
                    ["ohms-law"],
                    3,
                    35,
                    ["Find the total resistance of resistors in series and in parallel"],
                    ["Adding a resistor in parallel always raises the total resistance"],
                ),
            ],
        )
    ],
)

LESSON = {
    "lesson": """## Why these three quantities matter

Every phone charger, torch and doorbell is a circuit, and to understand any of them you need three ideas: voltage, current and resistance. They are linked by one short rule, and once you see the link you can predict what a circuit will do before you build it.

## A water pipe picture

Imagine water in a closed loop of pipe with a pump. The pump is the battery, and the push it gives the water is the **voltage**, measured in volts (V). The amount of water passing a point each second is the **current**, measured in amperes (A). A narrow section of pipe makes it harder for water to flow, and that opposition is the **resistance**, measured in ohms (symbol: the Greek letter omega). Push harder (more voltage) and more flows. Narrow the pipe (more resistance) and less flows.

Work one case through. A 6 V battery is connected across a lamp that has a resistance of 3 ohms. The current is the voltage divided by the resistance, so 6 divided by 3 gives 2 A. Change only the lamp to 6 ohms: 6 divided by 6 gives 1 A. The battery did not change, but doubling the resistance halved the current. Now keep the 6 ohm lamp and use a 12 V battery: 12 divided by 6 gives 2 A. Doubling the voltage doubled the current.

## Why it works, and where the picture stops

The pipe picture explains the direction of each effect, and the numbers above show the exact size: current rises in proportion to voltage and falls as resistance rises. The picture has limits. Water can be stored in a pipe, but current is the same everywhere in a simple loop, because charge is not used up. A lamp does not consume current; it turns some of the energy each charge carries into light and heat, and the same current continues back to the battery. Many beginners think the current is smaller after the lamp than before it. Measure at both points in a real loop and you read the same value.

Do not apply the rule blindly to every part. It describes components whose resistance stays steady, such as a plain resistor at a fixed temperature. A filament lamp gets hotter as more current flows and its resistance rises, so its numbers do not follow a straight line.

## Check yourself

1. A 9 V battery drives a 3 ohm resistor. What is the current?

<details>9 divided by 3 is 3 A.</details>

2. If you replace the resistor with a 9 ohm one on the same battery, does the current go up or down, and to what?

<details>It goes down, to 1 A.</details>

3. Is current used up as it passes through a lamp? Explain.

<details>No. The same current leaves the lamp as enters it; the lamp transfers energy, not charge.</details>
""",
    "key_points": [
        "Voltage is the push, current is the flow, resistance is the opposition to the flow.",
        "Current rises with voltage and falls as resistance rises: I = V divided by R.",
        "Current is the same all the way round a simple loop; it is not used up.",
    ],
    "pitfalls": [
        "Thinking the lamp uses up current, so less leaves than enters.",
        "Treating every component as having a fixed resistance, which a hot filament does not.",
    ],
    "resources": [
        dict(
            title="Ohm's law overview",
            url="https://en.wikipedia.org/wiki/Ohm%27s_law",
            kind="article",
            source="Wikipedia",
            minutes=10,
            level="intro",
        ),
        dict(
            title="Series and parallel circuits",
            url="https://en.wikipedia.org/wiki/Series_and_parallel_circuits",
            kind="article",
            source="Wikipedia",
            minutes=12,
            level="core",
        ),
    ],
}


def mcq(n, prompt, options, answer, why, difficulty):
    return dict(
        id=f"q{n}",
        prompt=prompt,
        options=options,
        answer=answer,
        explanation=why,
        difficulty=difficulty,
    )


QUIZ = {
    "quiz": [
        mcq(
            1,
            "Which quantity is measured in amperes?",
            ["Current", "Voltage", "Resistance"],
            0,
            "Current is the flow of charge, in amperes.",
            1,
        ),
        mcq(
            2,
            "A 12 V supply drives a 4 ohm resistor. What current flows?",
            ["3 A", "48 A", "0.33 A"],
            0,
            "I = V / R = 12 / 4 = 3 A.",
            2,
        ),
        mcq(
            3,
            "The resistance in a loop is doubled and the voltage stays the same. The current:",
            ["Halves", "Doubles", "Stays the same"],
            0,
            "I = V / R, so doubling R halves I.",
            2,
        ),
        mcq(
            4,
            "In a simple loop with one lamp, the current just after the lamp is:",
            ["The same as before it", "Smaller than before it", "Zero"],
            0,
            "Charge is not used up; the same current continues.",
            3,
        ),
        mcq(
            5,
            "Which statement about resistance is correct?",
            ["It opposes the flow of current", "It stores the current", "It pushes the current"],
            0,
            "Resistance opposes flow; voltage provides the push.",
            1,
        ),
    ],
    "prompts": [
        dict(
            id="not-used-up",
            prompt="Explain why the current is the same before and after a lamp even though the lamp lights up.",
            max_words=120,
            rubric=[
                dict(
                    criterion="Charge is conserved",
                    points=2,
                    look_for="Charge flows round the loop and is not consumed.",
                ),
                dict(
                    criterion="Energy transfer",
                    points=2,
                    look_for="The lamp transfers energy carried by the charge into light and heat.",
                ),
            ],
            model_answer="Current is the flow of charge. The charge goes through the lamp and back to the battery, so the same amount passes each point each second. The lamp turns some of the energy each charge carries into light and heat.",
        )
    ],
}


def atom(aid, kind, title, objective, body, seconds, **extra):
    return dict(
        id=aid, kind=kind, title=title, objective=objective, body=body, seconds=seconds, **extra
    )


ATOMS = {
    "atoms": [
        atom(
            "hook",
            "hook",
            "A torch in your hand",
            "See why circuits matter",
            "A torch works because a loop of wire lets charge flow. Three numbers describe it.",
            20,
        ),
        atom(
            "idea",
            "concept",
            "Push, flow, opposition",
            "Name the three quantities",
            "Voltage pushes, current flows, resistance opposes. Their units are volts, amperes and ohms.",
            60,
        ),
        atom(
            "worked",
            "worked",
            "A 6 V lamp",
            "Find a current",
            "6 V across 3 ohms gives 6 / 3 = 2 A. Double the resistance and the current halves to 1 A.",
            60,
        ),
        atom(
            "predict",
            "predict",
            "Your turn",
            "Predict a current",
            "Predict before you calculate.",
            60,
            steps=[
                dict(
                    state="A 10 V supply, a 5 ohm resistor.",
                    prompt="What current flows?",
                    options=["2 A", "50 A", "0.5 A"],
                    answer=0,
                    explanation="10 divided by 5 is 2 A.",
                )
            ],
        ),
    ]
}

FACTS = {
    "claims": [
        dict(where="lesson", claim="I = V / R for a fixed resistor", verdict="correct"),
        dict(
            where="lesson",
            claim="Current is the same everywhere in a simple series loop",
            verdict="correct",
        ),
        dict(where="lesson", claim="Filament lamp resistance rises as it heats", verdict="correct"),
        dict(where="quiz:q2", claim="12 V across 4 ohms is 3 A", verdict="correct"),
    ]
}
REVIEW = dict(
    scores={d: 5 for d in pkg.DIMENSIONS},
    summary="Correct, builds from an analogy to the formula, confronts the used-up-current misconception.",
    lesson=[],
    quiz=[],
    atoms=[],
)
SIMULATION = dict(
    renderer="simulation",
    params=dict(model="circuit", inputs=dict(voltage=6, resistance=3)),
    purpose="Change voltage and resistance and watch the current respond",
    fallback_text="A table: 6 V across 3 ohms gives 2 A; across 6 ohms gives 1 A; 12 V across 6 ohms gives 2 A.",
    alt_text="Controls for voltage and resistance and a readout of the resulting current.",
)
DESIGN = {
    "visuals": [SIMULATION, dict(SIMULATION, renderer="code-studio")]
}  # the 2nd must be dropped


def dx(concept_id, answer, stem, right, wrongs):
    options = [wrongs[0], right, *wrongs[1:]]
    return dict(
        concept=concept_id,
        stem=stem,
        options=options,
        answer=1,
        why=f"Because {right.lower().rstrip('.')}.",
    )


DIAGNOSTIC = {
    "items": [
        dx(
            "voltage-current-resistance",
            1,
            "Which quantity measures how much charge flows past a point each second?",
            "Current",
            ["Voltage", "Resistance", "Power"],
        ),
        dx(
            "ohms-law",
            1,
            "A 10 V supply is across a 5 ohm resistor. What current flows?",
            "2 A",
            ["50 A", "0.5 A", "15 A"],
        ),
        dx(
            "series-and-parallel",
            1,
            "Two 4 ohm resistors are in series. The total resistance is:",
            "8 ohms",
            ["2 ohms", "4 ohms", "16 ohms"],
        ),
    ]
}
CRITIC = {"verdict": "pass", "summary": "Sequenced, objectives are testable.", "issues": []}
NO_SOURCES = {"sources": []}


class Model:
    """Answers each role from the replies above and records what it was asked."""

    def __init__(self):
        self.asked: list[str] = []
        self.table = [
            (intents.SYSTEM, "intent", [INTENT]),
            (outline.ARCHITECT, "architect", [CIRCUITS]),
            (outline.CRITIC, "critic", [CRITIC]),
            (diagnostic.SYSTEM, "diagnostic", [DIAGNOSTIC]),
            (research.RESEARCHER, "researcher", [NO_SOURCES]),
            (pkg.LESSON, "author", [LESSON]),
            (pkg.QUIZ, "quiz", [QUIZ]),
            (pkg.ATOMS, "atoms", [ATOMS]),
            (pkg.FACTS, "facts", [FACTS]),
            (pkg.REVIEW, "reviewer", [REVIEW]),
            (design.SYSTEM, "experience", [DESIGN]),
        ]

    def make(self, settings):
        model = self

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                for prefix, role, replies in model.table:
                    if system.startswith(prefix):
                        model.asked.append(role)
                        yield Event("text", text=json.dumps(replies[0]))
                        yield usage_event(1500, 4000)
                        return
                raise AssertionError(f"unexpected role: {system[:60]}")

        return Provider()


@pytest.fixture
def web(monkeypatch):
    """Resource links answer 200 for the lesson's two pages; no real DNS or HTTP happens."""
    monkeypatch.setattr(links, "public_https", lambda url: url.startswith("https://"))
    known = {r["url"] for r in LESSON["resources"]}
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200 if str(request.url) in known else 404)
    )
    return lambda: httpx.AsyncClient(transport=transport)


def test_a_teenager_asks_for_circuits_and_gets_a_working_course(on, monkeypatch, web):
    model = Model()
    on.app.state.settings.gen_visuals = True
    monkeypatch.setattr(diagnostic, "make", model.make)
    original = intents.parse

    async def parse(engine, settings, text, user_id=None, make=None):
        return await original(engine, settings, text, user_id, model.make)

    monkeypatch.setattr(request_routes.intents, "parse", parse)

    # 1. Intent: free-text subject, fixed picks for who and how far, the adapter adds honesty.
    ada = login(on, subject="ada", name="Ada")
    made = on.post(
        URL,
        json={"text": REQUEST, "choices": ["reg-teen", "lvl-beginner", "time-15"]},
        headers=ada,
    ).json()
    got = made["intent"]
    assert made["source"] == "model" and got["adapter"] == "electronics"
    assert got["register"] == "teen" and got["minutes_per_day"] == 15
    assert got["needs_physical_practice"] is True  # added by the adapter, not claimed by the parser
    assert got["verifiable"] == "partly" and any("mains" in n for n in got["safety_notes"])

    # 2. Confirm, then the architect and critic write and check the outline.
    done = on.post(f"{URL}/{made['id']}/confirm", json={}, headers=ada).json()
    course_id = done["course_id"]
    state = on.app.state
    http = web()
    assert asyncio.run(
        jobs.run_once(state.engine, state.settings, default_catalog(), model.make, http)
    )
    assert model.asked[-2:] == ["architect", "critic"]
    plan = on.get(f"{URL}/{made['id']}").json()
    titles = [c["title"] for m in plan["blueprint"]["modules"] for c in m["concepts"]]
    assert titles == [
        "Voltage, current and resistance",
        "Ohm's law",
        "Series and parallel circuits",
    ]
    assert plan["ready"] == 0 and plan["total"] == 3 and plan["published"] is False

    # 3. The starting check: key stays on the server; a learner who knows Ohm's law starts there.
    check = on.post(f"{URL}/{made['id']}/diagnostic", headers=ada).json()
    assert len(check["questions"]) == 3 and "why" not in json.dumps(check)
    scored = on.post(
        f"{URL}/{made['id']}/diagnostic/answer",
        json={
            "answers": [_right(on, made["id"], i) for i in range(3)][:2]
            + [_wrong(on, made["id"], 2)]
        },
        headers=ada,
    ).json()
    assert scored["result"]["correct"] == 2 and scored["result"]["level"] == "know-basics"

    # 4. Publish privately, enrol at the diagnosed level; prefetch queues the first lessons.
    published = on.post(f"{URL}/{made['id']}/publish", headers=ada).json()
    assert published["enroll"]["level"] == "know-basics"
    with Session(state.engine) as db, db.begin():
        db.scalars(select(User)).one().birth_year = 1995
    assert on.post("/api/v1/enrollments", json=published["enroll"], headers=ada).status_code == 200

    # 5. Package the first lesson: author, quiz, atoms, facts, reviewer, designer all gate it.
    assert asyncio.run(
        jobs.run_once(state.engine, state.settings, default_catalog(), model.make, http)
    )
    assert {"author", "quiz", "atoms", "facts", "reviewer", "experience"} <= set(model.asked)
    # Provenance: the released concept names its job, and that job records every model call
    # with the exact prompt version that produced it.
    with Session(state.engine) as db:
        row = db.get(GeneratedConcept, (course_id, "ohms-law"))
        job = db.get(GenerationJob, row.job_id)
        released = job.log[-1]
        assert released["event"] == "released" and job.state == "done"
        roles_called = {c["role"] for c in released["calls"]}
        assert {"author", "facts", "reviewer"} <= roles_called
        assert all(len(c["prompt"]) == 12 and c["ms"] >= 0 for c in released["calls"])
    view = on.get("/api/v1/courses").json()
    assert course_id in {c["id"] for c in view["items"]}
    with Session(state.engine) as db:
        enrollment = db.scalars(select(Enrollment)).one()
        assert enrollment.level_id == "know-basics"
    plan = on.get(f"{URL}/{made['id']}").json()
    assert plan["ready"] == 1  # one lesson released, the rest honestly still planned

    # 6. What the learner sees: AI-labelled lesson, one registered visual with its fallback.
    # The learner already knows the basics (diagnostic), so the first lesson written was Ohm's law.
    first = plan["blueprint"]["modules"][0]["concepts"][1]
    assert first["id"] == "ohms-law" and first["status"] == "live"
    lesson_view = on.get(f"/api/v1/concepts/{course_id}:{first['id']}").json()
    assert lesson_view["citations"] == []  # no sources were found, so no claim cites one
    assert (
        lesson_view["ai_generated"] is True
        and "Not reviewed by a person" in lesson_view["attribution"]
    )
    assert [v["renderer"] for v in lesson_view["visuals"]] == ["simulation"]
    assert "2 A" in lesson_view["visuals"][0]["fallback_text"]
    # Electronics is only partly machine-verifiable and needs hands-on practice, so the passed
    # lesson is released but labelled as needing a person; findings stay out of the learner view.
    assert lesson_view["validation"]["status"] == "human_review_required"
    assert "not as verified" in lesson_view["validation"]["label"]
    assert set(lesson_view["validation"]) == {"status", "label", "reviewer"}
    assert lesson_view["lesson"].count("## ") >= 3
    # Planned lessons stay held, never shown as ready.
    assert (
        on.get(f"/api/v1/concepts/{course_id}:series-and-parallel").json()["error"]["code"]
        == "concept_preparing"
    )


def _stored(on, request_id):
    from socrat.models import Diagnostic

    with Session(on.app.state.engine) as db:
        return db.scalars(select(Diagnostic).where(Diagnostic.request_id == request_id)).one().items


def _right(on, request_id, i):
    return _stored(on, request_id)[i]["answer"]


def _wrong(on, request_id, i):
    return (_stored(on, request_id)[i]["answer"] + 1) % 4
