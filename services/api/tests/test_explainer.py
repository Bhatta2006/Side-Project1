import asyncio
import json
import time
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
from socrat.explainer import artifact, generator, routes
from socrat.models import AssistantMessage

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
    monkeypatch.setattr(routes, "make_provider", lambda _, **kwargs: provider)

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
    # check-artifact.test.mjs proves the checker skips a slow browser close; this only keeps a passing
    # visual well inside the 18 s budget, with room for a cold, loaded CI runner (6.5 s seen).
    assert time.monotonic() - started < 12
    assert checked["ok"] and checked["step_count"] == 4
    broken = HTML.replace("get currentStep(){return index}", "get currentStep(){return 0}")
    with pytest.raises(artifact.ArtifactError, match="currentStep must report"):
        asyncio.run(generator.render_check(artifact.validate(broken), Settings(environment="test")))
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


def test_ai_review_findings_repair_the_document_without_changing_the_request(monkeypatch):
    provider = Provider(
        [
            HTML,
            '{"issues":["The visual label contradicts the computed result"]}',
            HTML,
            '{"issues":[]}',
        ]
    )

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
    assert events[-1]["document"]["qa"]["ai_review"] == "passed"
    assert events[-1]["document"]["request"] == request
    repair = provider.calls[2][1]
    assert json.loads(repair[0].content)["learner_request"] == request
    assert "visual label contradicts" in repair[-1].content


def test_owned_persistent_artifact_idempotency_frame_and_report(client, configured):  # noqa: F811
    headers, provider = configured
    before = client.get("/api/v1/me/export").json()["evidence"]
    payload = dict(
        prompt="Explain electromagnetic induction with a moving magnet",
        request_id=str(uuid.uuid4()),
    )
    result = client.post("/api/v1/playground/generate", headers=headers, json=payload)
    assert result.status_code == 200, result.text
    data = result.json()
    assert "html" not in data and data["request"] == payload["prompt"] and len(provider.calls) == 1
    assert (
        client.post("/api/v1/playground/generate", headers=headers, json=payload).json()["id"]
        == data["id"]
    )
    assert len(provider.calls) == 1
    assert (
        client.post(
            "/api/v1/playground/generate",
            headers=headers,
            json={**payload, "prompt": "Different request"},
        ).status_code
        == 409
    )
    history = client.get("/api/v1/playground/artifacts").json()["items"]
    assert history[0]["id"] == data["id"]
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


def test_stream_progress_quota_scope_and_csrf(client, configured):  # noqa: F811
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
    streamed = client.post(
        "/api/v1/playground/generate",
        headers={**headers, "Accept": "text/event-stream"},
        json=payload,
    )
    assert (
        streamed.status_code == 200
        and "event: progress" in streamed.text
        and "event: ready" in streamed.text
    )
    assert "<script" not in streamed.text
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

    monkeypatch.setattr(routes, "make_provider", factory)
    payload = {"prompt": "Explain a cellular process visually"}
    first = client.post("/api/v1/playground/generate", headers=headers, json=payload)
    assert first.status_code == 200 and first.json()["model"] == "visual-coder-model"
    assert received == [
        ("visual-coder-model", {"chat_template_kwargs": {"enable_thinking": False}})
    ]
    assert client.app.state.settings.openai_model == "original-tutor-model"
    second = client.post("/api/v1/playground/generate", headers=headers, json=payload)
    assert second.status_code == 429 and second.json()["error"]["code"] == "playground_daily_limit"


def test_other_learner_cannot_read_or_report_artifact(client, configured):  # noqa: F811
    headers, _ = configured
    result = client.post(
        "/api/v1/playground/generate", headers=headers, json={"prompt": "Explain vectors"}
    ).json()
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
