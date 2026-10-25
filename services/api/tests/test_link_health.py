"""Link health for curated resources and practice links; offline by default, fixtures only."""

import csv
import importlib.util
from pathlib import Path

import httpx

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "content" / "link_health.py"
spec = importlib.util.spec_from_file_location("link_health", SCRIPT)
assert spec and spec.loader
link_health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(link_health)

ROBOTS_OPEN = "User-agent: *\nAllow: /\n"


def run(handler, urls, delay=0.0, sleeps=None):
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    client = httpx.Client(transport=httpx.MockTransport(record))
    results = link_health.check_all(
        urls, client, delay=delay, sleep=(sleeps.append if sleeps is not None else lambda s: None)
    )
    return {r.url: r for r in results}, seen


def test_head_falls_back_to_get_when_the_server_refuses_head():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=ROBOTS_OPEN)
        if request.method == "HEAD":
            return httpx.Response(405)
        return httpx.Response(200, text="<title>Docs</title>")

    results, _ = run(handler, ["https://docs.example.org/page"])
    assert results["https://docs.example.org/page"].status == "ok"
    assert results["https://docs.example.org/page"].method == "GET"


def test_robots_disallowed_urls_are_not_fetched():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
        return httpx.Response(200)

    results, seen = run(handler, ["https://site.example.org/private/x"])
    assert results["https://site.example.org/private/x"].status == "robots-disallowed"
    assert [r.url.path for r in seen] == ["/robots.txt"]


def test_requests_identify_socrat_and_wait_between_calls_to_the_same_host():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200)

    sleeps: list[float] = []
    urls = ["https://a.example.org/1", "https://a.example.org/2", "https://a.example.org/3"]
    _, seen = run(handler, urls, delay=1.5, sleeps=sleeps)
    assert all(r.headers["user-agent"] == link_health.USER_AGENT for r in seen)
    assert "Mozilla" not in link_health.USER_AGENT
    assert sleeps == [1.5, 1.5]


def test_bot_protected_hosts_are_unverifiable_and_other_errors_are_broken():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.host == "leetcode.com":
            return httpx.Response(403)
        return httpx.Response(404)

    results, _ = run(
        handler, ["https://leetcode.com/problems/two-sum/", "https://gone.example.org/x"]
    )
    assert results["https://leetcode.com/problems/two-sum/"].status == "unverifiable"
    assert results["https://gone.example.org/x"].status == "http 404"
    assert results["https://gone.example.org/x"].broken


def test_removed_youtube_videos_are_reported_missing():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=ROBOTS_OPEN)
        return httpx.Response(200, text="<html><title>- YouTube</title></html>")

    results, _ = run(handler, ["https://www.youtube.com/watch?v=gone"])
    assert results["https://www.youtube.com/watch?v=gone"].status == "missing video"


def test_collects_curated_resources_and_practice_links_from_the_catalog():
    links = link_health.collect()
    resources = [u for u, info in links.items() if "resource" in info["kinds"]]
    practice = [u for u, info in links.items() if "practice" in info["kinds"]]
    from socrat.catalog.registry import default_catalog

    concepts = default_catalog().concepts.values()
    assert len(resources) == len({str(r.url) for c in concepts for r in c.resources}) >= 152
    assert len(practice) == len({str(p.url) for c in concepts for p in c.practice_links}) >= 126


def test_offline_by_default_and_fixture_runs_write_a_csv(tmp_path, capsys):
    assert link_health.main(["--out", str(tmp_path / "none.csv")]) == 2
    assert "--live" in capsys.readouterr().err
    assert not (tmp_path / "none.csv").exists()

    fixtures = tmp_path / "fixtures.json"
    fixtures.write_text(
        '{"https://docs.python.org/3/": 200, "https://gone.example.org/": 404}', encoding="utf-8"
    )
    out = tmp_path / "report.csv"
    code = link_health.main(
        [
            "--fixtures",
            str(fixtures),
            "--out",
            str(out),
            "--url",
            "https://docs.python.org/3/",
            "--url",
            "https://gone.example.org/",
        ]
    )
    assert code == 1
    with out.open(encoding="utf-8", newline="") as handle:
        rows = {row["url"]: row for row in csv.DictReader(handle)}
    assert rows["https://docs.python.org/3/"]["status"] == "ok"
    assert rows["https://gone.example.org/"]["status"] == "http 404"
