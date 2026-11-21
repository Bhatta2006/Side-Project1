"""Planned pictures are drawn after release, checked by looking at them, and served."""

# ruff: noqa: F811
import json

from test_coursegen_package import generate, published, run, web  # noqa: F401
from test_director import Script, section
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.assistant import vertex
from socrat.assistant.gateway import ProviderError
from socrat.coursegen import illustrate

LESSON = "## Part 0\n\nIntro.\n\n## Part 1\n\nModels learn rules from examples.\n"


def test_the_check_keeps_only_text_free_pictures_that_show_the_idea():
    ok = {"matches": True, "has_text": False, "caption": "A robot sorting photos.", "alt": "Robot."}
    assert illustrate.verdict(json.dumps(ok))[0] == {"caption": ok["caption"], "alt": "Robot."}
    assert illustrate.verdict(json.dumps(ok | {"has_text": True}))[1] == "text in the picture"
    assert illustrate.verdict(json.dumps(ok | {"matches": False}))[1] == "does not show the idea"
    assert illustrate.verdict(json.dumps(ok | {"has_text": None}))[0] is None  # unsure: no
    assert illustrate.verdict("not json")[0] is None
    assert illustrate.section_text(LESSON, "part 1") == "Models learn rules from examples."
    assert illustrate.section_text(LESSON, "Part 9") == ""
    plan = {"sections": [section("A", picture="x"), section("B"), section("C", picture="y")]}
    assert illustrate.wanted(plan) == [{"section": "A", "idea": "x"}, {"section": "C", "idea": "y"}]
    assert "no text" in illustrate.draw_prompt("a cat", "", "body", "Cats").lower()


def test_pictures_are_drawn_after_release_and_served(client, published, web, monkeypatch):
    every = list(range(1, 7))
    plan = dict(
        thread="a robot that sorts the learner's photos",
        sections=[
            section("Part 0", every, every, interaction="predict-reveal"),
            section("Part 1", picture="a robot sorting a pile of photos into boxes"),
            section("Part 2", interaction="fill-blank"),
            section("Part 3", picture="a chart of errors falling"),
        ],
    )
    drawn = []

    async def draw(settings, prompt, **kw):
        drawn.append(prompt)
        if len(drawn) == 3:
            raise ProviderError("provider_empty_reply")
        return vertex.Media(b"\x89PNG fake", "image/png", "image-model")

    answers = iter(
        [
            {"matches": True, "has_text": False, "caption": "A robot sorts photos.", "alt": "R."},
            {"matches": True, "has_text": True, "caption": "A chart.", "alt": "C."},  # dropped
        ]
    )

    async def look(settings, image, mime, question, **kw):
        assert image == b"\x89PNG fake" and "Planned idea" in question
        return json.dumps(next(answers))

    monkeypatch.setattr(vertex, "generate_image", draw)
    monkeypatch.setattr(vertex, "look", look)
    settings = client.app.state.settings
    settings.gen_visuals = settings.gen_lesson_director = settings.gen_illustrations = True
    script = Script([plan], [])
    generate(client, published, "what-is-ml")
    for _ in range(4):  # the package, then the jobs its release queued
        run(client, script.make, web())
    assert len(drawn) == 2 and "Absolutely no text" in drawn[0] and "robot" in drawn[0]

    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner, course="ai-basics")
    items = client.get("/api/v1/concepts/ai-basics:what-is-ml/images").json()["items"]
    assert [(i["section"], i["provider"], i["title"]) for i in items] == [
        ("Part 1", "generated", "A robot sorts photos.")
    ]
    picture = client.get(items[0]["src"])
    assert picture.status_code == 200 and picture.content == b"\x89PNG fake"
    assert picture.headers["content-type"] == "image/png"
    assert client.get("/api/v1/illustrations/nope").status_code == 404
