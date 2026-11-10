"""Read the pages the researcher chose, so lessons are written from sources, not snippets.

A search result carries two lines of text. The author needs what the page says. This reads a
chosen page and returns its readable text as the source's passage, the same slot a video's
transcript fills.

The URL came from a search provider and the page is someone else's server, so everything is
untrusted and bounded: https to a public host only, re-checked on every redirect; the site's
robots.txt is honoured; only HTML or plain text; a hard size cap while downloading; the text
is stripped of markup and control characters and cut to a fixed length. The text goes to the
author marked as data to paraphrase and cite, never to copy and never as instructions.
"""

import asyncio
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from socrat.coursegen.links import USER_AGENT, public_https
from socrat.coursegen.search import clean
from socrat.coursegen.youtube import video_id

PAGE_CHARS = 6000  # per source: enough to teach from, small enough for the prompt
MAX_PAGES = 3  # pages read per lesson
MAX_BYTES = 1_500_000  # a page larger than this is not read
MAX_HOPS = 3
MIN_TEXT = 400  # less than this is a cookie wall or an app shell, not a page
TIMEOUT = 10
AGENT = "SocratCourseGen"  # the name robots.txt rules are matched against

# Text inside these is never content.
_SKIP = {"script", "style", "noscript", "svg", "nav", "header", "footer", "aside", "form"}
_SKIP |= {"button", "select", "iframe", "template", "figure"}
_BLOCKS = {"p", "div", "li", "br", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section"}
_VOID = {"br", "img", "hr", "input", "meta", "link", "source", "wbr", "area", "base", "col"}


class _Text(HTMLParser):
    """The page's readable text. When the page marks its content with <main> or <article>,
    only that is kept; otherwise everything outside navigation, forms and scripts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.focus = 0
        self.inside: list[str] = []  # text within <main> or <article>
        self.all: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in _VOID:
            if tag == "br":
                self._add(" ")
            return
        if tag in _SKIP:
            self.skip += 1
        elif tag in {"main", "article"}:
            self.focus += 1
        if tag in _BLOCKS:
            self._add(" ")

    def handle_endtag(self, tag):
        if tag in _SKIP and self.skip:
            self.skip -= 1
        elif tag in {"main", "article"} and self.focus:
            self.focus -= 1
        if tag in _BLOCKS:
            self._add(" ")

    def handle_data(self, data):
        if not self.skip:
            self._add(data)

    def _add(self, text: str) -> None:
        self.all.append(text)
        if self.focus:
            self.inside.append(text)


def readable(html_text: str, limit: int = PAGE_CHARS) -> str:
    """Plain text of an HTML page (or the text itself when it is not HTML), bounded."""
    parser = _Text()
    try:
        parser.feed(html_text)
        parser.close()
    except Exception:  # malformed markup: use what was read before it broke
        pass
    focused = clean("".join(parser.inside), limit)
    return focused if len(focused) >= MIN_TEXT else clean("".join(parser.all), limit)


_ROBOTS: dict[str, RobotFileParser | None] = {}  # host -> rules (None: no readable rules)


async def allowed_by_robots(client: httpx.AsyncClient, url: str) -> bool:
    """Whether the site's robots.txt lets this page be read. A site without a readable
    robots.txt has stated no rule, which the convention treats as allowed."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if host not in _ROBOTS:
        rules: RobotFileParser | None = None
        try:
            response = await client.get(f"https://{host}/robots.txt")
            if response.status_code == 200 and len(response.content) <= 500_000:
                rules = RobotFileParser()
                rules.parse(response.text.splitlines())
        except httpx.HTTPError:
            rules = None
        _ROBOTS[host] = rules
    rules = _ROBOTS[host]
    return rules is None or rules.can_fetch(AGENT, url)


async def read(client: httpx.AsyncClient, url: str) -> str:
    """The page's readable text, or "" when it may not or cannot be read."""
    for _ in range(MAX_HOPS + 1):
        if not await asyncio.to_thread(public_https, url):
            return ""
        if not await allowed_by_robots(client, url):
            return ""
        try:
            async with client.stream("GET", url) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    target = response.headers.get("location", "")
                    if not target:
                        return ""
                    url = urljoin(url, target)
                    continue  # the next hop is checked like the first
                kind = response.headers.get("content-type", "").split(";")[0].strip().lower()
                if response.status_code != 200 or kind not in {"text/html", "text/plain"}:
                    return ""
                body = b""
                async for chunk in response.aiter_bytes():
                    body += chunk
                    if len(body) > MAX_BYTES:
                        return ""
                text = body.decode(response.encoding or "utf-8", errors="replace")
        except (httpx.HTTPError, LookupError):
            return ""
        found = readable(text) if kind == "text/html" else clean(text, PAGE_CHARS)
        return found if len(found) >= MIN_TEXT else ""
    return ""


_NOT_PAGES = re.compile(r"\.(pdf|zip|mp4|mp3|pptx?|docx?|xlsx?)($|\?)", re.IGNORECASE)


async def with_pages(
    sources: list[dict], client: httpx.AsyncClient | None = None, limit: int = MAX_PAGES
) -> list[dict]:
    """The researcher's sources, the first ``limit`` readable pages carrying their own text as
    the passage the author writes from and the fact check reads. Videos keep their transcript;
    a page that cannot be read keeps its search snippet."""
    picked = [
        i
        for i, s in enumerate(sources)
        if not s.get("transcript")
        and not video_id(s.get("url", ""))
        and not _NOT_PAGES.search(s.get("url", ""))
    ][:limit]
    if not picked:
        return sources
    own = client is None
    client = client or httpx.AsyncClient(
        timeout=TIMEOUT, follow_redirects=False, headers={"User-Agent": USER_AGENT}
    )
    try:
        texts = await asyncio.gather(
            *(read(client, sources[i]["url"]) for i in picked), return_exceptions=True
        )
    finally:
        if own:
            await client.aclose()
    out = list(sources)
    for i, text in zip(picked, texts, strict=True):
        if isinstance(text, str) and len(text) > len(out[i].get("passage") or ""):
            out[i] = {**out[i], "passage": text, "page": True}
    return out
