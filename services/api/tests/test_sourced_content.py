"""The researcher: verified, cited, license-tagged public sources behind each lesson."""

import asyncio
import json

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
from test_learner_api import client, login  # noqa: F401
from test_style_engine import StyledScripted, admin_headers

from socrat.assistant.gateway import Event, usage_event
from socrat.catalog.registry import default_catalog
from socrat.coursegen import jobs, research
from socrat.coursegen.outline import ARCHITECT, CRITIC

OPENSTAX = "https://openstax.org/books/university-physics-volume-1"
SOURCES = {
    "sources": [
        {"title": "University Physics", "url": GOOD[0], "supports": "Newton's laws, in brief."},
        {"title": "University Physics", "url": GOOD[0], "supports": "duplicate"},
        {"title": "Dead page", "url": "https://example.org/gone", "supports": "unreachable"},
        {"title": "Plain http", "url": "http://example.org/x", "supports": "not https"},
        {"title": "No support", "url": GOOD[1], "supports": ""},
    ]
}


def test_candidates_drop_duplicates_and_malformed_entries():
    kept = research.candidates(SOURCES)
    assert [s["url"] for s in kept] == [GOOD[0], "https://example.org/gone"]
    assert research.candidates("not json") == [] and research.candidates({"sources": 3}) == []


def test_sources_are_ranked_by_fit_for_the_learner_and_weak_fits_are_dropped():
    data = {
        "sources": [
            {"title": "A", "url": "https://a.org/1", "supports": "x", "fit": 3, "role": "explain"},
            {"title": "B", "url": "https://b.org/1", "supports": "x", "fit": 5, "role": "visual"},
            {"title": "C", "url": "https://c.org/1", "supports": "x", "fit": 2, "role": "explain"},
        ]
    }
    kept = research.candidates(data)
    assert [s["title"] for s in kept] == ["B", "A"]
    assert (
        research.attach({"lesson": "t [1]"}, [{**kept[0], "n": 1, "license": "x"}])["resources"][0][
            "kind"
        ]
        == "interactive"
    )


def test_screen_keeps_only_reachable_sources_numbered_and_license_tagged(web):  # noqa: F811
    kept = asyncio.run(research.screen(SOURCES, web()))
    assert [(s["n"], s["url"]) for s in kept] == [(1, GOOD[0])]
    assert research._license(OPENSTAX) != "public web page"  # registered sites carry their licence
    assert research._license("https://example.org/x") == "public web page"


def test_lessons_must_cite_a_real_source():
    sources = [{"n": 1}, {"n": 2}]
    assert research.check("No citations here.", sources)
    assert research.check("Newton [1] and more [2].", sources) == []
    assert "matches no source" in research.check("See [1] and [7].", sources)[0]
    assert research.check("Anything", []) == []  # no sources found: nothing to cite


def test_attach_appends_sources_once_and_merges_resources():
    sources = [{"n": 1, "title": "Book", "url": "https://a.org/b", "license": "CC BY 4.0"}]
    first = research.attach({"lesson": "Body [1].", "resources": []}, sources)
    again = research.attach(first, sources)
    assert again["lesson"].count("## Sources") == 1 and "[Book](https://a.org/b)" in again["lesson"]
    assert [r["url"] for r in again["resources"]] == ["https://a.org/b"]
    assert "Informed by" in research.credit(sources) and research.credit([]) == ""


class Researched(StyledScripted):
    """The package script plus a researcher that returns the scripted source list."""

    def make(self, settings):
        script = self

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                if system == research.RESEARCHER:
                    yield Event("text", text=json.dumps(SOURCES))
                else:
                    role = next(r for prompt, r in ROLES.items() if system.startswith(prompt))
                    script.prompts[role].append(turns[0].content)
                    yield Event("text", text=script.replies[role].pop(0))
                yield usage_event(1000, 3000)

        return Provider()


def test_a_researched_lesson_is_sent_back_until_it_cites_and_then_credits_its_sources(client, web):  # noqa: F811
    admin = admin_headers(client)
    brief = BRIEF | {"budget_usd": 50, "research": True}
    client.post("/api/v1/admin/courses/briefs", json=brief, headers=admin)
    state = client.app.state

    class Outline:
        def make(self, settings):
            class Provider:
                name = "anthropic"

                async def converse(self, system, turns, max_tokens, *args, **kwargs):
                    reply = OUTLINE if system == ARCHITECT else None
                    if system == CRITIC:
                        reply = {"verdict": "pass", "summary": "ok", "issues": []}
                    yield Event("text", text=json.dumps(reply))
                    yield usage_event(1000, 2000)

            return Provider()

    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), Outline().make))
    client.post("/api/v1/admin/courses/ai-basics/publish", headers=admin)
    client.post(
        "/api/v1/admin/courses/ai-basics/concepts/generate",
        json={"concepts": ["what-is-ml"]},
        headers=admin,
    )
    cited = lesson()
    cited["lesson"] = cited["lesson"].replace("## Part 0", "## Part 0\n\nBacked by [1].\n\n", 1)
    script = Researched(
        author=[lesson(), cited], quiz=[QUIZ], atoms=[ATOMS], facts=[FACTS_OK], reviewer=[PASS]
    )
    asyncio.run(jobs.run_once(state.engine, state.settings, default_catalog(), script.make, web()))
    assert "Verified public sources" in script.prompts["author"][0]
    assert "Cite at least one" in script.prompts["author"][1]
    detail = client.get("/api/v1/admin/courses/ai-basics").json()
    concept = next(c for c in detail["course"]["concepts"] if c["id"] == "what-is-ml")
    assert concept["status"] == "live" and "## Sources" in concept["lesson"]
    assert "Informed by public sources" in concept["provenance"]["attribution_md"]
    log = detail["jobs"][0]["log"]
    assert any(e.get("role") == "researcher" and e["sources"][0]["n"] == 1 for e in log)
