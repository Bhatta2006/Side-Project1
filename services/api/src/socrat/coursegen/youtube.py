"""YouTube as a research source: videos and playlists found with the YouTube Data API, ranked
by views and by how well they fit the lesson, and (when the owner allows it) their captions
given to the author as source text.

Search uses the official API with the owner's key (``Settings.youtube_api_key``). Each lesson
costs about 100 quota units, so the free 10,000 a day covers about 100 lessons. A video is kept
only when its title or description shares a word with the query, so a popular but unrelated
video is never a source; shorts and videos over an hour are left out.

Captions have no official API for other people's videos: ``transcript`` uses
youtube-transcript-api, which reads the public captions the watch page shows. That is why it
sits behind ``Settings.youtube_transcripts`` (off by default). Like every source, a transcript
is untrusted data: cleaned, capped, and paraphrased by the author, never copied.
"""

import asyncio
import re

import httpx

from socrat.coursegen.search import Hit, _get, clean

API = "https://www.googleapis.com/youtube/v3"
PER_SEARCH = 8
PLAYLIST_SAMPLE = 5  # a playlist's reach is the views of its first few videos
MIN_SECONDS, MAX_SECONDS = 120, 3600
TRANSCRIPT_CHARS = 6000  # per video: enough to teach from, small enough for the prompt
MAX_TRANSCRIPTS = 2
ENGLISH = ["en", "en-US", "en-GB", "en-IN"]
_DURATION = re.compile(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")
_VIDEO = re.compile(r"^https://www\.youtube\.com/watch\?v=([\w-]{11})$")


def seconds(iso: str) -> int:
    """ISO 8601 duration (PT1H2M3S) in seconds; 0 when it cannot be read."""
    match = _DURATION.fullmatch(iso or "")
    if not match:
        return 0
    d, h, m, s = (int(x or 0) for x in match.groups())
    return ((d * 24 + h) * 60 + m) * 60 + s


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2}


async def search(client: httpx.AsyncClient, query: str, limit: int, key: str) -> list[Hit]:
    """Videos and playlists for ``query`` with their views. Failures add nothing."""
    found = await _get(
        client,
        f"{API}/search",
        {
            "part": "snippet",
            "q": query,
            "type": "video,playlist",
            "maxResults": PER_SEARCH,
            "safeSearch": "strict",
            "key": key,
        },
    )
    if found is None:
        return []
    items = found.json().get("items", [])
    videos = [i["id"]["videoId"] for i in items if i.get("id", {}).get("videoId")]
    playlists = [i["id"]["playlistId"] for i in items if i.get("id", {}).get("playlistId")]
    samples = await asyncio.gather(*(_sample(client, p, key) for p in playlists))
    stats = await _stats(client, videos + [v for s in samples for v in s], key)
    wanted = _words(query)
    out = []
    for item in items:
        ids, info = item.get("id", {}), item.get("snippet", {})
        title, about = clean(info.get("title", ""), 160), clean(info.get("description", ""))
        if not title or not wanted & (_words(title) | _words(about)):
            continue  # not about this lesson, however popular
        common = {
            "title": title,
            "snippet": about,
            "provider": "youtube",
            "author": clean(info.get("channelTitle", ""), 120),
            "published": str(info.get("publishedAt", ""))[:10],
        }
        if ids.get("videoId") in stats:
            views, length, licence = stats[ids["videoId"]]
            if not MIN_SECONDS <= length <= MAX_SECONDS:
                continue
            out.append(
                Hit(
                    url=f"https://www.youtube.com/watch?v={ids['videoId']}",
                    kind="video",
                    license=licence,
                    views=views,
                    **common,
                )
            )
        elif ids.get("playlistId"):
            sample = samples[playlists.index(ids["playlistId"])]
            out.append(
                Hit(
                    url=f"https://www.youtube.com/playlist?list={ids['playlistId']}",
                    kind="playlist",
                    license="YouTube standard licence; linked, not copied",
                    views=sum(stats[v][0] for v in sample if v in stats),
                    **common,
                )
            )
    return out[:limit]


async def _sample(client: httpx.AsyncClient, playlist: str, key: str) -> list[str]:
    response = await _get(
        client,
        f"{API}/playlistItems",
        {
            "part": "contentDetails",
            "playlistId": playlist,
            "maxResults": PLAYLIST_SAMPLE,
            "key": key,
        },
    )
    if response is None:
        return []
    return [
        str(i.get("contentDetails", {}).get("videoId", ""))
        for i in response.json().get("items", [])
        if i.get("contentDetails", {}).get("videoId")
    ]


async def _stats(
    client: httpx.AsyncClient, ids: list[str], key: str
) -> dict[str, tuple[int, int, str]]:
    """video id -> (views, seconds, licence), 50 ids per call (1 quota unit each)."""
    out: dict[str, tuple[int, int, str]] = {}
    unique = list(dict.fromkeys(ids))
    for start in range(0, len(unique), 50):
        response = await _get(
            client,
            f"{API}/videos",
            {
                "part": "statistics,contentDetails,status",
                "id": ",".join(unique[start : start + 50]),
                "key": key,
            },
        )
        for item in response.json().get("items", []) if response is not None else []:
            try:
                views = int(item.get("statistics", {}).get("viewCount", 0))
            except (TypeError, ValueError):
                views = 0
            licence = (
                "Creative Commons BY (YouTube)"
                if item.get("status", {}).get("license") == "creativeCommon"
                else "YouTube standard licence; linked, not copied"
            )
            out[item["id"]] = (
                views,
                seconds(item.get("contentDetails", {}).get("duration")),
                licence,
            )
    return out


def video_id(url: str) -> str:
    match = _VIDEO.match(url)
    return match.group(1) if match else ""


def transcript(video: str, chars: int = TRANSCRIPT_CHARS) -> str:
    """The video's captions as plain text (English when there are English ones), or "" when it
    has none or they cannot be read. Blocking: call it in a thread."""
    from youtube_transcript_api import YouTubeTranscriptApi

    try:
        listing = YouTubeTranscriptApi().list(video)
        try:
            chosen = listing.find_transcript(ENGLISH)
        except Exception:  # no English: whatever the video has
            chosen = next(iter(listing))
        text = " ".join(part.text for part in chosen.fetch())
    except Exception:  # captions off, video gone, or YouTube refused: no transcript
        return ""
    return clean(text, chars)


async def with_transcripts(sources: list[dict], limit: int = MAX_TRANSCRIPTS) -> list[dict]:
    """The researcher's sources, the first ``limit`` videos carrying their transcript as the
    passage the author writes from and the fact check reads."""
    picked = [i for i, s in enumerate(sources) if video_id(s.get("url", ""))][:limit]
    texts = await asyncio.gather(
        *(asyncio.to_thread(transcript, video_id(sources[i]["url"])) for i in picked)
    )
    out = list(sources)
    for i, text in zip(picked, texts, strict=True):
        if text:
            out[i] = {**out[i], "passage": text, "transcript": True}
    return out
