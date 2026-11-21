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


def test_a_first_lesson_gets_a_budget_that_fits_its_session():
    from socrat.coursegen import jobs
    from socrat.planner.engine import written_minutes

    budget = jobs.first_lesson_budget(10)
    words = int(budget.split("at most ")[1].split(" words")[0])
    used = written_minutes(" ".join(["w"] * words), jobs.FIRST_QUIZ_ITEMS)
    assert used["lesson"] + used["quiz"] <= 10 * 1.1  # passes first_session_over
    assert jobs.first_lesson_budget(5).count("at most 360 words") == 1  # never below 2 minutes


def test_a_sources_page_is_neither_sized_nor_a_planned_heading():
    from socrat.style.pages import PageProfile, check

    plan, _ = director.check(GOOD, CONCEPT, ["predict-reveal", "sort-buckets"], (3, 6))
    text = (
        "## A suspicious email\n\n## What you believed before\n\n## Flipping the condition\n\n"
        "## Check yourself\n\nQ\n\n## Sources\n\n[1] x\n"
    )
    assert director.heading_issues(text, plan) == []
    profile = PageProfile(words=(1, 400), ideas=1, pages=(3, 6), check_every=1, elements=())
    assert not any("Sources" in p for p in check(text, profile))


def test_the_door_opens_the_first_lesson_and_is_checked_as_soon_as_it_is_written():
    from socrat.coursegen import jobs

    door = "Estimating rent for a new apartment"
    plan, _ = director.check(GOOD, CONCEPT, ["predict-reveal", "sort-buckets"], (3, 6))
    assert door in director.author_block(plan, door)
    assert door not in director.author_block(plan)
    opens = "When estimating rent for a new apartment, you compare similar flats. " * 3
    assert jobs.door_issue(door, opens) == ""
    missed = jobs.door_issue(door, "Can your laptop load a 10 GB dataset? " * 5)
    assert door in missed and "first two or three sentences" in missed
    assert jobs.door_issue(None, "anything") == ""


def test_a_readable_first_lesson_draft_is_flagged_for_today():
    from socrat.coursegen import progress
    from socrat.models import GenerationJob

    first = GenerationJob(
        state="running", input={"trigger": "first"}, log=[{"event": "preview_ready"}]
    )
    later = GenerationJob(
        state="running", input={"trigger": "prefetch"}, log=[{"event": "preview_ready"}]
    )
    assert progress.readable(first)
    assert not progress.readable(later)  # only the first lesson's draft is shown (learn/preview.py)
    assert not progress.readable(GenerationJob(state="running", input={"trigger": "first"}, log=[]))


def test_a_planned_page_that_is_too_long_can_be_split_without_breaking_the_plan():
    """Live 2026-11-21: the page gate said "split it into two pages", the plan gate then said
    "use exactly the planned headings", and the first lesson failed after five rounds."""
    plan, _ = director.check(GOOD, CONCEPT, ["predict-reveal", "sort-buckets"], (3, 6))
    split = (
        "## A suspicious email\n\n## A suspicious email (continued)\n\n"
        "## What you believed before\n\n## Flipping the condition\n\n"
        "## Flipping the condition (part 2)\n\n## Check yourself\n"
    )
    assert director.heading_issues(split, plan) == []
    # A continuation of a heading that is not the one before it is still out of plan.
    wrong = "## A suspicious email\n\n## Flipping the condition (continued)\n\n" + split
    assert director.heading_issues(wrong, plan)

    long_page = (
        "Page 'A suspicious email' has about 420 words; this learner's pages hold about "
        "160-240. Split it into two pages."
    )
    told = director.page_issues([long_page, "Other issue."], plan)
    assert "(continued)" in told[0] and "A suspicious email" in told[0]
    assert told[1] == "Other issue."
    cut = "Page 'A suspicious em' has about 420 words; this learner's pages hold about 1-2. Split it into two pages."
    assert "'## A suspicious email (continued)'" in director.page_issues([cut], plan)[0]
