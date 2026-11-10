"""Visualise from a lesson: "show me this part" for one page of a lesson, a small free
allowance in the Playground, and opening a visual as a signal for the coach."""

# ruff: noqa: F811  (fixtures are imported from the explainer and learner API tests)
import uuid
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import Session
from test_explainer import configured, work  # noqa: F401
from test_learner_api import client, login, onboard  # noqa: F401
from test_shared_visuals import CONCEPT, second_learner, start, state

from socrat import entitlements
from socrat.explainer import shared
from socrat.learn.routes import catalog
from socrat.models import PlaygroundJob, SharedVisual

LESSON = """An opening line before any heading.

## What a variable is

A name for a value.

```python
## not a heading: it is inside code
x = 1
```

### A smaller heading stays on its page

More text.

## Changing it

Assign again.
"""


def test_the_lesson_is_split_into_the_same_pages_the_reader_sees():
    pages = shared.parts(LESSON)
    assert [title for title, _ in pages] == ["What a variable is", "Changing it"]
    first = pages[0][1]
    assert first.startswith("An opening line")  # text before the first heading joins page one
    assert "## not a heading" in first and "### A smaller heading" in first
    assert pages[1][1] == "Assign again."
    assert shared.parts("No headings at all.") == [("", "No headings at all.")]
    assert shared.parts("## Windows\r\nline") == [("Windows", "line")]


def test_a_parts_request_is_built_from_the_lesson_and_keyed_apart_from_the_lessons_own():
    concept = SimpleNamespace(title="Variables")
    title, text = shared.parts(LESSON)[1]
    prompt = shared.prompt_for_part(concept, title, text)
    assert "Changing it" in prompt and "Assign again." in prompt and "Variables" in prompt
    assert len(shared.prompt_for_part(concept, title, "x" * 9000)) <= 4000
    assert shared.key_for("zero:variables", None) == "zero:variables"
    assert shared.key_for("zero:variables", 3) == "zero:variables#3"
    one = shared.fingerprint_part(concept, title, text)
    assert one != shared.fingerprint_part(concept, title, text + " Edited.")
    assert one == shared.fingerprint_part(concept, title, text)


def test_show_me_this_part_is_off_by_default_and_then_cached_per_page(client, configured):
    headers, provider = configured
    pages = shared.parts(catalog().concept(CONCEPT).lesson)
    assert len(pages) >= 2
    assert start(client, headers, section=0).status_code == 404  # off: only the lesson's visual
    with_view = client.get(f"/api/v1/concepts/{CONCEPT}", headers=headers).json()
    assert with_view["section_visuals"] is False
    client.app.state.settings.explainer_section_visuals = True
    assert client.get(f"/api/v1/concepts/{CONCEPT}").json()["section_visuals"] is True
    assert start(client, headers, section=len(pages)).status_code == 404  # no such page
    assert start(client, headers, section=99).status_code == 422

    first = start(client, headers, section=1).json()
    assert first["state"] == "generating" and first["mine"]
    work(client)
    assert len(provider.calls) == 1
    assert pages[1][0] in provider.calls[0][1][0].content  # that page's own text
    ready = state(client, section=1).json()
    assert ready["state"] == "ready"
    # Another page, and the lesson's own visual, are different visuals.
    assert state(client, section=0).json()["state"] == "none"
    assert state(client).json()["state"] == "none"
    # The next learner gets the page's visual without a new generation.
    bob = second_learner(client)
    again = start(client, bob, section=1).json()
    assert again["state"] == "ready" and again["artifact"]["id"] == ready["artifact"]["id"]
    assert len(provider.calls) == 1
    with Session(client.app.state.engine) as db:
        keys = set(db.scalars(select(SharedVisual.concept)))
        assert keys == {f"{CONCEPT}#1"}
        assert db.scalars(select(PlaygroundJob.shared)).all() == [True]  # nobody's allowance


def test_a_free_learner_gets_a_small_weekly_allowance_only_when_one_is_set(
    client, configured, monkeypatch
):
    headers, _ = configured
    monkeypatch.setattr(entitlements, "ENABLED", True)  # plans on: this learner is on Free

    def ask():
        body = dict(prompt="Explain electromagnetic induction", request_id=str(uuid.uuid4()))
        return client.post("/api/v1/playground/generate", headers=headers, json=body)

    assert entitlements.limits("free")["playground"] == (0, "day")
    assert ask().status_code == 402  # as before
    monkeypatch.setattr(entitlements, "FREE_PLAYGROUND_PER_WEEK", 1)
    assert entitlements.limits("free")["playground"] == (1, "week")
    assert entitlements.limits("plus")["playground"] == (3, "day")  # paid plans are untouched
    assert ask().status_code == 202
    work(client)
    refused = ask()
    assert refused.status_code == 429 and refused.json()["error"]["code"] == "playground_week_limit"
    usage = client.get("/api/v1/billing/status", headers=headers).json()["usage"]["playground"]
    assert (usage["limit"], usage["used"], usage["window"]) == (1, 1, "week")


def test_opening_a_visual_is_a_signal_the_memory_keeps(client, configured):
    headers, _ = configured
    client.app.state.settings.lesson_signals = True
    for _ in range(2):
        sent = client.post(
            f"/api/v1/concepts/{CONCEPT}/signals", json={"kind": "visual"}, headers=headers
        )
        assert sent.status_code == 204
    items = client.get("/api/v1/memory", headers=headers).json()["items"]
    assert [i["kind"] for i in items] == ["visual"] and "2 times" in items[0]["text"]
