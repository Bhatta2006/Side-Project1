"""Rubric-graded work: free-text answers and projects, and their limits on mastery."""

import json

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_coursegen_exercises import Local, release, run  # noqa: F401
from test_coursegen_package import (  # noqa: F401  (fixtures)
    ATOMS,
    FACTS_OK,
    PASS,
    QUIZ,
    lesson,
    published,
    web,
)
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.assistant.gateway import Event, usage_event
from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.coursegen import grading, links, project
from socrat.coursegen import package as pkg
from socrat.learn import service as learn
from socrat.mastery import model as mastery
from socrat.models import Enrollment, Evidence, GeneratedConcept, GenerationJob

ROLES = {
    pkg.LESSON: "author",
    pkg.QUIZ: "quiz",
    pkg.ATOMS: "atoms",
    pkg.FACTS: "facts",
    pkg.REVIEW: "reviewer",
    project.DESIGNER: "designer",
    project.REVIEW: "checker",
    grading.GRADER: "grader",
}


class Scripted:
    def __init__(self, **replies):
        self.replies = {
            r: [x if isinstance(x, str) else json.dumps(x) for x in v] for r, v in replies.items()
        }
        self.prompts: dict[str, list[str]] = {role: [] for role in ROLES.values()}

    def make(self, settings):
        script = self

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                role = ROLES[system]
                script.prompts[role].append(turns[0].content)
                yield Event("text", text=script.replies[role].pop(0))
                yield usage_event(1000, 300)

        return Provider()


def package(**replies):
    return Scripted(
        **{
            "author": [lesson()],
            "quiz": [QUIZ],
            "atoms": [ATOMS],
            "facts": [FACTS_OK],
            "reviewer": [PASS],
            **replies,
        }
    )


def assess(client, concept, *kinds):  # noqa: F811
    with Session(client.app.state.engine) as db, db.begin():
        row = db.get(GeneratedConcept, ("ai-basics", concept))
        row.payload = {
            **row.payload,
            "outline": {**row.payload["outline"], "assessment": list(kinds)},
        }


def grades(*points):
    return {
        "criteria": [
            {"criterion": "Generalisation", "points": points[0], "note": "Covered."},
            {"criterion": "Cause", "points": points[1], "note": "Partly."},
        ],
        "feedback": "You explained generalisation; name a cause next time.",
    }


ANSWER = (
    "Training examples are only a sample. When new inputs look different, or the model "
    "simply memorised its examples, the rule it learned does not hold for them."
)
COPIED = (
    "A model only fits the examples it saw. If new data differs from them, or the model "
    "memorised its examples, its rule fails on the new cases."
)


@pytest.fixture
def learner(client, published, web, monkeypatch):  # noqa: F811
    release(client, web, package(), Local(languages=()))
    headers = login(client, subject="ada", name="Ada")
    onboard(client, headers, course="ai-basics")
    with Session(client.app.state.engine) as db, db.begin():
        enrollment = db.scalar(select(Enrollment))
        stamp = enrollment.created_at
        # The prerequisite from another course is known, so this concept is open.
        learn.set_state(
            db, enrollment, "zero:programs-and-output", mastery.placed(True, stamp), stamp
        )
    return headers


def grader(monkeypatch, *replies):
    script = Scripted(grader=list(replies))
    monkeypatch.setattr(grading, "make_provider", script.make)
    return script


def answer(client, headers, text, prompt="why-examples"):  # noqa: F811
    return client.post(
        "/api/v1/concepts/ai-basics:what-is-ml/answers",
        json={"prompt_id": prompt, "answer": text},
        headers=headers,
    )


def test_prompts_are_released_with_their_rubric_and_hidden_answer(client, learner):  # noqa: F811
    view = client.get("/api/v1/concepts/ai-basics:what-is-ml").json()
    [prompt] = view["prompts"]
    assert prompt["rubric"] == [
        {"criterion": "Generalisation", "points": 2},
        {"criterion": "Cause", "points": 2},
    ]
    assert prompt["last"] is None and "model_answer" not in prompt


def test_a_concept_assessed_by_explain_needs_prompts(client, published, web):  # noqa: F811
    script = package(quiz=[{"quiz": QUIZ["quiz"]}, QUIZ])
    release(client, web, script, Local(languages=()))
    assert "This concept is also assessed by free-text answers" in script.prompts["quiz"][0]
    assert "Write 1-3 free-text prompts; got 0." in script.prompts["quiz"][1]


def test_answers_are_graded_logged_and_limited(client, learner, monkeypatch):  # noqa: F811
    assert answer(client, learner, "Too short.").json()["error"]["code"] == "answer_length"
    script = grader(monkeypatch, grades(2, 1), grades(9, 2), "not json", grades(2, 2))
    first = answer(client, learner, ANSWER).json()
    assert first["grade"]["score"] == 0.75 and first["model_answer"].startswith("A model only")
    assert "Learner's work (between the markers)" in script.prompts["grader"][0]
    assert ANSWER in script.prompts["grader"][0]

    copied = answer(client, learner, COPIED).json()  # 9 points is clamped to 2, then capped
    assert copied["grade"]["copied"] and copied["grade"]["score"] == grading.COPIED

    failed = answer(client, learner, ANSWER)  # a failed grade costs no attempt
    assert failed.status_code == 503 and failed.json()["error"]["code"] == "grading_unavailable"
    assert answer(client, learner, ANSWER).json()["grade"]["score"] == 1.0
    assert answer(client, learner, ANSWER).json()["error"]["code"] == "answer_attempts"

    with Session(client.app.state.engine) as db:
        rows = db.scalars(select(Evidence).where(Evidence.kind == "explain")).all()
        assert [r.score for r in rows] == [0.75, 0.5, 1.0]
        assert rows[0].details["grade"]["criteria"][0]["note"] == "Covered."
    view = client.get("/api/v1/concepts/ai-basics:what-is-ml").json()
    assert view["prompts"][0]["last"]["grade"]["score"] == 1.0


def test_ai_grades_alone_never_master_a_concept():
    state, stamp = mastery.ConceptState(), 1_000_000
    for i in range(40):
        state = mastery.apply(state, "explain", 1.0, stamp + i)
        state = mastery.apply(state, "project", 1.0, stamp + i)
    assert state.mean > mastery.MASTERED and not state.mastered(stamp + 40)
    assert state.graded == state.evidence_count == 80
    judged = mastery.apply(state, "quiz", 1.0, stamp + 41)
    assert judged.mastered(stamp + 41)
    # Older stored states have no "graded" count and keep their mastery.
    legacy = mastery.ConceptState.from_dict(
        {k: v for k, v in judged.to_dict().items() if k != "graded"}
    )
    assert legacy.mastered(stamp + 41)


DESIGN = {
    "id": "spam-filter",
    "title": "Teach a spam filter",
    "summary": "Collect labelled messages, pick a loss and show how a simple rule improves.",
    "skills": ["framing a learning problem", "choosing a loss"],
    "constraints": ["Use at most 30 messages"],
    "milestones": [
        {
            "id": "data",
            "title": "Collect examples",
            "checklist": ["20+ labelled messages", "A note on bias"],
        },
        {
            "id": "loss",
            "title": "Measure the loss",
            "checklist": ["The loss you chose", "Its value for a rule"],
        },
    ],
    "rubric": [
        {
            "criterion": "Framing",
            "weight": 40,
            "full_marks": "Inputs, labels and goal are explicit.",
        },
        {"criterion": "Evidence", "weight": 40, "full_marks": "Numbers back every claim."},
        {"criterion": "Reflection", "weight": 20, "full_marks": "Names a limitation and a fix."},
    ],
    "self_review": ["Would a friend understand my labels?"],
}
SOUND = {
    "scores": {d: 5 for d in project.DIMENSIONS},
    "summary": "Doable and gradable.",
    "fixes": [],
}
MILESTONE = {
    "criteria": [
        {"criterion": "Framing", "points": 40, "note": "Clear."},
        {"criterion": "Evidence", "points": 30, "note": "Mostly."},
        {"criterion": "Reflection", "points": 20, "note": "Good."},
    ],
    "feedback": "Strong start.",
}


def test_a_finished_module_gets_a_graded_project(client, published, web, monkeypatch):  # noqa: F811
    for concept in ("what-is-ml", "loss"):
        assess(client, concept, "quiz", "project")
    release(client, web, package(quiz=[{"quiz": QUIZ["quiz"]}]), Local(languages=()), "what-is-ml")
    release(client, web, package(quiz=[{"quiz": QUIZ["quiz"]}]), Local(languages=()), "loss")
    with Session(client.app.state.engine) as db:
        queued = db.scalars(select(GenerationJob).where(GenerationJob.kind == "project")).all()
        assert [(j.target, j.state) for j in queued] == [("ideas", "queued")]

    script = Scripted(
        designer=[DESIGN | {"milestones": DESIGN["milestones"][:1]}, DESIGN], checker=[SOUND]
    )
    run(client, script.make, Local(languages=()))
    assert "Give at least 2 milestones." in script.prompts["designer"][1]
    spec = generated.merged(default_catalog()).projects["ai-basics:spam-filter"]
    assert spec.concepts == ["ai-basics:what-is-ml", "ai-basics:loss"]
    assert "Not reviewed by a person" in spec.provenance.attribution_md

    headers = login(client, subject="ada", name="Ada")
    onboard(client, headers, course="ai-basics")
    [listed] = client.get("/api/v1/projects").json()["projects"]
    assert [m["available"] for m in listed["milestones"]] == [True, False]

    url = "/api/v1/projects/ai-basics/spam-filter/milestones"
    work = {"work": "I labelled 24 messages as spam or not spam. " * 3, "checklist": [True, True]}
    assert (
        client.post(f"{url}/loss", json=work, headers=headers).json()["error"]["code"]
        == "milestone_locked"
    )
    unticked = work | {"checklist": [True, False]}
    assert (
        client.post(f"{url}/data", json=unticked, headers=headers).json()["error"]["code"]
        == "checklist_incomplete"
    )

    async def broken(urls, client=None):
        return list(urls)

    monkeypatch.setattr(links, "broken", broken)
    linked = work | {"link": "https://example.com/missing"}
    assert (
        client.post(f"{url}/data", json=linked, headers=headers).json()["error"]["code"]
        == "link_unreachable"
    )

    grader(monkeypatch, MILESTONE)
    done = client.post(f"{url}/data", json=work, headers=headers).json()
    assert done["passed"] and done["grade"]["score"] == 0.9
    with Session(client.app.state.engine) as db:
        rows = db.scalars(select(Evidence).where(Evidence.kind == "project")).all()
        assert sorted(r.concept for r in rows) == ["ai-basics:loss", "ai-basics:what-is-ml"]
    [listed] = client.get("/api/v1/projects").json()["projects"]
    assert [m["available"] for m in listed["milestones"]] == [True, True]
    assert (
        listed["milestones"][0]["done"] and listed["milestones"][0]["last"]["grade"]["score"] == 0.9
    )


def test_mastery_is_reached_in_a_course_without_code(client, learner, monkeypatch):  # noqa: F811
    """AI Basics has no code. Judged work over two weeks (quiz, checkpoint, spaced reviews)
    leaves the concept developing; the learner's graded explanations complete it."""
    concept = "ai-basics:what-is-ml"
    day = 86400
    with Session(client.app.state.engine) as db, db.begin():
        enrollment = db.scalar(select(Enrollment).where(Enrollment.course_id == "ai-basics"))
        start = enrollment.created_at - 12 * day
        for kind, offset in (("quiz", 0), ("checkpoint", 1), ("review", 2), ("review", 5)):
            learn.record_evidence(
                db, enrollment, concept, kind, 1.0, f"{kind}:{concept}", start + offset * day
            )
        state = learn.record_evidence(
            db, enrollment, concept, "review", 1.0, f"review:{concept}", enrollment.created_at
        )
        assert mastery.band(state, enrollment.created_at) == "developing"
    grader(monkeypatch, grades(2, 2), grades(2, 2), grades(2, 2))
    bands = [
        answer(client, learner, ANSWER + extra).json()["band"]
        for extra in ("", " Same-kind data helps.", " So does a held-out test set.")
    ]
    assert bands == ["developing", "developing", "strong"]
    progress = client.get("/api/v1/progress").json()
    bands = {c["id"]: c["band"] for m in progress["modules"] for c in m["concepts"]}
    assert bands[concept] == "strong"
