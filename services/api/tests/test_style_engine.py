"""Learning styles: the spec, the builder honouring it, and the tutor speaking it (admins only)."""

import asyncio
import json

from sqlalchemy import select
from sqlalchemy.orm import Session
from test_coursegen import BRIEF, OUTLINE
from test_coursegen_package import (  # noqa: F401
    ATOMS,
    FACTS_OK,
    GOOD,
    PASS,
    QUIZ,
    ROLES,
    Scripted,
    lesson,
    web,
)
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.assistant import service as assistant
from socrat.assistant.gateway import Event, usage_event
from socrat.assistant.prompts import GENERAL_SYSTEM, SYSTEM
from socrat.catalog.registry import default_catalog
from socrat.coursegen import jobs
from socrat.coursegen import package as pkg
from socrat.coursegen.outline import ARCHITECT, CRITIC
from socrat.models import Enrollment, User
from socrat.style import spec as styles

BITE = (
    "## One idea\n\n"
    + "A model is a rule fitted to examples, like guessing a pattern. " * 8
    + "\n\n<details>Examples.</details>\n"
)


def test_wishes_map_to_styles_and_bounds_follow_the_format():
    assert styles.from_rules("quantum mechanics for kids under 10").name == "For kids"
    assert styles.from_rules("5 minutes of physics a day").session_minutes == 5
    assert styles.from_rules("Harvard level math").rigor == "rigorous"
    assert styles.from_rules("make it a game").gamified
    assert styles.from_rules("top level overview").depth == "overview"
    assert styles.from_rules("something plain").name == "Standard"
    assert styles.from_rules("kids").notes == "kids"  # their words are kept
    assert styles.PRESETS["daily-5"].lesson_bounds() == styles.BITE_RANGE
    assert styles.PRESETS["rigorous"].lesson_bounds() == (5000, None)
    assert styles.parse({"format": "nonsense"}) is None and styles.parse(None) is None
    assert "LEARNING STYLE: For kids" in styles.block(styles.PRESETS["kids"])


def test_lesson_gates_follow_the_style_and_default_behaviour_is_unchanged():
    base = default_catalog()
    course = base.course("zero")
    concept = base.concept("zero:programs-and-output")
    short = {"lesson": BITE}
    default = pkg.check_lesson(concept, course, short)
    assert any("at least 3000" in p for p in default) and any("heading" in p for p in default)
    assert pkg.check_lesson(concept, course, {"lesson": BITE * 3}, styles.PRESETS["daily-5"]) == []
    too_long = {"lesson": BITE * 12}
    assert any(
        "at most" in p for p in pkg.check_lesson(concept, course, too_long, styles.PRESETS["kids"])
    )
    deep = pkg.check_lesson(concept, course, {"lesson": "x" * 3500}, styles.PRESETS["in-depth"])
    assert any("at least 5000" in p for p in deep)


def test_style_fit_is_required_only_when_the_course_has_a_style():
    facts, review = FACTS_OK, PASS
    assert pkg.verdict(facts, review)[0]
    assert not pkg.verdict(facts, review, style=True)[0]  # no style_fit score given
    scored = PASS | {"scores": PASS["scores"] | {"style_fit": 4}}
    assert pkg.verdict(facts, scored, style=True)[0]
    weak = PASS | {"scores": PASS["scores"] | {"style_fit": 2}}
    assert not pkg.verdict(facts, weak, style=True)[0]


def test_tutor_prompt_for_any_subject_drops_the_contest_steering():
    assert "Where the path leads" in SYSTEM and "Where the path leads" not in GENERAL_SYSTEM
    assert "competitive" not in GENERAL_SYSTEM.lower()
    assert "Changing the roadmap" in GENERAL_SYSTEM and "# Teaching\n" in GENERAL_SYSTEM
    assert GENERAL_SYSTEM.count("# Teaching move") == 1


def admin_headers(client):  # noqa: F811
    client.app.state.settings.admin_subjects = ["boss"]
    return login(client, subject="boss", name="Boss")


def test_style_api_is_admin_only_and_interprets_offline(client):  # noqa: F811
    learner = login(client, subject="ada", name="Ada")
    assert client.get("/api/v1/admin/style/presets", headers=learner).status_code == 403
    admin = admin_headers(client)
    keys = [p["key"] for p in client.get("/api/v1/admin/style/presets").json()["items"]]
    assert {"kids", "gamified", "daily-5", "rigorous"} <= set(keys)
    preview = client.post(
        "/api/v1/admin/style/interpret",
        json={"request": "quantum mechanics for kids under 10"},
        headers=admin,
    ).json()
    assert preview["source"] == "rules" and preview["style"]["name"] == "For kids"
    client.app.state.settings.style_engine_enabled = False
    assert client.get("/api/v1/admin/style/presets").status_code == 404


def turn(client, email_subject):  # noqa: F811
    """The tutor's plan for one general question, as the given account."""
    engine = client.app.state.engine
    with Session(engine) as db, db.begin():
        user = db.scalar(select(User).where(User.subject == email_subject))
        return assistant.prepare(
            db,
            default_catalog(),
            client.app.state.settings,
            user,
            "general",
            "Explain superposition",
            "chat",
            "",
            False,
            1_800_000_000,
        )


def test_admin_style_changes_the_tutor_and_other_accounts_never_get_it(client):  # noqa: F811
    admin = admin_headers(client)
    assert (
        client.put("/api/v1/admin/style/me", json={"preset": "kids"}, headers=admin).status_code
        == 409
    )  # needs an enrollment first
    onboard(client, admin)
    plain = turn(client, "boss")
    assert plain.system == "" and "learning_style" not in plain.turns[-1].content

    put = client.put("/api/v1/admin/style/me", json={"preset": "kids"}, headers=admin)
    assert put.json()["source"] == "preset"
    assert client.get("/api/v1/admin/style/me").json()["style"]["name"] == "For kids"
    styled = turn(client, "boss")
    assert styled.system == GENERAL_SYSTEM
    assert "<learning_style>" in styled.turns[-1].content
    assert "children under 10" in styled.turns[-1].content

    # The same stored style on a non-admin account is ignored.
    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner)
    engine = client.app.state.engine
    with Session(engine) as db, db.begin():
        ada = db.scalar(select(User).where(User.subject == "ada"))
        enrollment = db.scalar(select(Enrollment).where(Enrollment.user_id == ada.id))
        enrollment.adaptive = {
            **enrollment.adaptive,
            styles.STYLE_KEY: styles.PRESETS["kids"].model_dump(mode="json"),
        }
    ignored = turn(client, "ada")
    assert ignored.system == "" and "learning_style" not in ignored.turns[-1].content

    admin = login(client, subject="boss", name="Boss")  # ada's login replaced the session
    assert client.delete("/api/v1/admin/style/me", headers=admin).json() == {"style": None}
    assert turn(client, "boss").system == ""
    bad = client.put(
        "/api/v1/admin/style/me", json={"preset": "kids", "request": "also this"}, headers=admin
    )
    assert bad.status_code == 422


class StyledScripted(Scripted):
    """The package tests' script, matching roles by prefix since styled prompts add a note."""

    def make(self, settings):
        script = self

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                role = next(r for prompt, r in ROLES.items() if system.startswith(prompt))
                script.prompts[role].append(turns[0].content)
                yield Event("text", text=script.replies[role].pop(0))
                yield usage_event(1000, 3000)

        return Provider()


class Stylist:
    """Answers the Stylist, Architect and Critic; remembers what the Architect was asked."""

    def __init__(self, style: dict):
        self.style = style
        self.architect: list[str] = []

    def make(self, settings):
        script = self

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                if system == styles.STYLIST:
                    reply = script.style
                elif system == ARCHITECT:
                    script.architect.append(turns[0].content)
                    reply = OUTLINE
                else:
                    assert system == CRITIC
                    reply = {"verdict": "pass", "summary": "ok", "issues": []}
                yield Event("text", text=json.dumps(reply))
                yield usage_event(1000, 2000)

        return Provider()


DAILY = {
    "name": "Daily physics",
    "learner": "busy adults",
    "depth": "overview",
    "format": "bite",
    "session_minutes": 5,
    "tone": "warm",
    "tutor": "direct",
    "rigor": "intuitive",
    "gamified": False,
    "notes": "5 minutes of physics a day",
}


def test_a_free_text_wish_styles_the_outline_and_is_stored_with_the_brief(client):  # noqa: F811
    admin = admin_headers(client)
    brief = BRIEF | {"style_request": "5 minutes of physics a day"}
    assert client.post("/api/v1/admin/courses/briefs", json=brief, headers=admin).status_code == 200
    script = Stylist(DAILY)
    state = client.app.state
    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), script.make))
    assert "LEARNING STYLE: Daily physics" in script.architect[0]
    detail = client.get("/api/v1/admin/courses/ai-basics").json()
    assert detail["brief"]["style"]["session_minutes"] == 5
    log = detail["jobs"][0]["log"]
    assert log[0]["role"] == "stylist" and log[0]["source"] == "agent"


def test_a_styled_package_is_held_to_its_style_and_scored_for_fit(client, web):  # noqa: F811
    admin = admin_headers(client)
    brief = BRIEF | {"budget_usd": 50, "style": DAILY}
    client.post("/api/v1/admin/courses/briefs", json=brief, headers=admin)
    state = client.app.state
    outline = Stylist(DAILY)
    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), outline.make))
    client.post("/api/v1/admin/courses/ai-basics/publish", headers=admin)
    client.post(
        "/api/v1/admin/courses/ai-basics/concepts/generate",
        json={"concepts": ["what-is-ml"]},
        headers=admin,
    )
    small = lesson() | {"lesson": BITE * 2}
    needs_fit = PASS | {"scores": PASS["scores"] | {"style_fit": 5}}
    script = StyledScripted(
        author=[lesson(size=6), small],
        quiz=[QUIZ],
        atoms=[ATOMS],
        facts=[FACTS_OK],
        reviewer=[needs_fit],
    )
    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), script.make, web()))
    # Round 1 was far over the bite ceiling, so the author was sent back before anything else.
    assert "this style allows at most" in script.prompts["author"][1]
    assert "LEARNING STYLE: Daily physics" in script.prompts["author"][0]
    assert "Reference lesson" not in script.prompts["author"][0]  # bite: no long reference
    assert 'score "style_fit"' in pkg.REVIEW + pkg.STYLE_REVIEW
    detail = client.get("/api/v1/admin/courses/ai-basics").json()
    concept = next(c for c in detail["course"]["concepts"] if c["id"] == "what-is-ml")
    assert concept["status"] == "live" and len(concept["lesson"]) < styles.BITE_RANGE[1]
