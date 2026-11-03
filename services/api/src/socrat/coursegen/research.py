"""The researcher: finds public sources for a concept so the author writes from them and cites them.

Sources are only ever *read and paraphrased*, never copied: the model names pages it is sure of,
every URL is checked (public https, reachable), and what ships is a short "Sources" list plus an
"Informed by" credit. Registry entries tell the learner (and us) how each source is licensed.
"""

import re
from urllib.parse import urlparse

from socrat.catalog import sources as registry
from socrat.coursegen import links

MAX_SOURCES = 5

RESEARCHER = """You are the researcher for a course builder. Choose the best PUBLIC sources a
careful author would read before writing one lesson FOR THIS LEARNER. The learner's style,
level, goal and session length are in the context: a source that is excellent but pitched at
the wrong level or format is a bad source (kids need plain explainers and play; rigorous
courses need university notes and proofs; a 5-minute lesson needs one clear page, not a book).

Rules:
- Only pages you are certain exist at exactly that URL (https). A wrong URL is discarded.
- Prefer authority: open textbooks, university course notes, standards bodies, official
  documentation, then reputable explainers. Prefer the registry sources listed below.
- Mix roles: at least one that explains the idea ("explain"), and where they exist one with
  worked examples ("examples"), one visual or interactive ("visual"), one for practice ("practice").
- "supports" is YOUR PARAPHRASE of what the page backs, in one or two sentences. Never quote.
- "use" says how the author should use it FOR THIS LEARNER (one sentence).
- "fit" is 1-5: how well its level and format suit this learner. Do not list anything below 3.
- 3 to 5 sources, best first. No paywalled or login-only pages.

Reply with JSON only:
{"sources": [{"title": "...", "url": "https://...", "role": "explain|examples|visual|practice",
"supports": "...", "use": "...", "fit": 4}]}"""

ROLE_KIND = {
    "explain": "article",
    "examples": "article",
    "visual": "interactive",
    "practice": "docs",
}
MIN_FIT = 3


def registry_hint() -> str:
    entries = registry.load_registry().sources
    return "\n".join(f"- {e.name} ({e.url}): {e.content}" for e in entries)


def prompt(ctx: str) -> str:
    return f"{ctx}\n\nSources from our registry (prefer these):\n{registry_hint()}"


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").removeprefix("www.")


def _license(url: str) -> str:
    """The registry's license note when the URL's site is registered, else a neutral default."""
    host = _host(url)
    for entry in registry.load_registry().sources:
        known = _host(str(entry.url))
        if host == known or host.endswith("." + known):
            return entry.license
    return "public web page"


def candidates(data) -> list[dict]:
    """Well-formed, de-duplicated, capped; the URL check happens separately (network)."""
    raw = data.get("sources") if isinstance(data, dict) else None
    seen: set[str] = set()
    out: list[dict] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        url, title = str(item.get("url", "")).strip(), str(item.get("title", "")).strip()
        supports = str(item.get("supports", "")).strip()
        fit = item.get("fit")
        fit = fit if isinstance(fit, int) and not isinstance(fit, bool) else MIN_FIT
        role = item.get("role") if item.get("role") in ROLE_KIND else "explain"
        if not (url.startswith("https://") and title and supports) or url in seen:
            continue
        if fit < MIN_FIT:
            continue
        seen.add(url)
        out.append(
            {
                "title": title[:120],
                "url": url,
                "supports": supports[:300],
                "role": role,
                "use": str(item.get("use", "")).strip()[:200],
                "fit": min(fit, 5),
            }
        )
    out.sort(key=lambda x: -x["fit"])  # stable: the model's order breaks ties
    return out[:MAX_SOURCES]


NOMINAL_MINUTES = 10  # reading time for a researched source; nobody has timed it


async def screen(data, http=None, allowed: dict | None = None) -> list[dict]:
    """Candidates whose links are public and reachable, numbered from 1 and license-tagged.
    ``allowed`` (url -> search ``Hit``): only search results may be chosen, and their author,
    date, licence and ranking reasons travel with them."""
    found = candidates(data)
    if allowed is not None:
        found = [
            {
                **s,
                "author": allowed[s["url"]].author,
                "published": allowed[s["url"]].published,
                "license": allowed[s["url"]].license,
                "why": "; ".join(allowed[s["url"]].reasons),
            }
            for s in found
            if s["url"] in allowed
        ]
    dead = set(await links.broken([s["url"] for s in found], http)) if found else set()
    kept = [s for s in found if s["url"] not in dead]
    return [
        {**s, "n": i, "license": s.get("license") or _license(s["url"])}
        for i, s in enumerate(kept, 1)
    ]


def block(sources: list[dict]) -> str:
    """The numbered source list the author sees."""
    if not sources:
        return ""
    lines = [f"[{s['n']}] {s['title']} ({s['url']}) — {s['supports']}" for s in sources]
    return (
        "Verified public sources. Write ORIGINAL text from them: paraphrase, never quote or copy. "
        "Cite the ones you use inline as [1], [2]; use at least one.\n" + "\n".join(lines)
    )


def check(text: str, sources: list[dict]) -> list[str]:
    """The lesson must cite real source numbers."""
    if not sources:
        return []
    cited = {int(n) for n in re.findall(r"\[(\d{1,2})\]", text)}
    valid = {s["n"] for s in sources}
    if not cited & valid:
        return [
            f"Cite at least one of the numbered sources inline, like [1]. Sources: {sorted(valid)}."
        ]
    return [f"Citation [{n}] matches no source." for n in sorted(cited - valid)][:3]


def attach(lesson: dict, sources: list[dict]) -> dict:
    """Add the Sources section and merge the links into the lesson's resources (idempotent)."""
    if not sources:
        return lesson
    text = str(lesson.get("lesson", ""))
    if "\n## Sources" not in text:
        listing = "\n".join(
            f"{s['n']}. [{s['title']}]({s['url']}) — {s['license']}" for s in sources
        )
        text = f"{text.rstrip()}\n\n## Sources\n\n{listing}\n"
    have = {r.get("url") for r in lesson.get("resources", []) if isinstance(r, dict)}
    # A cited source the author did not list becomes a resource. It needs a site name and a
    # reading time to be a valid Resource; the time is a stated nominal value, not measured.
    extra = [
        {
            "title": s["title"],
            "url": s["url"],
            "kind": ROLE_KIND[s.get("role", "explain")],
            "source": (_host(s["url"]) or "web")[:80],
            "minutes": NOMINAL_MINUTES,
            "author": str(s.get("author", ""))[:200],
            "published": str(s.get("published", ""))[:40],
            "license": str(s.get("license", ""))[:120],
            "why": (str(s.get("why") or s.get("supports", "")))[:300],
        }
        for s in sources
        if s["url"] not in have
    ]
    return {**lesson, "lesson": text, "resources": [*lesson.get("resources", []), *extra][:8]}


def credit(sources: list[dict]) -> str:
    if not sources:
        return ""
    names = "; ".join(f"{s['title']} ({s['license']})" for s in sources)
    return f" Informed by public sources, paraphrased and not copied: {names}."
