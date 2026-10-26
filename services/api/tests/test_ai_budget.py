"""LLM cost guardrails: kill switch, burst limit, per-learner and global budgets, metering."""

import asyncio
from types import SimpleNamespace as NS

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.assistant import budget
from socrat.assistant.gateway import Event, ProviderError, Turn, usage_event
from socrat.config import Settings
from socrat.models import AIUsage, User, now


@pytest.fixture
def engine(tmp_path):
    from alembic import command
    from alembic.config import Config

    from socrat.database import make_engine

    url = f"sqlite:///{tmp_path / 'budget.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    bind = make_engine(url)
    with Session(bind) as db, db.begin():
        db.add(User(id="u1", issuer="dev", subject="u1", display_name="Ada"))
        db.add(User(id="u2", issuer="dev", subject="u2", display_name="Bob"))
    yield bind
    bind.dispose()


def settings(**extra) -> Settings:
    base = dict(
        _env_file=None,
        environment="test",
        ai_price_input_per_mtok=1.0,
        ai_price_output_per_mtok=1.0,
        ai_user_daily_budget_usd=0.01,  # 10,000 tokens
        ai_daily_budget_usd=0.015,
        ai_monthly_budget_usd=100.0,
    )
    return Settings(**(base | extra))


class Scripted:
    """A provider that answers "ok" and reports a fixed token count."""

    name = "anthropic"

    def __init__(self, tokens=4000):
        self.tokens = tokens
        self.calls = 0

    async def converse(self, system, turns, max_tokens, *args, **kwargs):
        self.calls += 1
        yield Event("text", "ok")
        yield usage_event(self.tokens, 0)


def ask(provider) -> str:
    async def run():
        return "".join(
            [
                e.text
                async for e in provider.converse("s", [Turn("user", "hi")], 50)
                if e.kind == "text"
            ]
        )

    return asyncio.run(run())


def test_usage_is_recorded_and_hidden_from_consumers(engine):
    config = settings()
    inner = Scripted(tokens=1234)
    metered = budget.Metered(inner, engine, config, user_id="u1", feature="tutor")
    assert ask(metered) == "ok"
    with Session(engine) as db:
        row = db.scalars(select(AIUsage)).one()
        assert (row.user_id, row.feature, row.input_tokens) == ("u1", "tutor", 1234)
        assert row.cost_usd == pytest.approx(0.001234)


def test_learner_daily_budget_then_global_daily_budget(engine):
    config = settings()
    inner = Scripted(tokens=4000)
    ada = budget.Metered(inner, engine, config, user_id="u1", feature="tutor")
    ask(ada)
    ask(ada)
    ask(ada)  # 12,000 tokens: Ada is now over her 10,000
    with pytest.raises(ProviderError, match="ai_budget_reached"):
        ask(ada)
    assert inner.calls == 3  # the refused call never reached the provider

    bob = budget.Metered(inner, engine, config, user_id="u2", feature="tutor")
    ask(bob)  # 16,000 tokens today: over the global 15,000
    with pytest.raises(ProviderError, match="ai_budget_reached"):
        ask(bob)


def test_kill_switch_and_burst_limit(engine):
    off = budget.Metered(
        Scripted(), engine, settings(ai_enabled=False), user_id="u1", feature="tutor"
    )
    with pytest.raises(ProviderError, match="ai_disabled"):
        ask(off)

    burst = budget.Metered(
        Scripted(tokens=1),
        engine,
        settings(ai_user_calls_per_minute=2, ai_user_daily_budget_usd=0),
        user_id="u1",
        feature="tutor",
    )
    ask(burst)
    ask(burst)
    with pytest.raises(ProviderError, match="ai_rate_limited"):
        ask(burst)


def test_zero_means_no_cap_and_offline_is_never_metered(engine):
    config = settings(ai_user_daily_budget_usd=0, ai_daily_budget_usd=0, ai_monthly_budget_usd=0)
    big = budget.Metered(
        Scripted(tokens=10_000_000), engine, config, user_id="u1", feature="lesson"
    )
    ask(big)
    ask(big)
    offline = NS(name="offline", converse=Scripted().converse)
    budget.Metered(offline, engine, settings(ai_enabled=False), user_id="u1", feature="tutor")
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(AIUsage)) == 2


def test_playground_and_tutor_do_not_use_up_each_others_allowance(engine):
    config = settings(ai_daily_budget_usd=100.0, ai_user_calls_per_minute=2)
    tutor = budget.Metered(Scripted(tokens=10_000), engine, config, user_id="u1", feature="tutor")
    ask(tutor)
    with pytest.raises(ProviderError, match="ai_budget_reached"):
        ask(tutor)
    # The playground is limited by its plan's generation count, not the tutor's spend or burst caps.
    visuals = budget.Metered(
        Scripted(tokens=50_000), engine, config, user_id="u1", feature="playground"
    )
    for _ in range(3):
        ask(visuals)
    # And playground spend never counts against the tutor.
    other = budget.Metered(
        Scripted(tokens=50_000), engine, config, user_id="u2", feature="playground"
    )
    ask(other)
    assert ask(budget.Metered(Scripted(), engine, config, user_id="u2", feature="tutor")) == "ok"
    # The site-wide budget still covers everything.
    capped = settings(ai_daily_budget_usd=0.1)
    with pytest.raises(ProviderError, match="ai_budget_reached"):
        ask(budget.Metered(Scripted(), engine, capped, user_id="u2", feature="playground"))


def test_summary_for_the_owner_dashboard(engine):
    config = settings(ai_user_daily_budget_usd=0, ai_daily_budget_usd=0)
    ask(budget.Metered(Scripted(tokens=2000), engine, config, user_id="u1", feature="tutor"))
    ask(budget.Metered(Scripted(tokens=1000), engine, config, user_id="u2", feature="playground"))
    with Session(engine) as db:
        report = budget.summary(db, config, now())
    assert report["today_usd"] == pytest.approx(0.003)
    assert report["learners_this_month"] == 2
    assert report["per_learner_usd"] == pytest.approx(0.0015)
    assert set(report["by_feature"]) == {"tutor", "playground"}


def test_tutor_falls_back_to_curated_hints_when_ai_is_off(tmp_path):
    from alembic import command
    from alembic.config import Config
    from fastapi.testclient import TestClient
    from test_learner_api import ORIGIN, login, onboard

    from socrat.main import create_app

    url = f"sqlite:///{tmp_path / 'tutor.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    app = create_app(
        Settings(
            database_url=url,
            environment="test",
            dev_login_enabled=True,
            ai_provider="anthropic",
            anthropic_api_key="k",
            ai_enabled=False,
        )
    )
    with TestClient(app, base_url=ORIGIN) as client:
        headers = login(client)
        onboard(client, headers)
        reply = client.post(
            "/api/v1/assistant/messages",
            json={"scope": "problem:greeting", "message": "How do I start?"},
            headers=headers,
        )
        assert reply.status_code == 200
        assert '"provider": "curated"' in reply.text and "ai_disabled" in reply.text
    app.state.engine.dispose()
