"""Run queued visual generations in the worker, so a closed tab or a deploy does not lose them."""

import asyncio
import json
import logging

from fastapi import HTTPException
from sqlalchemy import Engine, and_, or_, select
from sqlalchemy.orm import Session

from socrat.assistant import budget
from socrat.assistant.gateway import ProviderError, make_provider
from socrat.config import Settings
from socrat.database import record_event
from socrat.explainer import generator
from socrat.learn.routes import guard_instruction
from socrat.models import AssistantMessage, PlaygroundJob, User, now

GENERATION_SECONDS = 300
ACTIVE = ("queued", "running")
BEAT_SECONDS = 5
# A running job whose worker stopped beating (a deploy, a crash) is picked up again, at most once.
STALE_SECONDS = 30
MAX_TRIES = 2
log = logging.getLogger("socrat.explainer")


def playground_code(code: str) -> str:
    """The shared AI guardrail codes (ai_disabled, ai_budget_reached) worded for the playground."""
    return "playground_" + code if code.startswith("ai_") else code


def claim(engine: Engine) -> str | None:
    with Session(engine) as db, db.begin():
        job = db.scalars(
            select(PlaygroundJob)
            .where(
                or_(
                    PlaygroundJob.status == "queued",
                    and_(
                        PlaygroundJob.status == "running",
                        PlaygroundJob.heartbeat_at < now() - STALE_SECONDS,
                    ),
                )
            )
            .order_by(PlaygroundJob.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        ).first()
        if job is None:
            return None
        if job.tries >= MAX_TRIES:
            job.status, job.error = "failed", "playground_generation_interrupted"
            return None
        job.status, job.tries, job.heartbeat_at = "running", job.tries + 1, now()
        return job.id


def save(engine: Engine, job_id: str, **fields) -> str:
    """Record progress and a heartbeat; returns the job's status so a cancel is noticed."""
    with Session(engine) as db, db.begin():
        job = db.get(PlaygroundJob, job_id)
        if job is None:
            return "cancelled"
        if job.status == "running":
            for key, value in dict(fields, heartbeat_at=now()).items():
                setattr(job, key, value)
        return job.status


async def run(engine: Engine, settings: Settings, job_id: str):
    with Session(engine) as db:
        job = db.get(PlaygroundJob, job_id)
        assert job is not None
        user_id, thread_id = job.user_id, job.thread_id
        prompt, level, language, mode = job.prompt, job.level, job.language, job.mode or "sketch"
    main = asyncio.current_task()
    assert main is not None

    async def beat():
        while True:
            await asyncio.sleep(BEAT_SECONDS)
            if save(engine, job_id) != "running":
                main.cancel()  # cancelled by the learner
                return

    beater = asyncio.create_task(beat())
    try:
        async with asyncio.timeout(GENERATION_SECONDS):
            provider_settings = settings
            if settings.explainer_model:
                key = "openai_model" if settings.ai_provider == "openai" else "ai_model"
                provider_settings = settings.model_copy(update={key: settings.explainer_model})
            provider = budget.Metered(
                make_provider(
                    provider_settings, chat_template_kwargs=settings.explainer_chat_template_kwargs
                ),
                engine,
                provider_settings,
                user_id=user_id,
                feature="playground",
            )
            async for event in generator.generate(
                provider, provider_settings, prompt, language, level, mode
            ):
                if event["event"] == "progress":
                    progress = {
                        k: v
                        for k, v in event.items()
                        if k not in ("event", "mode") and v is not None
                    }
                    # An auto request learns its medium from the router's first event.
                    extra = {"mode": event["mode"]} if event.get("mode") else {}
                    if save(engine, job_id, progress=progress, **extra) != "running":
                        return
                    continue
                with Session(engine) as db, db.begin():
                    job = db.get(PlaygroundJob, job_id)
                    if job is None or job.status != "running":
                        return
                    learner = db.get(User, user_id)
                    if learner is None:
                        raise HTTPException(401, "authentication_required")
                    guard_instruction(db, None, learner)
                    db.add(
                        AssistantMessage(
                            id=job_id,
                            thread_id=thread_id,
                            role="assistant",
                            content=json.dumps(event["document"]),
                            provider=settings.ai_provider,
                            created_at=now(),
                        )
                    )
                    job.status = "ready"
                    record_event(db, user_id, "explainer.created", job_id)
                return
            fail(engine, job_id, "playground_generation_invalid")
    except TimeoutError:
        fail(engine, job_id, "playground_generation_timeout")
    except ProviderError as exc:
        fail(engine, job_id, playground_code(str(exc)))
    except HTTPException as exc:
        fail(engine, job_id, str(exc.detail))
    except Exception:
        log.exception("playground job failed")
        fail(engine, job_id, "playground_generation_unavailable")
    finally:
        beater.cancel()


def fail(engine: Engine, job_id: str, code: str):
    with Session(engine) as db, db.begin():
        job = db.get(PlaygroundJob, job_id)
        if job is not None and job.status == "running":
            job.status, job.error = "failed", code[:64]
