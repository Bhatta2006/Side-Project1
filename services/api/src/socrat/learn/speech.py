"""A lesson page read aloud by Gemini text-to-speech (``assistant/vertex.speak``).

``GET /api/v1/concepts/{id}/speech?page=N`` returns one page of the lesson (the same '## '
pages the web shows) as WAV audio. Code, hidden answers, tables and display formulas are left
out; inline maths is read as plain words. Off until ``SOCRAT_LESSON_SPEECH`` is set; the web
falls back to the browser's own voice whenever this is off or fails.
"""

import re
from collections import OrderedDict

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy.orm import Session

from socrat.assistant import vertex
from socrat.assistant.gateway import ProviderError

router = APIRouter(prefix="/api/v1/concepts")

STYLE = "Read this lesson page aloud to one learner, in a warm, clear, unhurried teaching voice:"
MAX_CHARS = 4000  # one page; longer is cut at a sentence
# ponytail: per-process memory cache; move to a table or object store if restarts make
# re-synthesis cost show up in the AI usage report.
_CACHE: OrderedDict[tuple, tuple[bytes, str]] = OrderedDict()
CACHE_SIZE = 24

_WORDS = {
    r"\times": " times ",
    r"\cdot": " times ",
    r"\le": " at most ",
    r"\ge": " at least ",
    r"\neq": " is not ",
    r"\cap": " and ",
    r"\cup": " or ",
    r"\in": " in ",
    r"\mid": " given ",
}


def pages(lesson: str) -> list[str]:
    """The lesson's '## ' pages, each with its heading; text before the first heading joins
    page one (as apps/web/src/lib/pages.ts splits them)."""
    parts = re.split(r"^## ", lesson.replace("\r\n", "\n"), flags=re.MULTILINE)
    lead, rest = parts[0].strip(), parts[1:]
    if not rest:
        return [lead] if lead else []
    out = [p.strip() for p in rest]
    if lead:
        title, _, body = out[0].partition("\n")
        out[0] = f"{title}\n{lead}\n{body}"
    return out


def _maths(tex: str) -> str:
    for command, word in _WORDS.items():
        tex = tex.replace(command, word)
    tex = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"\1 over \2", tex)
    tex = re.sub(r"\\[a-zA-Z]+", lambda m: m.group(0)[1:], tex)  # \sigma -> sigma
    tex = tex.replace("^c", " complement").replace("^", " to the ").replace("_", " ")
    return re.sub(r"[{}\\]", "", tex)


def speakable(page: str) -> str:
    """Plain sentences a voice can read."""
    text = re.sub(r"```.*?```", " ", page, flags=re.DOTALL)
    text = re.sub(r"<details.*?</details>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"\$\$.*?\$\$|\\\[.*?\\\]", " ", text, flags=re.DOTALL)
    text = re.sub(r"\$([^$\n]+?)\$", lambda m: _maths(m.group(1)), text)
    text = re.sub(r"^\s*\|.*$", " ", text, flags=re.MULTILINE)  # tables
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links keep their words
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[#*_`>]+", "", text)
    text = re.sub(r"^\s*[-+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    if len(text) > MAX_CHARS:
        cut = text.rfind(". ", 0, MAX_CHARS)
        text = text[: cut + 1 if cut > 0 else MAX_CHARS]
    return text


@router.get("/{qualified}/speech")
async def speech(qualified: str, request: Request, page: int = 0) -> Response:
    from socrat.learn.routes import catalog, engine, guard_instruction, user_of

    settings = request.app.state.settings
    if not settings.lesson_speech:
        raise HTTPException(404, "not_found")
    cat = catalog()
    if qualified not in cat.concepts:
        raise HTTPException(404, "not_found")
    with Session(engine(request)) as db:
        user = user_of(request, db)
        guard_instruction(db, cat, user, qualified)
    concept = cat.concept(qualified)
    found = pages(concept.lesson)
    if not 0 <= page < len(found):
        raise HTTPException(404, "no_such_page")
    version = concept.provenance.version if concept.provenance else 0
    key = (qualified, version, page, settings.vertex_tts_voice, settings.vertex_tts_model)
    if key not in _CACHE:
        text = speakable(found[page])
        if not text:
            raise HTTPException(404, "nothing_to_read")
        try:
            media = await vertex.speak(
                settings,
                f"{STYLE}\n\n{text}",
                engine=engine(request),
                user_id=user.id,
                feature="lesson_speech",
            )
        except ProviderError as exc:
            raise HTTPException(503, str(exc)) from exc
        _CACHE[key] = (media.data, media.mime)
        while len(_CACHE) > CACHE_SIZE:
            _CACHE.popitem(last=False)
    _CACHE.move_to_end(key)
    data, mime = _CACHE[key]
    return Response(data, media_type=mime, headers={"Cache-Control": "private, max-age=86400"})
