"""YouTube as a source: videos and playlists ranked by views and fit to the lesson, unrelated or
off-length videos left out, captions handed to the author as source text, and a stronger model
only for rewrites. No network: the API is mocked and captions are monkeypatched."""

import asyncio

import httpx

from socrat.config import Settings
from socrat.coursegen import research, roles, search, youtube

SEARCH = {
    "items": [
        {
            "id": {"videoId": "AAAAAAAAAAA"},
            "snippet": {
                "title": "Knife skills for beginners",
                "description": "How to hold a chef knife and use the claw grip",
                "channelTitle": "Cook School",
                "publishedAt": "2024-05-01T00:00:00Z",
            },
        },
        {
            "id": {"videoId": "BBBBBBBBBBB"},
            "snippet": {"title": "Top 10 car crashes", "description": "Wow"},
        },
        {
            "id": {"videoId": "CCCCCCCCCCC"},
            "snippet": {"title": "Knife trick #shorts", "description": "knife"},
        },
        {
            "id": {"playlistId": "PLxyz"},
            "snippet": {"title": "Basic knife skills course", "description": "Ten lessons"},
        },
    ]
}
VIDEOS = {
    "items": [
        {
            "id": "AAAAAAAAAAA",
            "statistics": {"viewCount": "2500000"},
            "contentDetails": {"duration": "PT12M30S"},
            "status": {"license": "creativeCommon"},
        },
        {
            "id": "BBBBBBBBBBB",
            "statistics": {"viewCount": "90000000"},
            "contentDetails": {"duration": "PT8M"},
        },
        {
            "id": "CCCCCCCCCCC",
            "statistics": {"viewCount": "500000"},
            "contentDetails": {"duration": "PT45S"},
        },
        {
            "id": "DDDDDDDDDDD",
            "statistics": {"viewCount": "40000"},
            "contentDetails": {"duration": "PT9M"},
        },
    ]
}
ITEMS = {"items": [{"contentDetails": {"videoId": "DDDDDDDDDDD"}}]}


def api():
    asked = []

    async def handler(request: httpx.Request) -> httpx.Response:
        asked.append(request.url.path)
        assert request.url.params["key"] == "k"
        answer = {"/youtube/v3/search": SEARCH, "/youtube/v3/videos": VIDEOS}
        return httpx.Response(200, json=answer.get(request.url.path, ITEMS))

    return httpx.AsyncClient(transport=httpx.MockTransport(handler)), asked


def test_videos_and_playlists_are_ranked_by_views_and_fit_to_the_lesson():
    client, asked = api()
    hits = asyncio.run(
        search.gather("knife skills claw grip", ["youtube"], client, youtube_key="k")
    )
    by_url = {h.url: h for h in hits}
    video = by_url["https://www.youtube.com/watch?v=AAAAAAAAAAA"]
    assert video.kind == "video" and video.views == 2_500_000 and video.author == "Cook School"
    assert video.license.startswith("Creative Commons") and "2,500,000 views" in video.reasons
    playlist = by_url["https://www.youtube.com/playlist?list=PLxyz"]
    assert playlist.kind == "playlist" and playlist.views == 40_000
    # Unrelated however popular, and a 45-second short, are not sources.
    assert not any("BBBBBBBBBBB" in u or "CCCCCCCCCCC" in u for u in by_url)
    assert hits[0] is video and "2,500,000 views" in search.block(hits)
    assert asked.count("/youtube/v3/search") == 1  # one query: the quota is 100 units a search


def test_without_a_key_youtube_is_not_searched():
    client, asked = api()
    assert asyncio.run(search.gather("knife", ["youtube"], client)) == []
    assert asked == []


def test_durations_are_read_from_iso_8601():
    assert youtube.seconds("PT1H2M3S") == 3723 and youtube.seconds("PT45S") == 45
    assert youtube.seconds("P1DT1M") == 86460 and youtube.seconds("junk") == 0


def test_the_first_videos_carry_their_transcript_as_the_passage(monkeypatch):
    seen = []

    def captions(video, chars=youtube.TRANSCRIPT_CHARS):
        seen.append(video)
        return "" if video == "BBBBBBBBBBB" else f"hold the knife like this {video}"

    monkeypatch.setattr(youtube, "transcript", captions)
    sources = [
        {"n": n, "title": f"Source {n}", "supports": "knives", "url": url, "passage": "about"}
        for n, url in enumerate(
            [
                "https://en.wikipedia.org/wiki/Knife",
                "https://www.youtube.com/watch?v=AAAAAAAAAAA",
                "https://www.youtube.com/watch?v=BBBBBBBBBBB",
                "https://www.youtube.com/watch?v=DDDDDDDDDDD",
            ],
            1,
        )
    ]
    out = asyncio.run(youtube.with_transcripts(sources))
    assert seen == ["AAAAAAAAAAA", "BBBBBBBBBBB"]  # two videos at most
    assert out[1]["passage"].startswith("hold the knife") and out[1]["transcript"]
    assert out[2]["passage"] == "about" and "transcript" not in out[2]  # no captions: as found
    assert out[0] == sources[0] and out[3] == sources[3]
    assert "hold the knife like this" in research.block(out)  # the author reads it, as data


def test_a_video_source_becomes_a_video_resource():
    source = {
        "n": 1,
        "title": "Knife skills",
        "url": "https://www.youtube.com/watch?v=AAAAAAAAAAA",
        "role": "examples",
        "media": "video",
        "license": "YouTube standard licence; linked, not copied",
        "supports": "the claw grip",
    }
    lesson = research.attach({"lesson": "Hold it [1].", "resources": []}, [source])
    assert lesson["resources"][0]["kind"] == "video"


def test_rewrites_use_the_reviser_model_and_fall_back_to_the_author():
    plain = Settings(gen_roles={"author": {"model": "cheap"}})
    assert roles.role_settings(plain, "reviser").ai_model == "cheap"
    mixed = Settings(gen_roles={"author": {"model": "cheap"}, "reviser": {"model": "strong"}})
    assert roles.role_settings(mixed, "reviser").ai_model == "strong"
    assert roles.role_settings(mixed, "author").ai_model == "cheap"
