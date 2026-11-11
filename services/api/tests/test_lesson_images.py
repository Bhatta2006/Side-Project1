"""Pictures on lessons: openly licensed, credited, about the lesson, and off by default."""

import asyncio

import httpx
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.config import Settings
from socrat.learn import images

COMMONS = {
    "query": {
        "pages": {
            "1": {
                "title": "File:Kannada vowels chart.png",
                "imageinfo": [
                    {
                        "thumburl": "https://upload.wikimedia.org/thumb/vowels.png",
                        "descriptionurl": "https://commons.wikimedia.org/wiki/File:Kannada_vowels_chart.png",
                        "width": 1200,
                        "height": 800,
                        "extmetadata": {
                            "LicenseShortName": {"value": "CC BY-SA 4.0"},
                            "Artist": {"value": "<a href='x'>Asha</a>"},
                            "ImageDescription": {"value": "Kannada vowels and their sounds"},
                        },
                    }
                ],
            },
            "2": {  # non-commercial: never shown in a paid product
                "title": "File:Kannada vowels poster.jpg",
                "imageinfo": [
                    {
                        "thumburl": "https://upload.wikimedia.org/thumb/poster.jpg",
                        "descriptionurl": "https://commons.wikimedia.org/wiki/File:poster.jpg",
                        "width": 900,
                        "extmetadata": {"LicenseShortName": {"value": "CC BY-NC 2.0"}},
                    }
                ],
            },
        }
    }
}
OPENVERSE = {
    "results": [
        {
            "title": "Kannada script sounds diagram",
            "thumbnail": "https://api.openverse.org/v1/images/abc/thumb/",
            "foreign_landing_url": "https://www.flickr.com/photos/x/1",
            "creator": "Ravi",
            "license": "by",
            "license_version": "2.0",
            "license_url": "https://creativecommons.org/licenses/by/2.0/",
            "width": 1024,
        },
        {  # nothing to do with the lesson
            "title": "Sunset over a lake",
            "thumbnail": "https://api.openverse.org/v1/images/def/thumb/",
            "foreign_landing_url": "https://www.flickr.com/photos/x/2",
            "license": "cc0",
            "width": 2000,
        },
    ]
}
BRAVE = {
    "results": [
        {
            "title": "Kannada vowels sounds explained",
            "url": "https://example.org/kannada-vowels",
            "source": "example.org",
            "thumbnail": {"src": "https://imgs.search.brave.com/t.jpg"},
        }
    ]
}


def transport(calls: list[str]):
    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.host)
        if request.url.host == "commons.wikimedia.org":
            return httpx.Response(200, json=COMMONS)
        if request.url.host == "api.openverse.org":
            return httpx.Response(200, json=OPENVERSE)
        if request.url.host == "api.search.brave.com":
            assert request.headers["X-Subscription-Token"] == "k"
            return httpx.Response(200, json=BRAVE)
        return httpx.Response(404)

    return httpx.MockTransport(handle)


LESSON = """Intro line.

## Kannada vowels

Kannada has these vowels.

## Their sounds

How each one sounds.

```python
## not a heading inside code
```

## Check yourself

1. Which vowel?
"""


def find(settings: Settings, key: str, lesson: str = LESSON):
    calls: list[str] = []

    async def go():
        async with httpx.AsyncClient(transport=transport(calls)) as http:
            return await images.find(key, "Kannada vowels sounds", settings, http, lesson=lesson)

    return asyncio.run(go()), calls


def test_each_section_gets_its_own_picture_and_checks_get_none():
    assert images.sections(LESSON) == ["Kannada vowels", "Their sounds"]
    assert images.section_query("Part 2: Layers", "neural networks") == "Layers neural networks"
    found, _ = find(Settings(lesson_images=True), "t0")
    assert [p["section"] for p in found] == ["Kannada vowels", "Their sounds"]
    assert len({p["src"] for p in found}) == len(found)  # never the same picture twice


def test_open_pictures_are_credited_about_the_lesson_and_never_non_commercial():
    found, calls = find(Settings(lesson_images=True), "t1")
    assert "api.search.brave.com" not in calls  # the wider web is its own switch
    srcs = [p["src"] for p in found]
    assert "https://upload.wikimedia.org/thumb/vowels.png" in srcs
    assert "https://upload.wikimedia.org/thumb/poster.jpg" not in srcs  # NC licence
    assert all("def" not in s for s in srcs)  # the sunset shares no word with the lesson
    commons = next(p for p in found if p["provider"] == "wikimedia")
    assert commons["credit"] == "Asha" and commons["license"] == "CC BY-SA 4.0"
    assert commons["source_url"].startswith("https://commons.wikimedia.org/")
    flickr = next(p for p in found if p["provider"] == "openverse")
    assert flickr["license"] == "CC BY 2.0" and flickr["credit"] == "Ravi"


def test_web_results_only_with_their_switch_and_a_key():
    settings = Settings(lesson_images=True, lesson_images_web=True, web_search_api_key="k")
    found, calls = find(settings, "t2")
    assert "api.search.brave.com" in calls
    web = [p for p in found if p["provider"] == "web"]
    assert web and web[0]["source_url"] == "https://example.org/kannada-vowels"
    assert web[0]["license"] == ""  # a web result keeps its owner's rights


def test_results_are_kept_for_a_day():
    find(Settings(lesson_images=True), "t3")
    again, calls = find(Settings(lesson_images=True), "t3")
    assert again and calls == []


def test_the_subject_of_a_lesson_title():
    assert (
        images.query_for("The Sound Case: Hearing and Saying Kannada")
        == "Hearing and Saying Kannada"
    )
    assert images.query_for("Loops", "Python from zero") == "Loops Python from zero"


def test_pictures_are_off_until_turned_on(client):  # noqa: F811
    onboard(client, login(client))
    response = client.get("/api/v1/concepts/zero:programs-and-output/images")
    assert response.status_code == 404


def test_the_model_names_what_each_picture_shows_and_code_still_checks(monkeypatch):
    asked = []

    async def plan(settings, title, parts):
        asked.append([t for t, _ in parts])
        return ["kannada vowels chart", None]  # the second section needs no picture

    monkeypatch.setattr(images, "plan_queries", plan)
    found, _ = find(Settings(lesson_images=True), "t5")
    assert asked == [["Kannada vowels", "Their sounds"]]
    assert [p["section"] for p in found] == ["Kannada vowels"]
    assert found[0]["license"] == "CC BY-SA 4.0"


def test_one_shared_word_is_not_a_match():
    stray = images.Picture(
        src="https://x/a.jpg",
        title="Plan of New Orleans",
        source_url="https://x/a",
        provider="wikimedia",
        license="Public domain",
        width=1000,
        text="Plan of New Orleans",
    )
    assert images.rank([stray], "pencil plan drawing grip") == []


def test_the_models_pick_is_kept_to_the_real_candidates(monkeypatch):
    seen = []

    async def pick(settings, title, parts, found):
        seen.append([len(g) for g in found])
        return [None, 0]  # nothing fits the first section; the first candidate fits the second

    monkeypatch.setattr(images, "choose", pick)
    found, _ = find(Settings(lesson_images=True), "t6")
    assert seen and all(n <= images.CANDIDATES for n in seen[0])
    assert [p["section"] for p in found] == ["Their sounds"]
