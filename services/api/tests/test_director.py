"""The Lesson Director: a checked plan reaches the author and the Experience Designer."""

# ruff: noqa: F811
import json

from test_coursegen_package import (  # noqa: F401
    ATOMS,
    FACTS_OK,
    PASS,
    QUIZ,
    ROLES,
    generate,
    lesson,
    published,
    run,
    web,
)
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.assistant.gateway import Event, usage_event
from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.catalog.schema import Concept, Outline
from socrat.coursegen import director
from socrat.engine import design

CONCEPT = Concept(
    id="x",
    title="Bayes",
    summary="How evidence changes a belief, step by step.",
    module="m",
    difficulty=2,
    estimated_minutes=10,
    status="planned",
    outline=Outline(
        objectives=["Compute a posterior", "Explain the prior"],
        misconceptions=["P(A|B) equals P(B|A)"],
        assessment=["quiz"],
    ),
)


def section(heading, objectives=(), misconceptions=(), interaction="", picture=""):
    return dict(
        heading=heading,
        goal="Teach it",
        objectives=list(objectives),
        misconceptions=list(misconceptions),
        hook="Uses the learner's spam filter project",
        interaction=interaction,
        idea="Sort the emails" if interaction else "",
        picture=picture,
    )


GOOD = dict(
    thread="the learner's own spam filter",
    sections=[
        section("A suspicious email", [1], interaction="predict-reveal"),
        section("What you believed before", [2]),
        section("Flipping the condition", [], [1], interaction="sort-buckets"),
    ],
)


def test_a_plan_must_cover_the_contract():
    plan, problems = director.check(GOOD, CONCEPT, ["predict-reveal", "sort-buckets"], (3, 6))
    assert problems == [] and [s["heading"] for s in plan["sections"]][0] == "A suspicious email"
    bad = dict(
        thread="",
        sections=[
            section("One", [1], interaction="evil-widget"),
            section("One", picture="a"),
            section("Two", picture="b"),
            section("Three", picture="c"),
        ],
    )
    _, problems = director.check(bad, CONCEPT, ["predict-reveal"], (3, 6))
    text = " ".join(problems)
    for expected in (
        "thread",
        "repeats",
        "evil-widget",
        "Objectives [2]",
        "Misconceptions [1]",
        "at least half",
        "at most 2 pictures",
    ):
        assert expected in text, expected
    _, problems = director.check(GOOD, CONCEPT, [], (4, 6))
    assert any("Plan 4-6 sections" in p for p in problems)
    assert any("not one of the listed" in p for p in problems)  # no interactions allowed


def test_the_author_must_use_the_planned_headings():
    plan, _ = director.check(GOOD, CONCEPT, ["predict-reveal", "sort-buckets"], (3, 6))
    text = "## A suspicious email\n\n## What you believed before\n\n## Flipping the condition\n\n"
    assert director.heading_issues(text + "## Check yourself\n", plan) == []
    assert director.heading_issues("## A suspicious email\n## Something else\n", plan)
    block = director.author_block(plan)
    assert "spam filter" in block and "## Flipping the condition" in block
    assert "Sort the emails" in director.designer_block(plan)


class Script:
    """Package replies plus the director's and the designer's."""

    def __init__(self, plans, visuals):
        self.plans = [json.dumps(p) for p in plans]
        self.visuals = visuals
        self.replies = {
            "author": [json.dumps(lesson())],
            "quiz": [json.dumps(QUIZ)],
            "atoms": [json.dumps(ATOMS)],
            "facts": [json.dumps(FACTS_OK)],
            "reviewer": [json.dumps(PASS)],
        }
        self.prompts: dict[str, list[str]] = {"director": [], "author": [], "experience": []}

    def make(self, settings):
        script = self

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                if system == director.SYSTEM:
                    script.prompts["director"].append(turns[0].content)
                    yield Event("text", text=script.plans.pop(0))
                elif system == design.SYSTEM:
                    script.prompts["experience"].append(turns[0].content)
                    yield Event("text", text=json.dumps({"visuals": script.visuals}))
                else:
                    role = ROLES[system]
                    if role in script.prompts:
                        script.prompts[role].append(turns[0].content)
                    yield Event("text", text=script.replies[role].pop(0))
                yield usage_event(1000, 3000)

        return Provider()


def test_the_plan_reaches_the_author_and_the_designer(client, published, web):
    every = list(range(1, 7))  # cover whatever the fixture outline lists
    plan = dict(
        thread="a robot that sorts the learner's photos",
        sections=[
            section("Part 0", every, every, interaction="predict-reveal"),
            section("Part 1"),
            section("Part 2", interaction="fill-blank"),
            section("Part 3"),
        ],
    )
    rejected = dict(plan, thread="")
    fill = dict(
        renderer="fill-blank",
        section="Part 2",
        params=dict(text="A model learns from [[examples]]."),
        purpose="Recall where rules come from",
        fallback_text="A model learns from examples.",
        alt_text="A sentence with a gap.",
    )
    script = Script([rejected, plan], [fill])
    settings = client.app.state.settings
    settings.gen_visuals = settings.gen_lesson_director = True
    generate(client, published, "what-is-ml")
    assert run(client, script.make, web())
    live = generated.merged(default_catalog()).concept("ai-basics:what-is-ml")
    assert live.status == "live" and live.visuals[0].section == "Part 2"
    assert len(script.prompts["director"]) == 2  # sent back once with the problems
    assert "thread" in script.prompts["director"][1]
    assert "LESSON PLAN" in script.prompts["author"][0]
    assert "robot that sorts" in script.prompts["author"][0]
    assert "Planned interactions" in script.prompts["experience"][0]


def test_without_the_flag_no_plan_is_asked_for(client, published, web):
    script = Script([], [])
    client.app.state.settings.gen_lesson_director = False
    generate(client, published, "what-is-ml")
    assert run(client, script.make, web())
    assert script.prompts["director"] == []
    assert "LESSON PLAN" not in script.prompts["author"][0]


def test_a_waiting_learner_gets_one_plan_try(client):
    import asyncio

    from socrat.coursegen import jobs

    asked = []

    class Reply:
        data = {"thread": "", "sections": []}  # fails its checks
        problem = ""
        cost_usd = 0.0

    async def ask(role, system, prompt, tokens):
        asked.append(role)
        return Reply()

    state = client.app.state
    with jobs.Session(state.engine) as db, db.begin():
        db.add(jobs.GenerationJob(id="j1", kind="package", course_id="c", input={}, log=[]))
    for tries, calls in ((1, 1), (2, 3)):
        plan = asyncio.run(
            jobs._direct(ask, state.engine, "j1", "", CONCEPT, [], (3, 6), "", tries)
        )
        assert plan is None and len(asked) == calls
