"""Transactional internal outbox consumer and Playground generation runner.

External consumers need their own idempotency.
"""

import asyncio
import logging

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from socrat import reminders
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


def start_jobs(engine: Engine, settings: Settings, running: set[asyncio.Task]):
    jobs.start_queued(engine, settings, running)


REMINDER_SWEEP_SECONDS = 15 * 60


async def serve(settings: Settings, engine: Engine):
    running: set[asyncio.Task] = set()
    next_reminders = 0.0
    while True:
        if (clock := asyncio.get_running_loop().time()) >= next_reminders:
            next_reminders = clock + REMINDER_SWEEP_SECONDS
            try:
                await asyncio.to_thread(reminders.sweep, engine, settings)
            except Exception:
                logging.exception("reminder_sweep_failed")
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
