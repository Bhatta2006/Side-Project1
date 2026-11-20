"""Backlog 2.6, the acceptance test (lesson0-generation-plan.md section 8): one learner's Lesson 0
answers traced from the claim to Today. The door they pick and the gap their snag shows reach the
outline job as data, the first lesson's prompt as a marked block, the released lesson (door first,
a probe item), and then publish -> enrol with the true session length -> ``/today`` opens that
lesson. A different learner (another door, no miss) changes exactly those things.

Every model call is scripted, and the script writes only from what the prompt carries, so the
learner's answers can reach the lesson only through the prompts.
"""
# ruff: noqa: F811

import asyncio
import json
import re

from sqlalchemy.orm import Session
from test_coursegen import OUTLINE
from test_coursegen_package import ATOMS, GOOD, PASS, QUIZ, lesson, web  # noqa: F401
from test_learner_api import ORIGIN, client, login  # noqa: F401
from test_learning_requests import MODEL_INTENT
from test_onboarding import CALIBRATION

from socrat import limits, onboarding
from socrat.assistant.gateway import Event, usage_event
from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.coursegen import jobs
from socrat.coursegen import learner_plan as lp
from socrat.coursegen import package as pkg
from socrat.coursegen.outline import ARCHITECT, CRITIC
from socrat.models import GenerationJob

URL = "/api/v1/onboarding"
GAP = "filter_by_the_wrong_column"  # CALIBRATION's label for the "Rows above 250" option
PASSED = {"verdict": "pass", "summary": "ok", "issues": []}
# A course that stands alone (CLAUDE.md): the fixture's link into ``basics`` is dropped.
_first = OUTLINE["modules"][0]["concepts"][0]
PLAN = OUTLINE | {
    "modules": [
        OUTLINE["modules"][0]
        | {"concepts": [_first | {"prerequisites": []}, *OUTLINE["modules"][0]["concepts"][1:]]}
    ]
}


def learner_block(prompt: str) -> dict:
    found = re.search(r"<learner>\n(.*?)\n</learner>", prompt, re.S)
    return json.loads(found.group(1)) if found else {}


def is_(system: str, role: str) -> bool:
    """A role's system prompt, possibly with a style or rules appended after it."""
    return system.startswith(role)


class Model:
    """Every role, answering from the prompt alone; records each prompt by role."""

    def __init__(self):
        self.prompts: dict[str, list[str]] = {}

    def reply(self, system: str, prompt: str) -> dict:
        if is_(system, onboarding.DOORS_SYSTEM):
            return {"doors": ["Split trip expenses", "Track cricket stats", "A movie watchlist"]}
        if is_(system, onboarding.CALIBRATION_SYSTEM):
            return CALIBRATION
        if is_(system, ARCHITECT):
            first = _first["id"]
            # Maps every gap it is shown to the first concept (a model's judgement, data here).
            gaps = learner_block(prompt).get("start", {}).get("gaps", [])
            return PLAN | {
                "gap_map": [{"gap": g, "concept": first, "confidence": "match"} for g in gaps]
            }
        if is_(system, CRITIC):
            return PASSED
        if is_(system, pkg.LESSON):
            door = learner_block(prompt).get("door")
            written = lesson()
            if door:  # the door opens the lesson, as LESSON_RULES ask
                written["lesson"] = (
                    f"## {door}\n\n{door}: the same idea, every day.\n\n" + (written["lesson"])
                )
            return written
        if is_(system, pkg.QUIZ):
            probe = learner_block(prompt).get("probe")
            if not probe:
                return QUIZ
            item = {
                "id": "probe-gap",
                "prompt": f"Without a hint: which rows does the filter keep ({probe[0]})?",
                "options": ["Rows matching the right column", "Rows above a number"],
                "answer": 0,
                "explanation": "A filter checks the column that answers the question.",
                "difficulty": 2,
                "probe": True,
            }
            return QUIZ | {"quiz": [*QUIZ["quiz"], item]}
        if is_(system, pkg.ATOMS):
            return ATOMS
        if is_(system, pkg.FACTS):
            return {"claims": []}
        if is_(system, pkg.REVIEW):
            return PASS
        return MODEL_INTENT if "intent" in system.lower() else {}

    def make(self, settings):
        script = self

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                prompt = turns[0].content
                script.prompts.setdefault(system, []).append(prompt)
                yield Event("text", text=json.dumps(script.reply(system, prompt)))
                yield usage_event(100, 200)

        return Provider()


def claim(client, model, subject, door, miss):
    """Lesson 0 as ``subject``: the door, the win, the snag (missed once if ``miss``)."""
    ada = login(client, subject=subject, name=subject.title())
    client.patch("/api/v1/me", json={"birth_year": 2001}, headers=ada)
    draft = client.post(
        URL, json={"text": "I want to learn SQL for my college project"}, headers=ada
    ).json()
    did = draft["id"]
    chosen = client.post(
        f"{URL}/{did}/choose", json={"mode": "builder", "door": door}, headers=ada
    ).json()
    win = chosen["win"]["options"].index("100 rupees")
    snag = client.post(
        f"{URL}/{did}/answer", json={"step": "win", "choice": win}, headers=ada
    ).json()["snag"]
    if miss:
        wrong = snag["options"].index("Rows above 250")
        client.post(f"{URL}/{did}/answer", json={"step": "snag", "choice": wrong}, headers=ada)
    right = snag["options"].index("Rows where who is Asha")
    client.post(f"{URL}/{did}/answer", json={"step": "snag", "choice": right}, headers=ada)
    claimed = client.post(f"{URL}/{did}/claim", json={"minutes": 25}, headers=ada)
    assert claimed.status_code == 200, claimed.text
    return ada, claimed.json()["request"]


def work(client, model, http):
    """Run every queued job (outline, then the first lesson) with the scripted model."""
    state = client.app.state
    while asyncio.run(
        jobs.run_once(state.engine, state.settings, default_catalog(), model.make, http)
    ):
        pass


def journey(client, monkeypatch, web, subject, door, miss):
    """Claim -> outline -> first lesson -> publish -> enrol -> Today, as one learner."""
    model = Model()
    monkeypatch.setattr(onboarding, "make", model.make)
    s = client.app.state.settings
    s.learning_requests_enabled = s.gen_learner_plan = s.gen_waiting_learner = True
    limits.LIMITER.clear()
    headers, req = claim(client, model, subject, door, miss)
    course = req["course_id"]
    first = f"{course}:{OUTLINE['modules'][0]['concepts'][0]['id']}"
    # Only the outline and the learner's first lesson run before publish.
    work(client, model, web())
    view = client.get(f"/api/v1/learning-requests/{req['id']}", headers=headers).json()
    assert view["start"]["state"] == "first_lesson_ready", view["start"]
    published = client.post(f"/api/v1/learning-requests/{req['id']}/publish", headers=headers)
    assert published.status_code == 200, published.text
    with Session(client.app.state.engine) as db, db.begin():  # the rest of the first slice
        for job in db.query(GenerationJob).filter_by(state="queued"):
            job.state = "cancelled"
    enroll = published.json()["enroll"]
    assert enroll["session_minutes"] == 25  # the true length travels to enrolment
    enrolled = client.post("/api/v1/enrollments", json=enroll, headers=headers)
    assert enrolled.status_code == 200, enrolled.text
    today = client.get("/api/v1/today", headers=headers).json()
    released = generated.merged(default_catalog()).concept(first)
    return dict(
        model=model,
        next=(today["next"] or {}).get("id"),
        first=first,
        lesson=released.lesson,
        probe=[q.id for q in released.quiz if q.probe],
        author=next(v for k, v in model.prompts.items() if is_(k, pkg.LESSON))[0],
    )


def test_one_learners_lesson0_answers_reach_their_first_lesson_and_today(client, monkeypatch, web):
    a = journey(client, monkeypatch, web, "ada", "Split trip expenses", miss=True)
    # The door and the gap reached the first lesson's prompt as data, in the marked block.
    block = learner_block(a["author"])
    assert block["door"] == "Split trip expenses" and block["probe"] == [GAP]
    assert lp.LESSON_RULES in a["author"]
    # The released lesson opens with the door; its check carries the probe item.
    assert a["lesson"].startswith("## Split trip expenses")
    assert a["probe"] == ["probe-gap"]
    # Today opens exactly that lesson.
    assert a["next"] == f"lesson:{a['first']}"

    # Another learner: another door, solved first try. Exactly those things change.
    b = journey(client, monkeypatch, web, "bo", "Track cricket stats", miss=False)
    other = learner_block(b["author"])
    assert other["door"] == "Track cricket stats" and "probe" not in other
    assert b["lesson"].startswith("## Track cricket stats")
    assert b["probe"] == []
    assert b["next"] == f"lesson:{b['first']}"

    # Everything not driven by the answers is the same.
    def body(text: str, door: str) -> str:
        return text.replace(f"## {door}\n\n{door}: the same idea, every day.\n\n", "")

    assert body(a["lesson"], "Split trip expenses") == body(b["lesson"], "Track cricket stats")
    assert a["next"].rsplit(":", 1)[1] == b["next"].rsplit(":", 1)[1]  # same first concept
