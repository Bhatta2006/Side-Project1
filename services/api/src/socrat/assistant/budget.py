"""LLM cost guardrails: a kill switch, per-learner and global budgets, and usage metering.

Every model call goes through ``Metered``. Before a call it checks, in order: the kill switch,
a per-minute burst limit, the learner's daily budget, and the global daily and monthly
budgets. A refused call raises ``ProviderError("ai_budget_reached")`` (or ``ai_disabled``),
which the tutor already answers with curated hints. After each model round the provider's
token counts are stored in ``ai_usage`` with an estimated cost.
"""

import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from socrat.assistant.gateway import Event, Provider, ProviderError, Turn
from socrat.config import Settings
from socrat.models import AIUsage, now

log = logging.getLogger("socrat.ai_budget")
# A warning is logged (and reaches error reporting) once spend passes this share of a budget.
WARN_SHARE = 0.8


def day_of(stamp: int) -> str:
    return datetime.fromtimestamp(stamp, UTC).strftime("%Y-%m-%d")


def cost(settings: Settings, input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens * settings.ai_price_input_per_mtok
        + output_tokens * settings.ai_price_output_per_mtok
    ) / 1_000_000


def spent(
    db: Session, *, since_day: str, user_id: str | None = None, exclude: str | None = None
) -> float:
    query = select(func.coalesce(func.sum(AIUsage.cost_usd), 0.0)).where(AIUsage.day >= since_day)
    if user_id is not None:
        query = query.where(AIUsage.user_id == user_id)
    if exclude is not None:
        query = query.where(AIUsage.feature != exclude)
    return float(db.scalar(query) or 0.0)


def check(db: Session, settings: Settings, user_id: str | None, stamp: int, feature: str = ""):
    """Raise ProviderError when the next model call is not allowed."""
    if not settings.ai_enabled:
        raise ProviderError("ai_disabled")
    today = day_of(stamp)
    # The playground's per-learner limit is its plan's generation count (entitlements.PLANS), with
    # one generation at a time; the per-learner rate and spend limits are the tutor's, so neither
    # feature uses up the other's allowance.
    if user_id is not None and feature != "playground":
        recent = db.scalar(
            select(func.count())
            .select_from(AIUsage)
            .where(
                AIUsage.user_id == user_id,
                AIUsage.feature != "playground",
                AIUsage.created_at > stamp - 60,
            )
        )
        if (recent or 0) >= settings.ai_user_calls_per_minute:
            raise ProviderError("ai_rate_limited")
        if settings.ai_user_daily_budget_usd and (
            spent(db, since_day=today, user_id=user_id, exclude="playground")
            >= settings.ai_user_daily_budget_usd
        ):
            raise ProviderError("ai_budget_reached")
    if settings.ai_daily_budget_usd and spent(db, since_day=today) >= settings.ai_daily_budget_usd:
        log.error("ai_daily_budget_reached", extra={"budget_usd": settings.ai_daily_budget_usd})
        raise ProviderError("ai_budget_reached")
    if settings.ai_monthly_budget_usd and (
        spent(db, since_day=today[:8] + "01") >= settings.ai_monthly_budget_usd
    ):
        log.error("ai_monthly_budget_reached", extra={"budget_usd": settings.ai_monthly_budget_usd})
        raise ProviderError("ai_budget_reached")


def record(
    db: Session,
    settings: Settings,
    *,
    user_id: str | None,
    feature: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    stamp: int,
) -> float:
    amount = cost(settings, input_tokens, output_tokens)
    db.add(
        AIUsage(
            user_id=user_id,
            feature=feature,
            provider=provider,
            model=model[:120],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=amount,
            day=day_of(stamp),
            created_at=stamp,
        )
    )
    if settings.ai_daily_budget_usd:
        before = spent(db, since_day=day_of(stamp))
        limit = settings.ai_daily_budget_usd * WARN_SHARE
        if before < limit <= before + amount:
            log.warning(
                "ai_daily_budget_80_percent",
                extra={"budget_usd": settings.ai_daily_budget_usd, "spent_usd": before + amount},
            )
    return amount


def model_name(settings: Settings, provider: Provider) -> str:
    if provider.name == "anthropic":
        return settings.ai_model
    if provider.name == "openai":
        return getattr(getattr(provider, "settings", settings), "openai_model", "") or "openai"
    return provider.name


class Metered:
    """Wraps a Provider: budget check before each call, usage recorded after each round."""

    def __init__(
        self,
        provider: Provider,
        engine: Engine,
        settings: Settings,
        *,
        user_id: str | None,
        feature: str,
        db: Session | None = None,
    ):
        """``db``: use the caller's session (and transaction) instead of short new ones,
        for calls made while the caller holds a write transaction."""
        self.db = db
        self.inner = provider
        self.name = provider.name
        self.engine = engine
        self.settings = settings
        self.user_id = user_id
        self.feature = feature

    async def converse(
        self, system: str, turns: list[Turn], max_tokens: int, *args, **kwargs
    ) -> AsyncIterator[Event]:
        if self.inner.name != "offline":
            if self.db is not None:
                check(self.db, self.settings, self.user_id, now(), self.feature)
            else:
                with Session(self.engine) as db:
                    check(db, self.settings, self.user_id, now(), self.feature)
        async for event in self.inner.converse(system, turns, max_tokens, *args, **kwargs):
            if event.kind != "usage":
                yield event
                continue
            usage = dict(
                user_id=self.user_id,
                feature=self.feature,
                provider=self.inner.name,
                model=model_name(self.settings, self.inner),
                input_tokens=event.arguments["input_tokens"],
                output_tokens=event.arguments["output_tokens"],
                stamp=now(),
            )
            if self.db is not None:
                record(self.db, self.settings, **usage)
            else:
                with Session(self.engine) as db, db.begin():
                    record(db, self.settings, **usage)


def summary(db: Session, settings: Settings, stamp: int) -> dict:
    """Spend for the owner dashboard: today, this month, by feature, per active learner."""
    today = day_of(stamp)
    month = today[:8] + "01"
    by_feature = {
        feature: dict(calls=calls, cost_usd=round(total or 0.0, 4), tokens=int(tokens or 0))
        for feature, calls, total, tokens in db.execute(
            select(
                AIUsage.feature,
                func.count(),
                func.sum(AIUsage.cost_usd),
                func.sum(AIUsage.input_tokens + AIUsage.output_tokens),
            )
            .where(AIUsage.day >= month)
            .group_by(AIUsage.feature)
        )
    }
    learners = db.scalar(
        select(func.count(func.distinct(AIUsage.user_id))).where(
            AIUsage.day >= month, AIUsage.user_id.is_not(None)
        )
    )
    month_cost = spent(db, since_day=month)
    days = [
        dict(day=day, cost_usd=round(total or 0.0, 4))
        for day, total in db.execute(
            select(AIUsage.day, func.sum(AIUsage.cost_usd))
            .where(AIUsage.day >= month)
            .group_by(AIUsage.day)
            .order_by(AIUsage.day)
        )
    ]
    return dict(
        enabled=settings.ai_enabled,
        today_usd=round(spent(db, since_day=today), 4),
        month_usd=round(month_cost, 4),
        daily_budget_usd=settings.ai_daily_budget_usd,
        monthly_budget_usd=settings.ai_monthly_budget_usd,
        user_daily_budget_usd=settings.ai_user_daily_budget_usd,
        learners_this_month=learners or 0,
        per_learner_usd=round(month_cost / learners, 4) if learners else 0.0,
        by_feature=by_feature,
        days=days,
        prices=dict(
            input_per_mtok=settings.ai_price_input_per_mtok,
            output_per_mtok=settings.ai_price_output_per_mtok,
        ),
    )
