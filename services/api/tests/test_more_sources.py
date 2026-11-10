"""The engine finds its own material: free courses, open textbooks, papers and articles, and
reads the pages it chose. No network: every site is a scripted response."""

import asyncio

import httpx
import pytest

from socrat.coursegen import fetch, links, search

OCW = {
    "results": [
        {
            "title": "Principles of Microeconomics",
            "url": "https://ocw.mit.edu/courses/14-01-principles-of-microeconomics/",
            "description": "<p>Supply and demand, consumer theory and markets.</p>",
            "license_cc": True,
            "runs": [{"instructors": [{"full_name": "Prof. J. Gruber"}]}],
        },
        {"title": "Elsewhere", "url": "https://example.com/not-ocw", "description": "x"},
    ]
}
STAX = {
    "items": [
        {
            "title": "Principles of Economics 3e",
            "book_state": "live",
            "description": "<p>Covers demand, supply and markets.</p>",
            "meta": {"html_url": "https://openstax.org/details/books/principles-economics-3e"},
        },
        {
            "title": "Algebra and Trigonometry",
            "book_state": "live",
            "description": "<p>Functions and graphs.</p>",
            "meta": {"html_url": "https://openstax.org/details/books/algebra-and-trigonometry"},
        },
        {
            "title": "Economics (old edition)",
            "book_state": "retired",
            "description": "x",
            "meta": {"html_url": "https://openstax.org/details/books/economics-old"},
        },
    ]
}
ALEX = {
    "results": [
        {
            "display_name": "Demand curves in electricity markets",
            "publication_year": 2019,
            "type": "article",
            "open_access": {"oa_url": "https://arxiv.org/pdf/1903.11383"},
            "authorships": [{"author": {"display_name": "M. Coulon"}}],
        },
        {"display_name": "No open copy", "open_access": {"oa_url": None}},
    ]
}
BRAVE = {
    "web": {
        "results": [
            {
                "title": "Supply and demand explained",
                "url": "https://www.khanacademy.org/economics/supply-demand",
                "description": "How <b>supply</b> and demand set a price.",
            },
            {"title": "Plain http", "url": "http://insecure.example/x", "description": "x"},
        ]
    }
}
VERSITY = {"query": {"search": [{"title": "Supply and Demand", "snippet": "A course page"}]}}


def site(routes: dict):
    """An httpx client where each host answers with its scripted JSON, HTML or callable."""
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        answer = routes.get(request.url.host)
        if callable(answer):
            answer = answer(request)
        if isinstance(answer, httpx.Response):
            return answer
        return httpx.Response(200, json=answer) if answer is not None else httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return client, seen


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    monkeypatch.setattr(search, "_OPENSTAX", [])
    monkeypatch.setattr(fetch, "_ROBOTS", {})
    monkeypatch.setattr(links, "public_https", lambda url: url.startswith("https://"))
    monkeypatch.setattr(fetch, "public_https", lambda url: url.startswith("https://"))


def test_free_courses_textbooks_and_papers_are_found_without_a_key():
    client, _ = site(
        {
            "api.learn.mit.edu": OCW,
            "openstax.org": STAX,
            "api.openalex.org": ALEX,
            "en.wikiversity.org": VERSITY,
        }
    )
    hits = asyncio.run(
        search.gather(
            "Supply and demand curves Economics",
            ["mit-ocw", "openstax", "openalex", "wikiversity"],
            client,
        )
    )
    by = {h.provider: h for h in hits}
    assert by["mit-ocw"].kind == "course" and by["mit-ocw"].author == "Prof. J. Gruber"
    assert by["mit-ocw"].license == "CC BY-NC-SA 4.0"
    assert by["openstax"].title == "Principles of Economics 3e" and by["openstax"].kind == "book"
    assert by["openalex"].kind == "paper" and by["openalex"].published == "2019"
    assert by["wikiversity"].kind == "course"
    urls = {h.url for h in hits}
    assert "https://example.com/not-ocw" not in urls  # only MIT's own pages
    assert not any("algebra" in u or "economics-old" in u for u in urls)  # "and" is no match


def test_the_web_provider_needs_its_key_and_keeps_only_https():
    client, seen = site({"api.search.brave.com": BRAVE})
    none = asyncio.run(search.gather("supply and demand", ["web"], client))
    assert none == [] and seen == []  # no key: no call at all
    hits = asyncio.run(search.gather("supply and demand", ["web"], client, keys={"web": "k-123"}))
    assert [h.url for h in hits] == ["https://www.khanacademy.org/economics/supply-demand"]
    assert hits[0].snippet == "How supply and demand set a price."  # markup stripped
    assert seen[0].headers["x-subscription-token"] == "k-123"
    assert "k-123" not in str(seen[0].url)  # the key travels in a header, never the URL


def test_a_result_that_shares_no_subject_word_is_never_offered():
    plasma = {
        "results": [
            {
                "title": "Seminar: Fusion and Plasma Physics",
                "url": "https://ocw.mit.edu/courses/22-012-seminar-fusion/",
                "description": "Tokamaks and the energy problem.",
            }
        ]
    }
    client, _ = site({"api.learn.mit.edu": plasma})
    assert asyncio.run(search.gather("supply and demand curves", ["mit-ocw"], client)) == []


PAGE = (
    "<html><head><title>T</title><script>steal()</script><style>p{}</style></head><body>"
    "<nav>Home | Courses | Donate</nav><main><h1>Supply and demand</h1>"
    + "<p>When the price rises, buyers want less and sellers offer more.</p>" * 12
    + "</main><footer>Cookie settings</footer></body></html>"
)


def html(body: str, kind: str = "text/html; charset=utf-8") -> httpx.Response:
    return httpx.Response(200, content=body.encode(), headers={"content-type": kind})


def test_a_chosen_page_is_read_and_becomes_the_passage():
    client, _ = site({"econ.example.org": lambda r: html(PAGE)})
    sources = [
        {"url": "https://econ.example.org/supply", "passage": "two lines", "title": "S"},
        {"url": "https://www.youtube.com/watch?v=abcdefghijk", "passage": "video", "title": "V"},
        {"url": "https://econ.example.org/paper.pdf", "passage": "pdf", "title": "P"},
    ]
    out = asyncio.run(fetch.with_pages(sources, client))
    assert out[0]["page"] is True and "buyers want less" in out[0]["passage"]
    for junk in ("steal()", "Donate", "Cookie settings", "<p>"):
        assert junk not in out[0]["passage"]
    assert len(out[0]["passage"]) <= fetch.PAGE_CHARS
    assert out[1]["passage"] == "video" and out[2]["passage"] == "pdf"  # not pages: untouched


def test_robots_txt_is_honoured():
    def answer(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private/")
        return html(PAGE)

    client, _ = site({"econ.example.org": answer})
    assert asyncio.run(fetch.read(client, "https://econ.example.org/private/notes")) == ""
    assert "buyers want less" in asyncio.run(fetch.read(client, "https://econ.example.org/open"))


def test_what_cannot_be_trusted_is_not_read(monkeypatch):
    def answer(request):
        path = request.url.path
        if path == "/hop":
            return httpx.Response(302, headers={"location": "https://10.0.0.5/admin"})
        if path == "/big":
            return html("<p>" + "x" * (fetch.MAX_BYTES + 10) + "</p>")
        if path == "/binary":
            return html("%PDF", "application/pdf")
        if path == "/thin":
            return html("<main><p>Please enable JavaScript.</p></main>")
        return httpx.Response(404)

    monkeypatch.setattr(fetch, "public_https", lambda url: "10.0.0.5" not in url)
    client, _ = site({"econ.example.org": answer})
    for path in ("hop", "big", "binary", "thin", "missing"):
        assert asyncio.run(fetch.read(client, f"https://econ.example.org/{path}")) == "", path
    assert asyncio.run(fetch.read(client, "http://econ.example.org/open")) == ""  # not https


def test_a_page_that_fails_keeps_its_snippet():
    client, _ = site({})
    sources = [{"url": "https://gone.example.org/x", "passage": "the snippet", "title": "G"}]
    assert asyncio.run(fetch.with_pages(sources, client)) == sources
