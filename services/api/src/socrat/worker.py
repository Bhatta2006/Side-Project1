"""Transactional internal outbox consumer and Playground generation runner.

External consumers need their own idempotency.
"""

import asyncio
import logging

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from socrat import reminders
from socrat.assistant.gateway import make_provider
from socrat.config import Settings
from socrat.database import make_engine
from socrat.explainer import jobs
from socrat.models import DeliveredEvent, OutboxEvent, now


def drain_once(engine: Engine) -> int:
    with Session(engine) as db, db.begin():
        events = db.scalars(
            select(OutboxEvent)
            .where(OutboxEvent.delivered_at.is_(None))
            .order_by(OutboxEvent.created_at, OutboxEvent.id)
            .limit(100)
            .with_for_update(skip_locked=True)
        ).all()
        for event in events:
            if db.get(DeliveredEvent, event.id) is None:
                db.add(DeliveredEvent(event_id=event.id))
            event.delivered_at = now()
        return len(events)


def award_perks(engine: Engine) -> int:
    from socrat.coursegen import community

    with Session(engine) as db, db.begin():
        return len(community.sweep(db, now()))


async def maintain_courses(engine: Engine, settings: Settings) -> dict:
    from socrat.catalog.registry import default_catalog
    from socrat.coursegen import maintain

    return await maintain.sweep(engine, settings, default_catalog(), now(), make=make_provider)


def start_jobs(engine: Engine, settings: Settings, running: set[asyncio.Task]):
    while len(running) < settings.explainer_concurrent_limit and (job_id := jobs.claim(engine)):
        task = asyncio.create_task(jobs.run(engine, settings, job_id))
        running.add(task)
        task.add_done_callback(running.discard)


REMINDER_SWEEP_SECONDS = 15 * 60
MAINTENANCE_SECONDS = 6 * 3600  # a batch of link checks four times a day


async def serve(settings: Settings, engine: Engine):
    running: set[asyncio.Task] = set()
    next_reminders = 0.0
    next_maintenance = 0.0
    while True:
        if (clock := asyncio.get_running_loop().time()) >= next_reminders:
            next_reminders = clock + REMINDER_SWEEP_SECONDS
            try:
                await asyncio.to_thread(reminders.sweep, engine, settings)
            except Exception:
                logging.exception("reminder_sweep_failed")
            try:
                await asyncio.to_thread(award_perks, engine)
            except Exception:
                logging.exception("creator_perk_sweep_failed")
        if (
            settings.maintainer_enabled
            and (clock := asyncio.get_running_loop().time()) >= next_maintenance
        ):
            next_maintenance = clock + MAINTENANCE_SECONDS
            try:
                await maintain_courses(engine, settings)
            except Exception:
                logging.exception("course_maintenance_failed")
        try:
            drain_once(engine)
        except Exception:
            logging.error("outbox_batch_failed")  # No payloads, identities or credentials.
        try:
            start_jobs(engine, settings, running)
        except Exception:
            logging.exception("playground_claim_failed")
        # ponytail: 2 s polling pickup; LISTEN/NOTIFY if queue latency ever matters.
        await asyncio.sleep(2)


def main():
    settings = Settings()
    engine = make_engine(settings.database_url_value)
    try:
        asyncio.run(serve(settings, engine))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
