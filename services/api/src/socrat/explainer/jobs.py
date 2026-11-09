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

# A large model writing a 3D film with a repair round can take several minutes.
GENERATION_SECONDS = 600
ACTIVE = ("queued", "running")
BEAT_SECONDS = 5
# A running job whose worker stopped beating (a deploy, a crash) is picked up again, at most once.
STALE_SECONDS = 30
MAX_TRIES = 2
log = logging.getLogger("socrat.explainer")


def explainer_settings(settings: Settings) -> tuple[Settings, Settings | None]:
    """Settings for the playground model, and for the 3D-only model when one is configured."""
    key = "openai_model" if settings.ai_provider == "openai" else "ai_model"
    update: dict = {
        "ai_timeout_seconds": max(settings.ai_timeout_seconds, settings.explainer_timeout_seconds)
    }
    if settings.explainer_model:
        update[key] = settings.explainer_model
    base = settings.model_copy(update=update)
    if not settings.explainer_3d_model:
        return base, None
    film: dict = {key: settings.explainer_3d_model}
    if settings.explainer_3d_price_input_per_mtok or settings.explainer_3d_price_output_per_mtok:
        film["ai_price_input_per_mtok"] = settings.explainer_3d_price_input_per_mtok
        film["ai_price_output_per_mtok"] = settings.explainer_3d_price_output_per_mtok
    return base, base.model_copy(update=film)


def may_use_3d(settings: Settings, user: User | None) -> bool:
    """3D films are admin-only while they are tested (explainer_3d_admin_only)."""
    if not settings.explainer_3d_admin_only:
        return True
    if user is None:
        return False
    emails = {e.lower() for e in settings.admin_emails}
    return (
        f"{user.issuer}|{user.subject}" in settings.admin_subjects
        or user.subject in settings.admin_subjects
        or (user.admin_email is not None and user.admin_email in emails)
    )


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
        # A job queued before the restriction, or by an account that lost admin, still gets sketches.
        if mode != "sketch" and not may_use_3d(settings, db.get(User, user_id)):
            mode = "sketch"
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
            provider_settings, film_settings = explainer_settings(settings)

            def metered(chosen):
                return budget.Metered(
                    make_provider(
                        chosen, chat_template_kwargs=settings.explainer_chat_template_kwargs
                    ),
                    engine,
                    chosen,
                    user_id=user_id,
                    feature="playground",
                )

            provider = metered(provider_settings)
            film_provider = metered(film_settings) if film_settings else None
            async for event in generator.generate(
                provider, provider_settings, prompt, language, level, mode, film_provider
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


def start_queued(engine: Engine, settings: Settings, running: set[asyncio.Task]) -> None:
    """Claim queued generations up to the concurrency limit and run each as a task."""
    while len(running) < settings.explainer_concurrent_limit and (job_id := claim(engine)):
        task = asyncio.create_task(run(engine, settings, job_id))
        running.add(task)
        task.add_done_callback(running.discard)


async def run_forever(engine: Engine, settings: Settings) -> None:
    """Run visual generations inside the API process, for setups without ``socrat.worker``.

    Without a runner a request stays queued for good and the page waits on "Getting it ready"
    forever (the bug behind "Watch it work does nothing" locally)."""
    running: set[asyncio.Task] = set()
    while True:
        try:
            start_queued(engine, settings, running)
        except Exception:
            log.exception("playground_claim_failed")
        await asyncio.sleep(2)


def fail(engine: Engine, job_id: str, code: str):
    with Session(engine) as db, db.begin():
        job = db.get(PlaygroundJob, job_id)
        if job is not None and job.status == "running":
            job.status, job.error = "failed", code[:64]
