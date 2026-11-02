"""Domain adapters and the renderer registry: typed, validated, honest about limits."""

import pytest

from socrat.coursegen import intent as intents
from socrat.engine import domains, renderers


def test_every_adapter_names_only_registered_renderers_and_capabilities():
    import socrat.harness.library  # noqa: F401  (registers math.check, physics.simulate)

    assert domains.check_adapter_renderers() == []


@pytest.mark.parametrize(
    ("text", "adapter"),
    [
        ("teach me calculus and quantum mechanics", "math-science"),
        ("competitive programming in C++", "software"),
        ("electrical circuits and signals", "electronics"),
        ("Carnatic music and ragas", "music"),
        ("become a professional animator", "animation-movement"),
        ("medieval European history", "general"),
    ],
)
def test_classification(text, adapter):
    assert domains.classify(text).id == adapter


def test_unknown_subject_is_general_not_forced_into_a_template():
    assert domains.classify("basket weaving").id == "general"
    assert domains.classify("python music", "").id == "general"  # a tie is not guessed


def test_adapter_makes_the_intent_more_cautious_never_less():
    base = intents.from_rules("teach me the piano")
    safe = base.model_copy(
        update=dict(
            needs_physical_practice=False, needs_external_evaluator=False, verifiable="fully"
        )
    )
    got = intents.apply_adapter(safe, "teach me the piano")
    assert got.adapter == "music" and got.verifiable == "limited"
    assert got.needs_physical_practice and got.needs_external_evaluator
    assert any("hearing" in n for n in got.safety_notes)
    brief = intents.to_brief(got, "piano-aaaaaa", 3.0)
    assert "Music and sound" in brief.notes and "limited" in brief.notes


def test_spec_validation_blocks_unknown_renderer_bad_params_and_missing_fallback():
    good = dict(
        renderer="function-plot",
        params=dict(expressions=["sin(x)"], x_range=[-6.28, 6.28]),
        purpose="See how amplitude changes the curve",
        fallback_text="A table of sin(x) at multiples of pi over 2.",
        alt_text="A sine wave crossing zero at multiples of pi.",
    )
    assert renderers.validate_spec(good) == []
    unknown = renderers.validate_spec({**good, "renderer": "evil-script"})
    assert unknown[0].startswith("unknown renderer")
    empty = renderers.validate_spec({**good, "params": {"expressions": []}})
    assert any("params" in p for p in empty)
    extra = renderers.validate_spec({**good, "params": {"code": "alert(1)"}})
    assert any("params" in p for p in extra)
    assert renderers.validate_spec({k: v for k, v in good.items() if k != "fallback_text"})
    assert renderers.validate_spec({**good, "version": "2.0"})


def test_every_renderer_declares_its_fallback_and_accessible_alternative():
    for manifest in renderers.all_manifests().values():
        info = renderers.describe(manifest)
        assert info["accessible_alternative"] and info["on_error"]
        assert info["input_schema"]["type"] == "object"


def test_selection_is_deterministic_and_falls_back_to_text():
    assert renderers.select("math-science", "visualise").id == "function-plot"
    assert renderers.select("software", "practise").id == "code-studio"
    assert renderers.select("music", "time").id == "timeline"
    assert renderers.select("music", "visualise").id != "concept-playground"  # sandboxed: opt-in
    assert renderers.select("general", "teleport").id == "markdown"


def test_a_new_renderer_registers_without_touching_the_compiler():
    class Meter(renderers.Params):
        value: float

    m = renderers.register(
        renderers.Manifest(
            id="test-meter",
            version="1.0",
            description="x",
            domains=("general",),
            params=Meter,
            events=(),
            runtime=(),
            evidence="exposure",
            accessible_alternative="a number",
            on_error="show the number",
            supports=("measure",),
        )
    )
    try:
        assert renderers.select("general", "measure").id == "test-meter"
        with pytest.raises(ValueError):
            renderers.register(m)
    finally:
        renderers._REGISTRY.pop("test-meter")


def test_catalogue_endpoints(tmp_path):
    from fastapi.testclient import TestClient

    from socrat.config import Settings
    from socrat.main import create_app

    url = f"sqlite:///{tmp_path / 'e.db'}"
    from alembic import command
    from alembic.config import Config

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    app = create_app(Settings(environment="test", database_url=url))
    with TestClient(app) as c:
        found = {d["id"] for d in c.get("/api/v1/engine/domains").json()["items"]}
        assert {"music", "software"} <= found
        assert any(
            r["id"] == "code-studio" for r in c.get("/api/v1/engine/renderers").json()["items"]
        )


def test_function_plot_accepts_only_math_characters():
    spec = dict(
        renderer="function-plot",
        params=dict(expressions=["alert(1); document.cookie"]),
        purpose="Show a curve",
        fallback_text="A table of values for the curve.",
        alt_text="A curve on axes.",
    )
    assert any("math characters" in p for p in renderers.validate_spec(spec))
    ok = {**spec, "params": dict(expressions=["a*sin(b*x)+c"])}
    assert renderers.validate_spec(ok) == []
