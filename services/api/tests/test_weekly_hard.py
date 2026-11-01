"""Hard weekly questions: written by the model, kept only when running them proves the answer."""

import asyncio
from types import SimpleNamespace

from test_assessments import finish_lesson
from test_learner_api import client, login, onboard  # noqa: F401  (client is a fixture)

from socrat.assessments import hard
from socrat.assessments import routes as assessment_routes
from socrat.assessments import service as assessments
from socrat.catalog.registry import default_catalog

CONCEPT = "zero:variables-and-types"


def question(code, options, answer):
    return dict(
        prompt="What does this print?",
        code=code,
        options=options,
        answer=answer,
        explanation="Because of the edge case.",
        edge="negative floor division",
    )


class FakeBroker:
    def __init__(self, outputs):
        self.outputs = outputs

    def available(self, languages):
        return languages

    async def run(self, language, source, inputs):
        return [dict(status="executed", stdout=self.outputs[source], stderr="")]


def test_only_questions_whose_answer_the_run_proves_are_kept(monkeypatch):
    items = [
        question("print(-7 // 2)", ["-3", "-4", "3", "-3.5"], 1),  # right
        question("print(7 % -3)", ["1", "-2", "2", "-1"], 0),  # mis-traced: prints -2
        question("print(1)", ["1", "1", "2", "3"], 0),  # duplicate options
    ]

    async def fake_ask(*args, **kwargs):
        return SimpleNamespace(data={"items": items})

    monkeypatch.setattr(hard, "ask", fake_ask)
    broker = FakeBroker({"print(-7 // 2)": "-4\n", "print(7 % -3)": "-2\n", "print(1)": "1\n"})
    settings = SimpleNamespace(ai_provider="openai")
    kept = asyncio.run(
        hard.generate(None, settings, default_catalog(), {CONCEPT: 3}, "python", broker=broker)
    )
    assert len(kept) == 1
    (item,) = kept
    assert item["options"][item["answer"]] == "-4" and sorted(item["options"]) == sorted(
        ["-3", "-4", "3", "-3.5"]
    )
    assert item["concept"] == CONCEPT and item["key"].startswith("gen-")


def test_offline_generates_nothing():
    settings = SimpleNamespace(ai_provider="offline")
    assert (
        asyncio.run(hard.generate(None, settings, default_catalog(), {CONCEPT: 2}, "python")) == []
    )


def test_generated_questions_replace_the_easiest_bank_ones(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(assessments, "exam_day", lambda user, now: True)
    made = {}

    async def fake_generate(engine, settings, catalog, wanted, language, user_id=None):
        made["wanted"] = wanted
        return [
            {
                **question("print(-7 // 2)", ["-3", "-4", "3", "-3.5"], 1),
                "concept": concept,
                "key": f"gen-{n:04d}",
            }
            for n, concept in enumerate(wanted)
        ]

    monkeypatch.setattr(assessment_routes.hard, "generate", fake_generate)
    headers = login(client, subject="hard", name="Hana")
    onboard(client, headers)
    for concept in ("zero:programs-and-output", CONCEPT):
        finish_lesson(client, headers, concept)
    view = client.post("/api/v1/assessments/start", json={}, headers=headers).json()
    generated = [q for q in view["questions"] if q["id"].startswith("gen-")]
    assert len(generated) == len(made["wanted"])
    assert len(view["questions"]) == sum(made["wanted"].values())
    assert all(q["difficulty"] == 7 and q["code"] == "print(-7 // 2)" for q in generated)

    first = generated[0]
    view = client.post(
        f"/api/v1/assessments/{view['id']}/answer",
        json={"item": first["id"], "choice": 1},
        headers=headers,
    ).json()
    done = client.post(f"/api/v1/assessments/{view['id']}/finish", headers=headers).json()
    graded = next(q for q in done["questions"] if q["id"] == first["id"])
    assert graded["correct"] and graded["answer"] == 1 and "Edge case" in graded["explanation"]
