"""Concept packages: lesson, quiz and atoms are drafted, gated, checked and released."""

import asyncio
import json

import httpx
import pytest
from test_coursegen import BRIEF, OUTLINE
from test_coursegen import Scripted as OutlineScript
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.assistant.gateway import Event, usage_event
from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.coursegen import jobs, links
from socrat.coursegen import package as pkg

GOOD = ["https://docs.example.org/ml/intro", "https://course.example.edu/ml/lecture-1"]
SECTION = "A model is a rule learned from examples rather than written by hand. " * 12


def lesson(size=4, urls=GOOD):
    text = "".join(f"## Part {i}\n\n{SECTION}\n\n" for i in range(size))
    text += (
        "## Check yourself\n\n1. What does a model learn?\n\n<details>From examples.</details>\n"
    )
    return {
        "lesson": text,
        "key_points": ["Models learn rules from data.", "Data quality bounds model quality."],
        "pitfalls": ["Assuming more data fixes everything.", "Testing on training data."],
        "resources": [
            {"title": f"Reading {i}", "url": u, "kind": "docs", "source": "Example", "minutes": 10}
            for i, u in enumerate(urls)
        ],
    }


QUIZ = {
    "quiz": [
        {
            "id": f"q{i}",
            "prompt": f"Which statement about learning from data is true ({i})?",
            "options": ["Rules come from examples", "Rules are typed by hand", "Data is optional"],
            "answer": 0,
            "explanation": "A model infers its rule from examples.",
            "difficulty": 1 + i % 5,
        }
        for i in range(5)
    ],
    "prompts": [
        {
            "id": "why-examples",
            "prompt": "Explain why a model trained on examples can be wrong on new data.",
            "max_words": 120,
            "rubric": [
                {
                    "criterion": "Generalisation",
                    "points": 2,
                    "look_for": "New data can differ from the training examples.",
                },
                {
                    "criterion": "Cause",
                    "points": 2,
                    "look_for": "Too few or unrepresentative examples, or memorising them.",
                },
            ],
            "model_answer": "A model only fits the examples it saw. If new data differs from "
            "them, or the model memorised its examples, its rule fails on the new cases.",
        }
    ],
}
STEP = {
    "state": "Examples: (1,2), (2,4)",
    "prompt": "What rule fits?",
    "options": ["y = 2x", "y = x + 1"],
    "answer": 0,
    "explanation": "Both pairs double.",
}
ATOMS = {
    "atoms": [
        {
            "id": "hook",
            "kind": "hook",
            "title": "Why learn rules",
            "objective": "See the point",
            "body": "Nobody can hand-write a spam filter. Examples can.",
            "seconds": 20,
        },
        {
            "id": "idea",
            "kind": "concept",
            "title": "The idea",
            "objective": "State the idea",
            "body": "A model is a rule fitted to examples.",
            "seconds": 60,
        },
        {
            "id": "worked",
            "kind": "worked",
            "title": "Fit a rule",
            "objective": "Fit by hand",
            "body": "Pairs (1,2) and (2,4) suggest y = 2x.",
            "seconds": 60,
        },
        {
            "id": "predict",
            "kind": "predict",
            "title": "Your turn",
            "objective": "Infer a rule",
            "body": "Guess the rule from two examples.",
            "seconds": 60,
            "steps": [STEP],
        },
    ]
}
SCORES = {d: 5 for d in pkg.DIMENSIONS}
PASS = {"scores": SCORES, "summary": "Deep and correct.", "lesson": [], "quiz": [], "atoms": []}
SHALLOW = PASS | {"scores": SCORES | {"depth": 3}, "lesson": ["Trace the example step by step."]}
FACTS_OK = {
    "claims": [{"where": "lesson", "claim": "Models learn from data", "verdict": "correct"}]
}
FACTS_BAD = {
    "claims": [
        {
            "where": "quiz:q2",
            "claim": "Data is optional",
            "verdict": "incorrect",
            "correction": "Data is required",
        }
    ]
}
ROLES = {
    pkg.LESSON: "author",
    pkg.QUIZ: "quiz",
    pkg.ATOMS: "atoms",
    pkg.FACTS: "facts",
    pkg.REVIEW: "reviewer",
}


class Scripted:
    def __init__(self, **replies):
        self.replies = {role: [json.dumps(r) for r in rs] for role, rs in replies.items()}
        self.prompts: dict[str, list[str]] = {role: [] for role in ROLES.values()}

    def make(self, settings):
        script = self

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                role = ROLES[system]
                script.prompts[role].append(turns[0].content)
                yield Event("text", text=script.replies[role].pop(0))
                yield usage_event(1000, 3000)

        return Provider()


@pytest.fixture
def web(monkeypatch):
    """Resource links: the good ones answer 200, anything else 404. No real DNS or HTTP."""
    monkeypatch.setattr(links, "public_https", lambda url: url.startswith("https://"))
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200 if str(request.url) in GOOD else 404)
    )
    return lambda: httpx.AsyncClient(transport=transport)


@pytest.fixture
def published(client):  # noqa: F811
    client.app.state.settings.admin_subjects = ["boss"]
    admin = login(client, subject="boss", name="Boss")
    client.post("/api/v1/admin/courses/briefs", json=BRIEF | {"budget_usd": 50}, headers=admin)
    outline = OutlineScript(
        architect=[json.dumps(OUTLINE)],
        critic=[json.dumps({"verdict": "pass", "summary": "ok", "issues": []})],
    )
    run(client, outline.make)
    assert client.post("/api/v1/admin/courses/ai-basics/publish", headers=admin).status_code == 200
    return admin


def run(client, make, http=None):  # noqa: F811
    state = client.app.state
    return asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), make, http))


def generate(client, admin, *concepts):  # noqa: F811
    return client.post(
        "/api/v1/admin/courses/ai-basics/concepts/generate",
        json={"concepts": list(concepts)},
        headers=admin,
    )


def test_package_is_revised_by_artifact_then_released(client, published, web):  # noqa: F811
    assert len(generate(client, published, "what-is-ml").json()["queued"]) == 1
    assert generate(client, published, "what-is-ml").json()["queued"] == []  # already queued
    script = Scripted(
        author=[
            lesson(size=1, urls=[GOOD[0], "https://nowhere.example.com/x"]),
            lesson(),
            lesson(),
        ],
        quiz=[QUIZ, QUIZ],
        atoms=[ATOMS],
        facts=[FACTS_BAD, FACTS_OK],
        reviewer=[SHALLOW, PASS],
    )
    assert run(client, script.make, web())
    # Round 1: the lesson failed its gates, so nothing else was spent on it.
    assert "needs at least 2000" in script.prompts["author"][1]
    assert "unreachable" in script.prompts["author"][1]
    # Round 2: the reviewer's depth note went to the author, the wrong key to the quiz builder.
    assert "Trace the example step by step." in script.prompts["author"][2]
    assert "[incorrect] quiz:q2" in script.prompts["quiz"][1]
    assert len(script.prompts["atoms"]) == 1  # atoms passed, so they were kept

    detail = client.get("/api/v1/admin/courses/ai-basics/concepts/what-is-ml", headers=published)
    run_log = detail.json()["jobs"][0]
    assert run_log["state"] == "done" and run_log["log"][-1]["event"] == "released"
    assert detail.json()["atoms"]["status"] == "released"

    catalog = generated.merged(default_catalog())
    assert catalog.concept("ai-basics:what-is-ml").status == "live"
    assert catalog.atom_packs["ai-basics:what-is-ml"].review is not None

    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner, course="ai-basics")
    view = client.get("/api/v1/concepts/ai-basics:what-is-ml").json()
    assert view["ai_generated"] is True and "Not reviewed by a person" in view["attribution"]
    assert len(view["key_points"]) == 2
    held = client.get("/api/v1/concepts/ai-basics:loss")
    assert held.json()["error"]["code"] == "concept_preparing"


def test_a_dead_extra_link_is_dropped_without_a_new_round(client, published, web):  # noqa: F811
    generate(client, published, "what-is-ml")
    script = Scripted(
        author=[lesson(urls=[*GOOD, "https://nowhere.example.com/x"])],
        quiz=[QUIZ],
        atoms=[ATOMS],
        facts=[FACTS_OK],
        reviewer=[PASS],
    )
    assert run(client, script.make, web())
    assert len(script.prompts["author"]) == 1
    view = client.get("/api/v1/admin/courses/ai-basics/concepts/what-is-ml", headers=published)
    assert view.json()["jobs"][0]["state"] == "done"
    live = generated.merged(default_catalog()).concept("ai-basics:what-is-ml")
    assert [str(r.url) for r in live.resources] == GOOD


def test_a_package_that_never_passes_stays_planned(client, published, web):  # noqa: F811
    generate(client, published, "loss")
    script = Scripted(
        author=[lesson()] * 3,
        quiz=[QUIZ],
        atoms=[ATOMS],
        facts=[FACTS_OK] * 3,
        reviewer=[SHALLOW] * 3,
    )
    run(client, script.make, web())
    detail = client.get("/api/v1/admin/courses/ai-basics/concepts/loss", headers=published).json()
    assert detail["jobs"][0]["state"] == "failed"
    assert detail["concept"]["status"] == "planned" and detail["atoms"] is None
    assert detail["jobs"][0]["output"]["scores"]["depth"] == 3  # the last draft is kept


def test_generation_needs_a_published_outline_and_planned_concepts(client, published):  # noqa: F811
    client.post(
        "/api/v1/admin/courses/briefs", json=BRIEF | {"id": "draft-course"}, headers=published
    )
    outline = OutlineScript(
        architect=[json.dumps(OUTLINE)],
        critic=[json.dumps({"verdict": "pass", "summary": "ok", "issues": []})],
    )
    run(client, outline.make)
    blocked = client.post(
        "/api/v1/admin/courses/draft-course/concepts/generate",
        json={"concepts": ["loss"]},
        headers=published,
    )
    assert blocked.json()["error"]["code"] == "publish_outline_first"
    assert generate(client, published, "nope").json()["error"]["code"] == "concept_not_planned"


def test_links_must_be_public_https():
    assert not links.public_https("http://example.com/")
    assert not links.public_https("https://127.0.0.1/admin")
    assert not links.public_https("https://localhost/x")
    assert not links.public_https("https://user:pw@example.com/")
    assert not links.public_https("https://metadata.internal/")


def test_lesson_gates_and_verdict_rules():
    course = default_catalog().course("zero")
    concept = default_catalog().concept("zero:programs-and-output")
    short = pkg.check_lesson(concept, course, {"lesson": "## a\n```rust\nx\n```"})
    assert any("characters" in p for p in short) and any("rust" in p for p in short)
    assert any("<details>" in p for p in short)
    passed, notes, _ = pkg.verdict(FACTS_OK, PASS)
    assert passed and notes == {"lesson": [], "quiz": [], "atoms": []}
    assert not pkg.verdict(FACTS_BAD, PASS)[0]  # an incorrect claim always blocks
    assert not pkg.verdict(None, PASS)[0]  # no fact check, no release
    assert not pkg.verdict(FACTS_OK, PASS | {"scores": SCORES | {"correctness": 4}})[0]


IMPRECISE = {
    "claims": [
        {
            "where": "lesson",
            "claim": "Insurance has a negative expected value (the company must profit)",
            "verdict": "imprecise",
            "correction": "Say 'usually has a slightly negative expected value'.",
        }
    ]
}


def pkg_lesson_text(draft):
    """The lesson text as stored: the author's text plus the Sources section, if any."""
    return draft["lesson"]


def _lesson_text(_client, concept):
    return generated.merged(default_catalog()).concept(f"ai-basics:{concept}").lesson


def test_an_imprecise_fact_gets_one_revision_before_release(client, published, web):  # noqa: F811
    """Found in a live run: a lesson shipped with a sentence the fact checker called imprecise.
    A package that passes but carries imprecise claims is revised once, then released."""
    generate(client, published, "what-is-ml")
    first, second = lesson(), lesson() | {"lesson": lesson()["lesson"] + "\nAdjusted wording.\n"}
    script = Scripted(
        author=[first, second],
        quiz=[QUIZ],
        atoms=[ATOMS],
        facts=[IMPRECISE, FACTS_OK],
        reviewer=[PASS, PASS],
    )
    run(client, script.make, web())
    assert len(script.prompts["author"]) == 2  # exactly one extra round
    assert "usually has a slightly negative expected value" in script.prompts["author"][1]
    assert "Adjusted wording." in _lesson_text(client, "what-is-ml")
    events = [
        e.get("event")
        for e in client.get(
            "/api/v1/admin/courses/ai-basics/concepts/what-is-ml", headers=published
        ).json()["jobs"][0]["log"]
    ]
    assert "polishing" in events and events[-1] == "released"


def test_a_polish_round_never_costs_the_lesson_that_already_passed(client, published, web):  # noqa: F811
    generate(client, published, "what-is-ml")
    first = lesson()
    ruined = lesson(size=1)  # the polish draft fails its length gate, twice
    script = Scripted(
        author=[first, ruined, ruined],
        quiz=[QUIZ],
        atoms=[ATOMS],
        facts=[IMPRECISE],
        reviewer=[PASS],
    )
    run(client, script.make, web())
    detail = client.get(
        "/api/v1/admin/courses/ai-basics/concepts/what-is-ml", headers=published
    ).json()
    assert (
        detail["jobs"][0]["state"] == "done" and detail["jobs"][0]["log"][-1]["event"] == "released"
    )
    assert len(script.prompts["author"]) == 3  # the polish round ran, and failed, twice
    events = [e.get("event") for e in detail["jobs"][0]["log"]]
    assert "polishing" in events
    released = _lesson_text(client, "what-is-ml")
    assert released.startswith(first["lesson"][:200]) and "Adjusted" not in released
    assert released == pkg_lesson_text(first)
    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner, course="ai-basics")
    label = client.get("/api/v1/concepts/ai-basics:what-is-ml").json()["validation"]["status"]
    assert label in {"pass_with_warnings", "human_review_required"}  # never "being revised"


def test_only_imprecise_claims_ask_for_a_polish_round():
    assert pkg.imprecise_notes(None) == {"lesson": [], "quiz": [], "atoms": []}
    assert pkg.imprecise_notes(FACTS_OK) == {"lesson": [], "quiz": [], "atoms": []}
    assert pkg.imprecise_notes(FACTS_BAD) == {
        "lesson": [],
        "quiz": [],
        "atoms": [],
    }  # blocking, not polish
    notes = pkg.imprecise_notes(
        {"claims": [{"where": "atom:a1", "claim": "x", "verdict": "imprecise", "correction": "y"}]}
    )
    assert notes["atoms"] == ["[imprecise] atom:a1: x → y"] and notes["lesson"] == []
