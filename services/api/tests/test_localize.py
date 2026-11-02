"""Languages: a translation is accepted only if code, numbers and glossary terms survive, it is
labelled until a named person reviews it, and it never outlives the English it came from.

The model is played by hand: ``HINDI`` is the Hindi reply a translator should give for FIXTURE;
the bad replies below are the mistakes a real one makes.
"""

# ruff: noqa: F811
import asyncio
import json

import pytest
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.assistant.gateway import Event, ProviderError, usage_event
from socrat.catalog.registry import default_catalog
from socrat.catalog.schema import QuizItem
from socrat.localize import glossary, locales, service, translate
from socrat.localize import routes as locale_routes
from socrat.models import ContentTranslation

LESSON = """## The big idea

A stack removes the item added last. Push adds 1 item and pop removes 1 item.

```python
s = []
s.append(3)
s.pop()
```

Calling `pop()` on an empty stack raises an error.
"""


def fixture_concept():
    base = default_catalog().concept("cp:bitmasks")
    quiz = QuizItem(
        id="lifo",
        prompt="Which item does pop remove from a stack?",
        options=[
            "The first item added",
            "The last item added",
            "The largest item",
            "A random item",
        ],
        answer=1,
        explanation="A stack removes the last item added.",
        difficulty=1,
    )
    return base.model_copy(
        update=dict(
            title="Stack: last in, first out",
            summary="A stack stores items so the newest one leaves first.",
            lesson=LESSON,
            key_points=["Push and pop both work at the top.", "An empty stack has 0 items."],
            pitfalls=["Popping an empty stack is an error."],
            quiz=[quiz],
            visuals=[],
        )
    )


HINDI = {
    "title": "stack: जो आख़िर में आया, वही पहले निकलेगा",
    "summary": "stack में चीज़ें इस तरह रखी जाती हैं कि सबसे नई चीज़ सबसे पहले निकलती है।",
    "lesson": (
        "## मुख्य विचार\n\n"
        "stack उस item को हटाता है जो सबसे आख़िर में जोड़ा गया था। Push 1 item जोड़ता है और "
        "pop 1 item हटाता है।\n\n"
        "⟦0⟧\n\n"
        "खाली stack पर ⟦1⟧ चलाने से error आता है।"
    ),
    "key_points.0": "Push और pop दोनों हमेशा top पर काम करते हैं।",
    "key_points.1": "खाली stack में 0 items होते हैं।",
    "pitfalls.0": "खाली stack से pop करना error है।",
    "quiz.lifo.prompt": "stack से pop कौन-सा item हटाता है?",
    "quiz.lifo.option.0": "सबसे पहले जोड़ा गया item",
    "quiz.lifo.option.1": "सबसे आख़िर में जोड़ा गया item",
    "quiz.lifo.option.2": "सबसे बड़ा item",
    "quiz.lifo.option.3": "कोई भी random item",
    "quiz.lifo.explanation": "stack सबसे आख़िर में जोड़ा गया item हटाता है।",
}


class Translator:
    """A provider that answers each call with the next scripted reply (a dict of units)."""

    def __init__(self, *replies):
        self.replies, self.prompts = list(replies), []

    def make(self, settings):
        script = self

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                script.prompts.append(turns[0].content)
                yield Event("text", text=json.dumps({"units": script.replies.pop(0)}))
                yield usage_event(1000, 3000)

        return Provider()


def run(client, concept, tag, translator):
    state = client.app.state
    return asyncio.run(
        translate.translate(state.engine, state.settings, concept, tag, translator.make)
    )


def test_a_good_translation_is_accepted_and_code_comes_back_untouched(client):
    concept = fixture_concept()
    translator = Translator(HINDI)
    got = run(client, concept, "hi", translator)
    assert got.rounds == 1
    assert "s.append(3)" in got.units["lesson"] and "`pop()`" in got.units["lesson"]
    # The model saw placeholders, never the code, and never an answer key.
    seen = translator.prompts[0]
    assert "s.append" not in seen and "⟦0⟧" in seen and "answer" not in seen.lower()
    assert not [k for k in got.units if k.endswith(".answer")]


@pytest.mark.parametrize(
    ("unit", "value", "why"),
    [
        ("lesson", HINDI["lesson"].replace("⟦0⟧", ""), "placeholders"),  # dropped code block
        ("lesson", HINDI["lesson"].replace("Push 1", "Push 2"), "numbers"),
        (
            "lesson",
            "## The big idea\n\nA stack removes the item added last, so the newest item leaves "
            "first and push adds 1 item and pop removes 1 item.\n\n⟦0⟧\n\nCalling ⟦1⟧ on an "
            "empty stack raises an error.",
            "not written in Hindi",
        ),
        ("quiz.lifo.prompt", "कौन-सा item pop हटाता है?", "must stay in English"),  # lost 'stack'
        ("lesson", HINDI["lesson"].replace("## ", ""), "headings"),
        ("key_points.0", "", "empty"),
    ],
)
def test_a_translation_that_breaks_a_rule_is_rejected(client, unit, value, why):
    bad = HINDI | {unit: value}
    translator = Translator(bad, bad)
    with pytest.raises(translate.TranslationError) as caught:
        run(client, fixture_concept(), "hi", translator)
    assert why in str(caught.value)


def test_missing_keys_are_rejected(client):
    short = {k: v for k, v in HINDI.items() if k != "summary"}
    with pytest.raises(translate.TranslationError, match="keys must match"):
        run(client, fixture_concept(), "hi", Translator(short, short))


def test_the_second_round_is_told_what_was_wrong(client):
    broken = HINDI | {"lesson": HINDI["lesson"].replace("⟦0⟧", "")}
    translator = Translator(broken, HINDI)
    got = run(client, fixture_concept(), "hi", translator)
    assert got.rounds == 2
    assert "Fix these problems" in translator.prompts[1] and "placeholders" in translator.prompts[1]


def test_no_model_means_no_translation(client):
    from socrat.assistant.gateway import make_provider

    state = client.app.state
    with pytest.raises(ProviderError):
        asyncio.run(
            translate.translate(
                state.engine, state.settings, fixture_concept(), "hi", make_provider
            )
        )


def test_english_is_not_a_target(client):
    with pytest.raises(translate.TranslationError):
        run(client, fixture_concept(), "en", Translator())
    with pytest.raises(translate.TranslationError):
        run(client, fixture_concept(), "xx", Translator())


# ------------------------------------------------------------ storing and overlays


def store(client, qualified="cp:bitmasks", units=None):
    concept = default_catalog().concept(qualified)
    result = translate.Result(units or {"title": "बिट मास्क"}, "test-model", 0.0, 1)
    with Session(client.app.state.engine) as db, db.begin():
        row = service.save(db, qualified, "hi", concept, result)
        return dict(status=row.status, reviewer=row.reviewer, units=row.units)


def test_saving_twice_replaces_and_resets_review(client):
    store(client)
    with Session(client.app.state.engine) as db, db.begin():
        db.get(ContentTranslation, ("cp:bitmasks", "hi")).status = "reviewed"
    row = store(client, units={"title": "बिट मास्क v2"})
    assert row["status"] == "machine" and row["reviewer"] is None
    assert row["units"]["title"].endswith("v2")
    with Session(client.app.state.engine) as db:
        assert db.query(ContentTranslation).count() == 1


def test_overlay_swaps_text_only_and_goes_stale_with_the_english(client):
    qualified = "cp:bitmasks"
    concept = default_catalog().concept(qualified)
    store(client, units={"title": "बिट मास्क", "key_points.0": "पहला बिंदु"})
    view = dict(
        title=concept.title,
        summary=concept.summary,
        lesson=concept.lesson,
        key_points=list(concept.key_points),
        pitfalls=list(concept.pitfalls),
        visuals=[],
        quiz=["unchanged"],
    )
    with Session(client.app.state.engine) as db:
        got = service.overlay(db, qualified, concept, "hi", view)
        assert got["title"] == "बिट मास्क" and got["key_points"][0] == "पहला बिंदु"
        assert got["key_points"][1] == concept.key_points[1]  # missing unit: English
        assert got["lesson"] == concept.lesson and got["quiz"] == ["unchanged"]
        assert got["translation"]["status"] == "machine" and got["translation"]["locale"] == "hi"
        # English text changes: the old translation must not be shown.
        newer = concept.model_copy(update=dict(lesson=concept.lesson + "\n\nNew paragraph."))
        assert service.overlay(db, qualified, newer, "hi", view)["translation"] is None
        assert service.overlay(db, qualified, concept, "en", view)["translation"] is None
        assert service.overlay(db, qualified, concept, "ta", view)["translation"] is None


def test_the_script_check_and_glossary_cover_the_launch_locales():
    for tag, loc in locales.LOCALES.items():
        assert loc.tag == tag and loc.native
    assert locales.get("hi").engine == "sarvam" and locales.get("ar").rtl
    assert locales.negotiate("hi-IN,hi;q=0.9,en;q=0.5") == "hi"
    assert locales.negotiate("pt-BR,pt;q=0.9") == "pt-BR"
    assert locales.negotiate("fr-FR") == "en" and locales.negotiate("") == "en"
    assert glossary.must_keep("A Stack and a queue.") == ["stack", "queue"]
    assert glossary.must_keep("The restack step") == []  # whole words only


# ------------------------------------------------------------ the API


def test_the_learner_picks_a_language_and_the_lesson_follows(client):
    headers = login(client)
    onboard(client, headers)
    english = client.get("/api/v1/concepts/zero:programs-and-output").json()
    assert english["translation"] is None
    store(client, "zero:programs-and-output", {"title": "प्रोग्राम और आउटपुट"})

    assert client.patch("/api/v1/me", json={"locale": "xx"}, headers=headers).status_code == 422
    me = client.patch("/api/v1/me", json={"locale": "hi"}, headers=headers).json()
    assert me["locale"] == "hi"
    got = client.get("/api/v1/concepts/zero:programs-and-output").json()
    assert got["title"] == "प्रोग्राम और आउटपुट" and got["translation"]["status"] == "machine"
    assert got["lesson"] == english["lesson"]  # that unit was not translated: English stays
    # ?locale=en shows the original for one view without changing the account.
    original = client.get("/api/v1/concepts/zero:programs-and-output?locale=en").json()
    assert original["title"] == english["title"] and original["translation"] is None
    assert client.get("/api/v1/me").json()["locale"] == "hi"
    client.patch("/api/v1/me", json={"locale": "en"}, headers=headers)
    assert (
        client.get("/api/v1/concepts/zero:programs-and-output").json()["title"] == english["title"]
    )


def test_locales_are_listed_for_anyone_with_a_suggestion(client):
    got = client.get("/api/v1/locales", headers={"Accept-Language": "te-IN,te;q=0.9"}).json()
    assert got["suggested"] == "te"
    assert {item["tag"] for item in got["items"]} >= {"en", "hi", "ar", "pt-BR"}


@pytest.fixture
def boss(client):
    client.app.state.settings.admin_subjects = ["boss"]
    return login(client, subject="boss", name="Boss")


def test_admin_translates_and_one_named_person_reviews(client, boss, monkeypatch):
    async def fake(engine, settings, concept, tag, make, user_id):
        return translate.Result({"title": "बिट मास्क"}, "test-model", 0.0, 1)

    monkeypatch.setattr(locale_routes.translate, "translate", fake)
    body = {"concept": "cp:bitmasks", "locale": "hi"}
    url = "/api/v1/admin/translations"
    assert client.post(url, json=body, headers=boss).json()["status"] == "machine"
    queue = client.get(url, headers=boss).json()["items"]
    assert [(i["concept"], i["status"], i["stale"]) for i in queue] == [
        ("cp:bitmasks", "machine", False)
    ]
    review = f"{url}/cp:bitmasks/hi/review"
    assert client.post(review, json={"reviewer": "A"}, headers=boss).status_code == 422
    done = client.post(review, json={"reviewer": "Asha Verma"}, headers=boss).json()
    assert done["status"] == "reviewed" and done["reviewer"] == "Asha Verma"
    # Re-translating means a new text: review starts over.
    assert client.post(url, json=body, headers=boss).json()["status"] == "machine"


def test_translation_failures_are_reported_plainly(client, boss, monkeypatch):
    url = "/api/v1/admin/translations"
    body = {"concept": "cp:bitmasks", "locale": "hi"}
    # No model configured in tests: honest 503, nothing stored.
    assert client.post(url, json=body, headers=boss).status_code == 503

    async def rejected(*args):
        raise translate.TranslationError("numbers changed")

    monkeypatch.setattr(locale_routes.translate, "translate", rejected)
    assert client.post(url, json=body, headers=boss).status_code == 422
    assert client.post(url, json=body | {"locale": "en"}, headers=boss).status_code == 422
    assert client.post(url, json=body | {"concept": "nope:x"}, headers=boss).status_code == 404
    assert client.get(url, headers=boss).json()["items"] == []


def test_translation_management_is_admin_only(client):
    headers = login(client)
    url = "/api/v1/admin/translations"
    assert client.get(url, headers=headers).status_code == 403
    body = {"concept": "cp:bitmasks", "locale": "hi"}
    assert client.post(url, json=body, headers=headers).status_code == 403
    assert (
        client.post(
            f"{url}/cp:bitmasks/hi/review", json={"reviewer": "Asha Verma"}, headers=headers
        )
    ).status_code == 403


# ------------------------------------------------------------ the tutor


def test_the_tutor_is_told_the_language_without_loosening_the_rules():
    from socrat import localize

    assert localize.tutor_directive("en") == ""
    assert localize.tutor_directive("xx") == ""
    hindi = localize.tutor_directive("hi")
    assert "Hindi" in hindi and "help ladder" in hindi and "stack" in hindi
    assert "do not reveal more" in hindi
