import asyncio
import json
import re
import time
import unittest.mock
import uuid
from pathlib import Path
from urllib.parse import urlparse

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.assistant.gateway import Event
from socrat.config import Settings
from socrat.explainer import artifact, generator, jobs, routes
from socrat.explainer import film as films
from socrat.models import AssistantMessage, PlaygroundJob

HTML = (Path(__file__).parent / "fixtures/visual.html").read_text(encoding="utf-8")
QA = dict(ok=True, step_count=4, checks=["working-interaction"])


class Provider:
    name = "test"

    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    async def converse(self, system, turns, *args):
        self.calls.append((system, list(turns)))
        yield Event("text", next(self.responses))


@pytest.fixture
def configured(client, monkeypatch):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    client.app.state.settings.ai_provider = "openai"
    provider = Provider([HTML] * 20)
    monkeypatch.setattr(jobs, "make_provider", lambda _, **kwargs: provider)

    async def check(*args):
        return QA

    monkeypatch.setattr(generator, "render_check", check)

    async def review(*args):
        pass

    monkeypatch.setattr(generator, "review", review)
    return headers, provider


def test_artifact_validation_and_compiler_boundaries():
    document = artifact.validate(HTML)
    assert document.title == "Interactive multiplier" and len(document.transcript) > 100
    compiled, csp = artifact.compile_document(HTML, "frame-id", "http://localhost:3000")
    assert "sandbox allow-scripts" in csp and "allow-same-origin" not in csp
    assert "connect-src 'none'" in csp and "script-src 'nonce-" in csp
    assert csp.endswith(", script-src 'unsafe-inline'")
    assert "<script nonce=" in compiled and "frame-id" in compiled
    # Side-by-side panels with fixed widths must wrap instead of needing a sideways scroll.
    assert "flexWrap = 'wrap'" in compiled and "gridTemplateColumns" in compiled
    filtered = HTML.replace(
        '<rect id="bar"',
        '<defs><filter id="glow"><feGaussianBlur stdDeviation="2"></feGaussianBlur></filter></defs><rect id="bar"',
    )
    assert "<fegaussianblur" in artifact.validate(filtered).html
    for reference in ["url(#glow)", 'url( "#glow" )', "url('#glow')"]:
        artifact.Validator.check_css("filter:" + reference)
    with pytest.raises(artifact.ArtifactError):
        artifact.Validator.check_css('background:url("https://example.com/image")')
    dark, _ = artifact.compile_document(HTML, "frame-id", "http://localhost:3000", "dark")
    assert "color-scheme:dark" in dark and "--primary: #4A63FF" in dark
    light, _ = artifact.compile_document(HTML, "frame-id", "http://localhost:3000")
    assert "--primary: #2340E8" in light
    # Proof (highlighter yellow) is a host concept and never reaches generated documents.
    assert "--proof" not in dark and "--proof" not in light and "#F7E33E" not in dark + light
    for bad in [
        HTML.replace("<main>", '<main onclick="alert(1)">'),
        HTML.replace("<main>", "<iframe></iframe><main>"),
        HTML.replace("<main>", "<form></form><main>"),
        HTML.replace("<main>", '<img src="https://example.com/a"><main>'),
        HTML.replace(
            "<head>", '<head><meta http-equiv="refresh" content="0;url=https://example.com">'
        ),
        HTML.replace("<style>", '<style>@import "https://example.com";'),
        HTML.replace('id="visual"', 'id="other"'),
        HTML[:-20],
        "x" * 300001,
    ]:
        with pytest.raises(artifact.ArtifactError):
            artifact.validate(bad)


def test_real_browser_preflight():
    started = time.monotonic()
    checked = asyncio.run(
        generator.render_check(artifact.validate(HTML), Settings(environment="test"))
    )
    # The checker must exit once its verdict is known; waiting for a slow browser close (about 6 s
    # with Edge on Windows) pushed passing visuals past the 18 s budget under load.
    assert time.monotonic() - started < 6
    assert checked["ok"] and checked["step_count"] == 4
    broken = HTML.replace("get currentStep(){return index}", "get currentStep(){return 0}")
    with pytest.raises(artifact.ArtifactError, match="currentStep must report"):
        asyncio.run(generator.render_check(artifact.validate(broken), Settings(environment="test")))
    # A trace table in a closed <details> keeps its cell and row breaks in the saved transcript.
    traced = re.sub(
        r'(<section id="transcript"[^>]*>)',
        r"\1<details><summary>Trace</summary><table><tr><th>Step</th><th>Array</th></tr>"
        r"<tr><td>0</td><td>[7, 2]</td></tr></table></details>",
        HTML,
        count=1,
    )
    transcript = asyncio.run(
        generator.render_check(artifact.validate(traced), Settings(environment="test"))
    )["transcript"]
    assert "Step\tArray" in transcript and "\n0\t[7, 2]" in transcript
    nonzero = HTML.replace("let index=0;", "let index=2;")
    assert asyncio.run(
        generator.render_check(artifact.validate(nonzero), Settings(environment="test"))
    )["ok"]
    text_scene = (
        HTML.replace('type="number"', 'type="text"')
        .replace("let index=0;", "let index=1;")
        .replace("get stepCount(){return 4}", "get stepCount(){return 1}")
        .replace("get currentStep(){return index}", "get currentStep(){return 0}")
    )
    assert asyncio.run(
        generator.render_check(artifact.validate(text_scene), Settings(environment="test"))
    )["ok"]
    # A single scene whose edited input is applied by a button, as many generated apps do.
    applied = (
        HTML.replace("let index=0;", "let index=1;")
        .replace("get stepCount(){return 4}", "get stepCount(){return 1}")
        .replace("get currentStep(){return index}", "get currentStep(){return 0}")
        .replace(
            "factor.addEventListener('input',render);",
            "document.getElementById('apply').addEventListener('click',render);",
        )
        .replace('value="2">', 'value="2"><button id="apply" type="button">Apply</button>')
    )
    assert asyncio.run(
        generator.render_check(artifact.validate(applied), Settings(environment="test"))
    )["ok"]


def test_generate_has_no_prescribed_examples_and_repairs_invalid_html(monkeypatch):
    provider = Provider(["<p>Incomplete</p>", HTML])

    async def check(*args):
        return QA

    monkeypatch.setattr(generator, "render_check", check)

    async def review(*args):
        pass

    monkeypatch.setattr(generator, "review", review)

    async def run():
        return [
            event
            async for event in generator.generate(
                provider,
                Settings(environment="test"),
                "Explain the CAP theorem with interactive server failures",
                "python",
                "deep",
            )
        ]

    events = asyncio.run(run())
    assert len(provider.calls) == 2 and events[-1]["event"] == "document"
    prompt = json.loads(provider.calls[0][1][0].content)
    assert prompt == dict(
        learner_request="Explain the CAP theorem with interactive server failures",
        default_language="python",
        depth="deep",
    )
    assert "No example or lesson is prescribed" in provider.calls[0][0]
    assert "Repair the complete HTML" in provider.calls[1][1][-1].content
    # A document cut off at the output limit is asked to be shorter, not patched.
    assert "cut off before </html>" in provider.calls[1][1][-1].content


def test_ai_review_uses_the_request_and_document_and_rejects_contradictions():
    provider = Provider(
        ['{"issues":["The illustrated result contradicts the computed current state"]}']
    )
    request = "Explain a concept with editable inputs"
    with pytest.raises(artifact.ArtifactError, match="Content review"):
        asyncio.run(generator.review(provider, HTML, request))
    assert json.loads(provider.calls[0][1][0].content) == dict(
        learner_request=request, document=HTML, rendered_states=[]
    )
    asyncio.run(generator.review(Provider(['{"issues":[]}']), HTML, request))
    with pytest.raises(generator.ProviderError, match="playground_review_unavailable"):
        asyncio.run(
            generator.review(Provider(["unstructured review", "still not JSON"]), HTML, request)
        )


def test_ai_review_tolerates_wrapped_json_and_retries_one_malformed_reply():
    request = "Explain a concept with editable inputs"
    asyncio.run(
        generator.review(
            Provider(['Here is my audit:\n```json\n{"issues": []}\n```']), HTML, request
        )
    )
    provider = Provider(['{"issues": [', '{"issues": []}'])
    asyncio.run(generator.review(provider, HTML, request))
    assert len(provider.calls) == 2


def test_reviewer_outage_does_not_discard_a_visual_that_passed_the_browser_check(monkeypatch):
    provider = Provider([HTML, "not json", "not json either"])

    async def check(*args):
        return QA

    monkeypatch.setattr(generator, "render_check", check)

    async def run():
        return [
            event
            async for event in generator.generate(
                provider, Settings(environment="test"), "Explain a stack", "python", "standard"
            )
        ]

    events = asyncio.run(run())
    assert events[-1]["event"] == "document"
    assert events[-1]["document"]["qa"]["ai_review"] == "unavailable"
    assert len(provider.calls) == 3  # one generation, no repair rounds spent on the reviewer


def test_prompt_lists_the_allowed_elements_and_forbids_hand_computed_traces():
    assert "Use only these elements" in generator.SYSTEM and " kbd " in generator.SYSTEM
    assert "Never hand-write values the JavaScript computes" in generator.SYSTEM
    artifact.validate(HTML.replace("</h1>", " <kbd>Enter</kbd> <sub>2</sub></h1>", 1))


def test_ai_review_findings_flag_the_visual_instead_of_regenerating(monkeypatch):
    provider = Provider([HTML, '{"issues":["The visual label contradicts the computed result"]}'])

    async def check(*args):
        return QA

    monkeypatch.setattr(generator, "render_check", check)
    request = "Explain a concept with editable inputs and a visual"

    async def run():
        return [
            event
            async for event in generator.generate(
                provider, Settings(environment="test"), request, "python", "standard"
            )
        ]

    events = asyncio.run(run())
    assert any(event.get("phase") == "reviewing" for event in events)
    qa = events[-1]["document"]["qa"]
    assert qa["ai_review"] == "flagged" and qa["review_notes"].startswith("The visual label")
    assert events[-1]["document"]["request"] == request
    assert len(provider.calls) == 2  # one generation and one review, no regeneration


def test_checker_rejection_restarts_the_steps_and_names_the_failed_step(monkeypatch):
    provider = Provider([HTML, HTML])
    checks = iter([artifact.ArtifactError("Label every control"), QA])

    async def check(*args):
        result = next(checks)
        if isinstance(result, Exception):
            raise result
        return result

    async def review(*args):
        pass

    monkeypatch.setattr(generator, "render_check", check)
    monkeypatch.setattr(generator, "review", review)

    async def run():
        return [
            event
            async for event in generator.generate(
                provider, Settings(environment="test"), "Explain a queue", "python", "standard"
            )
        ]

    progress = [
        (e["phase"], e["attempt"], e.get("failed"))
        for e in asyncio.run(run())[:-1]
        if e["phase"] != "generating" or not e["characters"]  # skip character-count updates
    ]
    assert progress == [
        ("generating", 1, None),
        ("checking", 1, None),
        ("generating", 2, "checking"),
        ("checking", 2, "checking"),
        ("reviewing", 2, "checking"),
    ]
    assert "Label every control" in provider.calls[1][1][-1].content


def work(client):  # noqa: F811
    """Run queued generations the way the worker does."""

    async def drain():
        while job_id := jobs.claim(client.app.state.engine):
            await jobs.run(client.app.state.engine, client.app.state.settings, job_id)

    def no_catalog():
        raise AssertionError("the worker must not load the ~770 MB catalog (512 MB limit)")

    # Production OOM-killed the worker at the final save while it loaded the catalog.
    with unittest.mock.patch("socrat.learn.routes.default_catalog", no_catalog):
        asyncio.run(drain())


def generate(client, headers, payload):  # noqa: F811
    queued = client.post("/api/v1/playground/generate", headers=headers, json=payload)
    assert queued.status_code == 202, queued.text
    work(client)
    return client.get("/api/v1/playground/jobs/" + queued.json()["id"]).json()


def test_owned_persistent_artifact_idempotency_frame_and_report(client, configured):  # noqa: F811
    headers, provider = configured
    before = client.get("/api/v1/me/export").json()["evidence"]
    payload = dict(
        prompt="Explain electromagnetic induction with a moving magnet",
        request_id=str(uuid.uuid4()),
    )
    queued = client.post("/api/v1/playground/generate", headers=headers, json=payload).json()
    assert queued["status"] == "queued" and len(provider.calls) == 0
    # A reload finds the generation still pending and resumes it.
    assert client.get("/api/v1/playground/artifacts").json()["pending"]["id"] == queued["id"]
    work(client)
    job = client.get("/api/v1/playground/jobs/" + queued["id"]).json()
    assert job["status"] == "ready" and job["progress"]["phase"] == "reviewing"
    data = job["artifact"]
    # No mode was sent: the router picked the medium from the prompt, then one generation ran.
    assert "html" not in data and data["request"] == payload["prompt"] and len(provider.calls) == 2
    assert provider.calls[0][0] == generator.ROUTER and job["mode"] == data["mode"] == "sketch"
    replay = client.post("/api/v1/playground/generate", headers=headers, json=payload).json()
    assert replay["artifact"]["id"] == data["id"]
    assert len(provider.calls) == 2
    assert (
        client.post(
            "/api/v1/playground/generate",
            headers=headers,
            json={**payload, "prompt": "Different request"},
        ).status_code
        == 409
    )
    history = client.get("/api/v1/playground/artifacts").json()
    assert history["items"][0]["id"] == data["id"] and history["pending"] is None
    assert client.get("/api/v1/playground/artifacts/" + data["id"]).status_code == 200
    frame_url = urlparse(data["frame_url"])
    frame = client.get(frame_url.path + "?" + frame_url.query)
    assert frame.status_code == 200 and frame.headers["referrer-policy"] == "no-referrer"
    assert "sandbox allow-scripts" in frame.headers["content-security-policy"]
    assert client.get(frame_url.path + "?token=bad").status_code == 403
    assert client.get("/api/v1/me/export").json()["evidence"] == before
    report_url = "/api/v1/playground/artifacts/" + data["id"] + "/report"
    assert (
        client.post(report_url, json={"reason": "The explanation is incorrect"}).status_code == 403
    )
    assert (
        client.post(
            report_url, headers=headers, json={"reason": "The explanation is incorrect"}
        ).status_code
        == 200
    )
    assert client.get(frame_url.path + "?" + frame_url.query).status_code == 410
    assert client.get("/api/v1/playground/artifacts").json()["items"] == []


def test_one_pending_job_cancel_and_interrupted_jobs(client, configured):  # noqa: F811
    headers, provider = configured
    first = client.post(
        "/api/v1/playground/generate", headers=headers, json={"prompt": "Explain heaps visually"}
    ).json()
    second = client.post(
        "/api/v1/playground/generate", headers=headers, json={"prompt": "Explain tries visually"}
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "playground_request_in_progress"
    cancel_url = "/api/v1/playground/jobs/" + first["id"] + "/cancel"
    assert client.post(cancel_url).status_code == 403  # CSRF
    assert client.post(cancel_url, headers=headers).json() == {"status": "cancelled"}
    work(client)
    assert len(provider.calls) == 0  # a cancelled job never reaches the model
    # A worker that died mid-generation (a deploy) stops beating: retried once, then failed.
    third = client.post(
        "/api/v1/playground/generate", headers=headers, json={"prompt": "Explain graphs visually"}
    ).json()
    engine = client.app.state.engine
    for _ in range(jobs.MAX_TRIES):
        assert jobs.claim(engine) == third["id"]
        with Session(engine) as db, db.begin():
            db.get(PlaygroundJob, third["id"]).heartbeat_at = 0
    assert jobs.claim(engine) is None
    job = client.get("/api/v1/playground/jobs/" + third["id"]).json()
    assert job["status"] == "failed" and job["error"] == "playground_generation_interrupted"
    other = login(client, subject="other")
    onboard(client, other)
    assert client.get("/api/v1/playground/jobs/" + third["id"]).status_code == 404


def test_ai_guardrails_stop_before_queueing_and_fail_jobs_in_playground_terms(
    client,  # noqa: F811
    configured,
    monkeypatch,
):
    headers, _ = configured
    settings = client.app.state.settings
    settings.ai_enabled = False
    paused = client.post(
        "/api/v1/playground/generate", headers=headers, json={"prompt": "Explain sets visually"}
    )
    assert paused.status_code == 503 and paused.json()["error"]["code"] == "playground_ai_disabled"
    settings.ai_enabled = True

    async def spent(*args, **kwargs):
        raise generator.ProviderError("ai_budget_reached")
        yield  # an async generator, like the real one

    monkeypatch.setattr(generator, "generate", spent)
    job = generate(client, headers, {"prompt": "Explain sets visually"})
    assert job["status"] == "failed" and job["error"] == "playground_ai_budget_reached"


def test_job_progress_quota_scope_and_csrf(client, configured):  # noqa: F811
    headers, _ = configured
    payload = dict(prompt="Explain recursion visually")
    assert client.post("/api/v1/playground/generate", json=payload).status_code == 403
    assert (
        client.post(
            "/api/v1/playground/generate",
            headers=headers,
            json={**payload, "concept": "dsa:complexity"},
        ).status_code
        == 404
    )
    client.app.state.settings.ai_daily_messages = 1
    job = generate(client, headers, payload)
    assert job["status"] == "ready" and job["progress"]["attempt"] == 1
    assert "<script" not in json.dumps(job)
    assert (
        client.post("/api/v1/playground/generate", headers=headers, json=payload).status_code == 429
    )
    with Session(client.app.state.engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(AssistantMessage)
                .where(AssistantMessage.role == "user")
            )
            == 1
        )


def test_visual_quota_and_model_override_do_not_change_tutor_settings(
    client,  # noqa: F811
    configured,
    monkeypatch,
):
    headers, provider = configured
    client.app.state.settings.openai_model = "original-tutor-model"
    client.app.state.settings.explainer_model = "visual-coder-model"
    client.app.state.settings.explainer_chat_template_kwargs = {"enable_thinking": False}
    client.app.state.settings.explainer_daily_messages = 1
    received = []

    def factory(settings, **kwargs):
        received.append((settings.openai_model, kwargs))
        return provider

    monkeypatch.setattr(jobs, "make_provider", factory)
    payload = {"prompt": "Explain a cellular process visually"}
    first = generate(client, headers, payload)
    assert first["artifact"]["model"] == "visual-coder-model"
    assert received == [
        ("visual-coder-model", {"chat_template_kwargs": {"enable_thinking": False}})
    ]
    assert client.app.state.settings.openai_model == "original-tutor-model"
    second = client.post("/api/v1/playground/generate", headers=headers, json=payload)
    assert second.status_code == 429 and second.json()["error"]["code"] == "playground_daily_limit"


def test_other_learner_cannot_read_or_report_artifact(client, configured):  # noqa: F811
    headers, _ = configured
    result = generate(client, headers, {"prompt": "Explain vectors"})["artifact"]
    second = login(client, subject="other")
    onboard(client, second)
    url = "/api/v1/playground/artifacts/" + result["id"]
    assert client.get(url).status_code == 404
    assert (
        client.post(
            url + "/report", headers=second, json={"reason": "Incorrect example"}
        ).status_code
        == 404
    )
    assert client.get("/api/v1/playground/artifacts").json()["items"] == []


def test_production_requires_independent_sandbox_and_checker():
    for sandbox in ["", "https://app.example.com", "https://visuals.example.com"]:
        settings = Settings.model_construct(
            environment="production",
            public_origin="https://app.example.com",
            ai_provider="openai",
            explainer_enabled=True,
            explainer_sandbox_origin=sandbox,
        )
        with pytest.raises(HTTPException) as rejected:
            routes.available(settings)
        assert rejected.value.status_code == 503


def test_prompt_skeleton_passes_the_validator_and_asks_for_a_hand_drawn_visual():
    artifact.validate(generator.SKELETON)
    assert "Sketch.mount" in generator.SKELETON and "var(--hand)" in generator.SKELETON
    assert "Show, do not tell" in generator.SYSTEM
    assert "never write <svg> markup" in generator.SYSTEM.lower().replace("  ", " ") or (
        "Never write <svg> markup" in generator.SYSTEM
    )
    compiled, _ = artifact.compile_document(generator.SKELETON, "c", "http://host.socrat.invalid")
    assert "--paper-lines" in compiled and "--pen" in compiled
    # The host's kit does the layout and arrives before the generated script that calls it.
    assert "feTurbulence" in artifact.KIT
    assert compiled.index("const Sketch") < compiled.index("Sketch.mount")


def test_browser_check_runs_the_skeleton_and_rejects_overlapping_text():
    settings = Settings(environment="test")
    skeleton = generator.SKELETON.replace(
        "Two to four plain sentences: the one idea, why it works, one thing to watch out for.",
        "Binary search halves the range each step. It works because the array is sorted, so one "
        "comparison rules out half of what is left. Watch out for arrays that are not sorted.",
    )
    assert asyncio.run(generator.render_check(artifact.validate(skeleton), settings))["ok"]
    # Hand-placed text that lands on other text is a layout failure, not a visual.
    crowded = HTML.replace(
        '<text id="value" x="30" y="180">0</text>',
        '<text id="value" x="30" y="180">0</text><text x="32" y="182">overlapping</text>',
    )
    with pytest.raises(artifact.ArtifactError, match="Layout problem"):
        asyncio.run(generator.render_check(artifact.validate(crowded), settings))
    # An id the scene does not contain is a script error the generator can repair.
    unknown = skeleton.replace("focus:s.found?['a.'+s.mid]:[]", "focus:['a.99']")
    with pytest.raises(artifact.ArtifactError, match="unknown id"):
        asyncio.run(generator.render_check(artifact.validate(unknown), settings))


def film_example():
    return json.loads(generator.FILM_EXAMPLE)


def test_example_film_passes_the_film_check_and_builds_a_valid_page():
    film = films.check(films.parse(generator.FILM_EXAMPLE))
    page = films.page(film)
    document = artifact.validate(page)
    assert document.title == film["title"] and "Chapters" in document.transcript
    assert "Clicky3D.film" in page and "window.__explainer = player" in page
    # The prompt embeds the example and documents the film's moving parts.
    for phrase in ('"chapters"', "Motions act in the part's own frame", "Flows are streams"):
        assert phrase in generator.SYSTEM_FILM
    compiled, _ = artifact.compile_document(page, "c", "http://host.socrat.invalid", mode="3d")
    # The stage arrives in the head, before the host page's script that plays the film.
    assert compiled.index("const Clicky3D") < compiled.index("Clicky3D.film('#board'")


def test_film_page_escapes_text_that_could_close_the_script():
    film = film_example()
    film["chapters"][0]["say"] = "Air </script><script>alert(1)</script> enters at the fan."
    page = films.page(films.check(film))
    assert "</script><script>alert" not in page
    artifact.validate(page)


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda f: f["parts"][1].update(kind="teapot"), "kind 'teapot' is unknown"),
        (lambda f: f["parts"][1].update(parent="missing"), "parent 'missing' is not a part id"),
        (
            lambda f: f["labels"][0].update(part="nope"),
            "labels\\[0\\].part 'nope' is not a part id",
        ),
        (lambda f: f["chapters"][2].update(run={"warp": 1}), "not a motion or flow id"),
        (
            lambda f: f["chapters"][3].update(say=f["chapters"][2]["say"]),
            "repeats an earlier chapter",
        ),
        (
            lambda f: f["chapters"][3].update(camera={"target": "nowhere"}),
            "camera.target 'nowhere'",
        ),
        (lambda f: f.update(chapters=f["chapters"][:1]), "chapters must list 2-10"),
        (lambda f: f["labels"][0].pop("detail"), r"labels\[0\]\.detail"),
        (lambda f: f["parts"][1].update(on={"part": "nope"}), "on.part must name another part"),
        (lambda f: f["parts"][2].update(at=[0, "x", 0]), "parts\\[2\\].at\\[1\\] must be a number"),
    ],
)
def test_film_check_names_the_field_to_repair(change, message):
    film = film_example()
    change(film)
    with pytest.raises(artifact.ArtifactError, match=message):
        films.check(film)


def test_film_show_names_a_part_or_nothing_without_failing():
    film = film_example()
    film["chapters"][2]["show"] = ["fan", "combustor", "ghost", "compressor"]
    checked = films.check(film)
    # Part ids become their callouts; an id that matches nothing shows no callout.
    assert checked["chapters"][2]["show"] == ["fan", "combustor", "compressor"]


def test_film_parse_accepts_a_fence_and_rejects_non_json():
    assert films.parse("```json\n" + generator.FILM_EXAMPLE + "\n```")["title"]
    with pytest.raises(artifact.ArtifactError, match="not valid JSON"):
        films.parse('{"title": "x",}')
    with pytest.raises(artifact.ArtifactError, match="must not contain NaN"):
        films.parse('{"title": NaN}')


def test_browser_check_plays_the_example_film():
    settings = Settings(environment="test")
    page = films.page(films.check(film_example()))
    result = asyncio.run(generator.render_check(artifact.validate(page), settings, "3d"))
    assert result["ok"] and result["step_count"] == len(film_example()["chapters"])
    assert result["observations"][0]["description"].startswith("Chapter 1 of")


def test_generate_selects_the_3d_prompt_and_data_by_mode(monkeypatch):
    provider = Provider([generator.FILM_EXAMPLE, HTML])

    async def check(document, settings, mode="sketch"):
        return dict(QA, mode=mode)

    monkeypatch.setattr(generator, "render_check", check)

    async def review(*args):
        pass

    monkeypatch.setattr(generator, "review", review)

    async def run(mode):
        return [
            event
            async for event in generator.generate(
                provider,
                Settings(environment="test"),
                "Explain how a jet engine makes thrust",
                "python",
                "standard",
                mode,
            )
        ]

    events = asyncio.run(run("3d"))
    assert provider.calls[0][0] == generator.SYSTEM_FILM
    payload = events[-1]["document"]
    assert payload["mode"] == "3d" and payload["prompt_version"] == "visual-3d-film-v1"
    # The model wrote data; the host built the page that plays it.
    assert payload["film"]["chapters"] and "Clicky3D.film" in payload["html"]

    events = asyncio.run(run("sketch"))
    assert "Sketch.mount" in provider.calls[1][0] and "Clicky3D" not in provider.calls[1][0]
    payload = events[-1]["document"]
    assert payload["mode"] == "sketch" and payload["prompt_version"] == "visual-sketch-v4"
    assert "film" not in payload


def test_a_broken_film_is_repaired_with_the_exact_problem(monkeypatch):
    broken = generator.FILM_EXAMPLE.replace('"kind": "rotor"', '"kind": "propeller"', 1)
    provider = Provider([broken, generator.FILM_EXAMPLE])

    async def check(document, settings, mode="sketch"):
        return dict(QA, mode=mode)

    monkeypatch.setattr(generator, "render_check", check)

    async def review(*args):
        pass

    monkeypatch.setattr(generator, "review", review)

    async def run():
        return [
            event
            async for event in generator.generate(
                provider,
                Settings(environment="test"),
                "How does a jet engine work?",
                "python",
                "standard",
                "3d",
            )
        ]

    events = asyncio.run(run())
    repair = provider.calls[1][1][-1].content
    assert (
        repair.startswith("Repair the complete film JSON.") and "'propeller' is unknown" in repair
    )
    assert events[-1]["document"]["film"]["title"]


@pytest.mark.parametrize(
    "routed, expected", [("3d", "3d"), (" 3D. ", "3d"), ("sketch", "sketch"), ("unsure", "sketch")]
)
def test_auto_mode_lets_the_prompt_pick_the_medium(monkeypatch, routed, expected):
    provider = Provider([routed, generator.FILM_EXAMPLE if expected == "3d" else HTML])

    async def check(document, settings, mode="sketch"):
        return dict(QA, mode=mode)

    monkeypatch.setattr(generator, "render_check", check)

    async def review(*args):
        pass

    monkeypatch.setattr(generator, "review", review)

    async def run():
        return [
            event
            async for event in generator.generate(
                provider,
                Settings(environment="test"),
                "How does a jet engine work?",
                "python",
                "standard",
                "auto",
            )
        ]

    events = asyncio.run(run())
    assert provider.calls[0][0] == generator.ROUTER
    assert events[0] == dict(event="progress", phase="generating", attempt=1, mode=expected)
    assert (provider.calls[1][0] == generator.SYSTEM_FILM) == (expected == "3d")
    assert events[-1]["document"]["mode"] == expected


def test_playground_mode_end_to_end(client, configured):  # noqa: F811
    headers, provider = configured
    payload = dict(
        prompt="Explain a camera aperture with a cutaway lens",
        request_id=str(uuid.uuid4()),
        mode="3d",
    )
    # 3D answers are films (JSON); the host turns them into the page.
    provider.responses = iter([generator.FILM_EXAMPLE] + [HTML] * 20)
    job = generate(client, headers, payload)
    assert job["status"] == "ready" and job["artifact"]["mode"] == "3d"
    # The same identity replays; only the mode flipping conflicts.
    assert (
        client.post("/api/v1/playground/generate", headers=headers, json=payload).status_code == 202
    )
    assert (
        client.post(
            "/api/v1/playground/generate", headers=headers, json={**payload, "mode": "sketch"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/playground/generate",
            headers=headers,
            json={**payload, "mode": "2d", "request_id": str(uuid.uuid4())},
        ).status_code
        == 422
    )
    # A sketch frame never injects the 3D kit.
    sketch = generate(
        client,
        headers,
        {**payload, "mode": "sketch", "request_id": str(uuid.uuid4())},
    )
    assert sketch["artifact"]["mode"] == "sketch"
    frame_url = urlparse(sketch["artifact"]["frame_url"])
    frame = client.get(frame_url.path + "?" + frame_url.query)
    assert frame.status_code == 200 and "Clicky3D" not in frame.text
    # The 3D artifact's frame carries the interactive stage.
    frame_url = urlparse(job["artifact"]["frame_url"])
    frame = client.get(frame_url.path + "?" + frame_url.query)
    assert frame.status_code == 200 and "const Clicky3D" in frame.text
