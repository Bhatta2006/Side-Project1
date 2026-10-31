"""Live generation without the web app: python scripts/dev/clicky3d/live.py "<prompt>" <out-dir> [mode] [level]
Uses the configured explainer model (it costs API credits); writes film.json, page.html, result.json."""

import asyncio
import json
import sys
import time
from pathlib import Path

from socrat.assistant.gateway import make_provider
from socrat.config import Settings
from socrat.explainer import generator
from socrat.explainer.artifact import compile_document


async def main(prompt: str, out: Path, mode: str, level: str):
    settings = Settings()
    if settings.explainer_model:
        key = "openai_model" if settings.ai_provider == "openai" else "ai_model"
        settings = settings.model_copy(update={key: settings.explainer_model})
    provider = make_provider(settings, chat_template_kwargs=settings.explainer_chat_template_kwargs)
    start = time.time()
    async for event in generator.generate(provider, settings, prompt, "python", level, mode):
        if event["event"] == "progress":
            print(f"{time.time() - start:6.1f}s", {k: v for k, v in event.items() if k != "event"}, flush=True)
            continue
        doc = event["document"]
        out.mkdir(parents=True, exist_ok=True)
        if "film" in doc:
            (out / "film.json").write_text(json.dumps(doc["film"], indent=1), encoding="utf-8")
        html, _ = compile_document(doc["html"], "live", "http://localhost:3000", mode=doc["mode"])
        (out / "page.html").write_text(html, encoding="utf-8")
        (out / "result.json").write_text(json.dumps({k: v for k, v in doc.items() if k not in ("html", "film")}, indent=1), encoding="utf-8")
        print(f"done in {time.time() - start:.0f}s: mode={doc['mode']} title={doc['title']!r} qa={doc['qa'].get('ai_review')}")


asyncio.run(main(sys.argv[1], Path(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else "auto", sys.argv[4] if len(sys.argv) > 4 else "standard"))
