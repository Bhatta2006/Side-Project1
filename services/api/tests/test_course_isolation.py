"""Course isolation under concurrent generation (master prompt 2, sections 4 and 19.3).

Three unrelated courses are briefed, outlined, published and given a first lesson at the same
time, with the model played by hand. Each course carries a unique marker in its brief, outline,
lesson, quiz and atoms. The test fails if any model prompt, stored artifact or learner response
for one course contains another course's marker. It also fails if a prompt contains no marker at
all, because that would mean the check proves nothing.

Not covered here: the tutor's context assembly and the review queue across courses; those have
their own tests and are listed as open in tasks/production-todo.md.
"""

# ruff: noqa: F811
import asyncio
import copy
import json

from test_coursegen_package import (  # noqa: F401
    ATOMS,
    FACTS_OK,
    GOOD,
    PASS,
    QUIZ,
    ROLES,
    lesson,
    web,
)
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.assistant.gateway import Event, usage_event
from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.coursegen import jobs
from socrat.coursegen.outline import ARCHITECT

MARKERS = {
    "dsa-iso": "ZXQDSAMARK7731",
    "guitar-iso": "ZXQGUITARMARK4402",
    "quantum-iso": "ZXQQUANTUMMARK9918",
}
SUBJECTS = {
    "dsa-iso": ("Data structures", "interview coders", "Solve stack and queue problems"),
    "guitar-iso": ("Beginner guitar", "adults with a guitar", "Play three open chords cleanly"),
    "quantum-iso": ("Quantum mechanics", "physics undergraduates", "Solve the particle in a box"),
}


def first_concept(course: str) -> str:
    return f"{course}-first"


def outline_for(course: str) -> dict:
    marker = MARKERS[course]

    def concept(cid, prerequisites=()):
        return dict(
            id=cid,
            title=cid.replace("-", " ").title(),
            summary=f"{marker} summary of {cid}.",
            prerequisites=list(prerequisites),
            difficulty=2,
            estimated_minutes=40,
            depth="overview",
            objectives=[f"{marker} explain {cid} with an example"],
            misconceptions=[f"{marker} a common slip"],
            assessment=["quiz", "explain"],
        )

    first, second = first_concept(course), f"{course}-second"
    return dict(
        tagline=f"{marker} tagline.",
        description=f"{marker} a course description long enough to be a real description.",
        shape=dict(studio="reading", loop="read-reflect", evidence=["quiz"], tools=[]),
        levels=[
            dict(id="brand-new", label="New", description="Start here.", start_concept=None),
            dict(id="some", label="Some", description="Skip.", start_concept=second),
        ],
        modules=[
            dict(
                id="core",
                title="Core",
                summary=f"{marker} module.",
                concepts=[concept(first), concept(second, [first])],
            )
        ],
    )


class Hand:
    """One model for every course. It answers by role and the course named in the prompt."""

    def __init__(self):
        self.seen: list[tuple[str, str, set[str]]] = []  # role, text, markers found

    def make(self, settings):
        hand = self

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                text = turns[0].content
                found = {c for c, m in MARKERS.items() if m in text}
                role = "architect" if system == ARCHITECT else ROLES.get(system, "critic")
                hand.seen.append((role, text, found))
                course = next(iter(found)) if len(found) == 1 else None
                yield Event("text", text=json.dumps(hand.reply(role, course)))
                yield usage_event(1000, 2000)

        return Provider()

    def reply(self, role: str, course: str | None) -> dict:
        if course is None:  # a leak or a missing marker: still answer so the run ends
            course = "dsa-iso"
        marker = MARKERS[course]
        if role == "architect":
            return outline_for(course)
        if role == "critic":
            return {"verdict": "pass", "summary": "ok", "issues": []}
        if role == "author":
            body = lesson()
            body["lesson"] += f"\n\n## Note\n\n{marker} belongs to this lesson only.\n"
            body["key_points"] = [f"{marker} key point.", "Examples make rules concrete."]
            return body
        if role == "quiz":
            quiz = copy.deepcopy(QUIZ)
            quiz["quiz"][0]["prompt"] = f"{marker} which statement about learning is true?"
            return quiz
        if role == "atoms":
            atoms = copy.deepcopy(ATOMS)
            atoms["atoms"][0]["body"] = f"{marker} hook."
            return atoms
        if role == "facts":
            return FACTS_OK
        return PASS


def run_all(client, hand, http=None, count=3):
    """Start `count` job runners at once, as parallel workers would."""
    state = client.app.state
    base = default_catalog()

    async def go():
        return await asyncio.gather(
            *[
                jobs.run_once(state.engine, state.settings, base, hand.make, http)
                for _ in range(count)
            ]
        )

    return asyncio.run(go())


def admin_login(client):
    client.app.state.settings.admin_subjects = ["boss"]
    return login(client, subject="boss", name="Boss")


def brief(course: str) -> dict:
    title, audience, outcome = SUBJECTS[course]
    marker = MARKERS[course]
    return dict(
        id=course,
        title=title,
        audience=f"{marker} {audience}",
        outcome=f"{marker} {outcome}",
        reuse=[],
        budget_usd=50.0,
        research=False,
    )


def build_three(client, web):
    """Brief, outline, publish and write the first lesson of all three courses concurrently."""
    admin = admin_login(client)
    hand = Hand()

    for course in MARKERS:
        r = client.post("/api/v1/admin/courses/briefs", json=brief(course), headers=admin)
        assert r.status_code == 200, r.text
    run_all(client, hand)

    for course in MARKERS:
        r = client.post(f"/api/v1/admin/courses/{course}/publish", headers=admin)
        assert r.status_code == 200, r.text
        queued = client.post(
            f"/api/v1/admin/courses/{course}/concepts/generate",
            json={"concepts": [first_concept(course)]},
            headers=admin,
        )
        assert queued.status_code == 200, queued.text
    run_all(client, hand, web())
    return admin, hand


def test_three_courses_generated_together_never_share_context(client, web):
    admin, hand = build_three(client, web)

    # 1. Every model prompt names exactly one course.
    assert hand.seen, "the model was never called"
    for role, text, found in hand.seen:
        assert len(found) == 1, f"{role} prompt names {sorted(found) or 'no course'}: {text[:200]}"
    roles_seen = {role for role, _, _ in hand.seen}
    assert {"architect", "critic", "author", "quiz", "atoms", "facts", "reviewer"} <= roles_seen
    per_course = {c: {r for r, _, f in hand.seen if f == {c}} for c in MARKERS}
    assert all("author" in roles for roles in per_course.values())

    # 2. Every stored artifact carries only its own course's marker.
    catalog = generated.merged(default_catalog())
    for course, marker in MARKERS.items():
        foreign = [m for c, m in MARKERS.items() if c != course]
        detail = client.get(f"/api/v1/admin/courses/{course}", headers=admin)
        concept = client.get(
            f"/api/v1/admin/courses/{course}/concepts/{first_concept(course)}", headers=admin
        )
        assert marker in detail.text and marker in concept.text
        for body in (detail.text, concept.text):
            assert not any(m in body for m in foreign), course
        assert catalog.concept(f"{course}:{first_concept(course)}").status == "live"

    # 3. A learner enrolled in one course never receives another course's text.
    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner, course="guitar-iso")
    for course in MARKERS:
        r = client.get(f"/api/v1/concepts/{course}:{first_concept(course)}")
        foreign = [m for c, m in MARKERS.items() if c != course]
        assert not any(m in r.text for m in foreign), course
    own = client.get(f"/api/v1/concepts/guitar-iso:{first_concept('guitar-iso')}")
    assert own.status_code == 200 and MARKERS["guitar-iso"] in own.text


def test_a_private_course_is_unreadable_to_other_learners(client, web):
    """A learner's own course (not shared) is served to its owner and to nobody else."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from socrat.models import GeneratedCourse, User

    build_three(client, web)
    owner = login(client, subject="ada", name="Ada")
    with Session(client.app.state.engine) as db, db.begin():
        ada = db.scalar(select(User).where(User.subject == "ada"))
        row = db.get(GeneratedCourse, "guitar-iso")
        row.owner_id, row.visibility = ada.id, "private"
    onboard(client, owner, course="guitar-iso")
    mine = f"/api/v1/concepts/guitar-iso:{first_concept('guitar-iso')}"
    first = client.get(mine)
    assert first.status_code == 200, first.text  # the owner reads it
    assert "guitar-iso" in {c["id"] for c in client.get("/api/v1/courses").json()["items"]}

    # Bob is enrolled in another course. He cannot list, join or read the private one.
    bob = login(client, subject="bob", name="Bob")
    assert "guitar-iso" not in {c["id"] for c in client.get("/api/v1/courses").json()["items"]}
    client.patch("/api/v1/me", json={"birth_year": 2001, "timezone": "UTC"}, headers=bob)
    attempt = dict(
        course="guitar-iso",
        language="python",
        level="brand-new",
        minutes_per_day=45,
        weekdays=[0, 1, 2, 3, 4, 5, 6],
    )
    joined = client.post("/api/v1/enrollments", json=attempt, headers=bob)
    assert joined.status_code == 404, joined.text
    onboard(client, bob, course="dsa-iso")
    other = client.get(mine)
    assert other.status_code in (403, 404), other.text
    assert MARKERS["guitar-iso"] not in other.text
