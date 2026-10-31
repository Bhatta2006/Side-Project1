"""The physics lab: vetted simulations, the builder's gate, and predict-observe grading."""

import copy
import math

from sqlalchemy import select
from sqlalchemy.orm import Session
from test_coursegen_package import web  # noqa: F401
from test_learner_api import client, login, onboard  # noqa: F401
from test_style_engine import admin_headers

from socrat import harness
from socrat.catalog.registry import default_catalog
from socrat.catalog.schema import Experiment
from socrat.coursegen import package as pkg
from socrat.harness import physics
from socrat.models import Evidence


def experiment(**kw) -> dict:
    base = dict(
        id="drop",
        prompt="A ball is dropped from 20 m on Earth. How long until it lands?",
        model="free_fall",
        params={"height": 20, "gravity": 9.81},
        predict="fall_time",
        vary="height",
        hints=["Use h = 1/2 g t^2.", "Solve for t."],
        difficulty=1,
        explanation="h = 1/2 g t^2, so t = sqrt(2h/g).",
    )
    return base | kw


def test_models_match_known_results():
    out = physics.simulate("projectile", dict(speed=20, angle=45, height=0, gravity=9.81))
    assert math.isclose(out["outputs"]["range"]["value"], 400 / 9.81, rel_tol=1e-4)
    assert out["outputs"]["range"]["unit"] == "m" and len(out["trace"]) > 10
    fall = physics.simulate("free_fall", dict(height=20, gravity=9.81))["outputs"]
    assert math.isclose(fall["fall_time"]["value"], math.sqrt(40 / 9.81), rel_tol=1e-5)
    swing = physics.simulate("pendulum", dict(length=1, gravity=9.81, amplitude=10))
    assert math.isclose(swing["outputs"]["period"]["value"], 2.00607, rel_tol=1e-4)
    spring = physics.simulate("spring_mass", dict(mass=1, stiffness=100, amplitude=0.1))
    assert math.isclose(spring["outputs"]["energy"]["value"], 0.5, rel_tol=1e-6)
    circuit = physics.simulate("circuit", dict(voltage=12, resistance=100))["outputs"]
    assert math.isclose(circuit["current"]["value"], 0.12) and circuit["power"]["unit"] == "W"


def test_the_harness_runs_the_simulation_and_refuses_bad_input():
    ok = harness.call(
        "physics.simulate", dict(model="free_fall", params=dict(height=5, gravity=9.81))
    )
    assert ok.ok and ok.output["outputs"]["impact_speed"]["unit"] == "m/s"
    for model, params in (
        ("free_fall", dict(height=-1, gravity=9.81)),  # out of range
        ("free_fall", dict(height=5)),  # missing
        ("warp_drive", dict()),
    ):
        assert not harness.call("physics.simulate", dict(model=model, params=params)).ok


def test_experiments_are_accepted_only_when_the_simulation_runs_them():
    good = [experiment(id="a"), experiment(id="b", predict="impact_speed", vary="")]
    parsed, problems = pkg.check_experiments(good)
    assert problems == [] and [e.id for e in parsed] == ["a", "b"]

    _, problems = pkg.check_experiments([*good, experiment(id="c", model="warp_drive", params={})])
    assert any("experiment c" in p and "unknown experiment" in p for p in problems)
    _, problems = pkg.check_experiments([*good, experiment(id="c", predict="colour")])
    assert any("cannot predict" in p for p in problems)
    _, problems = pkg.check_experiments([*good, experiment(id="c", params={"height": 20})])
    assert any("gravity" in p and "needed" in p for p in problems)
    leaked = experiment(id="c", prompt="Dropped from 20 m, it lands after 2.0191 s. When?")
    assert any("gives away" in p for p in pkg.check_experiments([*good, leaked])[1])
    assert pkg.check_experiments([experiment()])[1] == ["Write 2-4 experiments; got 1."]


def _catalog_with_experiments():
    cat = copy.deepcopy(default_catalog())
    first = next(
        q for q, c in cat.concepts.items() if q.startswith("zero:") and not cat.prerequisites[q]
    )
    items = [Experiment.model_validate(experiment()), Experiment.model_validate(experiment(id="b"))]
    cat.concepts[first] = cat.concepts[first].model_copy(update={"experiments": items})
    return cat, first


def test_the_lab_hides_the_result_grades_the_prediction_and_records_once(client, monkeypatch):  # noqa: F811
    cat, concept = _catalog_with_experiments()
    monkeypatch.setattr("socrat.lab.routes.catalog", lambda: cat)
    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner)
    course, slug = concept.split(":")
    assert client.get(f"/api/v1/lab/{course}/{slug}", headers=learner).status_code == 404

    admin = admin_headers(client)
    onboard(client, admin)
    listing = client.get(f"/api/v1/lab/{course}/{slug}", headers=admin).json()
    first = listing["experiments"][0]
    assert first["predict"] == {"name": "fall_time", "unit": "s"} and first["done"] is False
    assert (
        "2.019" not in str(listing)
        and first["vary"] == "height"
        and first["knobs"]["gravity"]["unit"] == "m/s^2"
    )

    def post(path, **kw):
        return client.post(f"/api/v1/lab/{path}", json=dict(concept=concept) | kw, headers=admin)

    assert (
        post("vary", experiment="drop", values={"height": 40}).status_code == 409
    )  # predict first

    off = post("predict", experiment="drop", given="5").json()
    assert off["verdict"] == "incorrect" and off["evidence"] is True
    assert math.isclose(off["result"]["value"], 2.0191, rel_tol=1e-3) and off["explanation"]
    again = post("predict", experiment="drop", given="2.02").json()
    assert again["verdict"] == "correct" and again["evidence"] is False  # the first one counts

    right = post("predict", experiment="b", given="2.02 s", hints_used=1).json()
    assert right["verdict"] == "correct" and right["evidence"] is True
    assert post("predict", experiment="b", given="banana").json()["verdict"] == "unreadable"

    taller = post("vary", experiment="drop", values={"height": 80}).json()
    assert taller["ok"] and math.isclose(
        taller["observed"]["outputs"]["fall_time"]["value"], math.sqrt(160 / 9.81), rel_tol=1e-4
    )
    assert post("vary", experiment="drop", values={"height": 1e6}).json()["ok"] is False
    assert post("predict", experiment="nope", given="1").status_code == 404

    with Session(client.app.state.engine) as db:
        rows = db.scalars(select(Evidence).where(Evidence.activity_id.like("lab:%"))).all()
        assert sorted((r.activity_id.split(":")[-1], r.score, r.assistance) for r in rows) == [
            ("b", 1.0, 1),
            ("drop", 0.0, 0),
        ]
    assert client.get(f"/api/v1/lab/{course}/{slug}", headers=admin).json()["experiments"][0][
        "done"
    ]


def test_a_physics_course_is_built_with_verified_experiments_and_flawed_ones_are_sent_back(
    client,  # noqa: F811
    web,  # noqa: F811
):
    import asyncio
    import json

    from test_coursegen import BRIEF, OUTLINE
    from test_coursegen_package import ATOMS, FACTS_OK, PASS, QUIZ, lesson
    from test_style_engine import StyledScripted

    from socrat.assistant.gateway import Event, usage_event
    from socrat.coursegen import jobs
    from socrat.coursegen.outline import ARCHITECT

    shape = dict(
        studio="lab",
        loop="predict-observe-explain",
        evidence=["numeric"],
        tools=["simulation", "graph"],
    )
    admin = admin_headers(client)
    client.post("/api/v1/admin/courses/briefs", json=BRIEF | {"budget_usd": 50}, headers=admin)
    state = client.app.state

    class Outline:
        def make(self, settings):
            class Provider:
                name = "anthropic"

                async def converse(self, system, turns, max_tokens, *args, **kwargs):
                    reply = OUTLINE | {"shape": shape}
                    if system != ARCHITECT:
                        reply = {"verdict": "pass", "summary": "ok", "issues": []}
                    yield Event("text", text=json.dumps(reply))
                    yield usage_event(1000, 2000)

            return Provider()

    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), Outline().make))
    client.post("/api/v1/admin/courses/ai-basics/publish", headers=admin)
    client.post(
        "/api/v1/admin/courses/ai-basics/concepts/generate",
        json={"concepts": ["what-is-ml"]},
        headers=admin,
    )
    flawed = QUIZ | {"experiments": [experiment(id="a"), experiment(id="b", model="warp_drive")]}
    sound = QUIZ | {"experiments": [experiment(id="a"), experiment(id="b", predict="impact_speed")]}
    script = StyledScripted(
        author=[lesson()],
        quiz=[flawed, sound],
        atoms=[ATOMS, ATOMS],
        facts=[FACTS_OK],
        reviewer=[PASS],
    )
    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), script.make, web()))
    assert 'Add "experiments"' in script.prompts["quiz"][0]
    assert "unknown experiment" in script.prompts["quiz"][1]
    detail = client.get("/api/v1/admin/courses/ai-basics").json()
    concept = next(c for c in detail["course"]["concepts"] if c["id"] == "what-is-ml")
    assert concept["status"] == "live"
    assert [e["id"] for e in concept["experiments"]] == ["a", "b"]
