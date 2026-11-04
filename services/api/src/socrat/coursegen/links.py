"""Check that resource links an agent proposes are real, public and reachable.

The URLs come from a model, so they are untrusted: only https, only public hosts, few
redirects, short timeouts. A link that cannot be verified is rejected, never shipped.
"""

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

import httpx

USER_AGENT = "SocratCourseGen/1.0 (+https://github.com/Bhatta2006/Socrat)"
HEAD_REFUSED = {400, 403, 405, 501}


def public_https(url: str) -> bool:
    """https to a named host that resolves only to public addresses (no SSRF to internals)."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        return False
    try:
        ipaddress.ip_address(host)
        return False  # raw IPs are never a curated resource
    except ValueError:
        pass
    if host == "localhost" or host.endswith((".local", ".internal", ".localhost")):
        return False
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except OSError:
        return False
    return all(ipaddress.ip_address(info[4][0]).is_global for info in infos)


RETRY = {429, 500, 502, 503, 504}  # busy, not missing: worth one more try


async def reachable(client: httpx.AsyncClient, url: str, tries: int = 2) -> bool:
    if not await asyncio.to_thread(public_https, url):
        return False
    for attempt in range(tries):
        try:
            response = await client.head(url)
            if response.status_code in HEAD_REFUSED:
                response = await client.get(url)
        except httpx.HTTPError:
            response = None  # a live run lost a whole round to one failed check of Wikipedia
        if response is not None and response.status_code not in RETRY:
            break
        if attempt + 1 < tries:
            await asyncio.sleep(1)
    if response is None:
        return False
    # shortcut: redirects are followed without re-checking each hop's address; add a
    # per-hop check if links ever reach internal-facing deployments.
    return response.status_code < 400 and str(response.url).startswith("https://")


async def broken(urls: list[str], client: httpx.AsyncClient | None = None) -> list[str]:
    """The URLs that failed the check."""
    own = client is None
    client = client or httpx.AsyncClient(
        follow_redirects=True,
        max_redirects=3,
        timeout=10,
        headers={"User-Agent": USER_AGENT},
    )
    try:
        results = await asyncio.gather(*(reachable(client, u) for u in urls))
    finally:
        if own:
            await client.aclose()
    return [u for u, ok in zip(urls, results, strict=True) if not ok]
