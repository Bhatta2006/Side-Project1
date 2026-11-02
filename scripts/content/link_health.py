"""Link health for curated course resources and practice links.

Offline by default: nothing touches the network unless ``--live`` is given. ``--fixtures``
replays recorded status codes (for tests and dry runs). Live checks are polite: one
robots.txt read per host, URLs disallowed by it are skipped, a delay between requests to
the same host, a Socrat User-Agent, HEAD first with a GET fallback.

Some sites (LeetCode, Codeforces) block automated clients; a 403/429/503 from those hosts
is reported as "unverifiable" rather than broken. Any broken link exits 1.

Usage:
  python scripts/content/link_health.py --live [--out .cache/link-health.csv] [--delay 1.0]
  python scripts/content/link_health.py --fixtures responses.json --url https://...
"""

import argparse
import concurrent.futures
import csv
import json
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.robotparser import RobotFileParser

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "api" / "src"))

from socrat.catalog.registry import CONTENT_ROOT, load  # noqa: E402

USER_AGENT = "SocratLinkHealth/1.0 (+https://github.com/Bhatta2006/Socrat)"
BOT_PROTECTED = {
    "leetcode.com",
    "codeforces.com",
    "realpython.com",
    "www.geeksforgeeks.org",
    "en.cppreference.com",
    "cppreference.com",
}
HEAD_REFUSED = {400, 403, 405, 501}
FIELDS = ["url", "host", "kinds", "concepts", "status", "http_status", "method", "final_url"]


@dataclass
class Result:
    url: str
    host: str
    status: str
    http_status: int | None = None
    method: str = ""
    final_url: str = ""

    @property
    def broken(self) -> bool:
        return self.status not in {"ok", "unverifiable", "robots-disallowed"}


def collect(root: Path = CONTENT_ROOT) -> dict[str, dict]:
    """URL -> {kinds, concepts} for every course resource and authored practice link."""
    catalog = load(root, tests_root=None)
    links: dict[str, dict] = {}
    for key, concept in catalog.concepts.items():
        for kind, items in (("resource", concept.resources), ("practice", concept.practice_links)):
            for item in items:
                entry = links.setdefault(str(item.url), {"kinds": set(), "concepts": set()})
                entry["kinds"].add(kind)
                entry["concepts"].add(key)
    return links


def robots_for(client: httpx.Client, url: httpx.URL) -> RobotFileParser:
    parser = RobotFileParser()
    try:
        response = client.get(url.copy_with(path="/robots.txt", query=None, fragment=None))
        lines = response.text.splitlines() if response.status_code == 200 else []
    except httpx.HTTPError:
        lines = []  # Unreadable robots.txt: treated as no restrictions, like most crawlers.
    parser.parse(lines)
    return parser


def check(client: httpx.Client, url: str) -> Result:
    target = httpx.URL(url)
    host = target.host
    youtube = host.endswith("youtube.com")
    try:
        method = "GET" if youtube else "HEAD"
        response = client.request(method, url, follow_redirects=True)
        if method == "HEAD" and response.status_code in HEAD_REFUSED:
            method = "GET"
            response = client.get(url, follow_redirects=True)
    except httpx.HTTPError as exc:
        if host in BOT_PROTECTED and isinstance(exc, httpx.TimeoutException):
            return Result(url, host, "unverifiable")
        return Result(url, host, f"error {type(exc).__name__}")
    code = response.status_code
    final = str(response.url)
    if code < 400:
        # YouTube answers 200 for removed videos; a real video page has a title.
        if youtube and "<title>- YouTube</title>" in response.text:
            return Result(url, host, "missing video", code, method, final)
        return Result(url, host, "ok", code, method, final)
    if host in BOT_PROTECTED and code in {403, 429, 503}:
        return Result(url, host, "unverifiable", code, method, final)
    return Result(url, host, f"http {code}", code, method, final)


def check_host(
    client: httpx.Client, urls: list[str], delay: float, sleep: Callable[[float], None]
) -> list[Result]:
    robots = robots_for(client, httpx.URL(urls[0]))
    results = []
    fetched = 0
    for url in urls:
        host = httpx.URL(url).host
        if not robots.can_fetch(USER_AGENT, url):
            results.append(Result(url, host, "robots-disallowed"))
            continue
        if fetched:
            sleep(delay)
        fetched += 1
        results.append(check(client, url))
    return results


def check_all(
    urls: list[str],
    client: httpx.Client,
    delay: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
    workers: int = 8,
) -> list[Result]:
    """Hosts run in parallel; each host's URLs run one at a time with ``delay`` between."""
    client.headers["User-Agent"] = USER_AGENT
    by_host: dict[str, list[str]] = {}
    for url in urls:
        by_host.setdefault(httpx.URL(url).host, []).append(url)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        batches = pool.map(lambda group: check_host(client, group, delay, sleep), by_host.values())
        found = {result.url: result for batch in batches for result in batch}
    return [found[url] for url in urls]


def fixture_client(path: Path) -> httpx.Client:
    """Replays recorded status codes; robots.txt is absent everywhere."""
    codes = json.loads(path.read_text(encoding="utf-8"))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(codes.get(str(request.url), 404))

    return httpx.Client(transport=httpx.MockTransport(handler))


def write_report(results: list[Result], links: dict[str, dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for r in results:
            info = links.get(r.url, {"kinds": set(), "concepts": set()})
            writer.writerow(
                dict(
                    url=r.url,
                    host=r.host,
                    kinds=";".join(sorted(info["kinds"])),
                    concepts=";".join(sorted(info["concepts"])),
                    status=r.status,
                    http_status="" if r.http_status is None else r.http_status,
                    method=r.method,
                    final_url=r.final_url,
                )
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check curated resource and practice links.")
    parser.add_argument("--live", action="store_true", help="make real network requests")
    parser.add_argument("--fixtures", type=Path, help="JSON of URL -> status code to replay")
    parser.add_argument("--out", type=Path, default=ROOT / ".cache" / "link-health.csv")
    parser.add_argument(
        "--delay", type=float, default=1.0, help="seconds between same-host requests"
    )
    parser.add_argument("--url", action="append", default=[], help="check only these URLs")
    args = parser.parse_args(argv)
    if not args.live and not args.fixtures:
        print(
            "Offline by default: pass --live to check links over the network, "
            "or --fixtures for recorded responses.",
            file=sys.stderr,
        )
        return 2
    links = {url: {"kinds": set(), "concepts": set()} for url in args.url} or collect()
    urls = sorted(links)
    client = fixture_client(args.fixtures) if args.fixtures else httpx.Client(timeout=20)
    with client:
        results = check_all(urls, client, delay=0.0 if args.fixtures else args.delay)
    write_report(results, links, args.out)
    broken = [r for r in results if r.broken]
    for r in broken:
        print(f"BROKEN {r.status}: {r.url}")
    counts = {
        s: sum(1 for r in results if r.status == s)
        for s in ("ok", "unverifiable", "robots-disallowed")
    }
    print(
        f"{len(results)} links: {counts['ok']} ok, {counts['unverifiable']} unverifiable (bot-protected), "
        f"{counts['robots-disallowed']} skipped by robots.txt, {len(broken)} broken. Report: {args.out}"
    )
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
