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
from socrat.explainer.jobs import explainer_settings


async def main(prompt: str, out: Path, mode: str, level: str):
    settings, film_settings = explainer_settings(Settings())
    kwargs = settings.explainer_chat_template_kwargs
    provider = make_provider(settings, chat_template_kwargs=kwargs)
    film_provider = (
        make_provider(film_settings, chat_template_kwargs=kwargs) if film_settings else None
    )
    # Tally the token usage the provider reports, across the router, attempts and the review.
    used = {"calls": 0, "input": 0, "output": 0}

    def count(chosen):
        converse = chosen.converse

        async def counted(*args, **kwargs):
            used["calls"] += 1
            async for event in converse(*args, **kwargs):
                if event.kind == "usage":
                    used["input"] += event.arguments.get("input_tokens", 0)
                    used["output"] += event.arguments.get("output_tokens", 0)
                yield event

        chosen.converse = counted

    for chosen in (provider, film_provider):
        if chosen is not None:
            count(chosen)
    start = time.time()
    async for event in generator.generate(
        provider, settings, prompt, "python", level, mode, film_provider
    ):
        if event["event"] == "progress":
            print(
                f"{time.time() - start:6.1f}s",
                {k: v for k, v in event.items() if k != "event"},
                flush=True,
            )
            continue
        doc = event["document"]
        out.mkdir(parents=True, exist_ok=True)
        if "film" in doc:
            (out / "film.json").write_text(json.dumps(doc["film"], indent=1), encoding="utf-8")
        html, _ = compile_document(doc["html"], "live", "http://localhost:3000", mode=doc["mode"])
        (out / "page.html").write_text(html, encoding="utf-8")
        (out / "result.json").write_text(
            json.dumps({k: v for k, v in doc.items() if k not in ("html", "film")}, indent=1),
            encoding="utf-8",
        )
        print(
            f"done in {time.time() - start:.0f}s: mode={doc['mode']} title={doc['title']!r} qa={doc['qa'].get('ai_review')}"
        )
        print(
            f"tokens: {used['calls']} calls, {used['input']} in, {used['output']} out, model={settings.explainer_3d_model or settings.explainer_model or 'default'}"
        )


asyncio.run(
    main(
        sys.argv[1],
        Path(sys.argv[2]),
        sys.argv[3] if len(sys.argv) > 3 else "auto",
        sys.argv[4] if len(sys.argv) > 4 else "standard",
    )
)
