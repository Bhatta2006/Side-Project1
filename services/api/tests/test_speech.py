"""Lesson pages read aloud by the server's voice: what is read, and when it is offered."""

# ruff: noqa: F811
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.assistant import vertex
from socrat.assistant.gateway import ProviderError
from socrat.catalog.registry import default_catalog
from socrat.learn import speech

PAGE = """Selection keeps rows

Selection $\\sigma$ keeps rows where $P(A \\mid B)$ holds, see [the docs](https://x.org).

$$\\sigma_{a}(R)$$

```sql
SELECT * FROM t;
```

| a | b |
|---|---|

<details><summary>Answer</summary>Hidden.</details>

- **Bold** point with `code`"""


def test_only_words_a_voice_can_read():
    text = speech.speakable(PAGE)
    assert "sigma keeps rows where P(A given B) holds, see the docs." in text
    for gone in ("SELECT", "$", "\\", "Hidden", "|", "**", "`", "https"):
        assert gone not in text, gone
    assert "Bold point with code" in text
    assert speech._maths(r"\frac{1}{2} \times S^c") == "1 over 2  times  S complement"


def test_pages_match_the_web_pages():
    lesson = "Lead line.\n\n## One\nFirst.\n\n## Two\nSecond."
    assert speech.pages(lesson) == ["One\nLead line.\nFirst.", "Two\nSecond."]
    assert speech.pages("No headings here.") == ["No headings here."]
    assert speech.pages("") == []


def test_a_page_is_spoken_once_then_served_from_memory(client, monkeypatch):
    calls = []

    async def speak(settings, text, **kw):
        calls.append(text)
        if "fail" in calls:
            raise ProviderError("provider_offline")
        return vertex.Media(b"RIFF fake wav", "audio/wav", "tts")

    monkeypatch.setattr(vertex, "speak", speak)
    speech._CACHE.clear()
    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner)
    url = "/api/v1/concepts/basics:values/speech"
    view = client.get("/api/v1/concepts/basics:values").json()
    assert view["speech"] is False
    assert client.get(url).status_code == 404  # off by default

    client.app.state.settings.lesson_speech = True
    assert client.get("/api/v1/concepts/basics:values").json()["speech"] is True
    first = client.get(url)
    assert first.status_code == 200 and first.content == b"RIFF fake wav"
    assert first.headers["content-type"] == "audio/wav"
    assert calls[0].startswith(speech.STYLE)
    assert client.get(url).status_code == 200 and len(calls) == 1  # cached
    lesson = default_catalog().concept("basics:values").lesson
    past = len(speech.pages(lesson))
    assert client.get(f"{url}?page={past}").status_code == 404  # the reading ends here

    calls.append("fail")
    speech._CACHE.clear()
    assert client.get(url).status_code == 503  # the browser's voice takes over
